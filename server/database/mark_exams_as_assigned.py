"""
Script to mark specific exams as assigned (instructor-created)
Sets exam.student_id = NULL for exams that should be assigned exams
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam

def mark_exams_as_assigned():
    """Mark exams as assigned by setting student_id = NULL"""
    print("=" * 60)
    print("Marking exams as assigned (instructor-created)...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Get all exams that currently have student_id set
        practice_exams = db.query(Exam).filter(Exam.student_id.isnot(None)).all()
        
        print(f"Found {len(practice_exams)} exams with student_id set")
        print("\nExams that are currently marked as practice:")
        for exam in practice_exams:
            print(f"  - Exam {exam.id}: {exam.title or exam.domain} (student_id: {exam.student_id})")
        
        print("\n" + "=" * 60)
        print("To mark an exam as assigned (instructor-created), set its student_id to NULL")
        print("=" * 60)
        
        # Option 1: Mark all exams with student_id set as assigned (if they should be)
        # Uncomment the following to mark ALL practice exams as assigned:
        # for exam in practice_exams:
        #     print(f"Marking exam {exam.id} ({exam.title or exam.domain}) as assigned")
        #     exam.student_id = None
        
        # Option 2: Mark specific exams by ID
        # Update this list with the exam IDs that should be assigned
        exam_ids_to_mark_as_assigned = []  # Add exam IDs here, e.g., [6, 8, 9]
        
        if exam_ids_to_mark_as_assigned:
            for exam_id in exam_ids_to_mark_as_assigned:
                exam = db.query(Exam).filter(Exam.id == exam_id).first()
                if exam:
                    print(f"Marking exam {exam.id} ({exam.title or exam.domain}) as assigned")
                    exam.student_id = None
        
        db.commit()
        print("\nDone!")

if __name__ == "__main__":
    mark_exams_as_assigned()
