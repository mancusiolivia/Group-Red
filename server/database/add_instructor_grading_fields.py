"""
Migration: Add instructor grading fields to answers table
Adds fields to track manual instructor grading and feedback
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text

def add_instructor_grading_fields():
    """Add instructor grading fields to answers table"""
    print("=" * 60)
    print("Adding instructor grading fields to answers table...")
    print("=" * 60)
    
    with get_db_session() as db:
        try:
            # Check if instructor_edited column already exists
            try:
                db.execute(text("SELECT instructor_edited FROM answers LIMIT 1"))
                print("instructor_edited column already exists in answers table")
            except:
                # Add instructor_edited column (0 = false, 1 = true)
                db.execute(text("ALTER TABLE answers ADD COLUMN instructor_edited INTEGER DEFAULT 0"))
                print("Added instructor_edited column to answers table")
            
            # Check if instructor_score column already exists
            try:
                db.execute(text("SELECT instructor_score FROM answers LIMIT 1"))
                print("instructor_score column already exists in answers table")
            except:
                # Add instructor_score column
                db.execute(text("ALTER TABLE answers ADD COLUMN instructor_score REAL"))
                print("Added instructor_score column to answers table")
            
            # Check if instructor_feedback column already exists
            try:
                db.execute(text("SELECT instructor_feedback FROM answers LIMIT 1"))
                print("instructor_feedback column already exists in answers table")
            except:
                # Add instructor_feedback column
                db.execute(text("ALTER TABLE answers ADD COLUMN instructor_feedback TEXT"))
                print("Added instructor_feedback column to answers table")
            
            # Check if instructor_edited_at column already exists
            try:
                db.execute(text("SELECT instructor_edited_at FROM answers LIMIT 1"))
                print("instructor_edited_at column already exists in answers table")
            except:
                # Add instructor_edited_at column
                db.execute(text("ALTER TABLE answers ADD COLUMN instructor_edited_at TIMESTAMP"))
                print("Added instructor_edited_at column to answers table")
            
            db.commit()
            print("Successfully added instructor grading fields")
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return
    
    print("=" * 60)

if __name__ == "__main__":
    add_instructor_grading_fields()
