# AI Career Intelligence

AI Career Intelligence is a React/Vite resume diagnostics app backed by an asynchronous FastAPI service. It supports authenticated resume analysis, ATS-oriented structural checks, role/JD keyword matching, optional LLM-assisted bullet tailoring, and persistent per-user analysis history.

## Architecture

- **Frontend:** React 19, TypeScript, Vite, and React Router. Configure the backend URL with `VITE_API_BASE_URL`; local builds default to `http://127.0.0.1:8000` and production builds default to the deployed Render API. Vercel's `vercel.json` rewrites SPA routes to `index.html`.
- **API:** FastAPI with async file upload handling and Uvicorn. The service binds to the platform-provided `PORT`.
- **Persistence:** SQLAlchemy 2.x and SQLite by default (`sqlite:///./sql_app.db`). SQLite connections enable foreign-key checks, cross-thread access, a 30-second busy timeout, and connection health checks.
- **Analysis:** PDF/DOCX text extraction, technical-skill matching, ATS structure checks, and per-keyword density diagnostics. ATS findings are heuristic guidance, not a guarantee of how a particular ATS vendor will rank a resume.

## Data model

| Entity | Important fields | Relationships |
|---|---|---|
| `users` | `id`, `name`, unique `email`, `password_hash` | One user owns many resume history records. |
| `resume_histories` | `id`, `user_email`, `filename`, `target_role`, `match_score`, `resume_score`, `ats_score`, `skill_gaps`, `action_roadmap`, `keyword_heatmap`, `ats_issues`, `tailored_bullets`, `created_at` | `user_email` references `users.email` with cascade deletion on newly created databases. |

JSON-valued history fields are stored as JSON text to preserve compatibility with SQLite and existing installations. Startup adds newly introduced history columns to an existing SQLite table. Existing tables are not rebuilt, so their original constraints remain unchanged; back up legacy databases before applying schema changes.

## REST API

All endpoints are served from the API origin. Interactive OpenAPI docs are available at `/docs`.

### `POST /register`

JSON request: `{"name":"Ada Example","email":"ada@example.com","password":"at-least-8-characters"}`. Creates an account and returns a bearer access token. Passwords are stored as PBKDF2-SHA256 hashes; legacy plaintext hashes are upgraded on successful login.

### `POST /login`

JSON request: `{"email":"ada@example.com","password":"..."}`. Returns `access_token`, `token_type`, `name`, and `email`. Tokens expire after 30 minutes. Use the `Authorization: Bearer <access_token>` header for protected operations.

### `POST /analyze-career`

Multipart form data:

- `file` (required): PDF or DOCX, up to 5 MiB.
- `target_role` (optional): Python Backend Developer, Full-Stack Developer, or Junior Data Scientist / ML Engineer.
- `job_description` (optional): up to 20,000 characters. If provided, its keywords are scored and tailored bullets are generated through the configured LLM provider.

Returns extracted skills, role match and resume-health scores, ATS score/issues, keyword heatmap, skill gaps, an action plan, and tailored bullet points (when a JD was submitted). Files are parsed in memory and are not persisted on the server. Tailoring requires `OPENAI_API_KEY`; without it, a JD tailoring request returns `503` rather than pretending to perform an LLM rewrite.

### `POST /upload-resume`

Authenticated compatibility endpoint accepting a PDF or DOCX multipart `file`. Returns parsed text, filename, byte size, and recognized skills. The uploaded file is processed in memory.

### `GET /user-history/{email}`

Requires a bearer token. The normalized path email must match the authenticated account; other accounts receive `403`. Returns the most recent 100 analyses, including scores, skill gaps, roadmap, ATS diagnostics, and tailoring results.

### Health and readiness

- `GET /`: service welcome response.
- `GET /health`: lightweight health check for deployment monitoring.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | No | SQLAlchemy URL; defaults to `sqlite:///./sql_app.db`. |
| `JWT_SECRET_KEY` | Yes | At least 32 characters; signing key for bearer tokens. The API refuses to start without it. Render blueprint generates one. |
| `CORS_ORIGINS` | No | Comma-separated exact frontend origins. Defaults to `https://careeriq-rho.vercel.app` and local Vite origins. Wildcard origins are rejected. CORS credentials are disabled because the app uses bearer tokens, not cookies. |
| `OPENAI_API_KEY` | For JD tailoring | API key for an OpenAI-compatible chat-completions provider. |
| `OPENAI_BASE_URL` | No | Provider API base; defaults to `https://api.openai.com/v1`. |
| `OPENAI_MODEL` | No | Provider model; defaults to `gpt-4o-mini`. |
| `PORT` | Platform-provided | Uvicorn listen port. |
| `VITE_API_BASE_URL` | Recommended in Vercel | Backend origin; set to `https://ai-career-intelligence-7x5r.onrender.com` in Vercel. Production builds otherwise use that same Render origin as a fallback. |

## Local development

Backend, from the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:JWT_SECRET_KEY = "local-development-secret-with-32-chars"
$env:CORS_ORIGINS = "http://localhost:5173"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, from the `frontend` directory:

```powershell
npm ci
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

Copy `.env.example` for local backend settings and `frontend/.env.example` to `frontend/.env` for frontend development settings. Both files contain placeholders/public URLs only. The frontend includes an error boundary for unexpected render failures, visible API/network/JSON error states, client-side PDF/DOCX and size checks, and an account form for registration/login.

## Testing and production build

```powershell
cd backend
python -m pytest
cd ..\frontend
npm run lint
npm run build
```

Tests cover malformed resume parsing, DOCX extraction (including table text), keyword scoring/ATS diagnostics, and SQLAlchemy history persistence.

## Deployment

### Render API

1. Connect the repository to Render and use the included `render.yaml` blueprint. It configures `rootDir: backend`, `pip install -r requirements.txt`, the `/health` check, and `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. Set `CORS_ORIGINS` to `https://careeriq-rho.vercel.app` (plus any required local origins), ensure `JWT_SECRET_KEY` is generated and at least 32 characters, and set `OPENAI_API_KEY` if JD tailoring is required. Render environment values override application defaults.
3. Configure Vercel's `VITE_API_BASE_URL` to `https://ai-career-intelligence-7x5r.onrender.com`, then redeploy the Vite app. The existing Vercel rewrite preserves direct SPA navigation and refreshes.
4. Alternatively, build the backend image from `backend/Dockerfile`; it binds to `$PORT` (default 8000).

SQLite is appropriate for local/single-instance or disposable free-tier deployments. Free Render instances have ephemeral filesystems, so the default SQLite database may be lost on redeploy/restart and does not support safe multi-instance writes. Use a persistent disk or managed PostgreSQL for durable production data and horizontal scaling; set `DATABASE_URL` accordingly.

## Security and privacy notes

- Analysis and history are scoped to a verified bearer-token identity; uploaded files are processed in memory.
- Set a unique secret `JWT_SECRET_KEY` in every deployed environment and configure exact CORS origins.
- Resume text is sent to the configured LLM provider only when the user requests JD tailoring. Review provider retention and privacy terms before processing sensitive resumes.
- Use HTTPS for deployed frontend/API traffic. Access tokens are stored in browser local storage by this client; production applications with stricter XSS threat models should use an HttpOnly secure-cookie session design.
