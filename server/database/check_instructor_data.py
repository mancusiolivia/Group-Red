"""
Quick script to check instructor data
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Instructor, Exam, Student

with get_db_session() as db:
    # Check all instructors
    instructors = db.query(Instructor).all()
    print("Instructors in database:")
    for inst in instructors:
        print(f"  ID: {inst.id}, Name: {inst.name}, Email: {inst.email}")
    
    # Check exam with instructor
    exam = db.query(Exam).filter(Exam.id == 4).first()
    if exam:
        instructor = db.query(Instructor).filter(Instructor.id == exam.instructor_id).first()
        print(f"\nExam 4 (Bio Exam):")
        print(f"  Instructor ID: {exam.instructor_id}")
        print(f"  Instructor Name: {instructor.name if instructor else 'NOT FOUND'}")
    
    # Check student
    student = db.query(Student).filter(Student.student_id == "student_001").first()
    if student:
        print(f"\nStudent student_001:")
        print(f"  ID: {student.id}")
        print(f"  Name: {student.name}")
        print(f"  Class Name: {student.class_name}")
