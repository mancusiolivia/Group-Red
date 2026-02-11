"""
Fix unstarted exams - Sets started_at to None for submissions that were assigned
but never actually started (have started_at set but no answers)

This fixes the issue where assigned exams show as "In Progress" even though
students haven't started them yet.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Submission, Answer, Exam

def fix_unstarted_exams():
    """Set started_at to None for submissions that have no answers"""
    print("=" * 60)
    print("Fixing unstarted exams...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Find all submissions that:
        # 1. Have started_at set (not None)
        # 2. Have no answers (never actually started)
        # 3. Are not submitted
        # 4. Are for assigned exams (exam.student_id is NULL)
        submissions = db.query(Submission).join(Exam).filter(
            Submission.started_at.isnot(None),
            Submission.submitted_at.is_(None),
            Exam.student_id.is_(None)  # Only assigned exams, not practice
        ).all()
        
        fixed_count = 0
        for submission in submissions:
            # Check if this submission has any answers
            answer_count = db.query(Answer).filter(Answer.submission_id == submission.id).count()
            
            if answer_count == 0:
                # This submission was assigned but never started - reset started_at
                print(f"Fixing submission {submission.id} (exam {submission.exam_id}, student {submission.student_id}): "
                      f"started_at={submission.started_at} -> None (no answers found)")
                submission.started_at = None
                fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"\nFixed {fixed_count} submission(s) - they will now show as 'Start' instead of 'In Progress'")
        else:
            print("\nNo unstarted exams found - all submissions are correctly marked")
    
    print("=" * 60)

if __name__ == "__main__":
    fix_unstarted_exams()
