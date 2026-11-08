# JIRO AI — Intelligence Without Boundaries

Self-hosted chat application with a local open-source model. No OpenAI/Gemini/Claude API key is required.

## Important hardware note

This repository contains the application code, **not model weights**. On an Android phone such as a Samsung Galaxy A15, running a full PyTorch + Transformers stack directly inside Termux is not a reliable assumption: PyTorch wheels and memory requirements vary by Android/CPU build. The recommended phone workflow is:

1. Run the web UI on the phone.
2. Run the inference backend on a Linux PC/server, or use the optional `llama.cpp` backend on a compatible Termux build.
3. Use a small quantized GGUF model for phone inference. The default model suggestion is Qwen2.5-0.5B-Instruct in GGUF Q4, subject to available RAM and model license.

The primary `transformers` engine uses PyTorch. An optional `llama-cpp-python` engine is included for lower-memory CPU deployments. It is not a claim that the phone has been benchmarked.

## Features implemented

- Chat UI with streaming responses (SSE)
- Persistent conversations and messages (SQLite / SQLAlchemy)
- Create, list, rename, delete conversations
- Stop generation (client disconnect cancels stream where supported)
- Copy response, Markdown rendering, code highlighting
- Model status/load/unload endpoints
- Runtime metrics (CPU/RAM; GPU metrics when supported)
- TXT/PDF/DOCX upload and basic document text extraction
- Local document context passed into chat (simple bounded context; not a full vector RAG index)
- Configurable model backend: `transformers` or `llama_cpp`
- Docker setup for Linux deployments

Not included yet: production authentication/multi-user isolation, a full vector database/RAG pipeline, vision model inference, actual LoRA training UI/worker, and robust distributed job scheduling. These are intentionally not represented as completed features.

## Quick start (Linux / PC)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`. The first model load downloads model files from Hugging Face if `HF_MODEL_ID` is configured and internet is available. Review the model card/license first.

### PyTorch model (recommended on Linux)

Set in `.env`:

```env
ENGINE=transformers
HF_MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
DEVICE=auto
```

The model is downloaded on first load. This is not a quantized model by default. For low RAM, use a compatible quantized runtime instead.

### Lower-memory GGUF runtime

Install a compatible `llama-cpp-python` wheel/build for your platform, set:

```env
ENGINE=llama_cpp
GGUF_MODEL_PATH=/absolute/path/to/model-q4_k_m.gguf
N_CTX=2048
N_THREADS=4
```

You must obtain the GGUF file yourself from a source whose license permits your use. The backend will not silently download a model.

## Android / Termux

Termux is not the same as a standard Linux distribution. Do not assume `pip install torch` will work. For a phone-only experiment, install Termux packages and try the optional llama.cpp path only if a compatible build is available:

```bash
pkg update && pkg upgrade
pkg install python clang cmake make git
```

Then install the Python dependencies that are available for your device. `llama-cpp-python` may require a native compilation and can fail due to memory/toolchain limits. If that happens, use a PC/Linux host for inference and open the JIRO AI web UI from your phone.

## Docker (Linux)

```bash
docker compose up --build
```

The container persists SQLite data in `./data`. For GPU acceleration, configure a CUDA-enabled PyTorch image and NVIDIA Container Toolkit on the host; the default Dockerfile is CPU-oriented.

## API

- `GET /api/health`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{id}`
- `PATCH /api/conversations/{id}`
- `DELETE /api/conversations/{id}`
- `POST /api/chat/stream` (SSE)
- `GET /api/models`
- `POST /api/models/load`
- `POST /api/models/unload`
- `GET /api/system/status`
- `GET /api/system/metrics`
- `POST /api/documents/upload`

## Safety

The app binds to `127.0.0.1` by default in the documented local setup. If you expose it to a network, add authentication, HTTPS, firewall rules, and per-user data isolation before using it with private data. Do not expose the unauthenticated API directly to the public internet.
