"""
Migration: Add submission_regrades table and llm_response column to regrades table
- submission_regrades: stores overall exam-level dispute results (one per submission)
- regrades.llm_response: stores the full structured JSON from the LLM dispute adjudication
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text


def add_submission_regrades_table():
    """Create submission_regrades table and add llm_response column to regrades"""
    print("=" * 60)
    print("Migration: submission_regrades table + regrades.llm_response column")
    print("=" * 60)

    with get_db_session() as db:
        try:
            # 1. Check if submission_regrades table already exists
            try:
                db.execute(text("SELECT id FROM submission_regrades LIMIT 1"))
                print("submission_regrades table already exists")
            except Exception:
                # Create the table
                db.execute(text("""
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
                print("Created submission_regrades table")

            # 2. Check if llm_response column already exists in regrades table
            try:
                db.execute(text("SELECT llm_response FROM regrades LIMIT 1"))
                print("llm_response column already exists in regrades table")
            except Exception:
                db.execute(text("ALTER TABLE regrades ADD COLUMN llm_response TEXT"))
                print("Added llm_response column to regrades table")

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
    add_submission_regrades_table()
