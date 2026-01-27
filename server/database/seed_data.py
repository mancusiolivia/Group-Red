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
from server.core.db_models import User, Instructor, Student

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
            db.flush()  # Get instructor.id
            print("[OK] Created default instructor")
        else:
            print("[OK] Default instructor already exists")
        
        # Create test students (if not exists)
        test_students = [
            {"student_id": "student_001", "name": "Test Student 1", "email": "student1@test.edu"},
            {"student_id": "student_002", "name": "Test Student 2", "email": "student2@test.edu"},
        ]
        
        created_students = {}
        for student_data in test_students:
            student = db.query(Student).filter(Student.student_id == student_data["student_id"]).first()
            if not student:
                student = Student(**student_data)
                db.add(student)
                db.flush()  # Get student.id
                created_students[student_data["student_id"]] = student
                print(f"[OK] Created test student: {student_data['student_id']}")
            else:
                created_students[student_data["student_id"]] = student
                print(f"[OK] Test student already exists: {student_data['student_id']}")
        
        # Create hard-coded users for login
        # Hard-coded credentials (plain text passwords as requested)
        student1_obj = created_students.get("student_001")
        student2_obj = created_students.get("student_002")
        
        hard_coded_users = [
            {
                "username": "admin",
                "password": "admin123",
                "user_type": "instructor",
                "instructor_id": instructor.id if instructor else None
            },
            {
                "username": "student1",
                "password": "password123",
                "user_type": "student",
                "student_id": student1_obj.id if student1_obj else None
            },
            {
                "username": "student2",
                "password": "password123",
                "user_type": "student",
                "student_id": student2_obj.id if student2_obj else None
            },
            {
                "username": "testuser",
                "password": "test123",
                "user_type": "student",
                "student_id": None
            }
        ]
        
        for user_data in hard_coded_users:
            user = db.query(User).filter(User.username == user_data["username"]).first()
            if not user:
                user = User(**user_data)
                db.add(user)
                print(f"[OK] Created user: {user_data['username']} (password: {user_data['password']})")
            else:
                print(f"[OK] User already exists: {user_data['username']}")
    
    print("=" * 60)
    print("Seed data creation complete!")
    print("=" * 60)
    print("\nHard-coded login credentials:")
    print("  - admin / admin123 (instructor)")
    print("  - student1 / password123 (student)")
    print("  - student2 / password123 (student)")
    print("  - testuser / test123 (student)")
    print("=" * 60)

if __name__ == "__main__":
    seed_initial_data()
