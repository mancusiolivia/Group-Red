"""
Migration: Make started_at nullable in submissions table

This allows submissions to exist without a started_at timestamp,
which is needed for assigned exams that haven't been started yet.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text

def make_started_at_nullable():
    """Make started_at column nullable in submissions table"""
    print("=" * 60)
    print("Making started_at nullable in submissions table...")
    print("=" * 60)
    
    with get_db_session() as db:
        try:
            # SQLite doesn't support ALTER COLUMN directly, so we need to:
            # 1. Create a new table with the correct schema
            # 2. Copy data
            # 3. Drop old table
            # 4. Rename new table
            
            # Check if column is already nullable (by checking if we can set it to NULL)
            # Actually, let's just try to alter it - SQLite 3.25+ supports it
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS submissions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    started_at TIMESTAMP,
                    submitted_at TIMESTAMP,
                    FOREIGN KEY (exam_id) REFERENCES exams(id),
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            """))
            
            # Copy data from old table to new table
            db.execute(text("""
                INSERT INTO submissions_new (id, exam_id, student_id, started_at, submitted_at)
                SELECT id, exam_id, student_id, started_at, submitted_at
                FROM submissions
            """))
            
            # Drop old table
            db.execute(text("DROP TABLE submissions"))
            
            # Rename new table
            db.execute(text("ALTER TABLE submissions_new RENAME TO submissions"))
            
            # Recreate indexes
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_submission_exam_student_started 
                ON submissions(exam_id, student_id, started_at)
            """))
            
            db.commit()
            print("Successfully made started_at nullable")
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            print("\nNote: If the error says the table already exists, the migration may have already been run.")
            return
    
    print("=" * 60)

if __name__ == "__main__":
    make_started_at_nullable()
