# unified_app.py

from typing import Optional

import gradio as gr
import nest_asyncio
import uvicorn

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.ml_service import get_ml_service


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI HR Screening Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nest_asyncio.apply()


def build_filters(
    min_age: Optional[int],
    max_age: Optional[int],
    min_experience: Optional[int],
    city: Optional[str],
    position_keywords: Optional[str],
    skills_keywords: Optional[str]
) -> dict:
    filters = {}

    if min_age is not None:
        filters["min_age"] = min_age

    if max_age is not None:
        filters["max_age"] = max_age

    if min_experience is not None:
        filters["min_experience"] = min_experience

    if city:
        filters["city"] = city.strip()

    if position_keywords:
        filters["position_keywords"] = [
            keyword.strip()
            for keyword in position_keywords.split(",")
            if keyword.strip()
        ]

    if skills_keywords:
        filters["skills_keywords"] = [
            keyword.strip()
            for keyword in skills_keywords.split(",")
            if keyword.strip()
        ]

    return filters


async def process_matching(
    vacancy_text: str,
    resumes_text: str,
    top_k: int,
    min_score: float,
    filters: Optional[dict] = None
):
    ml_service = get_ml_service()

    results = await ml_service.match_resumes_to_vacancy(
        vacancy_text=vacancy_text,
        resumes_text=resumes_text,
        top_k=top_k,
        min_score=min_score,
        manual_filters=filters or None
    )

    return results


# =========================================================
# API
# =========================================================

@app.post("/api/v1/match/advanced")
async def match_advanced(
    vacancy_file: UploadFile = File(...),
    resume_file: UploadFile = File(...),

    top_k: int = Form(20),
    min_score: float = Form(15.0),

    min_age: Optional[int] = Form(None),
    max_age: Optional[int] = Form(None),
    min_experience: Optional[int] = Form(None),

    city: Optional[str] = Form(None),
    position_keywords: Optional[str] = Form(None),
    skills_keywords: Optional[str] = Form(None)
):
    vacancy_content = await vacancy_file.read()
    resumes_content = await resume_file.read()

    vacancy_text = vacancy_content.decode("utf-8")
    resumes_text = resumes_content.decode("utf-8")

    filters = build_filters(
        min_age=min_age,
        max_age=max_age,
        min_experience=min_experience,
        city=city,
        position_keywords=position_keywords,
        skills_keywords=skills_keywords
    )

    candidates = await process_matching(
        vacancy_text=vacancy_text,
        resumes_text=resumes_text,
        top_k=top_k,
        min_score=min_score,
        filters=filters
    )

    return {
        "status": "success",
        "count": len(candidates),
        "candidates": candidates
    }


# =========================================================
# GRADIO UI
# =========================================================

async def run_gradio_matching(
    vacancy_file,
    resumes_file,
    top_k,
    min_score,
    min_age,
    max_age,
    min_experience,
    city,
    position_keywords,
    skills_keywords
):
    if vacancy_file is None or resumes_file is None:
        return "Загрузите файлы вакансии и резюме"

    with open(vacancy_file.name, "r", encoding="utf-8") as f:
        vacancy_text = f.read()

    with open(resumes_file.name, "r", encoding="utf-8") as f:
        resumes_text = f.read()

    filters = build_filters(
        min_age=min_age,
        max_age=max_age,
        min_experience=min_experience,
        city=city,
        position_keywords=position_keywords,
        skills_keywords=skills_keywords
    )

    results = await process_matching(
        vacancy_text=vacancy_text,
        resumes_text=resumes_text,
        top_k=top_k,
        min_score=min_score,
        filters=filters
    )

    if not results:
        return "Подходящие кандидаты не найдены"

    output = []

    for index, candidate in enumerate(results, start=1):
        output.append(
            f"""
Кандидат #{index}

Имя: {candidate.get("name", "Не указано")}
Score: {candidate.get("score", 0)}

Позиция: {candidate.get("position", "Не указано")}
Опыт: {candidate.get("experience", "Не указано")}
Город: {candidate.get("city", "Не указано")}
"""
        )

    return "\n".join(output)


def create_interface():
    with gr.Blocks(
        title="AI HR Скринер",
        theme=gr.themes.Soft()
    ) as demo:

        gr.Markdown("# AI HR Скринер")
        gr.Markdown("Система интеллектуального подбора кандидатов")

        with gr.Row():
            vacancy_file = gr.File(
                label="Файл вакансии",
                file_types=[".txt"]
            )

            resumes_file = gr.File(
                label="Файл резюме",
                file_types=[".txt"]
            )

        with gr.Row():
            top_k = gr.Slider(
                minimum=1,
                maximum=100,
                value=20,
                step=1,
                label="Количество кандидатов"
            )

            min_score = gr.Slider(
                minimum=0,
                maximum=100,
                value=15,
                step=1,
                label="Минимальный score"
            )

        with gr.Accordion("Дополнительные фильтры", open=False):

            with gr.Row():
                min_age = gr.Number(
                    label="Минимальный возраст",
                    precision=0
                )

                max_age = gr.Number(
                    label="Максимальный возраст",
                    precision=0
                )

                min_experience = gr.Number(
                    label="Минимальный опыт",
                    precision=0
                )

            city = gr.Textbox(
                label="Город"
            )

            position_keywords = gr.Textbox(
                label="Ключевые слова должности",
                placeholder="Python, Backend, ML"
            )

            skills_keywords = gr.Textbox(
                label="Ключевые навыки",
                placeholder="FastAPI, Docker, PostgreSQL"
            )

        run_button = gr.Button(
            "Запустить анализ",
            variant="primary"
        )

        result_output = gr.Textbox(
            label="Результаты",
            lines=25
        )

        run_button.click(
            fn=run_gradio_matching,
            inputs=[
                vacancy_file,
                resumes_file,
                top_k,
                min_score,
                min_age,
                max_age,
                min_experience,
                city,
                position_keywords,
                skills_keywords
            ],
            outputs=result_output
        )

    return demo


gradio_app = create_interface()

app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/"
)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    uvicorn.run(
        "unified_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
