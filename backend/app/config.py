import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TalkBuddy AI English Coach"
    API_V1_STR: str = "/api"

    # Auth Settings
    SECRET_KEY: str = "supersecretkeychangeinproduction1234567890!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 Days

    # Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "talkbuddy"
    DB_URL: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_URL:
            return self.DB_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # AI Model Settings (Ollama fallback)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    
    # LLM Service API Settings (for cloud deployments like Hugging Face Spaces)
    LLM_PROVIDER: str = "ollama"  # options: ollama, openai
    LLM_API_URL: str | None = None  # e.g., https://api.groq.com/openai/v1/chat/completions
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "llama3.1"   # e.g., llama3.1 (Ollama) or llama-3.1-8b-instant (Groq)

    WHISPER_MODEL: str = "base"  # options: tiny, base, small, medium
    WHISPER_DEVICE: str = "cpu"  # cpu or cuda

    # Piper TTS Settings
    PIPER_VOICE: str = "en_US-lessac-medium"

    # Directories
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def MODELS_DIR(self) -> str:
        path = os.path.join(self.BASE_DIR, "models")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def PIPER_BIN_DIR(self) -> str:
        path = os.path.join(self.BASE_DIR, "piper_bin")
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def TEMP_AUDIO_DIR(self) -> str:
        path = os.path.join(self.BASE_DIR, "temp_audio")
        os.makedirs(path, exist_ok=True)
        return path

    # Use SettingsConfigDict instead of inner Config class (pydantic v2)
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
