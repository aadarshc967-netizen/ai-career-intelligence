from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.resume_history import ResumeHistory
from models.user import User


def test_database_persists_user_history_and_analytics():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        user = User(name="Test User", email="test@example.com", password_hash="hash")
        session.add(user)
        session.flush()
        history = ResumeHistory(
            user_email=user.email,
            filename="resume.pdf",
            target_role="Python Backend Developer",
            match_score=80,
            resume_score=75,
            skill_gaps='["SQL"]',
            action_roadmap='["Practice SQL"]',
            ats_score=70,
            keyword_heatmap='[{"term":"Python","mentions":2}]',
        )
        session.add(history)
        session.commit()

        saved = session.query(ResumeHistory).filter_by(user_email=user.email).one()
        assert saved.filename == "resume.pdf"
        assert saved.match_score == 80
        assert saved.skill_gaps == '["SQL"]'
        assert saved.keyword_heatmap == '[{"term":"Python","mentions":2}]'

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
