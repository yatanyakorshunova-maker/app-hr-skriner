# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class VacancyModel(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    text_preview = Column(Text)  # Первые 500 символов для отображения
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class MatchResultModel(Base):
    __tablename__ = "match_results"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"), nullable=False)
    
    candidate_name = Column(String(255), nullable=False)
    match_score = Column(Float, nullable=False)
    rerank_score = Column(Float, nullable=True)
    
    # Данные кандидата (для отображения без парсинга заново)
    age = Column(String(50), nullable=True)
    city = Column(String(255), nullable=True)
    desired_position = Column(String(255), nullable=True)
    experience = Column(String(50), nullable=True)
    skills = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)