"""
Script to fix exam types in the database
- Practice exams: exam.student_id should be set to the student's campus ID
- Assigned exams: exam.student_id should be NULL

This script identifies exams that need fixing based on submissions.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam, Student, Submission

def fix_exam_types():
    """Fix exam types based on submissions
    - Practice exams: exam.student_id should match the student's campus ID (student generated)
    - Assigned exams: exam.student_id should be NULL (instructor created and assigned)
    """
    print("=" * 60)
    print("Fixing exam types in database...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get all exams
        all_exams = db.query(Exam).all()
        print(f"Found {len(all_exams)} total exams")
        
        fixed_count = 0
        practice_count = 0
        assigned_count = 0
        
        for exam in all_exams:
            # Check if this exam has any submissions
            submissions = db.query(Submission).filter(Submission.exam_id == exam.id).all()
            
            if not submissions:
                # No submissions - if student_id is set, it's a practice exam that hasn't been taken yet
                # If student_id is NULL, it's an assigned exam that hasn't been assigned yet
                if exam.student_id is not None:
                    practice_count += 1
                else:
                    assigned_count += 1
                continue
            
            # Get unique students who have submissions for this exam
            unique_student_ids = set(s.student_id for s in submissions)
            unique_students = [db.query(Student).filter(Student.id == sid).first() for sid in unique_student_ids]
            unique_students = [s for s in unique_students if s is not None]
            
            if not unique_students:
                continue
            
            # Determine exam type:
            # - If multiple students have submissions, it's definitely an assigned exam
            # - If only one student has submissions AND exam.student_id matches that student, it's practice
            # - If only one student has submissions BUT exam.student_id is NULL or doesn't match, 
            #   it could be either, but we'll check if the exam was created by an instructor
            
            if len(unique_students) > 1:
                # Multiple students = definitely assigned exam
                if exam.student_id is not None:
                    print(f"Fixing exam {exam.id} ({exam.title or exam.domain}): Multiple students have submissions - setting as assigned exam (student_id = NULL)")
                    exam.student_id = None
                    fixed_count += 1
                assigned_count += 1
            else:
                # Only one student - check if it matches
                student = unique_students[0]
                if exam.student_id == student.student_id:
                    # Correctly marked as practice
                    practice_count += 1
                elif exam.student_id is None:
                    # Currently marked as assigned, but only one student
                    # Check if instructor_id exists (instructor created it)
                    # If instructor_id exists, it's assigned. Otherwise, it might be practice.
                    # For now, if student_id is NULL and only one student, we'll assume it's practice
                    # (student generated it before we started tracking student_id properly)
                    print(f"Fixing exam {exam.id} ({exam.title or exam.domain}): Only one student, setting as practice exam for student {student.student_id}")
                    exam.student_id = student.student_id
                    fixed_count += 1
                    practice_count += 1
                else:
                    # student_id is set but doesn't match - fix it
                    print(f"Fixing exam {exam.id} ({exam.title or exam.domain}): student_id mismatch, setting to {student.student_id}")
                    exam.student_id = student.student_id
                    fixed_count += 1
                    practice_count += 1
        
        db.commit()
        
        print("=" * 60)
        print(f"Fixed {fixed_count} exams")
        print(f"Practice exams: {practice_count}")
        print(f"Assigned exams: {assigned_count}")
        print("=" * 60)
        print("\nNote: If you have exams that should be assigned but are showing as practice,")
        print("you may need to manually set exam.student_id = NULL for those exams.")

if __name__ == "__main__":
    fix_exam_types()
