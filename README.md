# ResearchMate AI

AI-powered research-to-publication workspace with literature intelligence, originality and citation analysis, RAG retrieval, multi-agent workflows, publication readiness, conference intelligence and notifications.

## Highlights
- **RAG:** document chunking, metadata-aware retrieval and evidence-oriented context.
- **Multi-agent workflow:** Paper Analyzer, Citation Agent, Originality Agent, Publication Agent and Conference Agent orchestrated in one workflow.
- **Originality:** exact/lexical/semantic analysis modules in the existing project, with suggestion-oriented reporting.
- **Citation analysis:** separates external claims from methodology/results and supports citation review.
- **Conference Intelligence:** category/search filters, verification status, source URL and explicit "Not verified" dates.
- **Notifications:** new conference, analysis and deadline notification model/API.
- **Publication Assistant:** dynamic project/paper selection; no hardcoded project or paper IDs and no fake fallback output.

## Run
### Backend
```bash
cd backend
python -m venv venv
# Windows: venv\\Scripts\\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# or cp .env.example .env
uvicorn app.main:app --reload --port 8001
```
Set `DATABASE_URL` and `GEMINI_API_KEY` in `.env`.

### Frontend
```bash
cd ResearchMate-AI-Complete-Frontend
npm install
npm run dev
```
Set `VITE_API_BASE_URL` in `.env` if the backend is not on port 8001.

## Important
Conference dates and publication facts are not fabricated by the new modules. Records should carry a source and verification status. LLM features require a valid Gemini key; deterministic modules continue to provide non-LLM diagnostics where possible.
