import os
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_MODE: str = "sqlite"
    DATABASE_URL: str = "sqlite:///./enterprise_pl.db"

    # Security
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,https://unified-pl.vercel.app,http://127.0.0.1:5500,http://localhost:5500,http://localhost:8080,http://127.0.0.1:8080,http://127.0.0.1:3000"
    )

    # AI APIs
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Domain Contamination Configurations
    CONTAM_RETAIL: float = 0.03
    CONTAM_CORPORATE: float = 0.05
    CONTAM_INVESTMENT: float = 0.08
    CONTAM_SME: float = 0.04

    model_config = SettingsConfigDict(env_file=env_path, extra="ignore")


settings = Settings()
