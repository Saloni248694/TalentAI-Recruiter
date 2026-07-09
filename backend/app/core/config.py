from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "dev-secret-change-me"
    CLAUDE_API_KEY: str = ""
    # ... your other fields ...
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REDIS_URL: str = "redis://localhost:6379"
    APP_NAME: str = "TalentAI Recruiter"
    UPLOAD_DIR: str = "uploads/resumes"

    class Config:
        env_file = ".env"

settings = Settings()