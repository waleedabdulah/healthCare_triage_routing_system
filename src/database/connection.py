from sqlmodel import SQLModel, create_engine, Session
from src.config.settings import get_settings
from functools import lru_cache

def get_engine():
    settings = get_settings()
    db_url = f"sqlite:///{settings.sqlite_db_path}"
    return create_engine(db_url, connect_args={"check_same_thread": False})


def create_db_and_tables():
    from src.models.db_models import TriageSession, Appointment  # noqa — registers models
    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as session:
        yield session
