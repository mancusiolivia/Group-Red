"""
Migration: Add assigned_exam_disputes table
- assigned_exam_disputes: stores student disputes for instructor-created (assigned) exams
- These disputes are reviewed by instructors (not automatically processed by LLM like practice exams)
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text


def add_assigned_exam_disputes_table():
    """Create assigned_exam_disputes table"""
    print("=" * 60)
    print("Migration: assigned_exam_disputes table")
    print("=" * 60)

    with get_db_session() as db:
        try:
            # Check if assigned_exam_disputes table already exists
            try:
                db.execute(text("SELECT id FROM assigned_exam_disputes LIMIT 1"))
                print("assigned_exam_disputes table already exists")
            except Exception:
                # Create the table
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS assigned_exam_disputes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        submission_id INTEGER NOT NULL,
                        question_id INTEGER,
                        student_argument TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','resolved','rejected')),
                        instructor_response TEXT,
                        instructor_decision TEXT CHECK(instructor_decision IN ('approved','rejected','partially_approved')),
                        resolved_at TIMESTAMP,
                        resolved_by INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
                        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL,
                        FOREIGN KEY (resolved_by) REFERENCES instructors(id) ON DELETE SET NULL
                    )
                """))
                
                # Create index for faster lookups
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_dispute_submission_question 
                    ON assigned_exam_disputes(submission_id, question_id)
                """))
                
                print("Created assigned_exam_disputes table and index")

            db.commit()
            print("Migration completed successfully")

        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return

    print("=" * 60)


if __name__ == "__main__":
    add_assigned_exam_disputes_table()
