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
        User, Instructor, Student, Exam, Question, Rubric,
        Submission, Answer, Regrade, SubmissionRegrade, AuditEvent
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Migrate: Add background_info column if it doesn't exist (for existing databases)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('questions')]
        if 'background_info' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE questions ADD COLUMN background_info TEXT"))
                conn.commit()
            print(f"[MIGRATION] Added background_info column to questions table")
    except Exception as e:
        # Ignore errors (column might already exist or table might not exist yet)
        pass
    
    # Migrate: Add student_id column to exams table if it doesn't exist
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('exams')]
        if 'student_id' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE exams ADD COLUMN student_id TEXT"))
                conn.commit()
            print(f"[MIGRATION] Added student_id column to exams table")
    except Exception as e:
        # Ignore errors (column might already exist or table might not exist yet)
        pass
    
    # Migrate: Add number_of_questions column to exams table if it doesn't exist
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('exams')]
        if 'number_of_questions' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE exams ADD COLUMN number_of_questions INTEGER"))
                conn.commit()
            print(f"[MIGRATION] Added number_of_questions column to exams table")
    except Exception as e:
        # Ignore errors (column might already exist or table might not exist yet)
        pass
    
    # Migrate: Add llm_response column to regrades table if it doesn't exist
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('regrades')]
        if 'llm_response' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE regrades ADD COLUMN llm_response TEXT"))
                conn.commit()
            print(f"[MIGRATION] Added llm_response column to regrades table")
    except Exception as e:
        pass
    
    # Migrate: Create submission_regrades table if it doesn't exist
    # (Base.metadata.create_all above handles this for new databases,
    #  but for existing databases the table might not exist yet)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if 'submission_regrades' not in inspector.get_table_names():
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS submission_regrades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        submission_id INTEGER NOT NULL UNIQUE,
                        student_argument TEXT NOT NULL,
                        decision TEXT NOT NULL CHECK(decision IN ('keep','update')),
                        explanation TEXT NOT NULL,
                        old_total_score INTEGER,
                        new_total_score INTEGER,
                        old_results_json TEXT,
                        new_results_json TEXT,
                        model_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
                    )
                """))
                conn.commit()
            print(f"[MIGRATION] Created submission_regrades table")
    except Exception as e:
        pass
    
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
