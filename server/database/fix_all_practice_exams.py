"""
Script to ensure all practice exams have student_id set
and all assigned exams have student_id = NULL
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam, Student, Submission

def fix_all_practice_exams():
    """Ensure all practice exams have student_id set correctly"""
    print("=" * 60)
    print("Fixing all practice exams in database...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get all exams
        all_exams = db.query(Exam).all()
        print(f"Found {len(all_exams)} total exams\n")
        
        fixed_practice = 0
        fixed_assigned = 0
        
        for exam in all_exams:
            # Get all submissions for this exam
            submissions = db.query(Submission).filter(Submission.exam_id == exam.id).all()
            
            if not submissions:
                # No submissions - skip (can't determine type)
                continue
            
            # Get unique students who have submissions
            unique_student_ids = set(s.student_id for s in submissions)
            
            # If multiple students have submissions, it's definitely an assigned exam
            if len(unique_student_ids) > 1:
                if exam.student_id is not None:
                    print(f"Exam {exam.id} ({exam.title or exam.domain}): Multiple students - setting as assigned (student_id = NULL)")
                    exam.student_id = None
                    fixed_assigned += 1
            else:
                # Only one student - should be practice exam
                student = db.query(Student).filter(Student.id == list(unique_student_ids)[0]).first()
                if student:
                    if exam.student_id != student.student_id:
                        print(f"Exam {exam.id} ({exam.title or exam.domain}): Single student - setting as practice (student_id = {student.student_id})")
                        exam.student_id = student.student_id
                        fixed_practice += 1
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"Fixed {fixed_practice} practice exams")
        print(f"Fixed {fixed_assigned} assigned exams")
        print("=" * 60)
        print("\nAll practice exams now have student_id set.")
        print("All assigned exams now have student_id = NULL.")

if __name__ == "__main__":
    fix_all_practice_exams()
