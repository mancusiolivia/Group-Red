"""
Seed data script - Creates initial users and test data
Run this after database initialization to set up default users
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Instructor, Student, User

def seed_initial_data():
    """Create initial users and test data"""
    print("=" * 60)
    print("Seeding initial database data...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Create default instructor (if not exists)
        instructor = db.query(Instructor).filter(Instructor.email == "default@system.edu").first()
        if not instructor:
            instructor = Instructor(
                name="System Default Instructor",
                email="default@system.edu",
                domain_expertise="General"
            )
            db.add(instructor)
            db.flush()  # Flush to get the ID
            print("[OK] Created default instructor")
        else:
            print("[OK] Default instructor already exists")
        
        # Create test students (if not exists)
        test_students = [
            {"student_id": "student_001", "name": "Test Student 1", "email": "student1@test.edu"},
            {"student_id": "student_002", "name": "Test Student 2", "email": "student2@test.edu"},
            {"student_id": "testuser", "name": "Test User", "email": "testuser@test.edu"},
        ]
        
        student_records = {}
        for student_data in test_students:
            student = db.query(Student).filter(Student.student_id == student_data["student_id"]).first()
            if not student:
                student = Student(**student_data)
                db.add(student)
                db.flush()  # Flush to get the ID
                print(f"[OK] Created test student: {student_data['student_id']}")
            else:
                print(f"[OK] Test student already exists: {student_data['student_id']}")
            student_records[student_data["student_id"]] = student
        
        # Create User accounts for authentication
        # Admin/Instructor user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password="admin123",
                user_type="instructor",
                instructor_id=instructor.id
            )
            db.add(admin_user)
            print("[OK] Created admin user account")
        else:
            print("[OK] Admin user already exists")
        
        # Student users
        user_accounts = [
            {"username": "student1", "password": "password123", "student_id": "student_001"},
            {"username": "student2", "password": "password123", "student_id": "student_002"},
            {"username": "testuser", "password": "test123", "student_id": "testuser"},
        ]
        
        for user_data in user_accounts:
            user = db.query(User).filter(User.username == user_data["username"]).first()
            if not user:
                student_record = student_records.get(user_data["student_id"])
                if student_record:
                    user = User(
                        username=user_data["username"],
                        password=user_data["password"],
                        user_type="student",
                        student_id=student_record.id
                    )
                    db.add(user)
                    print(f"[OK] Created user account: {user_data['username']}")
                else:
                    print(f"[WARNING] Student record not found for {user_data['username']}")
            else:
                print(f"[OK] User account already exists: {user_data['username']}")
    
    print("=" * 60)
    print("Seed data creation complete!")
    print("=" * 60)

if __name__ == "__main__":
    seed_initial_data()
