"""
Migration: Add time_limit_minutes to exams and end_time to submissions
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from sqlalchemy import text

def add_time_limit_fields():
    """Add time_limit_minutes to exams and end_time to submissions"""
    print("=" * 60)
    print("Adding time_limit_minutes to exams and end_time to submissions...")
    print("=" * 60)
    
    with get_db_session() as db:
        try:
            # Check if time_limit_minutes column already exists in exams
            try:
                db.execute(text("SELECT time_limit_minutes FROM exams LIMIT 1"))
                print("time_limit_minutes column already exists in exams table")
            except:
                # Add time_limit_minutes column to exams table
                db.execute(text("ALTER TABLE exams ADD COLUMN time_limit_minutes INTEGER"))
                print("Added time_limit_minutes column to exams table")
            
            # Check if end_time column already exists in submissions
            try:
                db.execute(text("SELECT end_time FROM submissions LIMIT 1"))
                print("end_time column already exists in submissions table")
            except:
                # Add end_time column to submissions table
                db.execute(text("ALTER TABLE submissions ADD COLUMN end_time TIMESTAMP"))
                print("Added end_time column to submissions table")
            
            db.commit()
            print("Successfully added time limit fields")
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return
    
    print("=" * 60)

if __name__ == "__main__":
    add_time_limit_fields()
