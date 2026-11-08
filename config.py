from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "JIRO AI"
    database_url: str = "sqlite:///./data/jiro.db"
    engine: str = "transformers"
    hf_model_id: str = "Qwen/Qwen2.5-0.5B-Instruct"
    device: str = "auto"
    max_new_tokens: int = 384
    temperature: float = 0.7
    top_p: float = 0.9
    repetition_penalty: float = 1.08
    max_history_messages: int = 16
    max_upload_mb: int = 10
    upload_dir: str = "./data/uploads"
    gguf_model_path: str = ""
    n_ctx: int = 2048
    n_threads: int = 4
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
