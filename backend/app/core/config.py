from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GEMINI_API_KEY: str = ""
    APP_NAME: str = "TalentAI Recruiter"
    UPLOAD_DIR: str = "uploads/resumes"

    class Config:
        env_file = ".env"

settings = Settings()