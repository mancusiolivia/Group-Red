"""
Script to check exam types and see which exams are showing up incorrectly
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam, Instructor, Student

def check_exam_types():
    """Check all exams and their types"""
    print("=" * 60)
    print("Checking exam types...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get default instructor
        default_instructor = db.query(Instructor).filter(Instructor.email == "default@system.edu").first()
        default_instructor_id = default_instructor.id if default_instructor else None
        
        # Get all exams
        all_exams = db.query(Exam).all()
        print(f"\nTotal exams: {len(all_exams)}\n")
        
        # Get all instructors
        all_instructors = db.query(Instructor).all()
        instructor_map = {inst.id: inst.email for inst in all_instructors}
        
        print("Exam breakdown:")
        print("-" * 60)
        
        for exam in all_exams:
            instructor_email = instructor_map.get(exam.instructor_id, "Unknown")
            is_default = exam.instructor_id == default_instructor_id
            is_practice = exam.student_id is not None
            is_assigned = exam.student_id is None
            
            exam_type = "PRACTICE" if is_practice else "ASSIGNED"
            instructor_type = "DEFAULT" if is_default else "REAL"
            
            print(f"Exam ID {exam.id}: {exam.title or exam.domain}")
            print(f"  Instructor: {instructor_email} ({instructor_type})")
            print(f"  Student ID: {exam.student_id or 'NULL'}")
            print(f"  Type: {exam_type}")
            print()
        
        # Count by type
        practice_exams = [e for e in all_exams if e.student_id is not None]
        assigned_exams = [e for e in all_exams if e.student_id is None]
        default_instructor_exams = [e for e in all_exams if e.instructor_id == default_instructor_id]
        
        print("=" * 60)
        print(f"Practice exams (student_id set): {len(practice_exams)}")
        print(f"Assigned exams (student_id NULL): {len(assigned_exams)}")
        print(f"Default instructor exams: {len(default_instructor_exams)}")
        print("=" * 60)
        
        # Check for problematic exams (assigned exams with default instructor)
        problematic = [e for e in assigned_exams if e.instructor_id == default_instructor_id]
        if problematic:
            print(f"\n⚠️  WARNING: {len(problematic)} exams are marked as ASSIGNED but use DEFAULT instructor!")
            print("These should be practice exams (student_id should be set)")
            for exam in problematic:
                print(f"  - Exam ID {exam.id}: {exam.title or exam.domain}")

if __name__ == "__main__":
    check_exam_types()
