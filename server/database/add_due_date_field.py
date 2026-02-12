"""
Migration: Add due_date to exams table
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text

def add_due_date_field():
    """Add due_date column to exams table"""
    print("=" * 60)
    print("Adding due_date to exams table...")
    print("=" * 60)
    
    with get_db_session() as db:
        try:
            # Check if due_date column already exists in exams
            try:
                db.execute(text("SELECT due_date FROM exams LIMIT 1"))
                print("due_date column already exists in exams table")
            except:
                # Add due_date column to exams table
                db.execute(text("ALTER TABLE exams ADD COLUMN due_date TIMESTAMP"))
                print("Added due_date column to exams table")
            
            db.commit()
            print("Successfully added due_date field")
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return
    
    print("=" * 60)

if __name__ == "__main__":
    add_due_date_field()
