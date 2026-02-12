"""
Migration script to add prevent_tab_switching column to exams table
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from sqlalchemy import text
from server.core.database import get_db_session

def add_prevent_tab_switching():
    print("=" * 60)
    print("Adding prevent_tab_switching to exams table...")
    print("=" * 60)

    with get_db_session() as db:
        try:
            # Add prevent_tab_switching to exams table
            db.execute(text("ALTER TABLE exams ADD COLUMN prevent_tab_switching INTEGER DEFAULT 0"))
            print("Added prevent_tab_switching column to exams table")

            db.commit()
            print("Successfully added prevent_tab_switching field")

        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            print("\nNote: If the error says the column already exists, the migration may have already been run.")
            return
    print("=" * 60)

if __name__ == "__main__":
    add_prevent_tab_switching()
