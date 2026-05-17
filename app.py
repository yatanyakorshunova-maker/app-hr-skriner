import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# ==================== НАСТРОЙКИ ====================
st.set_page_config(
    page_title="AI HR Скринер", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 AI HR Скринер")
st.header("Подбор кандидатов под вакансию")
st.divider()

# ==================== ИНИЦИАЛИЗАЦИЯ SESSION_STATE ====================
if "candidates_active" not in st.session_state:
    st.session_state.candidates_active = []  # Активные кандидаты
if "candidates_rejected" not in st.session_state:
    st.session_state.candidates_rejected = []  # Отсеянные кандидаты
if "last_search" not in st.session_state:
    st.session_state.last_search = None
if "vacancy_text_cache" not in st.session_state:
    st.session_state.vacancy_text_cache = ""

# ==================== ФУНКЦИИ ====================
def get_api_url() -> str:
    """Определяет URL бэкенда (для локальной разработки или продакшена)"""
    # Для локального запуска бэкенда
    local_url = "http://localhost:8000"
    
    # Если запущено в Streamlit Cloud или другом облаке
    if "BACKEND_URL" in st.secrets:
        return st.secrets["BACKEND_URL"]
    
    # Попробуем проверить доступность локального бэкенда
    try:
        response = requests.get(f"{local_url}/", timeout=2)
        if response.status_code == 200:
            return local_url
    except:
        pass
    
    # Если ничего не сработало — просим пользователя
    return st.text_input(
        "🔌 Введите URL бэкенда:",
        value=local_url,
        help="Пример: http://localhost:8000 или https://your-backend.onrender.com"
    )

def process_candidates(result: Dict[str, Any]) -> List[Dict]:
    """Преобразует ответ API в единый формат"""
    candidates = result.get("top_candidates", [])
    processed = []
    
    for idx, cand in enumerate(candidates):
        # Создаем уникальный ID для кандидата
        unique_id = f"{cand.get('name', 'unknown')}_{cand.get('age', '0')}_{cand.get('city', 'unknown')}_{idx}"
        
        processed.append({
            "id": unique_id,
            "name": cand.get("name", "Не указано"),
            "age": cand.get("age", "—"),
            "city": cand.get("city", "—"),
            "experience": cand.get("experience", "—"),
            "skills": cand.get("skills", "—"),
            "desired_position": cand.get("desired_position", "—"),
            "salary": cand.get("salary", "—"),
            "education": cand.get("education", "—"),
            "match_score": cand.get("match_score", 0),
            "rerank_score": cand.get("rerank_score_percent", None),
            "raw_data": cand
        })
    
    return processed

# ==================== БОКОВАЯ ПАНЕЛЬ ====================
with st.sidebar:
    st.header("⚙️ Параметры поиска")
    
    # Подключение к бэкенду
    api_url = get_api_url()
    st.success(f"✅ Бэкенд: {api_url}")
    
    st.divider()
    
    # Фильтры
    st.subheader("📊 Фильтры кандидатов")
    
    min_age = st.number_input(
        "Минимальный возраст",
        min_value=18, max_value=70, value=None, 
        placeholder="Не важно"
    )
    
    max_age = st.number_input(
        "Максимальный возраст", 
        min_value=18, max_value=70, value=None,
        placeholder="Не важно"
    )
    
    min_experience = st.number_input(
        "Минимальный опыт (лет)",
        min_value=0, max_value=50, value=None,
        placeholder="Не важно"
    )
    
    city = st.text_input("Город", placeholder="Например: Москва")
    
    position_keywords = st.text_input(
        "Ключевые слова в должности",
        placeholder="Backend, Python, Data Scientist"
    )
    
    skills_keywords = st.text_input(
        "Ключевые навыки",
        placeholder="Python, SQL, Docker"
    )
    
    st.divider()
    
    # Параметры матчинга
    st.subheader("🎯 Параметры матчинга")
    
    min_score = st.slider(
        "Минимальный процент совпадения",
        min_value=0.0, max_value=100.0, value=15.0, step=5.0
    )
    
    top_k = st.slider(
        "Количество лучших кандидатов",
        min_value=5, max_value=50, value=20, step=5
    )
    
    use_reranking = st.checkbox("Использовать reranking", value=True)
    use_auto_filters = st.checkbox("Авто-фильтры из вакансии", value=True)
    
    st.divider()
    
    # Управление отсеянными
    st.subheader("🗑️ Управление")
    
    if st.button("🔄 Очистить список отсеянных", use_container_width=True):
        st.session_state.candidates_rejected = []
        st.rerun()
    
    if st.button("🧹 Сбросить все результаты", use_container_width=True):
        st.session_state.candidates_active = []
        st.session_state.candidates_rejected = []
        st.session_state.last_search = None
        st.rerun()
    
    st.caption(f"📊 Статус: {len(st.session_state.candidates_active)} активных, {len(st.session_state.candidates_rejected)} отсеянных")

# ==================== ОСНОВНОЙ КОНТЕНТ ====================

# Поле для вакансии
st.subheader("📄 Текст вакансии")
vacancy_text = st.text_area(
    "Вставьте описание вакансии:",
    value=st.session_state.vacancy_text_cache,
    height=200,
    placeholder="Требуется Python разработчик с опытом от 3 лет..."
)

# Загрузка файла с резюме
st.subheader("📁 Резюме кандидатов")
uploaded_file = st.file_uploader(
    "Загрузите файл с резюме (формат .txt)",
    type=["txt"],
    help="Файл должен быть в формате, который понимает парсер"
)

# Кнопка запуска
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("🚀 ЗАПУСТИТЬ ПОДБОР", type="primary", use_container_width=True)

# ==================== ОБРАБОТКА ЗАПУСКА ====================
if run_button:
    if not uploaded_file:
        st.error("❌ Ошибка: загрузите файл с резюме")
        st.stop()
    
    if not vacancy_text.strip():
        st.error("❌ Ошибка: введите текст вакансии")
        st.stop()
    
    # Сохраняем текст вакансии в кэш
    st.session_state.vacancy_text_cache = vacancy_text
    
    # Подготавливаем данные для отправки
    files = {
        "vacancy_file": ("vacancy.txt", vacancy_text.encode("utf-8"), "text/plain"),
        "resume_file": ("resumes.txt", uploaded_file.getvalue(), "text/plain")
    }
    
    data = {
        "top_k": str(top_k),
        "min_score": str(min_score),
        "use_reranking": str(use_reranking).lower(),
        "use_auto_filters": str(use_auto_filters).lower()
    }
    
    # Добавляем фильтры, если они заданы
    if min_age:
        data["min_age"] = str(min_age)
    if max_age:
        data["max_age"] = str(max_age)
    if min_experience:
        data["min_experience"] = str(min_experience)
    if city and city.strip():
        data["city"] = city.strip()
    if position_keywords and position_keywords.strip():
        data["position_keywords"] = position_keywords.strip()
    if skills_keywords and skills_keywords.strip():
        data["skills_keywords"] = skills_keywords.strip()
    
    # Отправляем запрос
    with st.spinner("🧠 Анализируем резюме... (может занять 15-40 секунд)"):
        try:
            response = requests.post(
                f"{api_url}/api/v1/match/advanced",
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Обрабатываем результат
                new_candidates = process_candidates(result)
                
                # Обновляем session_state
                st.session_state.candidates_active = new_candidates
                st.session_state.candidates_rejected = []
                st.session_state.last_search = datetime.now()
                
                st.success(f"✅ Найдено {len(new_candidates)} кандидатов!")
                st.rerun()
            else:
                st.error(f"❌ Ошибка API: {response.status_code}")
                st.code(response.text)
                
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Не удалось подключиться к бэкенду по адресу: {api_url}")
            st.info("💡 Убедитесь, что бэкенд запущен и доступен")
        except requests.exceptions.Timeout:
            st.error("⏰ Превышено время ожидания (300 секунд)")
        except Exception as e:
            st.error(f"❌ Неизвестная ошибка: {str(e)}")

# ==================== ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ====================

if st.session_state.candidates_active or st.session_state.candidates_rejected:
    
    # Вкладки
    tab_active, tab_rejected = st.tabs([
        f"✅ АКТИВНЫЕ ({len(st.session_state.candidates_active)})",
        f"❌ ОТСЕЯННЫЕ ({len(st.session_state.candidates_rejected)})"
    ])
    
    # ========== ВКЛАДКА АКТИВНЫЕ ==========
    with tab_active:
        if st.session_state.candidates_active:
            # Таблица с краткой информацией
            df_data = []
            for c in st.session_state.candidates_active:
                df_data.append({
                    "Имя": c["name"],
                    "Возраст": c["age"],
                    "Город": c["city"],
                    "Опыт": c["experience"],
                    "Совпадение %": c["match_score"],
                    "Навыки": c["skills"][:50] + "..." if len(c["skills"]) > 50 else c["skills"]
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("📋 Детальная информация")
            
            # Детальные карточки с кнопками отсева
            for c in st.session_state.candidates_active:
                with st.expander(f"👤 {c['name']} — Совпадение: {c['match_score']:.1f}%"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**🏷️ Имя:** {c['name']}")
                        st.write(f"**🎂 Возраст:** {c['age']}")
                        st.write(f"**📍 Город:** {c['city']}")
                        st.write(f"**💼 Опыт:** {c['experience']} лет")
                    
                    with col2:
                        st.write(f"**💰 Зарплата:** {c['salary']}")
                        st.write(f"**📚 Образование:** {c['education'][:100] if c['education'] else '—'}")
                        if c['rerank_score']:
                            st.write(f"**🎯 Rerank:** {c['rerank_score']:.1f}%")
                    
                    with col3:
                        st.write("")
                        st.write("")
                        if st.button("❌ Отсеять", key=f"reject_{c['id']}", type="secondary"):
                            # Перемещаем из активных в отсеянные
                            st.session_state.candidates_rejected.append(c)
                            st.session_state.candidates_active = [
                                                                x for x in st.session_state.candidates_active if x["id"] != c["id"]
                            ]
                            st.rerun()
                    
                    if c['desired_position'] and c['desired_position'] != '—':
                        st.write(f"**💼 Желаемая должность:** {c['desired_position']}")
                    
                    if c['skills'] and c['skills'] != '—':
                        st.write(f"**🔧 Навыки:** {c['skills']}")
        else:
            st.info("📭 Нет активных кандидатов. Загрузите резюме и запустите подбор.")
    
    # ========== ВКЛАДКА ОТСЕЯННЫЕ ==========
    with tab_rejected:
        if st.session_state.candidates_rejected:
            # Таблица с отсеянными
            df_rejected = []
            for c in st.session_state.candidates_rejected:
                df_rejected.append({
                    "Имя": c["name"],
                    "Возраст": c["age"],
                    "Город": c["city"],
                    "Совпадение %": c["match_score"],
                    "Причина": "Отсеян пользователем"
                })
            
            df_r = pd.DataFrame(df_rejected)
            st.dataframe(df_r, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🔄 Восстановить кандидатов")
            
            # Кнопки восстановления
            cols = st.columns(3)
            for idx, c in enumerate(st.session_state.candidates_rejected):
                col_idx = idx % 3
                with cols[col_idx]:
                    if st.button(f"↩️ {c['name']} ({c['match_score']:.0f}%)", key=f"restore_{c['id']}"):
                        # Перемещаем из отсеянных в активные
                        st.session_state.candidates_active.append(c)
                        st.session_state.candidates_rejected = [
                                                                x for x in st.session_state.candidates_rejected if x["id"] != c["id"]
                        ]
                        st.rerun()
        else:
            st.info("📭 Нет отсеянных кандидатов")
    
    # Информация о времени последнего поиска
    if st.session_state.last_search:
        st.caption(f"🕐 Последний поиск: {st.session_state.last_search.strftime('%d.%m.%Y %H:%M:%S')}")

else:
    # Пустое состояние
    st.info("👋 Загрузите файл с резюме и текст вакансии, затем нажмите 'Запустить подбор'")

st.divider()
st.caption("🤖 AI HR Скринер — умный подбор кандидатов")
