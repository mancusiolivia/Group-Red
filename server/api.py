"""
All API endpoints for the Essay Testing System
Handles all GET, POST, and other HTTP endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import json
from datetime import datetime

from pydantic import BaseModel

from server.core.models import QuestionRequest, StudentResponse, GradingRequest
from server.core.llm_service import call_together_ai, extract_json_from_response, QUESTION_GENERATION_TEMPLATE, GRADING_TEMPLATE
from server.core.database import get_db
from server.core.db_models import (
    User, Instructor, Student, Exam, Question, Rubric,
    Submission, Answer
)
from server.core.config import TOGETHER_AI_MODEL
from server.core.auth import create_session, delete_session, get_current_user, require_auth

router = APIRouter()


# ============================================================================
# Authentication Models
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    username: str = None
    user_type: str = None


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/api/login", tags=["auth"], response_model=LoginResponse)
async def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login endpoint - validates username/password from database"""
    # Query user from database
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check password (hard-coded, plain text comparison for now)
    if user.password != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create session
    session_token = create_session(user.id, user.username)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=86400  # 24 hours
    )
    
    return LoginResponse(
        success=True,
        message="Login successful",
        username=user.username,
        user_type=user.user_type
    )


@router.post("/api/logout", tags=["auth"])
async def logout(request: Request, response: Response):
    """Logout endpoint - clears session"""
    session_token = request.cookies.get("session_token")
    if session_token:
        delete_session(session_token)
    
    # Clear cookie
    response.delete_cookie(key="session_token", samesite="lax")
    
    return {"success": True, "message": "Logged out successfully"}


@router.get("/api/me", tags=["auth"])
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "user_type": current_user.user_type,
        "student_id": current_user.student_id,
        "instructor_id": current_user.instructor_id
    }


def get_or_create_default_instructor(db: Session) -> Instructor:
    """Get or create a default instructor for exams"""
    instructor = db.query(Instructor).filter(Instructor.email == "default@system.edu").first()
    if not instructor:
        instructor = Instructor(
            name="System Default Instructor",
            email="default@system.edu",
            domain_expertise="General"
        )
        db.add(instructor)
        db.commit()
        db.refresh(instructor)
    return instructor


def get_or_create_student(db: Session, student_id: str, name: str = None, email: str = None) -> Student:
    """Get or create a student by student_id"""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        student = Student(
            student_id=student_id,
            name=name or f"Student {student_id}",
            email=email
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


# ============================================================================
# Test Endpoint
# ============================================================================

@router.get("/test", tags=["test"])
async def test_route():
    """Test route to verify server is working"""
    print("=" * 50)
    print("TEST ROUTE HIT!")
    print("=" * 50)
    return {"message": "Test route works!", "server": "essay-testing-system"}


# ============================================================================
# Question Generation Endpoints
# ============================================================================

@router.post("/api/generate-questions", tags=["questions"])
async def generate_questions(
    request: QuestionRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate essay questions using LLM and store in database
    
    If a student is authenticated, their student_id will be stored with the exam.
    This allows students to retrieve all their past questions later.
    """
    import time
    import sys
    start_time = time.time()
    
    # Force flush stdout to ensure logs appear immediately
    print(f"DEBUG: [START] Generate questions request - Domain: {request.domain}, Questions: {request.num_questions}", flush=True)
    sys.stdout.flush()
    
    # Call LLM BEFORE opening database transaction to avoid long-held locks
    llm_response = None
    question_data = None
    
    try:
        # Complete the prompt template
        prompt = QUESTION_GENERATION_TEMPLATE.format(
            domain=request.domain,
            professor_instructions=request.professor_instructions or "No specific instructions provided.",
            num_questions=request.num_questions
        )
        print(f"DEBUG: Prompt created ({len(prompt)} chars)", flush=True)
        sys.stdout.flush()

        # Call LLM first (this can take time - don't hold DB lock during this)
        print(f"DEBUG: Starting LLM call...", flush=True)
        sys.stdout.flush()
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON."
        )
        print(f"DEBUG: LLM call completed", flush=True)
        sys.stdout.flush()

        # Parse LLM response BEFORE database operations
        try:
            question_data = extract_json_from_response(llm_response)
            print(f"DEBUG: Successfully parsed JSON response")
            print(
                f"DEBUG: Response type: {type(question_data)}, Is list: {isinstance(question_data, list)}")
            if isinstance(question_data, list):
                print(
                    f"DEBUG: Number of questions in response: {len(question_data)}")
        except ValueError as e:
            print(f"DEBUG: JSON extraction failed: {e}")
            # Provide a user-friendly error message
            error_message = (
                "The AI returned a response that couldn't be parsed as JSON. "
                "This sometimes happens with AI responses. Please try generating questions again."
            )
            # Include the original error in logs but not in user-facing message
            print(f"DEBUG: Full error details: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        # Now do database operations (quick - only after LLM call completes)
        print(f"DEBUG: Starting database operations...")

        # Handle multiple questions or single question
        if isinstance(question_data, dict):
            print("DEBUG: LLM returned single question object, converting to list")
            question_data = [question_data]
        elif isinstance(question_data, list):
            print(f"DEBUG: LLM returned array with {len(question_data)} question(s)")
            if len(question_data) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="LLM returned an empty array. No questions were generated."
                )
            if len(question_data) < request.num_questions:
                print(
                    f"DEBUG: Warning - requested {request.num_questions} questions but got {len(question_data)}")
        else:
            print(f"DEBUG: Unexpected response type: {type(question_data)}")
            question_data = [question_data]
        
        # Get or create default instructor
        instructor = get_or_create_default_instructor(db)
        
        # Get student_id if user is authenticated and is a student
        student_id_value = None
        if current_user and current_user.user_type == "student":
            if current_user.student_id:
                # Get the student's campus ID (student_id string)
                student = db.query(Student).filter(Student.id == current_user.student_id).first()
                if student:
                    student_id_value = student.student_id
            else:
                # If no student_id linked, try to get/create by username
                student = get_or_create_student(db, current_user.username, name=current_user.username)
                student_id_value = student.student_id
        
        # Create exam in database
        exam = Exam(
            instructor_id=instructor.id,
            student_id=student_id_value,  # Track which student generated this exam
            domain=request.domain,
            title=f"{request.domain} Exam",
            instructions_to_llm=request.professor_instructions,
            model_name=TOGETHER_AI_MODEL,
            temperature=0.7
        )
        db.add(exam)
        db.flush()  # Get exam.id without committing
        
        questions_list = []
        
        # Create questions in database
        for idx, q_data in enumerate(question_data):
            if not isinstance(q_data, dict):
                print(
                    f"DEBUG: Warning - question {idx} is not a dict: {type(q_data)}")
                continue
            
            # Calculate total points from rubric
            rubric_data = q_data.get("grading_rubric", {})
            total_points = rubric_data.get("total_points", 10.0)
            
            question = Question(
                exam_id=exam.id,
                q_index=idx + 1,  # 1-indexed
                prompt=q_data.get("question_text", ""),
                background_info=q_data.get("background_info", ""),
                model_answer=None,  # Can be added later
                points_possible=total_points
            )
            db.add(question)
            db.flush()  # Get question.id
            
            # Store rubric
            rubric_text = json.dumps(rubric_data, indent=2)
            rubric = Rubric(
                question_id=question.id,
                rubric_text=rubric_text
            )
            db.add(rubric)
            
            # Build response format for API (keeping backward compatibility)
            questions_list.append({
                "question_id": str(question.id),  # Convert to string for compatibility
                "background_info": q_data.get("background_info", ""),
                "question_text": q_data.get("question_text", ""),
                "grading_rubric": rubric_data,
                "domain_info": q_data.get("domain_info", "")
            })
        
        if len(questions_list) == 0:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="No valid questions were generated from the LLM response."
            )
        
        # Commit all changes
        db.commit()
        db.refresh(exam)
        
        elapsed = time.time() - start_time
        print(f"DEBUG: [SUCCESS] Created exam {exam.id} with {len(questions_list)} question(s) in {elapsed:.2f}s")
        return {
            "exam_id": str(exam.id),  # Convert to string for compatibility
            "questions": questions_list
        }
    
    except HTTPException as e:
        # Re-raise HTTP exceptions as-is (already user-friendly)
        try:
            db.rollback()
        except:
            pass  # Session might already be closed
        raise e
    except Exception as e:
        elapsed = time.time() - start_time
        # Log the full error for debugging
        print(f"DEBUG: [ERROR] Unexpected error in generate_questions after {elapsed:.2f}s: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to rollback, but don't fail if session is already closed
        try:
            db.rollback()
            print(f"DEBUG: [ERROR] Database rollback completed")
        except Exception as rollback_error:
            print(f"DEBUG: [ERROR] Rollback failed (session may be closed): {rollback_error}")
        
        # Return a more informative error message
        error_detail = f"An error occurred while generating questions: {str(e)}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.get("/api/student/{student_id}/questions", tags=["questions"])
async def get_student_questions(
    student_id: str,
    db: Session = Depends(get_db)
):
    """Get all questions that have been generated for a specific student
    
    This endpoint retrieves all exam questions that were generated by or for
    the student identified by student_id. Questions are organized by exam.
    
    Args:
        student_id: The student's campus ID (string)
    
    Returns:
        List of exams with their questions, ordered by creation date (newest first)
    """
    # Verify student exists
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student with ID '{student_id}' not found"
        )
    
    # Get all exams generated by this student
    exams = db.query(Exam).filter(Exam.student_id == student_id)\
        .order_by(Exam.created_at.desc()).all()
    
    result = []
    for exam in exams:
        # Get all questions for this exam
        questions = db.query(Question).filter(Question.exam_id == exam.id)\
            .order_by(Question.q_index).all()
        
        # Get rubrics for each question
        questions_data = []
        for question in questions:
            rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
            rubric_data = {}
            if rubric:
                try:
                    rubric_data = json.loads(rubric.rubric_text)
                except:
                    rubric_data = {"raw": rubric.rubric_text}
            
            questions_data.append({
                "question_id": str(question.id),
                "exam_id": str(exam.id),
                "q_index": question.q_index,
                "question_text": question.prompt,
                "background_info": question.background_info or "",
                "points_possible": question.points_possible,
                "grading_rubric": rubric_data,
                "created_at": question.created_at.isoformat() if question.created_at else None
            })
        
        result.append({
            "exam_id": str(exam.id),
            "domain": exam.domain,
            "title": exam.title,
            "instructions_to_llm": exam.instructions_to_llm,
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
            "questions": questions_data
        })
    
    return {
        "student_id": student_id,
        "student_name": student.name,
        "total_exams": len(result),
        "total_questions": sum(len(exam["questions"]) for exam in result),
        "exams": result
    }


# ============================================================================
# Exam Endpoints
# ============================================================================

@router.get("/api/my-exams", tags=["exams"])
async def get_my_exams(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all past exams for the current authenticated user"""
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
        student_id = student.id
    else:
        # Create or get student using username
        student = get_or_create_student(db, current_user.username, name=current_user.username)
        student_id = student.id
    
    # Get all submissions for this student
    submissions = db.query(Submission).filter(
        Submission.student_id == student_id
    ).order_by(Submission.started_at.desc()).all()
    
    if not submissions:
        return {"exams": []}
    
    # Get unique exams and calculate scores
    exam_data = {}
    for submission in submissions:
        exam_id = submission.exam_id
        
        # Skip if we already processed this exam
        if exam_id in exam_data:
            continue
        
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            continue
        
        # Get all answers for this submission
        answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
        
        # Calculate total score
        total_score = 0.0
        max_score = 0.0
        for answer in answers:
            if answer.llm_score is not None:
                total_score += float(answer.llm_score)
            # Get max points from question
            question = db.query(Question).filter(Question.id == answer.question_id).first()
            if question:
                max_score += float(question.points_possible)
        
        # Get question count
        question_count = db.query(Question).filter(Question.exam_id == exam_id).count()
        
        exam_data[exam_id] = {
            "exam_id": str(exam.id),
            "domain": exam.domain,
            "title": exam.title or f"{exam.domain} Exam",
            "submission_id": str(submission.id),
            "started_at": submission.started_at.isoformat() if submission.started_at else None,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "total_score": round(total_score, 2),
            "max_score": round(max_score, 2),
            "percentage": round((total_score / max_score * 100), 2) if max_score > 0 else 0.0,
            "question_count": question_count
        }
    
    return {"exams": list(exam_data.values())}


@router.post("/api/exam/{exam_id}/start", tags=["exams"])
async def start_exam(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create or get an in-progress submission for an exam"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    # Get or create in-progress submission
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        # Create new submission
        submission = Submission(
            exam_id=exam_id_int,
            student_id=student.id,
            started_at=datetime.utcnow()
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
    
    return {
        "submission_id": str(submission.id),
        "exam_id": str(exam.id),
        "started_at": submission.started_at.isoformat() if submission.started_at else None
    }


@router.post("/api/exam/{exam_id}/submit", tags=["exams"])
async def submit_exam(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Mark an exam submission as submitted (moves it to Past Exams)"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    # Get in-progress submission
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No in-progress exam found")
    
    # Mark as submitted
    submission.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(submission)
    
    # Force SQLite checkpoint to ensure change is immediately visible
    try:
        from sqlalchemy import text
        db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        db.commit()
    except Exception as e:
        print(f"DEBUG: Checkpoint warning (non-critical): {e}")
    
    return {
        "success": True,
        "message": "Exam submitted successfully",
        "submission_id": str(submission.id),
        "exam_id": str(exam.id),
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
    }


@router.get("/api/my-exams/in-progress", tags=["exams"])
async def get_in_progress_exams(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all in-progress exams (not yet submitted) for the current authenticated user"""
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
        student_id = student.id
    else:
        # Create or get student using username
        student = get_or_create_student(db, current_user.username, name=current_user.username)
        student_id = student.id
    
    # Get all in-progress submissions (submitted_at is None)
    submissions = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).all()
    
    if not submissions:
        return {"exams": []}
    
    # Get exam details and current progress
    exam_data = []
    for submission in submissions:
        exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if not exam:
            continue
        
        # Get questions for this exam
        questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
        
        # Get answers already submitted for this in-progress exam
        answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
        answered_count = len(answers)
        
        exam_data.append({
            "exam_id": str(exam.id),
            "submission_id": str(submission.id),
            "domain": exam.domain,
            "title": exam.title or f"{exam.domain} Exam",
            "started_at": submission.started_at.isoformat() if submission.started_at else None,
            "question_count": len(questions),
            "answered_count": answered_count,
            "progress_percentage": round((answered_count / len(questions) * 100), 1) if questions else 0.0
        })
    
    return {"exams": exam_data}


@router.delete("/api/exam/{exam_id}/in-progress", tags=["exams"])
async def delete_in_progress_exam(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete an in-progress exam submission"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    # Get in-progress submission
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No in-progress exam found")
    
    # Delete the submission (cascade will delete associated answers)
    db.delete(submission)
    db.commit()
    
    return {"message": "In-progress exam deleted successfully", "exam_id": str(exam_id)}


@router.get("/api/exam/{exam_id}/resume", tags=["exams"])
async def get_exam_to_resume(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get exam data for resuming an in-progress exam"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    # Get in-progress submission
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No in-progress exam found")
    
    # Load questions with rubrics, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_list = []
    for q in questions:
        # Get rubric for question
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        # Get existing answer if any (including grade information)
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id
        ).first()
        
        # Include answer with grade information if it exists
        existing_answer_data = None
        if answer:
            existing_answer_data = {
                "response_text": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "graded_at": answer.graded_at.isoformat() if answer.graded_at else None
            }
        
        questions_list.append({
            "question_id": str(q.id),
            "background_info": q.background_info or "",
            "question_text": q.prompt,
            "grading_rubric": rubric_data,
            "domain_info": exam.domain,
            "existing_answer": answer.student_answer if answer else None,
            "existing_answer_data": existing_answer_data  # Include full answer data with grades
        })
    
    return {
        "exam_id": str(exam.id),
        "domain": exam.domain,
        "title": exam.title or f"{exam.domain} Exam",
        "submission_id": str(submission.id),
        "questions": questions_list
    }


@router.get("/api/exam/{exam_id}/my-results", tags=["exams"])
async def get_my_exam_results(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get exam results for the current authenticated user"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        # Create or get student using username
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found for this exam")
    
    # Load questions with rubrics, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_with_answers = []
    for q in questions:
        # Get rubric for question
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        # Get answer for this question (one-to-one mapping: one answer per question)
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id  # Exact one-to-one mapping
        ).first()
        
        answer_data = None
        if answer:
            answer_data = {
                "answer_id": str(answer.id),
                "response_text": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "graded_at": answer.graded_at.isoformat() if answer.graded_at else None,
                "grading_model_name": answer.grading_model_name
            }
        
        questions_with_answers.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "question_text": q.prompt,
            "background_info": q.background_info or "",
            "points_possible": float(q.points_possible),
            "grading_rubric": rubric_data,
            "answer": answer_data  # One-to-one: exactly one answer or None
        })
    
    return {
        "exam_id": str(exam.id),
        "exam_title": exam.title,
        "domain": exam.domain,
        "submission_id": str(submission.id),
        "student_id": student.student_id,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "questions_with_answers": questions_with_answers  # Each question has exactly one answer or None
    }


@router.get("/api/exam/{exam_id}/with-answers", tags=["exams"])
async def get_exam_with_answers(exam_id: str, student_id: str, db: Session = Depends(get_db)):
    """Get exam with all questions and their corresponding answers mapped one-to-one"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student and submission
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found for this student and exam")
    
    # Load questions with rubrics, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_with_answers = []
    for q in questions:
        # Get rubric for question
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        # Get answer for this question (one-to-one mapping: one answer per question)
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id  # Exact one-to-one mapping
        ).first()
        
        answer_data = None
        if answer:
            answer_data = {
                "answer_id": str(answer.id),
                "response_text": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "graded_at": answer.graded_at.isoformat() if answer.graded_at else None,
                "grading_model_name": answer.grading_model_name
            }
        
        questions_with_answers.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "question_text": q.prompt,
            "points_possible": float(q.points_possible),
            "grading_rubric": rubric_data,
            "answer": answer_data  # One-to-one: exactly one answer or None
        })
    
    return {
        "exam_id": str(exam.id),
        "exam_title": exam.title,
        "domain": exam.domain,
        "submission_id": str(submission.id),
        "student_id": student_id,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "questions_with_answers": questions_with_answers  # Each question has exactly one answer or None
    }


@router.get("/api/exam/{exam_id}", tags=["exams"])
async def get_exam(exam_id: str, student_id: str = None, db: Session = Depends(get_db)):
    """Get exam details from database with optional student answers mapped one-to-one"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get student and submission if student_id is provided
    submission = None
    if student_id:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if student:
            submission = db.query(Submission).filter(
                Submission.exam_id == exam_id_int,
                Submission.student_id == student.id
            ).order_by(Submission.started_at.desc()).first()
    
    # Load questions with rubrics, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_list = []
    for q in questions:
        # Get rubric for question
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        # Get answer for this question if submission exists (one-to-one mapping)
        answer_data = None
        if submission:
            answer = db.query(Answer).filter(
                Answer.submission_id == submission.id,
                Answer.question_id == q.id
            ).first()
            
            if answer:
                answer_data = {
                    "answer_id": str(answer.id),
                    "response_text": answer.student_answer,
                    "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                    "llm_feedback": answer.llm_feedback or "",
                    "graded_at": answer.graded_at.isoformat() if answer.graded_at else None,
                    "grading_model_name": answer.grading_model_name
                }
        
        questions_list.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "background_info": q.background_info or "",
            "question_text": q.prompt,
            "grading_rubric": rubric_data,
            "domain_info": exam.domain or "",
            "points_possible": float(q.points_possible),
            "answer": answer_data  # One-to-one mapping: None if no answer exists
        })
    
    return {
        "exam_id": str(exam.id),
        "domain": exam.domain,
        "title": exam.title,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "questions": questions_list
    }


# ============================================================================
# Response Submission and Grading Endpoints
# ============================================================================

@router.post("/api/submit-response", tags=["responses"])
async def submit_response(
    response: StudentResponse, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Submit student response and get graded result, store in database"""
    try:
        # Get exam and question
        try:
            exam_id_int = int(response.exam_id)
            question_id_int = int(response.question_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid exam_id or question_id format")
        
        exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        question = db.query(Question).filter(
            Question.id == question_id_int,
            Question.exam_id == exam_id_int
        ).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
        if not rubric:
            raise HTTPException(status_code=500, detail="Rubric not found for question")
        
        # Parse rubric
        try:
            rubric_data = json.loads(rubric.rubric_text)
        except:
            rubric_data = {"text": rubric.rubric_text}
        
        # Prepare grading prompt
        rubric_str = json.dumps(rubric_data, indent=2)
        prompt = GRADING_TEMPLATE.format(
            question_text=question.prompt,
            grading_rubric=rubric_str,
            background_info=question.background_info or "",
            domain_info=exam.domain or "",
            student_response=response.response_text,
            time_spent=response.time_spent_seconds or 0
        )

        # Call LLM for grading
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON with accurate scores."
        )

        # Parse grading result
        grade_data = extract_json_from_response(llm_response)
        
        # Get student from authenticated user
        if current_user.user_type == "student" and current_user.student_id:
            # User is linked to a student record
            student = db.query(Student).filter(Student.id == current_user.student_id).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student record not found for user")
        else:
            # Create or get student using username as student_id
            student_id_str = current_user.username
            student = get_or_create_student(db, student_id_str, name=current_user.username)
        
        # Create or get in-progress submission (submitted_at IS NULL)
        submission = db.query(Submission).filter(
            Submission.exam_id == exam_id_int,
            Submission.student_id == student.id,
            Submission.submitted_at.is_(None)  # Only get in-progress submissions
        ).order_by(Submission.started_at.desc()).first()
        
        if not submission:
            # Create new in-progress submission (submitted_at should be None, not set)
            submission = Submission(
                exam_id=exam_id_int,
                student_id=student.id,
                started_at=datetime.utcnow(),
                submitted_at=None  # In-progress, not submitted yet
            )
            db.add(submission)
            db.flush()
        
        # Check if answer already exists for this submission+question (one-to-one constraint)
        existing_answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == question_id_int
        ).first()
        
        if existing_answer:
            # Update existing answer (one-to-one: only one answer per question per submission)
            existing_answer.student_answer = response.response_text
            existing_answer.llm_score = float(grade_data.get("total_score", 0.0))
            existing_answer.llm_feedback = grade_data.get("feedback", "")
            existing_answer.graded_at = datetime.utcnow()
            existing_answer.grading_model_name = TOGETHER_AI_MODEL
            existing_answer.grading_temperature = 0.7
            answer = existing_answer
        else:
            # Create new answer record (one-to-one mapping: question_id -> answer)
            answer = Answer(
                submission_id=submission.id,
                question_id=question_id_int,  # Ensures exact one-to-one mapping
                student_answer=response.response_text,
                llm_score=float(grade_data.get("total_score", 0.0)),
                llm_feedback=grade_data.get("feedback", ""),
                graded_at=datetime.utcnow(),
                grading_model_name=TOGETHER_AI_MODEL,
                grading_temperature=0.7
            )
            db.add(answer)
        
        db.commit()
        db.refresh(answer)
        
        # Refresh submission to get latest state before checking completion
        db.refresh(submission)
        
        # Check if all questions for this exam have been answered
        # If so, mark the submission as submitted
        all_questions = db.query(Question).filter(Question.exam_id == exam_id_int).all()
        answered_questions = db.query(Answer).filter(Answer.submission_id == submission.id).all()
        
        # Mark submission as submitted if all questions have been answered
        if len(answered_questions) >= len(all_questions) and submission.submitted_at is None:
            submission.submitted_at = datetime.utcnow()
            db.commit()
            db.refresh(submission)
            # Force SQLite checkpoint to ensure change is immediately visible
            try:
                from sqlalchemy import text
                db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
                db.commit()
            except Exception as e:
                print(f"DEBUG: Checkpoint warning (non-critical): {e}")
            print(f"DEBUG: All questions answered, marking submission {submission.id} as submitted")
        
        # Create grade result response
        grade_result = {
            "question_id": response.question_id,
            "scores": grade_data.get("scores", {}),
            "total_score": grade_data.get("total_score", 0.0),
            "explanation": grade_data.get("explanation", ""),
            "feedback": grade_data.get("feedback", "")
        }
        
        print(f"DEBUG: Successfully stored answer {answer.id} for submission {submission.id}")
        return grade_result
    
    except HTTPException as e:
        db.rollback()
        # Re-raise HTTPException with its original detail message
        raise e
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Unexpected error in submit_response: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while grading your response. Please try again."
        )


@router.get("/api/response/{exam_id}/{question_id}", tags=["responses"])
async def get_response(exam_id: str, question_id: str, student_id: str = None, db: Session = Depends(get_db)):
    """Get stored student response and grade from database with exact question-answer mapping"""
    try:
        exam_id_int = int(exam_id)
        question_id_int = int(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id or question_id format")
    
    # Verify question exists and belongs to exam
    question = db.query(Question).filter(
        Question.id == question_id_int,
        Question.exam_id == exam_id_int
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found for this exam")
    
    # Find answer - filter by student_id if provided, otherwise get most recent
    query = db.query(Answer).join(Submission).filter(
        Submission.exam_id == exam_id_int,
        Answer.question_id == question_id_int
    )
    
    if student_id:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if student:
            query = query.filter(Submission.student_id == student.id)
    
    answer = query.order_by(Answer.graded_at.desc()).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Get question details for complete mapping
    rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
    rubric_data = {}
    if rubric:
        try:
            rubric_data = json.loads(rubric.rubric_text)
        except:
            rubric_data = {"text": rubric.rubric_text}
    
    return {
        "exam_id": exam_id,
        "question_id": question_id,
        "question": {
            "question_id": str(question.id),
            "q_index": question.q_index,
            "question_text": question.prompt,
            "points_possible": float(question.points_possible),
            "grading_rubric": rubric_data
        },
        "answer": {
            "answer_id": str(answer.id),
            "response_text": answer.student_answer,
            "time_spent_seconds": None,  # Not stored currently
            "grade": {
                "question_id": question_id,
                "scores": {},  # Could parse from feedback if needed
                "total_score": float(answer.llm_score) if answer.llm_score else 0.0,
                "explanation": "",
                "feedback": answer.llm_feedback or ""
            },
            "submitted_at": answer.graded_at.isoformat() if answer.graded_at else None,
            "grading_model_name": answer.grading_model_name
        }
    }
