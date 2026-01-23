"""
Database connection and session management using SQLAlchemy
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

from server.core.config import DATABASE_PATH

# Create SQLAlchemy engine with better SQLite configuration
# Enable WAL mode for better concurrent access and add timeout for locks
engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={
        "check_same_thread": False,  # Needed for SQLite with async
        "timeout": 30.0  # Wait up to 30 seconds for locks to be released
    },
    pool_pre_ping=True,  # Verify connections before using them
    echo=False  # Set to True for SQL query logging
)


# Enable WAL mode for better concurrent read/write access
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and optimize SQLite for concurrent access"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
    cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def init_db():
    """Initialize database by creating all tables"""
    # Import all models to ensure they're registered
    from server.core.db_models import (
        Instructor, Student, Exam, Question, Rubric,
        Submission, Answer, Regrade, AuditEvent
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_PATH}")


def get_db() -> Session:
    """
    Dependency function for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    Note: Route handlers should explicitly commit() or rollback() transactions
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close the session to release database locks
        # Note: If route handler didn't commit, changes will be rolled back automatically
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Usage:
        with get_db_session() as db:
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
