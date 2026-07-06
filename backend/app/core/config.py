from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CLAUDE_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379"
    APP_NAME: str = "TalentAI Recruiter"
    UPLOAD_DIR: str = "uploads/resumes"

    class Config:
        env_file = ".env"

settings = Settings()