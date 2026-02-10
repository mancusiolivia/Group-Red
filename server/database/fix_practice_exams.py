"""
Script to mark student-generated exams as practice exams
Sets exam.student_id to the student's campus ID for practice exams
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam, Student, Submission

def fix_practice_exams():
    """Mark all student-generated exams as practice exams"""
    print("=" * 60)
    print("Marking student-generated exams as practice exams...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get all exams
        all_exams = db.query(Exam).all()
        print(f"Found {len(all_exams)} total exams\n")
        
        fixed_count = 0
        
        for exam in all_exams:
            # Get all submissions for this exam
            submissions = db.query(Submission).filter(Submission.exam_id == exam.id).all()
            
            if not submissions:
                continue
            
            # Get unique students who have submissions
            unique_student_ids = set(s.student_id for s in submissions)
            
            # If only one student has submissions, it's likely a practice exam
            # (student generated it for themselves)
            if len(unique_student_ids) == 1:
                student = db.query(Student).filter(Student.id == list(unique_student_ids)[0]).first()
                if student:
                    # Check if exam.student_id is NULL or doesn't match
                    if exam.student_id != student.student_id:
                        print(f"Marking exam {exam.id} ({exam.title or exam.domain}) as practice exam for student {student.student_id}")
                        exam.student_id = student.student_id
                        fixed_count += 1
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"Fixed {fixed_count} exams - marked as practice exams")
        print("=" * 60)
        print("\nPractice exams now have student_id set.")
        print("Only instructor-created exams (student_id = NULL) will appear in Assigned Exams.")

if __name__ == "__main__":
    fix_practice_exams()
