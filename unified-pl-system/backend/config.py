from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dev.db"  # SQLite for dev by default
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    OPENAI_API_KEY: str = ""

    # Domain Contamination Configurations
    CONTAM_RETAIL: float = 0.03
    CONTAM_CORPORATE: float = 0.05
    CONTAM_INVESTMENT: float = 0.08
    CONTAM_SME: float = 0.04

    class Config:
        env_file = ".env"

settings = Settings()
