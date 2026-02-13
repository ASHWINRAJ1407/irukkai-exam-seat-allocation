"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam-seat-allocation-secret-key-2024')
    
    # Updated to use PostgreSQL as the default fallback
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'postgresql+psycopg2://irukkai_user:irukkai_password@localhost:5432/irukkai'
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    DEFAULT_HALL_CAPACITY = 45
    STUDENTS_PER_BENCH = 3
    BENCHES_PER_HALL = 15