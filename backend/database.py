from sqlalchemy import create_engine
from urllib.parse import quote_plus
from sqlalchemy.orm import sessionmaker, declarative_base

password = "aadarsh@01"

DATABASE_URL = (
    f"postgresql://postgres:{quote_plus(password)}@localhost:5432/careeriq"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()