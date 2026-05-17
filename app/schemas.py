# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List

class FilterSettings(BaseModel):
    """
    Настройки фильтров для пользователя.
    Логика: поле = None → фильтр ВЫКЛЮЧЕН, поле = значение → фильтр ВКЛЮЧЁН.
    """
    # === Индивидуальные фильтры ===
    min_age: Optional[int] = Field(None, ge=16, le=70, description="Мин. возраст (null = выкл)")
    max_age: Optional[int] = Field(None, ge=16, le=70, description="Макс. возраст (null = выкл)")
    min_experience: Optional[int] = Field(None, ge=0, le=50, description="Мин. опыт в годах (null = выкл)")
    city: Optional[str] = Field(None, description="Город (null = не фильтровать)")
    
    # Ключевые слова (None или пустой список = фильтр выкл)
    position_keywords: Optional[List[str]] = Field(default=None, description="Должности (null/[] = выкл)")
    skills_keywords: Optional[List[str]] = Field(default=None, description="Навыки (null/[] = выкл)")
    
    # === Параметры ранжирования (всегда применяются) ===
    min_score: float = Field(15.0, ge=0.0, le=100.0, description="Мин. порог совпадения %")
    top_k: int = Field(10, ge=1, le=100, description="Сколько лучших кандидатов вернуть")
    
    # === Дополнительные настройки ===
    use_auto_filters: bool = Field(True, description="Авто-извлечение фильтров из вакансии")
    use_reranking: bool = Field(True, description="Включить reranking")
    it_threshold: float = Field(6.0, ge=0.0, le=20.0, description="Порог IT-кандидата")


class CandidateMatch(BaseModel):
    """Модель кандидата в ответе API"""
    name: str
    age: Optional[str] = None
    city: Optional[str] = None
    desired_position: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[str] = None
    education: Optional[str] = None
    salary: Optional[str] = None
    match_score: float
    rerank_score_percent: Optional[float] = None


class MatchResponse(BaseModel):
    """Ответ эндпоинта /match"""
    status: str
    message: str
    resumes_processed: int
    candidates_found: int
    filters_applied: dict
    top_candidates: List[CandidateMatch]