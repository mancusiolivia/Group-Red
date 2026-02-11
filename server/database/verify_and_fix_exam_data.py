"""
Verify and fix exam data - Ensures all assigned exams have instructor info
and all students have class names assigned
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.core.database import get_db_session
from server.core.db_models import Exam, Instructor, Student, Submission

def verify_and_fix_exam_data():
    """Verify and fix missing instructor and class data"""
    print("=" * 60)
    print("Verifying and fixing exam data...")
    print("=" * 60)
    
    with get_db_session() as db:
        # Check for exams without instructors
        exams_without_instructor = db.query(Exam).filter(
            Exam.instructor_id.is_(None)
        ).all()
        
        if exams_without_instructor:
            print(f"\nFound {len(exams_without_instructor)} exams without instructor_id")
            # Get default instructor
            default_instructor = db.query(Instructor).filter(
                Instructor.email == "default@system.edu"
            ).first()
            
            if not default_instructor:
                default_instructor = Instructor(
                    name="System Default Instructor",
                    email="default@system.edu",
                    domain_expertise="General"
                )
                db.add(default_instructor)
                db.flush()
                print("Created default instructor")
            
            for exam in exams_without_instructor:
                exam.instructor_id = default_instructor.id
                print(f"  - Assigned default instructor to exam {exam.id} ({exam.title or exam.domain})")
            
            db.commit()
            print(f"Fixed {len(exams_without_instructor)} exams\n")
        else:
            print("All exams have instructors assigned\n")
        
        # Check for students without class names
        students_without_class = db.query(Student).filter(
            (Student.class_name.is_(None)) | (Student.class_name == "")
        ).all()
        
        if students_without_class:
            print(f"Found {len(students_without_class)} students without class_name")
            
            # Import the class assignment function
            from server.database.assign_classes_to_students import CS_CLASSES
            
            for i, student in enumerate(students_without_class):
                class_name = CS_CLASSES[i % len(CS_CLASSES)]
                student.class_name = class_name
                print(f"  - Assigned {class_name} to {student.name} ({student.student_id})")
            
            db.commit()
            print(f"Fixed {len(students_without_class)} students\n")
        else:
            print("All students have class names assigned\n")
        
        # Verify assigned exams have proper data
        print("Verifying assigned exams (instructor-created exams)...")
        assigned_exams = db.query(Exam).filter(Exam.student_id.is_(None)).all()
        
        print(f"Found {len(assigned_exams)} assigned exams")
        for exam in assigned_exams:
            instructor = db.query(Instructor).filter(Instructor.id == exam.instructor_id).first()
            instructor_name = instructor.name if instructor else "MISSING"
            
            # Count submissions for this exam
            submission_count = db.query(Submission).filter(Submission.exam_id == exam.id).count()
            
            print(f"  - Exam {exam.id}: {exam.title or exam.domain}")
            print(f"    Instructor: {instructor_name} (ID: {exam.instructor_id})")
            print(f"    Submissions: {submission_count}")
            
            if not instructor:
                print(f"    WARNING: Instructor not found for exam {exam.id}!")
        
        print("\n" + "=" * 60)
        print("Verification complete!")
        print("=" * 60)

if __name__ == "__main__":
    verify_and_fix_exam_data()
