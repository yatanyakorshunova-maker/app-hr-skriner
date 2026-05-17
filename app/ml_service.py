import os
import sys
import re
import torch
import numpy as np
import asyncio
from scipy.special import softmax
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer, CrossEncoder

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from x_russian_cities import is_valid_russian_city, normalize_city
from x_it_keywords import is_it_candidate

class MLService:
    _instance: Optional["MLService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        print("🔄 Загрузка ML-моделей...")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"   → Устройство: {device}")
        
        self.model = SentenceTransformer("ai-forever/sbert_large_nlu_ru")
        self.reranker = CrossEncoder(
            "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
            max_length=512,
            device=device
        )
        print("✅ Модели загружены")

    def parse_resume_text(self, content: str) -> List[Dict]:
        blocks = re.split(r'(=== Резюме кандидата №\d+ ===)', content)
        resumes = []
        for i in range(1, len(blocks), 2):
            block = blocks[i+1] if i+1 < len(blocks) else ""
            resume = {
                'name': '', 'age': None, 'experience': None, 'city': '',
                'desired_position': '', 'skills': '', 'education': '',
                'salary': '', 'last_job': '', 'comment': ''
            }
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            for line in lines:
                if line.startswith('Имя:'): resume['name'] = line[4:].strip()
                elif line.startswith('Возраст:'): resume['age'] = line[8:].strip()
                elif line.startswith('Город:'): resume['city'] = line[6:].strip()
                elif line.startswith('Желаемая должность:'): resume['desired_position'] = line[19:].strip()
                elif line.startswith('Опыт') and ':' in line: resume['experience'] = line.split(':', 1)[1].strip()
                elif line.startswith('Навыки:'): resume['skills'] = line[7:].strip()
                elif line.startswith('Образование:'): resume['education'] = line[12:].strip()
                elif line.startswith('Ожидаемая зарплата:'): resume['salary'] = line[19:].strip()
                elif line.startswith('Последнее место работы:'): resume['last_job'] = line[24:].strip()
                elif line.startswith('Комментарий:'): resume['comment'] = line[12:].strip()
            if resume['name']:
                resumes.append(resume)
        return resumes

    def build_resume_text(self, resume: Dict) -> str:
        parts = []
        if resume.get('name'): parts.append(f"Имя: {resume['name'].strip()}")
        if resume.get('age'): parts.append(f"Возраст: {resume['age']}")
        if resume.get('city'): parts.append(f"Город: {resume['city'].strip()}")
        if resume.get('desired_position'): parts.append(f"Желаемая должность: {resume['desired_position'].strip()}")
        if resume.get('experience'): parts.append(f"Опыт работы: {resume['experience']} лет")
        if resume.get('skills'): parts.append(f"Навыки: {resume['skills'].strip()}")
        if resume.get('education'): parts.append(f"Образование: {resume['education'].strip()}")
        return "\n".join(parts).strip()

    def extract_age(self, text: str) -> Optional[int]:
        if not text: return None
        text_str = str(text).strip().lower()
        if text_str in ['неизвестен', 'unknown', '-', '', 'нет']: return None
        matches = re.findall(r'\b(\d{1,2})\b', text_str)
        for m in matches:
            age = int(m)
            if 16 <= age <= 70: return age
        return None

    def extract_experience(self, text: str) -> Optional[int]:
        if not text: return None
        text_str = str(text).strip().lower()
        if text_str in ['неизвестен', 'unknown', 'нет', '-', '', '0']: return None
        matches = re.findall(r'\b(\d{1,2})\b', text_str)
        for m in matches:
            exp = int(m)
            if 0 <= exp <= 50: return exp
        return None

    def is_valid_name(self, name: str) -> bool:
        if not name or len(name) < 5: return False
        if any(w in name.lower() for w in ['test@mail.ru', 'неизвестный', 'unknown']): return False
        words = name.split()
        if len(words) < 2 or len(words) > 4: return False
        for word in words:
            if not re.match(r'^[А-ЯЁ][а-яё\-]+$', word): return False
        return True

    def extract_auto_filters(self, vacancy_text: str) -> dict:
        text = vacancy_text.lower()
        filters = {
            'min_age': None, 'max_age': None, 'min_experience': None, 
            'city': None, 'position_keywords': [], 'skills_keywords': []
        }
        
        age_match = re.findall(r'возраст[а-я\s]*(\d{1,2})\s*[-–—]\s*(\d{1,2})', text)
        if age_match: 
            filters['min_age'], filters['max_age'] = int(age_match[0][0]), int(age_match[0][1])
        
        exp_match = re.findall(r'(?:опыт|стаж)[а-я\s]*(\d{1,2})\s*(?:год|лет|года)', text)
        if exp_match: 
            filters['min_experience'] = int(exp_match[0])
        
        for kw in ['data scientist', 'ml engineer', 'backend', 'frontend', 'python', 'sql', 'docker']:
            if kw in text: 
                (filters['position_keywords'] if kw in ['data scientist', 'ml engineer', 'backend', 'frontend'] 
                 else filters['skills_keywords']).append(kw.title())
        
        return filters

    def apply_hr_filters(self, resume: dict, filters: dict) -> bool:
        age = resume.get('parsed_age')
        exp = resume.get('parsed_experience')
        position = resume.get('desired_position', '').lower()
        skills = resume.get('skills', '').lower()
        city = resume.get('city', '').lower()
        
        if filters.get('min_age') and age and age < filters['min_age']: return False
        if filters.get('max_age') and age and age > filters['max_age']: return False
        if filters.get('min_experience') and exp and exp < filters['min_experience']: return False
        if filters.get('city') and city and filters['city'].lower() not in normalize_city(city): return False
        if filters.get('position_keywords') and not any(kw.lower() in position for kw in filters['position_keywords']): return False
        if filters.get('skills_keywords') and not any(kw.lower() in skills for kw in filters['skills_keywords']): return False
        
        return True

    async def match_resumes_to_vacancy(
        self, vacancy_text: str, resumes_text: str, top_k: int, min_score: float,
        use_auto_filters: bool = True, manual_filters: Optional[dict] = None,
        it_threshold: float = 2.0
    ) -> List[Dict]:
        resumes = self.parse_resume_text(resumes_text)
        if not resumes: return []
        
        print(f"Всего резюме: {len(resumes)}")
        
        active_filters = {}
        if use_auto_filters:
            auto = self.extract_auto_filters(vacancy_text)
            active_filters.update({k: v for k, v in auto.items() if v})
        
        if manual_filters:
            for k, v in manual_filters.items():
                if v: active_filters[k] = v
        
        print(f"Активные фильтры: {active_filters}")
        
        valid_resumes = []
        for r in resumes:
            if not self.is_valid_name(r.get('name', '')): continue
            age = self.extract_age(r.get('age'))
            if age is None: continue
            r['parsed_age'] = age
            exp = self.extract_experience(r.get('experience'))
            if exp is None: continue
            r['parsed_experience'] = exp
            if not is_valid_russian_city(r.get('city', '')): continue
            is_it, _ = is_it_candidate(r, threshold=it_threshold)
            if not is_it: continue
            if active_filters and not self.apply_hr_filters(r, active_filters): continue
            valid_resumes.append(r)
        
        print(f"После фильтрации: {len(valid_resumes)} резюме")
        if not valid_resumes: return []
        
        vacancy_emb = self.model.encode(vacancy_text, convert_to_tensor=True)
        results = []
        
        for r in valid_resumes:
            text = self.build_resume_text(r)
            if len(text) < 30: continue
            emb = self.model.encode(text, convert_to_tensor=True)
            sim = torch.nn.functional.cosine_similarity(vacancy_emb.unsqueeze(0), emb.unsqueeze(0)).item()
            score = round(sim * 100, 1)
            if score >= min_score:
                r['match_score'] = score
                results.append(r)
        
        results.sort(key=lambda x: x['match_score'], reverse=True)
        if len(results) > 3:
            results = await self._rerank(vacancy_text, results[:top_k * 2])
            
        return results[:top_k]

    async def _rerank(self, vacancy_text: str, candidates: List[Dict]) -> List[Dict]:
        if not candidates: return []
        pairs = [[vacancy_text, self.build_resume_text(c)] for c in candidates]
        raw_scores = await asyncio.to_thread(self.reranker.predict, pairs, show_progress_bar=False)
        scores = np.array(raw_scores)
        normalized = softmax(scores) * 100
        for i, c in enumerate(candidates):
            c['rerank_score_percent'] = round(float(normalized[i]), 1)
        candidates.sort(key=lambda x: x.get('rerank_score_percent', 0), reverse=True)
        return candidates

def get_ml_service() -> MLService:
    return MLService()