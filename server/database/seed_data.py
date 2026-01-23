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
from server.core.db_models import Instructor, Student
from werkzeug.security import generate_password_hash  # For password hashing

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
            print("✓ Created default instructor")
        else:
            print("✓ Default instructor already exists")
        
        # Create test students (if not exists)
        test_students = [
            {"student_id": "student_001", "name": "Test Student 1", "email": "student1@test.edu"},
            {"student_id": "student_002", "name": "Test Student 2", "email": "student2@test.edu"},
        ]
        
        for student_data in test_students:
            student = db.query(Student).filter(Student.student_id == student_data["student_id"]).first()
            if not student:
                student = Student(**student_data)
                db.add(student)
                print(f"✓ Created test student: {student_data['student_id']}")
            else:
                print(f"✓ Test student already exists: {student_data['student_id']}")
        
        # If you add User model with authentication, create default admin here:
        # from server.core.db_models import User
        # admin = db.query(User).filter(User.username == "admin").first()
        # if not admin:
        #     admin = User(
        #         username="admin",
        #         email="admin@system.edu",
        #         password_hash=generate_password_hash("admin123"),  # Change this!
        #         role="admin"
        #     )
        #     db.add(admin)
        #     print("✓ Created default admin user")
    
    print("=" * 60)
    print("Seed data creation complete!")
    print("=" * 60)

if __name__ == "__main__":
    seed_initial_data()
