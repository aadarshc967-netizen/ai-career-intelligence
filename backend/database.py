import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from sqlalchemy.orm import sessionmaker, declarative_base

# Render ya environment variable se DATABASE_URL le, warna local fallback use kare
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    password = "aadarsh@01"
    DATABASE_URL = f"postgresql://postgres:{quote_plus(password)}@localhost:5432/careeriq"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()