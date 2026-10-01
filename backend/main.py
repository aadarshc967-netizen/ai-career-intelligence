from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime
from passlib.context import CryptContext
from jose import jwt

from database import engine, Base, SessionLocal
from models.user import User

app = FastAPI(
    title="AI Career Intelligence API",
    description="Backend API for AI-powered career analysis",
    version="1.0.0"
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# JWT Security Configurations
SECRET_KEY = "super-secret-key-ai-career-intelligence"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Resume History Model for Dashboard History Tracking
class ResumeHistoryModel(Base):
    __tablename__ = "resume_histories"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    filename = Column(String)
    target_role = Column(String)
    match_score = Column(Integer)
    resume_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Initialize Database tables (Yeh sabhi models ke define hone ke baad chalna chahiye)
Base.metadata.create_all(bind=engine)

# Pydantic Models
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/login")
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or user.password_hash != data.password:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email
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

@app.post("/analyze-career")
async def analyze_career(
    file: UploadFile = File(...), 
    target_role: str = Form("Python Backend Developer"),
    user_email: str = Form("guest@example.com"),
    db: Session = Depends(get_db)
):
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

    # Distinct Role-Specific Skill Requirements & Weightage
    role_requirements = {
        "Python Backend Developer": {
            "core": ["Python", "SQL", "Git"],
            "frameworks": ["FastAPI", "Django", "Flask"],
            "database": ["PostgreSQL", "MySQL", "MongoDB"]
        },
        "Full-Stack Developer": {
            "core": ["JavaScript", "HTML", "CSS", "Git"],
            "frameworks": ["React", "TypeScript", "Node.js"],
            "database": ["SQL", "MongoDB"]
        },
        "Junior Data Scientist / ML Engineer": {
            "core": ["Python", "SQL"],
            "frameworks": ["Pandas", "NumPy", "TensorFlow", "PyTorch"],
            "database": ["Machine Learning", "Artificial Intelligence", "Data Science"]
        }
    }

    # Get requirement groups for the selected target role
    selected_reqs = role_requirements.get(target_role, role_requirements["Python Backend Developer"])
    
    all_role_skills = selected_reqs["core"] + selected_reqs["frameworks"] + selected_reqs["database"]
    
    # Calculate intelligent match score based on presence in resume
    matched_skills_count = sum(1 for skill in all_role_skills if skill in skills)
    match_percentage = int((matched_skills_count / len(all_role_skills)) * 100)
    # Ensure reasonable percentage bounds
    match_percentage = max(25, min(match_percentage, 96))

    # Dynamic Resume Health Score based on skill variety and tools
    resume_score = min(35 + (len(skills) * 9) + (10 if "Git" in skills else 0) + (10 if "SQL" in skills else 0), 98)

    # Find missing skills specifically for this target role
    missing_skills = [s for s in all_role_skills if s not in skills]
    
    # Role-specific tailored roadmap
    roadmap = [
        f"Step 1: Bridge critical skill gaps for {target_role} by learning: {', '.join(missing_skills[:3]) if missing_skills else 'advanced architecture'}.",
        f"Step 2: Build 2 high-impact production projects specifically targeting {target_role}.",
        "Step 3: Optimize code efficiency, write clean unit tests, and document architecture professionally.",
        "Step 4: Practice system design problems and mock interviews tailored to top tech companies."
    ]

    dos_and_donts = {
        "dos": [
            f"Highlight projects and experience specifically related to {target_role}.",
            "Use clear action verbs and quantifiable impact metrics in your experience bullet points.",
            "Ensure core tools like Git and relevant frameworks are prominently featured at the top."
        ],
        "donts": [
            "Avoid listing irrelevant technologies that do not align with your chosen target role.",
            "Do not use generic templates without customizing skills to match the job description.",
            "Avoid walls of text; keep descriptions concise and impact-driven."
        ]
    }

    # Save Analysis History to Database
    new_history = ResumeHistoryModel(
        user_email=user_email,
        filename=file.filename,
        target_role=target_role,
        match_score=match_percentage,
        resume_score=resume_score
    )
    db.add(new_history)
    db.commit()

    return {
        "filename": file.filename,
        "extracted_skills": skills,
        "target_role": target_role,
        "match_score": match_percentage,
        "resume_score": resume_score,
        "current_suitability": [target_role, "Software Engineer Intern"],
        "skill_gaps": missing_skills,
        "future_action_plan": roadmap,
        "dos_and_donts": dos_and_donts
    }

@app.get("/user-history/{email}")
def get_user_history(email: str, db: Session = Depends(get_db)):
    history = db.query(ResumeHistoryModel).filter(ResumeHistoryModel.user_email == email).all()
    return history

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
        "Python", "Java", "C", "C++", "JavaScript", "TypeScript", "React",
        "Node.js", "HTML", "CSS", "SQL", "MySQL", "PostgreSQL", "MongoDB",
        "Git", "GitHub", "Docker", "Machine Learning", "Deep Learning",
        "Artificial Intelligence", "Data Science", "Pandas", "NumPy",
        "TensorFlow", "PyTorch", "FastAPI", "Django", "Flask"
    ]

    text_lower = text.lower()
    found_skills = []

    for skill in skills_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills