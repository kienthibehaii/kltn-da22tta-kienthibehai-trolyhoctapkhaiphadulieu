# AGENTS.md — RAG Learning Assistant

## Dev commands

| Action | Command |
|--------|---------|
| Start backend | `python run_backend.py` (port 8000) |
| Start frontend | `cd frontend && npm run dev` (port 3000) |
| Start both | `START_FULLSTACK.bat` (Windows) |
| All tests | `pytest` (coverage ≥80% enforced) |
| One test file | `pytest tests/unit/test_auth.py -v` |
| Frontend lint | `cd frontend && npm run lint` (tsc --noEmit) |

## Architecture

- **Backend**: `backend_api.py` (FastAPI) loads RAG pipeline on startup (~15-30s). Vector DB is `chroma_db_new/` (ChromaDB). Config in `config.py`.
- **Frontend**: Express server (`frontend/server.ts`) proxies `/api/*` to backend `http://127.0.0.1:8000`. Also serves React SPA via Vite middleware.
- **RAG pipeline** (`rag.py`): Hybrid search (Vector 70% + BM25 30%) → Cross-encoder reranking → Gemini 2.5 Flash generation.
- **Auth**: JWT-based. Google OAuth login supported. MongoDB optional for persistence.

## Key quirks

- **Windows OpenMP bug**: several files set `os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'` at the top. Always include this in new scripts.
- **LLM rate limit**: Gemini free tier allows ~15 req/min. Offline fallback knowledge base exists in `rag.py` when `IS_OFFLINE_MODE = True`.
- **Vector store loading**: uses `chroma_db_new/` — not `chroma_db/`. Documents cached in `documents.pkl` inside that directory.
- **User file isolation**: uploaded files prefixed with `{user_id}__`. Security filter queries always include `{"source": {"$in": allowed_files}}`.
- **asyncio**: long-running RAG calls use `await asyncio.to_thread()` to avoid blocking uvicorn's event loop. Follow this pattern for new endpoints.
- **Startup**: API returns 503 while pipeline loads; frontend retries up to 3 times with 5s delay.
- **Frontend**: built from an AI Studio app (`@google/genai` package). Dev server is `tsx server.ts`, not `vite` directly.

## Testing

- `conftest.py` at project root sets up TestClient, test user, auth headers, conversations with cleanup fixtures.
- Tests requiring MongoDB will fail if no connection (mock or skip accordingly).
- Integration tests in `tests/integration/` use real API flow.
- Load tests in `tests/load/` (locustfile.py).
- Timeout: 300s per test (pytest.ini).

## Structure notes

- `auth/` contains auth manager, JWT, user/admin routes, chat history.
- `services/` has standalone microservice stubs (not actively used; main code is monolithic).
- `evaluation/` has standalone RAG evaluation benchmarks (retrieval, generation, citation metrics).
- `.env` needs at minimum `GOOGLE_API_KEY` (Gemini).
- Frontend `.env` needs `GEMINI_API_KEY` for standalone fallback mode.
