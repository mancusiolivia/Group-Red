"""
Migration script to add student_id column to exams table
Run: python3 server/database/migrate_add_student_id_to_exams.py
"""
import os
import sys
import sqlite3

# Get paths
database_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(database_dir)
project_root = os.path.dirname(server_dir)

database_path = os.path.join(project_root, "data", "app.db")

def main():
    """Add student_id column to exams table if it doesn't exist"""
    if not os.path.exists(database_path):
        print(f"[ERROR] Database file not found at: {database_path}")
        print("Please start the server first to create the database.")
        sys.exit(1)
    
    print("=" * 60)
    print("Migration: Add student_id to exams table")
    print("=" * 60)
    print(f"Database: {database_path}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(exams)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'student_id' in columns:
            print("\n[INFO] Column 'student_id' already exists in exams table.")
            print("[INFO] Migration not needed.")
        else:
            print("\n[INFO] Adding 'student_id' column to exams table...")
            # Add student_id column (nullable String)
            cursor.execute("ALTER TABLE exams ADD COLUMN student_id TEXT")
            conn.commit()
            print("[SUCCESS] Column 'student_id' added successfully!")
        
        conn.close()
        print("\n[SUCCESS] Migration completed!")
        
    except Exception as e:
        print(f"\n[ERROR] Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
