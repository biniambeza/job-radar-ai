import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Configure engine arguments tailored for dialect (Neon PostgreSQL vs SQLite)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "pool_pre_ping": True,  # Critical for Neon serverless auto-suspend & reconnect
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Optimized for Neon PostgreSQL (pooled connections & serverless lifecycle)
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 300  # Recycle connections every 5 min to handle Neon idle timeout

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for models
Base = declarative_base()

def get_db():
    """Dependency yield for FastAPI request lifecycle and services."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    import app.models  # Ensure models are registered with Base metadata
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")

def check_db_connection() -> bool:
    """Test connection to the database (useful for Neon startup verification)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
