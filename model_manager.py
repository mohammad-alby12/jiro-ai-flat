import threading
from typing import Optional
from config import settings

class ModelManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.model = None
        self.tokenizer = None
        self.runtime = None
        self.loaded = False
        self.error: Optional[str] = None
        self.model_name = settings.hf_model_id

    def load(self):
        with self.lock:
            if self.loaded:
                return self.status()
            try:
                if settings.engine == "llama_cpp":
                    if not settings.gguf_model_path:
                        raise RuntimeError("GGUF_MODEL_PATH belum diatur.")
                    from llama_cpp import Llama
                    self.runtime = Llama(
                        model_path=settings.gguf_model_path,
                        n_ctx=settings.n_ctx,
                        n_threads=settings.n_threads,
                        verbose=False,
                    )
                    self.model_name = settings.gguf_model_path
                else:
                    import torch
                    from transformers import AutoTokenizer, AutoModelForCausalLM
                    device = settings.device
                    if device == "auto":
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    dtype = torch.float16 if device == "cuda" else torch.float32
                    self.tokenizer = AutoTokenizer.from_pretrained(settings.hf_model_id)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        settings.hf_model_id,
                        torch_dtype=dtype,
                        low_cpu_mem_usage=True,
                    )
                    self.model.to(device)
                    self.model.eval()
                    self.runtime = {"device": device}
                    self.model_name = settings.hf_model_id
                self.loaded = True
                self.error = None
            except Exception as exc:
                self.loaded = False
                self.error = f"{type(exc).__name__}: {exc}"
                self.model = self.tokenizer = self.runtime = None
                raise
            return self.status()

    def unload(self):
        with self.lock:
            self.model = self.tokenizer = self.runtime = None
            self.loaded = False
            try:
                import torch, gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            return self.status()

    def status(self):
        return {
            "engine": settings.engine,
            "loaded": self.loaded,
            "model": self.model_name,
            "error": self.error,
        }

manager = ModelManager()
