"""
Script to set specific exams as assigned (instructor-created)
Sets exam.student_id = NULL for exams that should be assigned exams
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam

def set_exams_as_assigned():
    """Set specific exams as assigned by setting student_id = NULL
    This marks them as instructor-created/assigned exams, not practice exams
    """
    print("=" * 60)
    print("Setting exams as assigned (instructor-created)...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Find exams by title that should be assigned (instructor-created)
        # These are exams that should appear in the Assigned Exams section, not Practice Exams
        exam_titles = ['Taco Exam', 'Joes Exam', 'Computer Science Exam']
        
        for title in exam_titles:
            exams = db.query(Exam).filter(Exam.title == title).all()
            for exam in exams:
                if exam.student_id is not None:
                    print(f"Setting exam {exam.id} ({exam.title}) as assigned (student_id: {exam.student_id} -> NULL)")
                    exam.student_id = None
                else:
                    print(f"Exam {exam.id} ({exam.title}) is already marked as assigned")
        
        db.commit()
        print("\nDone! These exams will now appear ONLY in the Assigned Exams section.")
        print("They will NOT appear in Practice Exams.")

if __name__ == "__main__":
    set_exams_as_assigned()
