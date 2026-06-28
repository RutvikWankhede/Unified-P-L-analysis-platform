from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost/unified_pl"

    # Security
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://unified-pl.vercel.app"

    # AI APIs
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Domain Contamination Configurations
    CONTAM_RETAIL: float = 0.03
    CONTAM_CORPORATE: float = 0.05
    CONTAM_INVESTMENT: float = 0.08
    CONTAM_SME: float = 0.04

    class Config:
        env_file = ".env"


settings = Settings()
