import json, os, uuid, time
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import psutil
from database import Base, engine, get_db
from db_models import Conversation, Message
from schemas import ConversationCreate, ConversationRename, ChatRequest
from config import settings
from model_manager import manager
from inference import generate
from documents import extract_text

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name}

@app.get("/api/conversations")
def list_conversations(db: Session = Depends(get_db)):
    rows = db.scalars(select(Conversation).order_by(desc(Conversation.updated_at))).all()
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in rows]

@app.post("/api/conversations")
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    c = Conversation(id=str(uuid.uuid4()), title=payload.title.strip() or "New chat")
    db.add(c); db.commit()
    return {"id": c.id, "title": c.title}

@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c: raise HTTPException(404, "Conversation not found")
    return {"id": c.id, "title": c.title, "messages": [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in c.messages
    ]}

@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, payload: ConversationRename, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c: raise HTTPException(404, "Conversation not found")
    c.title = payload.title.strip(); db.commit()
    return {"id": c.id, "title": c.title}

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c: raise HTTPException(404, "Conversation not found")
    db.delete(c); db.commit()
    return {"deleted": True}

@app.get("/api/models")
def models():
    return {"active": manager.status(), "available": [
        {"id": settings.hf_model_id, "engine": settings.engine, "source": "local inference"},
    ]}

@app.post("/api/models/load")
def load_model():
    try: return manager.load()
    except Exception as exc: raise HTTPException(503, str(exc))

@app.post("/api/models/unload")
def unload_model():
    return manager.unload()

@app.get("/api/system/status")
def system_status():
    try:
        import torch
        cuda = torch.cuda.is_available()
    except Exception:
        cuda = False
    return {"engine": settings.engine, "model": manager.status(), "cuda_available": cuda}

@app.get("/api/system/metrics")
def metrics():
    mem = psutil.virtual_memory()
    return {"cpu_percent": psutil.cpu_percent(interval=0.15),
            "ram_total_mb": round(mem.total / 1048576),
            "ram_used_mb": round(mem.used / 1048576),
            "ram_percent": mem.percent,
            "process_rss_mb": round(psutil.Process().memory_info().rss / 1048576)}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".txt", ".pdf", ".docx"}:
        raise HTTPException(400, "Hanya TXT, PDF, dan DOCX yang didukung.")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Ukuran file melewati batas.")
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    target = Path(settings.upload_dir) / safe_name
    target.write_bytes(data)
    try:
        content = extract_text(str(target), suffix)[:30000]
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(400, f"Gagal membaca dokumen: {exc}")
    return {"document_id": safe_name, "filename": file.filename, "text": content}

@app.post("/api/chat/stream")
def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    c = db.get(Conversation, payload.conversation_id)
    if not c: raise HTTPException(404, "Conversation not found")
    user_msg = Message(id=str(uuid.uuid4()), conversation_id=c.id, role="user", content=payload.message)
    db.add(user_msg)
    if c.title == "New chat":
        c.title = payload.message[:48].strip() or "New chat"
    db.commit()
    history = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)).all()
    prompt = [{"role": "system", "content": payload.system_prompt}]
    prompt += [{"role": m.role, "content": m.content} for m in history[-settings.max_history_messages:]]
    def event_stream():
        full = ""
        try:
            yield "event: start\ndata: {}\n\n"
            for chunk in generate(prompt, payload.temperature, payload.top_p, payload.max_new_tokens):
                full += chunk
                yield "event: token\ndata: " + json.dumps({"text": chunk}, ensure_ascii=False) + "\n\n"
            # Separate short-lived DB session because streaming outlives request handling.
            from database import SessionLocal
            s = SessionLocal()
            try:
                s.add(Message(id=str(uuid.uuid4()), conversation_id=c.id, role="assistant", content=full))
                s.commit()
            finally: s.close()
            yield "event: done\ndata: {}\n\n"
        except Exception as exc:
            yield "event: error\ndata: " + json.dumps({"message": str(exc)}) + "\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# Serve the frontend as static files. Mounted last, after every /api/* route
# above, so it only catches paths those routes don't already handle.
_frontend_dir = Path(__file__).resolve().parent / "static"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
