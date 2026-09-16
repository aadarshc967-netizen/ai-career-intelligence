from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pypdf import PdfReader
from docx import Document
from database import engine, Base
from models.user import User

app = FastAPI(
    title="AI Career Intelligence API",
    description="Backend API for AI-powered career analysis",
    version="1.0.0"
)
Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "AI Career Intelligence API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Career Intelligence API"
    }
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path

app = FastAPI(
    title="AI Career Intelligence API",
    description="Backend API for AI-powered career analysis",
    version="1.0.0"
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "AI Career Intelligence API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Career Intelligence API"
    }


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed"
        )

    file_path = UPLOAD_DIR / file.filename

    content = await file.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 5MB"
        )

    with open(file_path, "wb") as f:
        f.write(content)
        resume_text = extract_text(file_path)
        skills = extract_skills(resume_text)

    return {
        "message": "Resume uploaded successfully",
        "filename": file.filename,
        "size": len(content),
        "text": resume_text,
        "skills": skills
    }
def extract_text(file_path: Path):
    if file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))

        text = ""

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text

    elif file_path.suffix.lower() == ".docx":
        document = Document(str(file_path))

        text = ""

        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"

        return text

    return ""

def extract_skills(text: str):
    skills_list = [
        "Python",
        "Java",
        "C",
        "C++",
        "JavaScript",
        "TypeScript",
        "React",
        "Node.js",
        "HTML",
        "CSS",
        "SQL",
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "Git",
        "GitHub",
        "Docker",
        "Machine Learning",
        "Deep Learning",
        "Artificial Intelligence",
        "Data Science",
        "Pandas",
        "NumPy",
        "TensorFlow",
        "PyTorch",
        "FastAPI",
        "Django",
        "Flask"
    ]

    text_lower = text.lower()

    found_skills = []

    for skill in skills_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills

from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from database import SessionLocal
from models.user import User


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=data.password
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    }