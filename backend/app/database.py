from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

def get_engine_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # If generic postgresql:// without explicit driver, select whichever driver is installed
    if url.startswith("postgresql://") and not (
        url.startswith("postgresql+psycopg://") or 
        url.startswith("postgresql+psycopg2://")
    ):
        try:
            import psycopg  # psycopg 3
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            try:
                import psycopg2
                return url.replace("postgresql://", "postgresql+psycopg2://", 1)
            except ImportError:
                return url
    return url


db_url = get_engine_url(settings.DATABASE_URL)

# Connection pooling for stability under concurrent WebSocket usage.
# If SQLite is used, pooling options are not supported.
if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Detect stale connections before use
        pool_recycle=1800,    # Recycle connections every 30 minutes
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Modern SQLAlchemy 2.0 declarative base class."""
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
