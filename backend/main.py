import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models.resume_history import ResumeHistory
from models.user import User
from resume_analysis import (
    analyze_ats,
    calculate_role_match,
    extract_resume,
    extract_skills,
    jd_keywords,
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("Set JWT_SECRET_KEY to a secret of at least 32 characters")

app = FastAPI(
    title="AI Career Intelligence API",
    description="Resume diagnostics, job matching, and career history",
    version="2.0.0",
)

configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in configured_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


def migrate_history_columns() -> None:
    existing_columns = {column["name"] for column in inspect(engine).get_columns("resume_histories")}
    column_types = {
        "skill_gaps": "TEXT NOT NULL DEFAULT '[]'",
        "action_roadmap": "TEXT NOT NULL DEFAULT '[]'",
        "ats_score": "INTEGER NOT NULL DEFAULT 0",
        "keyword_heatmap": "TEXT NOT NULL DEFAULT '[]'",
        "ats_issues": "TEXT NOT NULL DEFAULT '[]'",
        "tailored_bullets": "TEXT NOT NULL DEFAULT '[]'",
    }
    with engine.begin() as connection:
        for column, definition in column_types.items():
            if column not in existing_columns:
                connection.execute(text(f"ALTER TABLE resume_histories ADD COLUMN {column} {definition}"))


Base.metadata.create_all(bind=engine)
migrate_history_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, salt_hex, digest_hex = stored_hash.split("$")
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(stored_hash.encode("utf-8"), password.encode("utf-8"))


def create_access_token(email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication is required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from error
    if not isinstance(email, str):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


def parse_json_list(value: str) -> list:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


@app.get("/")
def root():
    return {"message": "AI Career Intelligence API is running"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "AI Career Intelligence API"}


@app.post("/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="A name is required")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(name=name, email=email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from error
    db.refresh(user)
    return {
        "access_token": create_access_token(user.email),
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@app.post("/login")
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    email = normalize_email(data.email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(data.password)
        db.commit()
    return {
        "access_token": create_access_token(user.email),
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


async def read_resume(file: UploadFile) -> tuple[str, str, list[str], int]:
    extension = Path(file.filename or "").suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded resume is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File size must be less than 5MB")
    try:
        resume_text, layout_issues = extract_resume(content, extension)
    except (ValueError, OSError, KeyError) as error:
        raise HTTPException(status_code=422, detail="The resume file is invalid or could not be parsed") from error
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the resume")
    return resume_text, Path(file.filename or "resume").name[:255], layout_issues, len(content)


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    resume_text, filename, _, size = await read_resume(file)
    return {
        "message": "Resume uploaded and parsed successfully",
        "filename": filename,
        "size": size,
        "text": resume_text,
        "skills": extract_skills(resume_text),
    }


def role_skills(target_role: str) -> list[str]:
    requirements = {
        "Python Backend Developer": [
            "Python", "SQL", "Git", "FastAPI", "Django", "Flask", "PostgreSQL", "MySQL", "MongoDB",
        ],
        "Full-Stack Developer": [
            "JavaScript", "HTML", "CSS", "Git", "React", "TypeScript", "Node.js", "SQL", "MongoDB",
        ],
        "Junior Data Scientist / ML Engineer": [
            "Python", "SQL", "Pandas", "NumPy", "TensorFlow", "PyTorch", "Machine Learning",
            "Artificial Intelligence", "Data Science",
        ],
    }
    return requirements.get(target_role, requirements["Python Backend Developer"])


async def tailor_bullets(resume_text: str, job_description: str) -> list[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="JD tailoring requires OPENAI_API_KEY to be configured")

    endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Improve resume bullet points for relevance to the supplied job description. "
                    "Return only a JSON object with a 'bullets' array of rewritten bullet strings. "
                    "Do not invent employers, skills, metrics, achievements, or qualifications. "
                    "Preserve the candidate's factual claims and use concise action-oriented language."
                ),
            },
            {
                "role": "user",
                "content": f"Job description:\n{job_description}\n\nResume:\n{resume_text[:18000]}",
            },
        ],
        "response_format": {"type": "json_object"},
    }

    def request_completion() -> dict:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        response_data = await asyncio.to_thread(request_completion)
    except HTTPError as error:
        raise HTTPException(status_code=502, detail=f"LLM provider rejected the tailoring request (HTTP {error.code})") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="The LLM provider could not complete the tailoring request") from error

    try:
        content = response_data["choices"][0]["message"]["content"]
        bullets = json.loads(content)["bullets"]
        if not isinstance(bullets, list) or not bullets or not all(isinstance(item, str) and item.strip() for item in bullets):
            raise ValueError("Invalid bullets")
        return [item.strip()[:1000] for item in bullets[:20]]
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="The LLM provider returned an invalid tailoring response") from error


@app.post("/analyze-career")
async def analyze_career(
    file: UploadFile = File(...),
    target_role: str = Form("Python Backend Developer", max_length=200),
    job_description: str = Form("", max_length=20_000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if job_description.strip() and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="JD tailoring requires OPENAI_API_KEY to be configured")
    resume_text, filename, layout_issues, _ = await read_resume(file)
    role_keywords = role_skills(target_role)
    target_keywords = jd_keywords(job_description) if job_description.strip() else role_keywords
    match_score, skill_gaps = calculate_role_match(resume_text, target_keywords)
    ats_analysis = analyze_ats(resume_text, filename, target_keywords, layout_issues)
    resume_score = round(ats_analysis["score"] * 0.65 + match_score * 0.35)
    skills = extract_skills(resume_text)
    roadmap = [
        f"Build evidence for these priority skills: {', '.join(skill_gaps[:3])}." if skill_gaps else "Deepen your expertise in the skills most emphasized by the target role.",
        f"Create two measurable projects demonstrating fit for {target_role}.",
        "Rewrite experience bullets with clear actions, scope, and truthful measurable outcomes.",
        "Review the ATS findings and retest after updating the resume.",
    ]
    tailored = []
    if job_description.strip():
        tailored = await tailor_bullets(resume_text, job_description)

    history = ResumeHistory(
        user_email=user.email,
        filename=filename,
        target_role=target_role[:200],
        match_score=match_score,
        resume_score=resume_score,
        skill_gaps=json.dumps(skill_gaps),
        action_roadmap=json.dumps(roadmap),
        ats_score=ats_analysis["score"],
        keyword_heatmap=json.dumps(ats_analysis["keyword_heatmap"]),
        ats_issues=json.dumps(ats_analysis["issues"]),
        tailored_bullets=json.dumps(tailored),
    )
    db.add(history)
    db.commit()

    return {
        "filename": filename,
        "extracted_skills": skills,
        "target_role": target_role,
        "match_score": match_score,
        "resume_score": resume_score,
        "ats_analysis": ats_analysis,
        "skill_gaps": skill_gaps,
        "future_action_plan": roadmap,
        "tailored_bullets": tailored,
    }


@app.get("/user-history/{email}")
def get_user_history(
    email: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if normalize_email(email) != user.email.casefold():
        raise HTTPException(status_code=403, detail="You may only access your own analysis history")
    history = (
        db.query(ResumeHistory)
        .filter(ResumeHistory.user_email == user.email)
        .order_by(ResumeHistory.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "target_role": item.target_role,
            "match_score": item.match_score,
            "resume_score": item.resume_score,
            "ats_score": item.ats_score,
            "skill_gaps": parse_json_list(item.skill_gaps),
            "action_roadmap": parse_json_list(item.action_roadmap),
            "keyword_heatmap": parse_json_list(item.keyword_heatmap),
            "ats_issues": parse_json_list(item.ats_issues),
            "tailored_bullets": parse_json_list(item.tailored_bullets),
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in history
    ]
