"""
Script to assign CS-related classes to all students in the database
Creates mock course numbers and distributes students across them
"""
import sys
import os
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Student, User

# CS-related course numbers
CS_CLASSES = [
    "CS101 - Introduction to Computer Science",
    "CS201 - Data Structures and Algorithms",
    "CS301 - Software Engineering",
    "CS401 - Database Systems",
    "CS501 - Machine Learning",
    "CS202 - Object-Oriented Programming",
    "CS302 - Web Development",
    "CS402 - Computer Networks",
    "CS502 - Artificial Intelligence",
    "CS103 - Programming Fundamentals"
]

def assign_classes_to_students():
    """Assign CS classes to all students in the database"""
    print("=" * 60)
    print("Assigning CS classes to students...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get all students
        all_students = db.query(Student).all()
        print(f"Found {len(all_students)} total students\n")
        
        # Get all user accounts that are instructors to exclude their student records
        instructor_users = db.query(User).filter(User.user_type == "instructor").all()
        instructor_student_ids = {user.student_id for user in instructor_users if user.student_id}
        instructor_usernames = {user.username.lower() for user in instructor_users}
        
        # Filter out students that are linked to instructor accounts
        students = [
            s for s in all_students 
            if s.id not in instructor_student_ids 
            and s.student_id.lower() not in instructor_usernames
        ]
        
        print(f"Assigning classes to {len(students)} students (excluding instructor accounts)\n")
        
        if len(students) == 0:
            print("No students found to assign classes to.")
            return
        
        # Distribute students across classes
        assigned_count = 0
        for i, student in enumerate(students):
            # Distribute students evenly across classes
            class_name = CS_CLASSES[i % len(CS_CLASSES)]
            student.class_name = class_name
            assigned_count += 1
            print(f"Assigned {class_name} to {student.name} ({student.student_id})")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"Successfully assigned classes to {assigned_count} students")
        print("=" * 60)
        print("\nClasses assigned:")
        for class_name in CS_CLASSES:
            count = sum(1 for s in students if s.class_name == class_name)
            print(f"  - {class_name}: {count} students")

if __name__ == "__main__":
    assign_classes_to_students()
