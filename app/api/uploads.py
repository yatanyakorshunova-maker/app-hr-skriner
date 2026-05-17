from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml_service import get_ml_service
from app.db import get_db
from app.models import VacancyModel, MatchResultModel

router = APIRouter(prefix="/api/v1", tags=["Matching"])

class CandidateMatch(BaseModel):
    name: str
    age: Optional[str] = None
    city: Optional[str] = None
    desired_position: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[str] = None
    match_score: float
    rerank_score_percent: Optional[float] = None

class MatchResponse(BaseModel):
    status: str
    message: str
    candidates_count: int
    vacancy_id: int
    top_candidates: List[CandidateMatch]

class HistoryItem(BaseModel):
    id: int
    filename: str
    candidates_count: int
    created_at: str

class HistoryResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[HistoryItem]

@router.post("/match/simple", response_model=MatchResponse)
async def match_simple(
    vacancy_file: UploadFile = File(..., description="Файл вакансии .txt"),
    resume_file: UploadFile = File(..., description="Файл с резюме .txt"),
    top_k: int = Form(10, ge=1, le=100),
    min_score: float = Form(15.0, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db)
):
    vacancy_text = (await vacancy_file.read()).decode("utf-8", errors="ignore")
    resume_text = (await resume_file.read()).decode("utf-8", errors="ignore")
    
    ml = get_ml_service()
    results = await ml.match_resumes_to_vacancy(
        vacancy_text=vacancy_text,
        resumes_text=resume_text,
        top_k=top_k,
        min_score=min_score,
        use_auto_filters=True,
        manual_filters=None
    )
    
    # Сохраняем вакансию в БД
    db_vacancy = VacancyModel(
        filename=vacancy_file.filename,
        text_preview=vacancy_text[:500]
    )
    db.add(db_vacancy)
    await db.flush()  # Получаем ID
    
    # Сохраняем результаты матчинга
    match_records = [
        MatchResultModel(
            vacancy_id=db_vacancy.id,
            candidate_name=c['name'],
            match_score=c['match_score'],
            rerank_score=c.get('rerank_score_percent'),
            age=c.get('age'),
            city=c.get('city'),
            desired_position=c.get('desired_position'),
            experience=c.get('experience'),
            skills=c.get('skills')
        ) for c in results
    ]
    db.add_all(match_records)
    await db.commit()
    
    candidates = [
        CandidateMatch(
            name=c['name'],
            age=c.get('age'),
            city=c.get('city'),
            desired_position=c.get('desired_position'),
            experience=c.get('experience'),
            skills=c.get('skills'),
            match_score=c['match_score'],
            rerank_score_percent=c.get('rerank_score_percent')
        ) for c in results
    ]
    
    return MatchResponse(
        status="success",
        message=f"Найдено {len(candidates)} кандидатов. Сохранено в БД.",
        candidates_count=len(candidates),
        vacancy_id=db_vacancy.id,
        top_candidates=candidates
    )

@router.post("/match/advanced", response_model=MatchResponse)
async def match_advanced(
    vacancy_file: UploadFile = File(..., description="Файл вакансии"),
    resume_file: UploadFile = File(..., description="Файл с резюме"),
    top_k: int = Form(10, ge=1, le=100),
    min_score: float = Form(15.0, ge=0.0, le=100.0),
    min_age: Optional[int] = Form(None),
    max_age: Optional[int] = Form(None),
    min_experience: Optional[int] = Form(None),
    city: Optional[str] = Form(None),
    position_keywords: Optional[str] = Form(None),
    skills_keywords: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    vacancy_text = (await vacancy_file.read()).decode("utf-8", errors="ignore")
    resume_text = (await resume_file.read()).decode("utf-8", errors="ignore")
    
    manual_filters = {
        'min_age': min_age,
        'max_age': max_age,
        'min_experience': min_experience,
        'city': city,
        'position_keywords': [kw.strip() for kw in position_keywords.split(',')] if position_keywords else [],
        'skills_keywords': [kw.strip() for kw in skills_keywords.split(',')] if skills_keywords else []
    }
    
    ml = get_ml_service()
    results = await ml.match_resumes_to_vacancy(
        vacancy_text=vacancy_text,
        resumes_text=resume_text,
        top_k=top_k,
        min_score=min_score,
        use_auto_filters=True,  # Пустые поля берутся из вакансии
        manual_filters=manual_filters
    )
    
    # Сохраняем в БД
    db_vacancy = VacancyModel(
        filename=vacancy_file.filename,
        text_preview=vacancy_text[:500]
    )
    db.add(db_vacancy)
    await db.flush()
    
    match_records = [
        MatchResultModel(
            vacancy_id=db_vacancy.id,
            candidate_name=c['name'],
            match_score=c['match_score'],
            rerank_score=c.get('rerank_score_percent'),
            age=c.get('age'),
            city=c.get('city'),
            desired_position=c.get('desired_position'),
            experience=c.get('experience'),
            skills=c.get('skills')
        ) for c in results
    ]
    db.add_all(match_records)
    await db.commit()
    
    candidates = [
        CandidateMatch(
            name=c['name'],
            age=c.get('age'),
            city=c.get('city'),
            desired_position=c.get('desired_position'),
            experience=c.get('experience'),
            skills=c.get('skills'),
            match_score=c['match_score'],
            rerank_score_percent=c.get('rerank_score_percent')
        ) for c in results
    ]
    
    return MatchResponse(
        status="success",
        message=f"Найдено {len(candidates)} кандидатов. Сохранено в БД.",
        candidates_count=len(candidates),
        vacancy_id=db_vacancy.id,
        top_candidates=candidates
    )

@router.get("/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю поисков с пагинацией"""
    offset = (page - 1) * limit
    
    # Подсчёт общего количества
    count_stmt = select(func.count(VacancyModel.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # Получаем вакансии с количеством кандидатов
    stmt = (
        select(
            VacancyModel.id,
            VacancyModel.filename,
            VacancyModel.created_at,
            func.count(MatchResultModel.id).label('candidates_count')
        )
        .outerjoin(MatchResultModel, VacancyModel.id == MatchResultModel.vacancy_id)
        .group_by(VacancyModel.id)
        .order_by(VacancyModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    vacancies = result.all()
    
    items = [
        HistoryItem(
            id=v.id,
            filename=v.filename,
            candidates_count=v.candidates_count,
            created_at=v.created_at.isoformat() if v.created_at else ""
        ) for v in vacancies
    ]
    
    return HistoryResponse(
        total=total,
        page=page,
        limit=limit,
        items=items
    )

@router.get("/history/{vacancy_id}", response_model=MatchResponse)
async def get_vacancy_results(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить результаты конкретного поиска"""
    # Проверяем существование вакансии
    vacancy_stmt = select(VacancyModel).where(VacancyModel.id == vacancy_id)
    vacancy_result = await db.execute(vacancy_stmt)
    vacancy = vacancy_result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")
    
    # Получаем результаты матчинга
    results_stmt = (
        select(MatchResultModel)
        .where(MatchResultModel.vacancy_id == vacancy_id)
        .order_by(MatchResultModel.match_score.desc())
    )
    results_result = await db.execute(results_stmt)
    results = results_result.scalars().all()
    
    candidates = [
        CandidateMatch(
            name=r.candidate_name,
            age=r.age,
            city=r.city,
            desired_position=r.desired_position,
            experience=r.experience,
            skills=r.skills,
            match_score=r.match_score,
            rerank_score_percent=r.rerank_score
        ) for r in results
    ]
    
    return MatchResponse(
        status="success",
        message=f"Результаты для вакансии {vacancy.filename}",
        candidates_count=len(candidates),
        vacancy_id=vacancy_id,
        top_candidates=candidates
    )