import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "enterprise_pl.db").replace("\\", "/")


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_MODE: str = "sqlite"
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey123")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,https://unified-pl.vercel.app,http://127.0.0.1:5500,http://localhost:5500,http://localhost:8080,http://127.0.0.1:8080,http://127.0.0.1:3000"
    )
    MAX_UPLOAD_SIZE_BYTES: int = 26214400  # 25 MB max upload

    # AI APIs
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Domain Contamination Configurations
    CONTAM_RETAIL: float = 0.03
    CONTAM_CORPORATE: float = 0.05
    CONTAM_INVESTMENT: float = 0.08
    CONTAM_SME: float = 0.04

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=env_path, extra="ignore")


settings = Settings()
