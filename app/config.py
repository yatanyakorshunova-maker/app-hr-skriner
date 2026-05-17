# app/config.py
import os

class Settings:
    # Для macOS: три слэша /// = текущий пользователь без пароля
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg:///resume_db"  # ← Исправлено!
    )
    PROJECT_NAME: str = "Resume Matcher API"
    VERSION: str = "1.0.0"

settings = Settings()