cat > README.md << EOF
# Resume Matcher API

AI-powered resume matching system using sentence transformers.

## Features
- Semantic resume-vacancy matching
- Automatic filter extraction from job descriptions
- Advanced filtering (age, experience, city, skills)
- PostgreSQL storage
- Reranking with CrossEncoder

## Installation

1. Clone the repo:
\`\`\`bash
git clone <your-repo-url>
cd backend
\`\`\`

2. Create virtual environment:
\`\`\`bash
python -m venv venv
source venv/bin/activate
\`\`\`

3. Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

4. Setup PostgreSQL:
\`\`\`bash
createdb resume_db
\`\`\`

5. Run:
\`\`\`bash
uvicorn main:app --reload
\`\`\`

## API Endpoints
- POST /api/v1/match/simple - Basic matching
- POST /api/v1/match/advanced - Advanced matching with filters
- GET /api/v1/history - Search history
- GET /api/v1/history/{vacancy_id} - Specific results

## Tech Stack
- FastAPI
- PostgreSQL + SQLAlchemy (async)
- Sentence Transformers (SBERT)
- CrossEncoder for reranking
EOF