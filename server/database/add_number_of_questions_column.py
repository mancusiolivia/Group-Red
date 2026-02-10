"""
Script to add number_of_questions column to exams table
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import sqlite3

def add_number_of_questions_column():
    """Add number_of_questions column to exams table"""
    print("=" * 60)
    print("Adding number_of_questions column to exams table...")
    print("=" * 60)
    
    # Get database path
    from server.core.config import DATABASE_PATH
    
    # Connect directly to SQLite to add column
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(exams)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'number_of_questions' in columns:
            print("Column 'number_of_questions' already exists in exams table.")
            conn.close()
            return
        
        # Add the column
        cursor.execute("ALTER TABLE exams ADD COLUMN number_of_questions INTEGER")
        conn.commit()
        print("Successfully added 'number_of_questions' column to exams table.")
        
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_number_of_questions_column()
