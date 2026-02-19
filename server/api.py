"""
All API endpoints for the Essay Testing System
Handles all GET, POST, and other HTTP endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, Form
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import uuid
import json
from datetime import datetime

from pydantic import BaseModel

from server.core.models import QuestionRequest, StudentResponse, GradingRequest
from server.core.llm_service import (
    call_together_ai, extract_json_from_response,
    QUESTION_GENERATION_TEMPLATE, GRADING_TEMPLATE,
    adjudicate_dispute_question, adjudicate_dispute_overall,
)
from server.core.database import get_db
from server.core.db_models import (
    User, Instructor, Student, Exam, Question, Rubric,
    Submission, Answer, Regrade, SubmissionRegrade, AssignedExamDispute
)
from server.core.config import TOGETHER_AI_MODEL
from server.core.auth import create_session, delete_session, get_current_user, require_auth
from server.core.file_extractor import extract_text_from_file, summarize_text
from server.core.file_extractor import extract_text_from_file, summarize_text

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


def get_or_create_instructor_for_user(db: Session, user: User) -> Instructor:
    """Get or create an instructor record for a user"""
    # Get default instructor to check against
    default_instructor = db.query(Instructor).filter(Instructor.email == "default@system.edu").first()
    default_instructor_id = default_instructor.id if default_instructor else None
    
    if user.instructor_id:
        instructor = db.query(Instructor).filter(Instructor.id == user.instructor_id).first()
        if instructor:
            # If user is linked to default instructor, create a new one for them
            if instructor.id == default_instructor_id:
                print(f"DEBUG: get_or_create_instructor_for_user - User {user.username} is linked to default instructor, creating new instructor record", flush=True)
                # Create new instructor record for this user
                new_instructor = Instructor(
                    name=user.username,
                    email=f"{user.username}@system.edu",
                    domain_expertise="General"
                )
                db.add(new_instructor)
                db.flush()  # Get the ID
                
                # Link to user
                user.instructor_id = new_instructor.id
                db.commit()
                db.refresh(new_instructor)
                db.refresh(user)
                print(f"DEBUG: get_or_create_instructor_for_user - Created new instructor_id={new_instructor.id} for user={user.username}", flush=True)
                return new_instructor
            else:
                print(f"DEBUG: get_or_create_instructor_for_user - Found existing instructor_id={instructor.id} for user={user.username}", flush=True)
                return instructor
    
    # Create new instructor record
    print(f"DEBUG: get_or_create_instructor_for_user - Creating new instructor for user={user.username}", flush=True)
    instructor = Instructor(
        name=user.username,
        email=f"{user.username}@system.edu",
        domain_expertise="General"
    )
    db.add(instructor)
    db.flush()  # Get the ID
    
    # Link to user
    user.instructor_id = instructor.id
    db.commit()
    db.refresh(instructor)
    db.refresh(user)  # Refresh user to ensure instructor_id is persisted
    print(f"DEBUG: get_or_create_instructor_for_user - Created instructor_id={instructor.id} and linked to user={user.username} (user.instructor_id={user.instructor_id})", flush=True)
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

@router.post("/api/extract-file-content", tags=["questions"])
async def extract_file_content(
    file: UploadFile = File(...),
    num_questions: int = Form(1),
    current_user: User = Depends(get_current_user)
):
    """Extract text content from uploaded file (PDF, TXT, DOCX) and extract topics based on number of questions"""
    try:
        # Validate file size (max 10MB)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 10MB limit. Please upload a smaller file."
            )
        
        # Extract text
        extracted_text = extract_text_from_file(file)
        
        # Extract topics based on number of questions
        from server.core.file_extractor import extract_topics_from_content
        topics = extract_topics_from_content(extracted_text, num_topics=num_questions)
        
        # If we have topics, format them clearly for separate question generation
        if topics and len(topics) > 0:
            # Format topics so each gets its own question (don't combine them)
            topics_list = "\n".join([f"- {topic}" for i, topic in enumerate(topics)])
            # Also include full content for context (truncated)
            summarized_text = summarize_text(extracted_text, max_length=3000)
            combined_content = f"""Extracted Topics from Uploaded File (Create ONE question per topic, DO NOT combine topics):
{topics_list}

--- Full Document Content (for context) ---
{summarized_text}"""
        else:
            # Fallback: just summarize the content
            combined_content = summarize_text(extracted_text, max_length=5000)
        
        return {
            "success": True,
            "extracted_text": combined_content,
            "topics": topics,
            "original_length": len(extracted_text),
            "truncated": len(extracted_text) > 5000
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


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
        # Handle topic - if provided, use it; otherwise use domain
        topic_context = request.topic if request.topic and request.topic.strip() else request.domain
        
        # Check if multiple topics are provided (comma-separated)
        topics_list = []
        if topic_context and ',' in topic_context:
            # Split by comma and clean up
            topics_list = [t.strip() for t in topic_context.split(',') if t.strip()]
        elif topic_context:
            topics_list = [topic_context.strip()]
        
        # Format topics for the prompt
        if len(topics_list) > 1:
            # Multiple topics - format them clearly
            topics_formatted = "\n".join([f"Topic {i+1}: {topic}" for i, topic in enumerate(topics_list)])
            topic_instruction = f"""
CRITICAL TOPIC INSTRUCTIONS:
You have been provided with {len(topics_list)} SEPARATE topics. You MUST create ONE question per topic. DO NOT combine topics.

The topics are:
{topics_formatted}

You must create exactly {len(topics_list)} questions - one for each topic listed above. Each question must focus on ONLY ONE topic. Do not combine "Topic 1" and "Topic 2" into a single question.

Topic Focus: {topic_context}
"""
        else:
            # Single topic
            topic_instruction = f"Topic Focus: {topic_context}"
        
        # Handle uploaded content
        uploaded_content_section = ""
        uploaded_content_instruction = ""
        if request.uploaded_content and request.uploaded_content.strip():
            uploaded_content_section = f"""
Uploaded Course Materials:
{request.uploaded_content}
"""
            uploaded_content_instruction = "IMPORTANT: Base your questions on the uploaded course materials above. The questions should align with the content, terminology, and concepts covered in these materials."
        
        # Complete the prompt template
        prompt = QUESTION_GENERATION_TEMPLATE.format(
            domain=request.domain,
            topic=topic_instruction,
            difficulty=request.difficulty or "mixed",
            professor_instructions=request.professor_instructions or "No specific instructions provided.",
            num_questions=request.num_questions,
            uploaded_content_section=uploaded_content_section,
            uploaded_content_instruction=uploaded_content_instruction
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

        # Determine instructor and student_id based on user type
        student_id_value = None
        if current_user and current_user.user_type == "instructor":
            # For instructors: use their own instructor record, and student_id = None (assigned exam)
            instructor = get_or_create_instructor_for_user(db, current_user)
            student_id_value = None  # Explicitly set to None for assigned exams
            print(f"DEBUG: Instructor creating exam - instructor_id={instructor.id}, user.username={current_user.username}, student_id={student_id_value}", flush=True)
        else:
            # For students: use default instructor, and set student_id (practice exam)
            instructor = get_or_create_default_instructor(db)
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
        print(f"DEBUG: Exam created - exam.id={exam.id}, exam.instructor_id={exam.instructor_id}, exam.student_id={exam.student_id}", flush=True)
        
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
            
            # Get individual question difficulty (for mixed difficulty exams)
            question_difficulty = q_data.get("difficulty", request.difficulty or "medium")
            # If exam difficulty is not mixed, use exam difficulty; otherwise use question's difficulty
            if request.difficulty and request.difficulty.lower() != "mixed":
                question_difficulty = request.difficulty.lower()
            
            question = Question(
                exam_id=exam.id,
                q_index=idx + 1,  # 1-indexed
                prompt=q_data.get("question_text", ""),
                background_info=q_data.get("background_info", ""),
                model_answer=None,  # Can be added later
                points_possible=total_points,
                difficulty=question_difficulty
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
                "domain_info": q_data.get("domain_info", ""),
                "difficulty": question.difficulty or request.difficulty or "medium"  # Include individual question difficulty
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
    """Get all practice exams (student-generated) for the current authenticated user"""
    # Get student record for user
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
        student_id = student.id
        student_campus_id = student.student_id  # The string campus ID
    else:
        # Create or get student using username
        student = get_or_create_student(db, current_user.username, name=current_user.username)
        student_id = student.id
        student_campus_id = student.student_id
    
    # Get all submissions for PRACTICE exams only (where exam.student_id matches the student's campus ID)
    submissions = db.query(Submission).join(Exam).filter(
        Submission.student_id == student_id,
        Exam.student_id == student_campus_id  # Only practice exams (student-generated)
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
    
    from datetime import timedelta
    
    # ALWAYS check if exam has actually been started (has answers)
    answer_count = db.query(Answer).filter(Answer.submission_id == submission.id).count() if submission else 0
    
    # Debug logging BEFORE any changes
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"=== START EXAM DEBUG ===")
    logger.warning(f"exam_id: {exam.id}, time_limit_minutes: {exam.time_limit_minutes}")
    if submission:
        logger.warning(f"submission.id: {submission.id}, submission.started_at: {submission.started_at}, submission.end_time: {submission.end_time}")
        logger.warning(f"answer_count: {answer_count}")
    
    if not submission:
        # Create new submission - timer starts NOW
        start_time = datetime.utcnow()
        end_time = None
        
        # Calculate end_time if exam has a time limit
        if exam.time_limit_minutes and exam.time_limit_minutes > 0:
            end_time = start_time + timedelta(minutes=exam.time_limit_minutes)
        
        logger.warning(f"Creating NEW submission - started_at: {start_time}, end_time: {end_time}")
        
        submission = Submission(
            exam_id=exam_id_int,
            student_id=student.id,
            started_at=start_time,
            end_time=end_time
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
    elif answer_count == 0:
        # No answers = exam hasn't actually been started yet
        # ALWAYS reset started_at to NOW regardless of what it was before
        old_started_at = submission.started_at
        old_end_time = submission.end_time
        start_time = datetime.utcnow()
        submission.started_at = start_time
        
        if exam.time_limit_minutes and exam.time_limit_minutes > 0:
            end_time = start_time + timedelta(minutes=exam.time_limit_minutes)
            submission.end_time = end_time
        else:
            end_time = None
            submission.end_time = None
        
        logger.warning(f"RESETTING started_at (no answers)")
        logger.warning(f"  Old started_at: {old_started_at}, New started_at: {start_time}")
        logger.warning(f"  Old end_time: {old_end_time}, New end_time: {end_time}")
        if old_started_at:
            time_diff = (start_time - old_started_at).total_seconds() / 60
            logger.warning(f"  Time difference: {time_diff} minutes")
        if old_end_time and end_time:
            end_time_diff = (end_time - old_end_time).total_seconds() / 60
            logger.warning(f"  End time difference: {end_time_diff} minutes")
        
        db.commit()
        db.refresh(submission)
    else:
        # Exam has answers - check if started_at seems reasonable
        start_time = submission.started_at
        now = datetime.utcnow()
        time_since_started = (now - start_time).total_seconds() / 60 if start_time else None
        
        # If started_at is more than 24 hours ago or in the future, something is wrong - reset it
        if start_time and (time_since_started > 24 * 60 or time_since_started < 0):
            logger.warning(f"WARNING: started_at seems incorrect! started_at: {start_time}, now: {now}, diff: {time_since_started} minutes")
            logger.warning(f"  Resetting started_at to NOW even though exam has answers")
            start_time = datetime.utcnow()
            submission.started_at = start_time
        
        logger.warning(f"Using started_at: {start_time} (has {answer_count} answers, time since started: {time_since_started} minutes)")
        if exam.time_limit_minutes and exam.time_limit_minutes > 0:
            expected_end_time = start_time + timedelta(minutes=exam.time_limit_minutes)
            logger.warning(f"  Expected end_time: {expected_end_time}, Current end_time: {submission.end_time}")
            
            # Calculate what the timer would show
            if submission.end_time:
                timer_show_minutes = (submission.end_time - now).total_seconds() / 60
                logger.warning(f"  Timer would show: {timer_show_minutes} minutes")
            
            if not submission.end_time or abs((submission.end_time - expected_end_time).total_seconds()) > 60:
                # Update end_time if it's missing or more than 1 minute off
                logger.warning(f"  Updating end_time from {submission.end_time} to {expected_end_time}")
                submission.end_time = expected_end_time
                db.commit()
                db.refresh(submission)
            end_time = submission.end_time
        else:
            submission.end_time = None
            end_time = None
            db.commit()
            db.refresh(submission)
    
    logger.warning(f"FINAL: started_at: {submission.started_at}, end_time: {submission.end_time}")
    if submission.started_at and submission.end_time:
        final_diff = (submission.end_time - submission.started_at).total_seconds() / 60
        logger.warning(f"FINAL time difference: {final_diff} minutes (should be {exam.time_limit_minutes})")
    logger.warning(f"=== END START EXAM DEBUG ===")
    
    # Use submission.end_time for the response (it's been updated in the database)
    response_end_time = submission.end_time
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Exam start - exam_id: {exam.id}, time_limit_minutes: {exam.time_limit_minutes}")
    logger.info(f"Submission - started_at: {submission.started_at}, end_time: {response_end_time}")
    if submission.started_at and response_end_time:
        time_diff = (response_end_time - submission.started_at).total_seconds() / 60
        logger.info(f"Time difference: {time_diff} minutes")
    
    # Ensure ISO format includes 'Z' to indicate UTC timezone
    def format_utc_iso(dt):
        if dt is None:
            return None
        # Add 'Z' suffix to indicate UTC
        iso_str = dt.isoformat()
        if '+' in iso_str or iso_str.endswith('Z'):
            return iso_str
        return iso_str + 'Z'
    
    return {
        "submission_id": str(submission.id),
        "exam_id": str(exam.id),
        "time_limit_minutes": exam.time_limit_minutes,
        "prevent_tab_switching": bool(exam.prevent_tab_switching) if exam.prevent_tab_switching is not None else False,
        "end_time": format_utc_iso(response_end_time),
        "started_at": format_utc_iso(submission.started_at)
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
    
    # Get any submission (in-progress or already submitted) for this exam and student
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id
    ).order_by(Submission.started_at.desc()).first()
    
    print(f"DEBUG: submit_exam - Looking for submission: exam_id={exam_id_int}, student_id={student.id}")
    
    if submission:
        # Check if already submitted
        if submission.submitted_at:
            print(f"DEBUG: Submission {submission.id} already submitted at {submission.submitted_at}")
            return {
                "success": True,
                "message": "Exam already submitted",
                "submission_id": str(submission.id),
                "exam_id": str(exam.id),
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
            }
        print(f"DEBUG: Found in-progress submission {submission.id}, submitted_at={submission.submitted_at}")
    else:
        # No submission exists - create one and mark it as submitted immediately
        print(f"DEBUG: No submission found, creating new one and marking as submitted")
        submission = Submission(
            exam_id=exam_id_int,
            student_id=student.id,
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow()  # Mark as submitted immediately
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        print(f"DEBUG: Created and marked submission {submission.id} as submitted")
        # Force SQLite checkpoint
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
    
    # Mark as submitted (submission exists and is in-progress)
    submission.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(submission)
    print(f"DEBUG: Marked submission {submission.id} as submitted at {submission.submitted_at}")
    
    # Force SQLite checkpoint to ensure change is immediately visible
    try:
        from sqlalchemy import text
        db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        db.commit()
        print(f"DEBUG: SQLite checkpoint completed")
    except Exception as e:
        print(f"DEBUG: Checkpoint warning (non-critical): {e}")
    
    return {
        "success": True,
        "message": "Exam submitted successfully",
        "submission_id": str(submission.id),
        "exam_id": str(exam.id),
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
    }


@router.get("/api/my-exams/assigned", tags=["exams"])
async def get_assigned_exams(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all assigned exams (instructor-assigned, not practice) for the current student"""
    try:
        if current_user.user_type != "student":
            raise HTTPException(status_code=403, detail="Only students can access this endpoint")
        
        # Get student record for user
        if current_user.user_type == "student" and current_user.student_id:
            student = db.query(Student).filter(Student.id == current_user.student_id).first()
            if not student:
                raise HTTPException(status_code=404, detail="Student record not found for user")
            student_id = student.id
        else:
            student = get_or_create_student(db, current_user.username, name=current_user.username)
            student_id = student.id
        
        # Refresh student to ensure we have latest data including class_name
        db.refresh(student)
        
        # Get all submissions for assigned exams only (where exam.student_id is NULL)
        # This ensures we only get instructor-created exams, not student-generated practice exams
        # Use eager loading to get exam and instructor data in one query
        from sqlalchemy.orm import joinedload
        submissions = db.query(Submission).join(Exam).options(
            joinedload(Submission.exam).joinedload(Exam.instructor)
        ).filter(
            Submission.student_id == student_id,
            Exam.student_id.is_(None)  # Only assigned exams (instructor-created), not practice (student-generated)
        ).order_by(Submission.started_at.desc()).all()
        
        if not submissions:
            return {"exams": []}
        
        # Helper function to format UTC datetime with 'Z' suffix
        def format_utc_iso(dt):
            if dt is None:
                return None
            iso_str = dt.isoformat()
            if '+' in iso_str or iso_str.endswith('Z'):
                return iso_str
            return iso_str + 'Z'
        
        # Get unique exams and their status
        exam_data = {}
        for submission in submissions:
            exam_id = submission.exam_id
            
            # Skip if we already processed this exam
            if exam_id in exam_data:
                continue
            
            exam = submission.exam  # Use the eagerly loaded exam
            if not exam:
                continue
            
            # Double-check: ensure this is NOT a practice exam (student_id must be NULL)
            if exam.student_id is not None:
                # This is a practice exam, skip it
                continue
            
            # Check if exam is overdue and handle auto-submission/grading
            is_overdue = False
            if exam.due_date and exam.due_date < datetime.utcnow():
                is_overdue = True
                # If overdue and not submitted, auto-submit (even if no answers)
                if submission.submitted_at is None:
                    # Auto-submit overdue exam
                    submission.submitted_at = datetime.utcnow()
                    
                    # If submission was never started, set started_at to now (or keep existing)
                    if submission.started_at is None:
                        submission.started_at = datetime.utcnow()
                    
                    # Grade any ungraded answers
                    ungraded_answers = db.query(Answer).filter(
                        Answer.submission_id == submission.id,
                        Answer.llm_score.is_(None)  # Not graded yet
                    ).all()
                    
                    for answer in ungraded_answers:
                        # Get question and rubric for grading
                        question = db.query(Question).filter(Question.id == answer.question_id).first()
                        if question:
                            rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
                            if rubric:
                                try:
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
                                        student_response=answer.student_answer,
                                        time_spent=0  # Unknown for auto-graded overdue exams
                                    )

                                    # Call LLM for grading
                                    llm_response = await call_together_ai(
                                        prompt,
                                        system_prompt="You are an expert educator. Always return valid JSON with accurate scores."
                                    )

                                    # Parse grading result
                                    grade_data = extract_json_from_response(llm_response)

                                    # Update answer with grade
                                    answer.llm_score = float(grade_data.get("total_score", 0.0))
                                    answer.llm_feedback = grade_data.get("feedback", "")
                                    answer.graded_at = datetime.utcnow()
                                    answer.grading_model_name = TOGETHER_AI_MODEL
                                    answer.grading_temperature = 0.7
                                    
                                    print(f"DEBUG: Auto-graded overdue answer {answer.id} for submission {submission.id}")
                                except Exception as e:
                                    print(f"DEBUG: Error auto-grading overdue answer {answer.id}: {e}")
                                    # Continue even if grading fails
                                    import traceback
                                    traceback.print_exc()
                    
                    db.commit()
                    db.refresh(submission)
                    print(f"DEBUG: Auto-submitted overdue exam {exam.id} for student {student_id} (had answers: {len(ungraded_answers) > 0})")
            
            # Check if exam is in progress or completed
            is_completed = submission.submitted_at is not None
            
            # Check if student has actually started (has any answers)
            has_answers = db.query(Answer).filter(Answer.submission_id == submission.id).count() > 0
            
            # Only mark as in progress if it's been started (has started_at AND has answers) but not completed
            is_in_progress = not is_completed and submission.started_at is not None and has_answers
            
            # Get question count
            question_count = db.query(Question).filter(Question.exam_id == exam_id).count()
            
            # Get instructor information (use eagerly loaded instructor if available)
            instructor = exam.instructor if hasattr(exam, 'instructor') and exam.instructor else None
            if not instructor:
                instructor = db.query(Instructor).filter(Instructor.id == exam.instructor_id).first()
            instructor_name = instructor.name if instructor else "Unknown Instructor"
            
            # Get class name from student record (refresh to ensure we have latest)
            class_name = student.class_name if student.class_name else None
            
            # Get dispute information for this submission
            disputes = db.query(AssignedExamDispute).filter(
                AssignedExamDispute.submission_id == submission.id
            ).all()
            
            dispute_info = None
            if disputes:
                # Get the most recent dispute (or any pending one)
                pending_dispute = next((d for d in disputes if d.status == "pending"), None)
                resolved_dispute = next((d for d in disputes if d.status == "resolved"), None)
                
                if pending_dispute:
                    dispute_info = {
                        "status": "pending",
                        "dispute_id": pending_dispute.id,
                        "target": "overall" if pending_dispute.question_id is None else "question",
                        "question_id": pending_dispute.question_id,
                        "created_at": pending_dispute.created_at.isoformat() if pending_dispute.created_at else None,
                    }
                elif resolved_dispute:
                    dispute_info = {
                        "status": "resolved",
                        "dispute_id": resolved_dispute.id,
                        "target": "overall" if resolved_dispute.question_id is None else "question",
                        "question_id": resolved_dispute.question_id,
                        "instructor_decision": resolved_dispute.instructor_decision,
                        "instructor_response": resolved_dispute.instructor_response,
                        "resolved_at": resolved_dispute.resolved_at.isoformat() if resolved_dispute.resolved_at else None,
                        "created_at": resolved_dispute.created_at.isoformat() if resolved_dispute.created_at else None,
                    }
            
            # Debug logging
            print(f"DEBUG: Exam {exam.id} ({exam.title}) - Instructor ID: {exam.instructor_id}, Instructor: {instructor_name}, Student Class: {class_name}, Student ID: {student.id}, Student Name: {student.name}")
            
            exam_data[exam_id] = {
                "exam_id": str(exam.id),
                "domain": exam.domain,
                "title": exam.title or f"{exam.domain} Exam",
                "submission_id": str(submission.id),
                "started_at": submission.started_at.isoformat() if submission.started_at else None,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "is_completed": is_completed,
                "is_in_progress": is_in_progress,
                "question_count": question_count,
                "instructor_name": instructor_name or "Unknown Instructor",
                "class_name": class_name or None,
                "due_date": format_utc_iso(exam.due_date) if exam.due_date else None,
                "time_limit_minutes": exam.time_limit_minutes,
                "is_overdue": is_overdue,
                "dispute": dispute_info
            }
        
        # Debug: log the final response
        result = list(exam_data.values())
        print(f"DEBUG: Returning {len(result)} exams with data: {[{'id': e['exam_id'], 'instructor': e.get('instructor_name'), 'class': e.get('class_name')} for e in result]}")
        
        return {"exams": list(exam_data.values())}
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the error and return a proper error response
        print(f"ERROR in get_assigned_exams: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading assigned exams: {str(e)}")


@router.get("/api/my-profile", tags=["profile"])
async def get_my_profile(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get current user's profile information"""
    try:
        if current_user.user_type == "student":
            # Get student record
            if current_user.student_id:
                student = db.query(Student).filter(Student.id == current_user.student_id).first()
            else:
                student = get_or_create_student(db, current_user.username, name=current_user.username)
            
            if not student:
                raise HTTPException(status_code=404, detail="Student record not found")
            
            # Get exam statistics
            total_exams = db.query(Submission).join(Exam).filter(
                Submission.student_id == student.id,
                Exam.student_id.is_(None)  # Only assigned exams
            ).count()
            
            completed_exams = db.query(Submission).join(Exam).filter(
                Submission.student_id == student.id,
                Exam.student_id.is_(None),
                Submission.submitted_at.isnot(None)
            ).count()
            
            return {
                "username": current_user.username,
                "name": student.name,
                "email": student.email or f"{current_user.username}@university.edu",  # Mock email if not set
                "student_id": student.student_id,
                "class_name": student.class_name or "Not assigned",
                "user_type": "Student",
                "total_exams": total_exams,
                "completed_exams": completed_exams,
                "in_progress_exams": total_exams - completed_exams,
                "account_created": current_user.created_at.isoformat() if current_user.created_at else None
            }
        else:
            # Instructor profile
            instructor = None
            if current_user.instructor_id:
                instructor = db.query(Instructor).filter(Instructor.id == current_user.instructor_id).first()
            
            if not instructor:
                instructor = get_or_create_instructor_for_user(db, current_user)
            
            # Get instructor statistics
            total_exams = db.query(Exam).filter(Exam.instructor_id == instructor.id).count()
            total_students = db.query(Student).distinct().count()
            
            return {
                "username": current_user.username,
                "name": instructor.name,
                "email": instructor.email or f"{current_user.username}@university.edu",  # Mock email if not set
                "user_type": "Instructor",
                "domain_expertise": instructor.domain_expertise or "General",
                "total_exams_created": total_exams,
                "total_students": total_students,
                "account_created": current_user.created_at.isoformat() if current_user.created_at else None
            }
    except Exception as e:
        print(f"Error getting profile: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading profile: {str(e)}")


@router.get("/api/my-exams/in-progress", tags=["exams"])
async def get_in_progress_exams(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all in-progress exams (not yet submitted) for the current authenticated user"""
    try:
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
        
        # Get student's campus ID for filtering practice exams
        student_campus_id = student.student_id  # The string campus ID
        
        # Get all in-progress submissions (submitted_at is None)
        # Include both practice exams (exam.student_id matches) and assigned exams (exam.student_id is NULL)
        submissions = db.query(Submission).join(Exam).filter(
            Submission.student_id == student_id,
            Submission.submitted_at.is_(None),
            # Include practice exams OR assigned exams
            ((Exam.student_id == student_campus_id) | (Exam.student_id.is_(None)))
        ).order_by(Submission.started_at.desc()).all()
        
        # For practice exams, also check for exams that exist but don't have submissions yet
        # (exams that were generated but never started)
        practice_exams_without_submissions = db.query(Exam).filter(
            Exam.student_id == student_campus_id,  # Practice exams only
            ~Exam.id.in_([s.exam_id for s in submissions])  # Exams without submissions
        ).all()
        
        # Get exam details and current progress
        exam_data = []
        
        # Process submissions (exams that have been started)
        for submission in submissions:
            exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
            if not exam:
                continue
            
            # Get answers already submitted for this in-progress exam
            answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
            answered_count = len(answers)
            
            # For assigned exams: only include if actually started (have started_at AND have at least one answer)
            # For practice exams: include if started_at is set (even if no answers yet)
            is_practice = exam.student_id == student_campus_id
            if not is_practice:
                # Assigned exam - must have started and have answers
                if submission.started_at is None or answered_count == 0:
                    continue
            else:
                # Practice exam - must have started_at (even if no answers yet)
                if submission.started_at is None:
                    continue
            
            # Get questions for this exam
            questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
            
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
        
        # For practice exams: also include exams that were generated but never started (no submission exists yet)
        # These are practice exams that exist but the student hasn't clicked "Start Exam" yet
        submission_exam_ids = {s.exam_id for s in submissions} if submissions else set()
        practice_exams_without_submissions = db.query(Exam).filter(
            Exam.student_id == student_campus_id  # Practice exams only
        ).all()
        
        # Filter out exams that already have submissions
        practice_exams_without_submissions = [
            exam for exam in practice_exams_without_submissions 
            if exam.id not in submission_exam_ids
        ]
        
        for exam in practice_exams_without_submissions:
            # Check if exam has questions (was fully generated)
            questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
            if not questions:
                continue  # Skip exams without questions
            
            # Check if exam was submitted (by checking if there's any submission with submitted_at set)
            completed_submission = db.query(Submission).filter(
                Submission.exam_id == exam.id,
                Submission.student_id == student_id,
                Submission.submitted_at.isnot(None)
            ).first()
            
            if completed_submission:
                continue  # Skip completed exams
            
            # This is a practice exam that was generated but never started
            # Include it in the in-progress list
            exam_data.append({
                "exam_id": str(exam.id),
                "submission_id": None,  # No submission yet
                "domain": exam.domain,
                "title": exam.title or f"{exam.domain} Exam",
                "started_at": None,  # Not started yet
                "question_count": len(questions),
                "answered_count": 0,
                "progress_percentage": 0.0
            })
        
        return {"exams": exam_data}
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the error and return a proper error response
        print(f"ERROR in get_in_progress_exams: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading in-progress exams: {str(e)}")


@router.delete("/api/exam/{exam_id}/in-progress", tags=["exams"])
async def delete_in_progress_exam(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete an in-progress exam submission
    
    For practice exams (student-generated), this will delete the entire exam.
    For assigned exams (instructor-generated), this will only delete the submission.
    """
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
    
    # Get the exam first to check if it exists
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

    # Get student's campus ID for checking practice exams
    student_campus_id = student.student_id
    
    # Check if this is a practice exam (student-generated)
    is_practice_exam = exam.student_id == student_campus_id
    
    # Get in-progress submission
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id_int,
        Submission.student_id == student.id,
        Submission.submitted_at.is_(None)
    ).order_by(Submission.started_at.desc()).first()
    
    if is_practice_exam:
        # For practice exams, delete the entire exam (which will cascade delete submissions and answers)
        # This ensures the exam is completely removed when regenerating
        db.delete(exam)
        db.commit()
        return {"message": "Practice exam deleted successfully", "exam_id": str(exam_id)}
    elif submission:
        # For assigned exams, only delete the submission (don't delete the exam itself)
        # Delete the submission (cascade will delete associated answers)
        db.delete(submission)
        db.commit()
        return {"message": "In-progress exam deleted successfully", "exam_id": str(exam_id)}
    else:
        # No submission exists and it's not a practice exam
        raise HTTPException(status_code=404, detail="No in-progress exam found")


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
    
    # If no submission exists, create one (for practice exams that were generated but never started)
    if not submission:
        # Check if this is a practice exam (exam.student_id matches student's campus ID)
        student_campus_id = student.student_id
        is_practice_exam = exam.student_id == student_campus_id
        
        if is_practice_exam:
            # Create a new submission for this practice exam
            submission = Submission(
                exam_id=exam_id_int,
                student_id=student.id,
                started_at=datetime.utcnow()
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)
        else:
            # For assigned exams, they should have a submission (created when assigned)
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
            "difficulty": q.difficulty or exam.difficulty or "medium",  # Include individual question difficulty
            "existing_answer": answer.student_answer if answer else None,
            "existing_answer_data": existing_answer_data  # Include full answer data with grades
        })
    
    # Helper function to format UTC datetime with 'Z' suffix
    def format_utc_iso(dt):
        if dt is None:
            return None
        iso_str = dt.isoformat()
        if '+' in iso_str or iso_str.endswith('Z'):
            return iso_str
        return iso_str + 'Z'
    
    return {
        "exam_id": str(exam.id),
        "domain": exam.domain,
        "title": exam.title or f"{exam.domain} Exam",
        "submission_id": str(submission.id),
        "time_limit_minutes": exam.time_limit_minutes,
        "prevent_tab_switching": bool(exam.prevent_tab_switching) if exam.prevent_tab_switching is not None else False,
        "due_date": format_utc_iso(exam.due_date) if exam.due_date else None,
        "end_time": format_utc_iso(submission.end_time),
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
    total_score = 0.0
    max_score = 0.0
    has_instructor_edits = False
    
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
            # Use instructor score if edited, otherwise use LLM score
            final_score = float(answer.instructor_score) if answer.instructor_edited and answer.instructor_score is not None else (float(answer.llm_score) if answer.llm_score is not None else None)
            
            if answer.instructor_edited:
                has_instructor_edits = True
            
            answer_data = {
                "answer_id": str(answer.id),
                "response_text": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "graded_at": answer.graded_at.isoformat() if answer.graded_at else None,
                "grading_model_name": answer.grading_model_name,
                "instructor_edited": bool(answer.instructor_edited) if answer.instructor_edited is not None else False,
                "instructor_score": float(answer.instructor_score) if answer.instructor_score is not None else None,
                "instructor_feedback": answer.instructor_feedback or "",
                "instructor_edited_at": answer.instructor_edited_at.isoformat() if answer.instructor_edited_at else None,
                "final_score": final_score  # The score that should be displayed (instructor or LLM)
            }
            
            if final_score is not None:
                total_score += final_score
        
        max_score += float(q.points_possible)
        
        questions_with_answers.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "question_text": q.prompt,
            "background_info": q.background_info or "",
            "points_possible": float(q.points_possible),
            "grading_rubric": rubric_data,
            "answer": answer_data  # One-to-one: exactly one answer or None
        })
    
    percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0.0
    
    # Get dispute information for this submission
    disputes = db.query(AssignedExamDispute).filter(
        AssignedExamDispute.submission_id == submission.id
    ).all()
    
    dispute_info = None
    if disputes:
        # Get the most recent dispute (or any pending one)
        pending_dispute = next((d for d in disputes if d.status == "pending"), None)
        resolved_dispute = next((d for d in disputes if d.status == "resolved"), None)
        
        if pending_dispute:
            dispute_info = {
                "status": "pending",
                "dispute_id": pending_dispute.id,
                "target": "overall" if pending_dispute.question_id is None else "question",
                "question_id": pending_dispute.question_id,
                "student_argument": pending_dispute.student_argument,
                "created_at": pending_dispute.created_at.isoformat() if pending_dispute.created_at else None,
            }
        elif resolved_dispute:
            dispute_info = {
                "status": "resolved",
                "dispute_id": resolved_dispute.id,
                "target": "overall" if resolved_dispute.question_id is None else "question",
                "question_id": resolved_dispute.question_id,
                "student_argument": resolved_dispute.student_argument,
                "instructor_decision": resolved_dispute.instructor_decision,
                "instructor_response": resolved_dispute.instructor_response,
                "resolved_at": resolved_dispute.resolved_at.isoformat() if resolved_dispute.resolved_at else None,
                "created_at": resolved_dispute.created_at.isoformat() if resolved_dispute.created_at else None,
            }
    
    return {
        "exam_id": str(exam.id),
        "exam_title": exam.title,
        "domain": exam.domain,
        "submission_id": str(submission.id),
        "student_id": student.student_id,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": percentage,
        "has_instructor_edits": has_instructor_edits,
        "questions_with_answers": questions_with_answers,  # Each question has exactly one answer or None
        "dispute": dispute_info
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
            db.flush()  # Flush to get the ID
            print(f"DEBUG: Created new submission {submission.id} for exam {exam_id_int}, student {student.id}")
        else:
            # If submission exists but hasn't been started yet, set started_at now
            if submission.started_at is None:
                submission.started_at = datetime.utcnow()
                db.flush()
            print(f"DEBUG: Using existing submission {submission.id} for exam {exam_id_int}, student {student.id}")
        
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
        print(f"DEBUG: Committed answer for submission {submission.id}, submitted_at={submission.submitted_at}")
        
        # Force SQLite checkpoint to ensure submission is immediately visible to other queries
        try:
            from sqlalchemy import text
            db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            db.commit()
        except Exception as e:
            print(f"DEBUG: Checkpoint warning in submit_response (non-critical): {e}")
        
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
            "feedback": grade_data.get("feedback", ""),
            "rubric_breakdown": grade_data.get("rubric_breakdown", []),
            "annotations": grade_data.get("annotations", [])
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


# ============================================================================
# Instructor Endpoints
# ============================================================================

@router.get("/api/instructor/classes", tags=["instructor"])
async def get_all_classes(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all unique classes in the system (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can access this endpoint")
    
    # Get all unique class names from students (excluding None/empty)
    classes = db.query(Student.class_name).filter(
        Student.class_name.isnot(None),
        Student.class_name != ""
    ).distinct().all()
    
    class_names = [c[0] for c in classes if c[0]]
    class_names.sort()
    
    return {"classes": class_names}


@router.get("/api/instructor/students", tags=["instructor"])
async def get_all_students(
    class_name: str = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all students in the system (instructor only) - excludes instructor/admin accounts. Optionally filter by class."""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can access this endpoint")
    
    # Get all students, but exclude those that are linked to instructor user accounts
    query = db.query(Student)
    
    # Filter by class if provided
    if class_name:
        query = query.filter(Student.class_name == class_name)
    
    all_students = query.order_by(Student.name).all()
    
    # Get all user accounts that are instructors to exclude their student records
    instructor_users = db.query(User).filter(User.user_type == "instructor").all()
    
    # Create sets of IDs/usernames to exclude
    instructor_student_ids = {user.student_id for user in instructor_users if user.student_id}
    instructor_usernames = {user.username.lower() for user in instructor_users}
    
    # Filter out students that are:
    # 1. Linked to instructor accounts via foreign key (student_id)
    # 2. Have a student_id string that matches an instructor username
    students = [
        s for s in all_students 
        if s.id not in instructor_student_ids 
        and s.student_id.lower() not in instructor_usernames
    ]
    
    # Get assignment counts and dispute counts for each student
    # Only count submissions for assigned exams (where exam.student_id is NULL, meaning instructor-created)
    students_data = []
    for student in students:
        # Count submissions for assigned exams only (exclude practice exams)
        # Practice exams have exam.student_id set, assigned exams have exam.student_id = NULL
        submissions = db.query(Submission).join(Exam).filter(
            Submission.student_id == student.id,
            Exam.student_id.is_(None)  # Only count assigned exams, not practice exams
        ).all()
        
        submission_count = len(submissions)
        
        # Count pending disputes for this student
        submission_ids = [s.id for s in submissions]
        pending_disputes_count = 0
        if submission_ids:
            pending_disputes_count = db.query(AssignedExamDispute).filter(
                AssignedExamDispute.submission_id.in_(submission_ids),
                AssignedExamDispute.status == "pending"
            ).count()
        
        students_data.append({
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "class_name": student.class_name,
            "created_at": student.created_at.isoformat() if student.created_at else None,
            "assigned_exams_count": submission_count,
            "pending_disputes_count": pending_disputes_count
        })
    
    return {"students": students_data}


@router.get("/api/instructor/students/{student_id}", tags=["instructor"])
async def get_student_details(
    student_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific student (FERPA compliant - only educational info)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can access this endpoint")
    
    # Get student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get all assigned exam submissions for this student (only instructor-created exams)
    submissions = db.query(Submission).join(Exam).filter(
        Submission.student_id == student.id,
        Exam.student_id.is_(None)  # Only assigned exams, not practice exams
    ).order_by(Submission.started_at.desc()).all()
    
    # Get exam details with scores
    exam_details = []
    for submission in submissions:
        exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
        if not exam:
            continue
        
        # Get all answers for this submission
        answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
        has_answers = len(answers) > 0
        
        # Calculate total score (use instructor score if edited, otherwise use LLM score)
        total_score = 0.0
        max_score = 0.0
        for answer in answers:
            # Use instructor score if edited, otherwise use LLM score
            final_score = float(answer.instructor_score) if answer.instructor_edited and answer.instructor_score is not None else (float(answer.llm_score) if answer.llm_score is not None else 0.0)
            total_score += final_score
            
            # Get max points from question
            question = db.query(Question).filter(Question.id == answer.question_id).first()
            if question:
                max_score += float(question.points_possible)
        
        percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0.0
        
        # Get question count
        question_count = db.query(Question).filter(Question.exam_id == exam.id).count()
        
        # Get dispute information for this submission
        dispute = db.query(AssignedExamDispute).filter(
            AssignedExamDispute.submission_id == submission.id,
            AssignedExamDispute.status == "pending"
        ).first()
        
        has_pending_dispute = dispute is not None
        
        exam_details.append({
            "exam_id": exam.id,
            "exam_title": exam.title or f"{exam.domain} Exam",
            "domain": exam.domain,
            "question_count": question_count,
            "started_at": submission.started_at.isoformat() if submission.started_at else None,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "total_score": round(total_score, 2),
            "max_score": round(max_score, 2),
            "percentage": percentage,
            "is_completed": submission.submitted_at is not None,
            "is_in_progress": submission.submitted_at is None and submission.started_at is not None and has_answers,
            "has_pending_dispute": has_pending_dispute
        })
    
    # FERPA compliant: Only return educational information
    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email,
            "class_name": student.class_name
        },
        "exams": exam_details,
        "total_exams_assigned": len(exam_details),
        "completed_exams": len([e for e in exam_details if e["is_completed"]]),
        "in_progress_exams": len([e for e in exam_details if e["is_in_progress"]])
    }


@router.get("/api/instructor/exam/{exam_id}/review", tags=["instructor"])
async def review_exam(
    exam_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get exam details for review before assignment (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can review exams")
    
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    # Get or create instructor record
    instructor = get_or_create_instructor_for_user(db, current_user)
    
    # Get exam and verify it belongs to this instructor
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify instructor owns this exam
    if not current_user.instructor_id or exam.instructor_id != current_user.instructor_id:
        raise HTTPException(status_code=403, detail="You can only review your own exams")
    
    # Verify this is an assigned exam, not a practice exam
    if exam.student_id is not None:
        raise HTTPException(status_code=400, detail="Cannot review practice exams. Only instructor-created exams can be reviewed.")
    
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
        
        questions_list.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "background_info": q.background_info or "",
            "question_text": q.prompt,
            "grading_rubric": rubric_data,
            "points_possible": float(q.points_possible),
            "model_answer": q.model_answer or ""
        })
    
    # Count submissions
    submissions_count = db.query(Submission).filter(Submission.exam_id == exam.id).count()
    
    return {
        "exam_id": str(exam.id),
        "domain": exam.domain,
        "title": exam.title,
        "instructions_to_llm": exam.instructions_to_llm,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "questions_count": len(questions_list),
        "submissions_count": submissions_count,
        "questions": questions_list
    }


@router.get("/api/instructor/exams", tags=["instructor"])
async def get_instructor_exams(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all exams created by the current instructor (only assigned exams, not student practice exams)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can access this endpoint")
    
    # Get or create instructor record
    instructor = get_or_create_instructor_for_user(db, current_user)
    print(f"DEBUG: get_instructor_exams - user.username={current_user.username}, instructor.id={instructor.id}, user.instructor_id={current_user.instructor_id}", flush=True)
    
    # Get default instructor
    default_instructor = db.query(Instructor).filter(Instructor.email == "default@system.edu").first()
    default_instructor_id = default_instructor.id if default_instructor else None
    
    # CRITICAL: Only show exams created by the logged-in instructor's own instructor record
    # AND exclude all default instructor exams (those are student practice exams)
    # The key is: if instructor.id == default_instructor_id, we should show NO exams
    # because all default instructor exams are student practice exams
    
    if instructor.id == default_instructor_id:
        # This instructor is the default instructor - don't show any exams
        # because all default instructor exams are student practice exams
        exams = []
        print(f"DEBUG: Instructor is default instructor, returning empty list", flush=True)
    else:
        # This is a real instructor - only show their own exams that are assigned (student_id = NULL)
        exams = db.query(Exam).filter(
            Exam.instructor_id == instructor.id,
            Exam.student_id.is_(None),  # Only assigned exams, not practice
            Exam.instructor_id != default_instructor_id  # Double-check: exclude default instructor
        ).order_by(Exam.created_at.desc()).all()
        print(f"DEBUG: Found {len(exams)} exams for instructor_id={instructor.id}", flush=True)
        for exam in exams:
            print(f"DEBUG:   - Exam ID={exam.id}, title={exam.title}, instructor_id={exam.instructor_id}, student_id={exam.student_id}", flush=True)
    
    exams_data = []
    for exam in exams:
        # Count questions for this exam
        questions_count = db.query(Question).filter(Question.exam_id == exam.id).count()
        
        # Count submissions for this exam
        submissions_count = db.query(Submission).filter(Submission.exam_id == exam.id).count()
        
        exams_data.append({
            "id": exam.id,
            "title": exam.title,
            "domain": exam.domain,
            "instructions_to_llm": exam.instructions_to_llm,
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
            "questions_count": questions_count,
            "submissions_count": submissions_count
        })
    
    return {"exams": exams_data}


class CreateExamRequest(BaseModel):
    title: str
    domain: str
    instructions_to_llm: str
    number_of_questions: int = 5


@router.post("/api/instructor/create-exam", tags=["instructor"])
async def create_exam(
    request: CreateExamRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a new exam (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can create exams")
    
    # Get or create instructor record
    instructor = get_or_create_instructor_for_user(db, current_user)
    
    # Create exam (assigned exam, not practice)
    # student_id = NULL means this is an assigned exam, not a practice exam
    exam = Exam(
        instructor_id=instructor.id,
        student_id=None,  # NULL = assigned exam (instructor-created), not practice
        domain=request.domain,
        title=request.title,
        instructions_to_llm=request.instructions_to_llm,
        number_of_questions=request.number_of_questions,
        model_name=TOGETHER_AI_MODEL,
        temperature=0.7
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    
    return {
        "exam_id": str(exam.id),
        "title": exam.title,
        "domain": exam.domain,
        "message": "Exam created successfully. You can now generate questions for this exam."
    }


class EditExamRequest(BaseModel):
    title: str
    domain: str
    instructions_to_llm: Optional[str] = None
    number_of_questions: int = 5

class AssignExamRequest(BaseModel):
    exam_id: int
    student_ids: List[int]
    time_limit_minutes: Optional[int] = None  # Optional time limit in minutes (None = no time limit)
    prevent_tab_switching: bool = False  # Prevent tab switching (anti-cheating)
    due_date: Optional[datetime] = None  # Optional due date for the exam (None = no due date)


@router.put("/api/instructor/edit-exam/{exam_id}", tags=["instructor"])
async def edit_exam(
    exam_id: str,
    request: EditExamRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Edit an exam and regenerate questions (instructor only)
    
    This will:
    1. Update exam details (title, domain, instructions)
    2. Delete all existing questions and rubrics
    3. Regenerate questions based on new instructions
    """
    import time
    start_time = time.time()
    
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can edit exams")
    
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    try:
        # Get or create instructor record
        instructor = get_or_create_instructor_for_user(db, current_user)
        
        # Get exam and verify it belongs to this instructor
        exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Verify instructor owns this exam
        if not current_user.instructor_id or exam.instructor_id != current_user.instructor_id:
            raise HTTPException(status_code=403, detail="You can only edit your own exams")
        
        # Verify this is an assigned exam, not a practice exam
        if exam.student_id is not None:
            raise HTTPException(status_code=400, detail="Cannot edit practice exams. Only instructor-created exams can be edited.")
        
        print(f"DEBUG: [START] Edit exam {exam_id_int} - Domain: {request.domain}, Questions: {request.number_of_questions}", flush=True)
        
        # Step 1: Delete all existing questions and rubrics (cascade will handle related data)
        existing_questions = db.query(Question).filter(Question.exam_id == exam.id).all()
        for question in existing_questions:
            # Delete rubric first (if exists)
            rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
            if rubric:
                db.delete(rubric)
            # Delete question (answers will remain but won't be linked to valid questions)
            db.delete(question)
        
        db.flush()
        print(f"DEBUG: Deleted {len(existing_questions)} existing questions", flush=True)
        
        # Step 2: Update exam details
        exam.title = request.title
        exam.domain = request.domain
        exam.instructions_to_llm = request.instructions_to_llm
        exam.number_of_questions = request.number_of_questions
        exam.model_name = TOGETHER_AI_MODEL
        exam.temperature = 0.7
        
        db.flush()
        print(f"DEBUG: Updated exam details", flush=True)
        
        # Step 3: Generate new questions using the same logic as generate_questions
        try:
            # Complete the prompt template
            prompt = QUESTION_GENERATION_TEMPLATE.format(
                domain=request.domain,
                professor_instructions=request.instructions_to_llm or "No specific instructions provided.",
                num_questions=request.number_of_questions
            )
            
            # Call LLM
            llm_response = await call_together_ai(
                prompt,
                system_prompt="You are an expert educator. Always return valid JSON."
            )
            
            # Parse LLM response
            question_data = extract_json_from_response(llm_response)
            
            # Handle multiple questions or single question
            if isinstance(question_data, dict):
                question_data = [question_data]
            elif isinstance(question_data, list):
                if len(question_data) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail="LLM returned an empty array. No questions were generated."
                    )
            else:
                question_data = [question_data]
            
            # Create new questions
            questions_list = []
            for idx, q_data in enumerate(question_data):
                if not isinstance(q_data, dict):
                    continue
                
                # Calculate total points from rubric
                rubric_data = q_data.get("grading_rubric", {})
                total_points = rubric_data.get("total_points", 10.0)
                
                question = Question(
                    exam_id=exam.id,
                    q_index=idx + 1,
                    prompt=q_data.get("question_text", ""),
                    background_info=q_data.get("background_info", ""),
                    model_answer=None,
                    points_possible=total_points
                )
                db.add(question)
                db.flush()
                
                # Store rubric
                rubric_text = json.dumps(rubric_data, indent=2)
                rubric = Rubric(
                    question_id=question.id,
                    rubric_text=rubric_text
                )
                db.add(rubric)
                
                questions_list.append({
                    "question_id": str(question.id),
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
            print(f"DEBUG: [SUCCESS] Updated exam {exam.id} with {len(questions_list)} new question(s) in {elapsed:.2f}s")
            
            return {
                "success": True,
                "message": f"Exam updated successfully. Generated {len(questions_list)} new question(s).",
                "exam_id": str(exam.id),
                "questions_count": len(questions_list)
            }
        
        except HTTPException as e:
            db.rollback()
            raise e
        except Exception as e:
            db.rollback()
            elapsed = time.time() - start_time
            print(f"DEBUG: [ERROR] Unexpected error generating questions after {elapsed:.2f}s: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate questions: {str(e)}"
            )
    
    except HTTPException as e:
        # Re-raise HTTP exceptions as-is (already properly formatted)
        try:
            db.rollback()
        except:
            pass  # Session might already be closed
        raise e
    except Exception as e:
        # Catch any other unexpected errors and return JSON error
        try:
            db.rollback()
        except:
            pass  # Session might already be closed
        elapsed = time.time() - start_time
        print(f"DEBUG: [ERROR] Unexpected error editing exam after {elapsed:.2f}s: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while editing the exam: {str(e)}"
        )


@router.post("/api/instructor/assign-exam", tags=["instructor"])
async def assign_exam(
    request: AssignExamRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Assign an exam to one or more students (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can assign exams")
    
    # Verify exam exists and belongs to this instructor
    exam = db.query(Exam).filter(Exam.id == request.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify this is an assigned exam, not a practice exam
    if exam.student_id is not None:
        raise HTTPException(status_code=400, detail="Cannot assign practice exams. Only instructor-created exams can be assigned.")
    
    # Verify instructor owns this exam
    if not current_user.instructor_id or exam.instructor_id != current_user.instructor_id:
        raise HTTPException(status_code=403, detail="You can only assign your own exams")
    
    # Verify exam has questions
    questions_count = db.query(Question).filter(Question.exam_id == exam.id).count()
    if questions_count == 0:
        raise HTTPException(status_code=400, detail="Cannot assign exam without questions. Please generate questions first.")
    
    # Update exam with time limit if provided
    if request.time_limit_minutes is not None and request.time_limit_minutes > 0:
        exam.time_limit_minutes = request.time_limit_minutes
    else:
        exam.time_limit_minutes = None  # No time limit
    
    # Update exam with prevent_tab_switching setting
    exam.prevent_tab_switching = 1 if request.prevent_tab_switching else 0
    
    # Update exam with due date if provided
    exam.due_date = request.due_date if request.due_date else None
    
    # Verify all students exist
    students = []
    for student_id in request.student_ids:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found")
        students.append(student)
    
    # Create submissions for each student (if they don't already have one)
    assigned_count = 0
    already_assigned = []
    
    for student in students:
        # Check if submission already exists
        existing = db.query(Submission).filter(
            Submission.exam_id == exam.id,
            Submission.student_id == student.id
        ).first()
        
        if existing:
            already_assigned.append(student.name)
            continue
        
        # Create new submission (started_at is None until student actually starts the exam)
        submission = Submission(
            exam_id=exam.id,
            student_id=student.id,
            started_at=None  # Will be set when student actually starts the exam
        )
        db.add(submission)
        assigned_count += 1
    
    db.commit()
    
    message = f"Exam assigned to {assigned_count} student(s) successfully."
    if already_assigned:
        message += f" {len(already_assigned)} student(s) already had this exam assigned: {', '.join(already_assigned)}"
    
    return {
        "success": True,
        "message": message,
        "assigned_count": assigned_count,
        "already_assigned_count": len(already_assigned)
    }


@router.get("/api/instructor/students/{student_id}/exam/{exam_id}/answers", tags=["instructor"])
async def get_student_exam_answers(
    student_id: int,
    exam_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get a student's answers for a specific exam (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can view student answers")
    
    # Get student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get exam
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify instructor owns this exam
    if not current_user.instructor_id or exam.instructor_id != current_user.instructor_id:
        raise HTTPException(status_code=403, detail="You can only view answers for your own exams")
    
    # Get submission for this student and exam
    submission = db.query(Submission).filter(
        Submission.student_id == student.id,
        Submission.exam_id == exam.id
    ).order_by(Submission.started_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found for this student and exam")
    
    # Get all questions for this exam, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_with_answers = []
    total_score = 0.0
    max_score = 0.0
    
    for q in questions:
        # Get rubric for question
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        # Get answer for this question
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id
        ).first()
        
        answer_data = None
        if answer:
            # Use instructor score if edited, otherwise use LLM score
            final_score = float(answer.instructor_score) if answer.instructor_edited and answer.instructor_score is not None else (float(answer.llm_score) if answer.llm_score is not None else None)
            
            answer_data = {
                "answer_id": str(answer.id),
                "response_text": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "graded_at": answer.graded_at.isoformat() if answer.graded_at else None,
                "grading_model_name": answer.grading_model_name,
                "instructor_edited": bool(answer.instructor_edited) if answer.instructor_edited is not None else False,
                "instructor_score": float(answer.instructor_score) if answer.instructor_score is not None else None,
                "instructor_feedback": answer.instructor_feedback or "",
                "instructor_edited_at": answer.instructor_edited_at.isoformat() if answer.instructor_edited_at else None,
                "final_score": final_score  # The score that should be displayed (instructor or LLM)
            }
            if final_score is not None:
                total_score += final_score
        
        max_score += float(q.points_possible)
        
        questions_with_answers.append({
            "question_id": str(q.id),
            "q_index": q.q_index,
            "question_text": q.prompt,
            "background_info": q.background_info or "",
            "points_possible": float(q.points_possible),
            "grading_rubric": rubric_data,
            "answer": answer_data
        })
    
    percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0.0
    
    # Get all disputes for this submission
    disputes = db.query(AssignedExamDispute).filter(
        AssignedExamDispute.submission_id == submission.id
    ).order_by(AssignedExamDispute.created_at.desc()).all()
    
    disputes_data = []
    for dispute in disputes:
        # Get question info if it's a question dispute
        question_info = None
        if dispute.question_id:
            question = db.query(Question).filter(Question.id == dispute.question_id).first()
            if question:
                question_info = {
                    "question_number": question.q_index,
                    "prompt": question.prompt,
                }
        
        disputes_data.append({
            "dispute_id": dispute.id,
            "status": dispute.status,
            "target": "overall" if dispute.question_id is None else "question",
            "question_id": dispute.question_id,
            "question_info": question_info,
            "student_argument": dispute.student_argument,
            "instructor_decision": dispute.instructor_decision,
            "instructor_response": dispute.instructor_response,
            "created_at": dispute.created_at.isoformat() if dispute.created_at else None,
            "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        })
    
    return {
        "exam_id": str(exam.id),
        "exam_title": exam.title or f"{exam.domain} Exam",
        "domain": exam.domain,
        "student_id": student.id,
        "student_name": student.name,
        "student_student_id": student.student_id,
        "submission_id": str(submission.id),
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "percentage": percentage,
        "questions_with_answers": questions_with_answers,
        "disputes": disputes_data
    }


class UpdateGradeRequest(BaseModel):
    answer_id: int
    score: float
    feedback: str = ""


@router.put("/api/instructor/answers/{answer_id}/grade", tags=["instructor"])
async def update_answer_grade(
    answer_id: int,
    request: UpdateGradeRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update a student's answer grade and feedback (instructor only)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can update grades")
    
    # Get answer
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # Get submission and exam to verify ownership
    submission = db.query(Submission).filter(Submission.id == answer.submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify instructor owns this exam
    if not current_user.instructor_id or exam.instructor_id != current_user.instructor_id:
        raise HTTPException(status_code=403, detail="You can only update grades for your own exams")
    
    # Get question to validate score is within bounds
    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Validate score is within bounds (0 to points_possible)
    if request.score < 0 or request.score > question.points_possible:
        raise HTTPException(
            status_code=400, 
            detail=f"Score must be between 0 and {question.points_possible} (points possible for this question)"
        )
    
    # Update answer with instructor grading
    answer.instructor_edited = 1
    answer.instructor_score = request.score
    answer.instructor_feedback = request.feedback
    answer.instructor_edited_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Grade updated successfully",
        "answer_id": answer_id,
        "instructor_score": float(answer.instructor_score),
        "instructor_feedback": answer.instructor_feedback,
        "instructor_edited_at": answer.instructor_edited_at.isoformat()
    }


# ============================================================================
# Practice Exam Dispute Endpoints
# ============================================================================

def resolve_practice_submission(db: Session, exam_id: int, student: Student):
    """Resolve exam + latest graded submission for a practice exam dispute.
    
    Enforces:
    - Exam exists
    - Exam is a practice exam owned by this student (strong check: exam.student_id == student.student_id)
    - A graded submission exists
    
    Returns (exam, submission) or raises HTTPException.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Strong ownership check — matches convention in delete_in_progress_exam, start_exam, etc.
    student_campus_id = student.student_id
    if exam.student_id != student_campus_id:
        raise HTTPException(status_code=403, detail="Disputes are only available for your own practice exams")

    # Use codebase convention: order_by(started_at DESC), filter submitted_at IS NOT NULL
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id,
        Submission.student_id == student.id,
        Submission.submitted_at.isnot(None)
    ).order_by(Submission.started_at.desc()).first()

    if not submission:
        raise HTTPException(status_code=404, detail="No graded submission found for this exam")

    return exam, submission


def _build_lock_state(db: Session, submission: Submission, exam_id: int):
    """Build the lock_state dict for a submission (used by both endpoints)."""
    # Disputed questions: find Regrade rows for this submission's answers
    disputed_q_indices = (
        db.query(Question.q_index)
        .join(Answer, Answer.question_id == Question.id)
        .join(Regrade, Regrade.answer_id == Answer.id)
        .filter(Answer.submission_id == submission.id)
        .all()
    )
    disputed_questions = sorted([row[0] for row in disputed_q_indices])

    # Overall used
    overall_used = db.query(SubmissionRegrade).filter(
        SubmissionRegrade.submission_id == submission.id
    ).first() is not None

    num_questions = db.query(Question).filter(Question.exam_id == exam_id).count()

    return {
        "overall_used": overall_used,
        "disputed_questions": disputed_questions,
        "num_questions": num_questions,
    }


class DisputeRequest(BaseModel):
    exam_id: int
    target: str  # "overall" | "question"
    question_number: Optional[int] = None
    argument: str


@router.get("/api/practice/dispute/state", tags=["disputes"])
async def get_dispute_state(
    exam_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the current dispute lock state for a practice exam submission."""
    # Two-step student resolution (existing convention)
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)

    exam, submission = resolve_practice_submission(db, exam_id, student)

    lock = _build_lock_state(db, submission, exam.id)
    lock["submission_id"] = submission.id
    return lock


@router.post("/api/practice/dispute", tags=["disputes"])
async def submit_dispute(
    request: DisputeRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Submit a grade dispute for a practice exam (question-level or overall)."""
    # Two-step student resolution (existing convention)
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)

    exam, submission = resolve_practice_submission(db, request.exam_id, student)

    # Validate target
    if request.target not in ("question", "overall"):
        raise HTTPException(status_code=400, detail="target must be 'question' or 'overall'")

    if request.target == "question":
        return await _handle_question_dispute(db, exam, submission, request)
    else:
        return await _handle_overall_dispute(db, exam, submission, request)


async def _handle_question_dispute(
    db: Session, exam: Exam, submission: Submission, request: DisputeRequest
):
    """Handle a single-question dispute."""
    # Validate question_number
    if request.question_number is None:
        raise HTTPException(status_code=400, detail="question_number is required for question disputes")

    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    num_questions = len(questions)

    if request.question_number < 1 or request.question_number > num_questions:
        raise HTTPException(status_code=400, detail=f"question_number must be between 1 and {num_questions}")

    # Find the question by q_index
    question = next((q for q in questions if q.q_index == request.question_number), None)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {request.question_number} not found")

    # Find the answer
    answer = db.query(Answer).filter(
        Answer.submission_id == submission.id,
        Answer.question_id == question.id,
    ).first()
    if not answer:
        raise HTTPException(status_code=404, detail="No answer found for this question")

    # Enforcement: block if overall dispute already exists
    overall_exists = db.query(SubmissionRegrade).filter(
        SubmissionRegrade.submission_id == submission.id
    ).first()
    if overall_exists:
        raise HTTPException(status_code=409, detail="Overall dispute already submitted; disputes locked for this attempt.")

    # Enforcement: block if this question already has a regrade
    existing_regrade = db.query(Regrade).filter(Regrade.answer_id == answer.id).first()
    if existing_regrade:
        raise HTTPException(status_code=409, detail="You can only dispute each question once.")

    # Build LLM payload
    rubric = db.query(Rubric).filter(Rubric.question_id == question.id).first()
    rubric_text = rubric.rubric_text if rubric else "No rubric available"

    original_score = float(answer.llm_score) if answer.llm_score is not None else 0.0
    original_feedback = answer.llm_feedback or "No feedback"

    # Call LLM
    try:
        llm_result = await adjudicate_dispute_question(
            question_text=question.prompt,
            rubric_text=rubric_text,
            student_answer=answer.student_answer,
            original_score=original_score,
            original_feedback=original_feedback,
            student_argument=request.argument,
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"DEBUG: Unexpected error in question dispute LLM call: {exc}")
        raise HTTPException(status_code=503, detail="AI service error. Please try again.")

    decision = llm_result["decision"]
    new_score = float(llm_result["question_score_new"])
    new_feedback = llm_result.get("feedback_new", original_feedback)

    # Store the regrade row
    regrade = Regrade(
        answer_id=answer.id,
        student_argument=request.argument,
        regrade_score=new_score,
        regrade_feedback=new_feedback,
        llm_response=json.dumps(llm_result),
        regraded_at=datetime.utcnow(),
        regrade_model_name=TOGETHER_AI_MODEL,
        regrade_temperature=0.3,
    )
    db.add(regrade)

    # If decision is "update", also update the Answer
    old_total = _compute_submission_total(db, submission)
    if decision == "update":
        answer.llm_score = new_score
        answer.llm_feedback = new_feedback

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"DEBUG: DB error saving regrade: {exc}")
        raise HTTPException(status_code=409, detail="Could not save dispute — it may already exist.")

    new_total = _compute_submission_total(db, submission)
    lock_state = _build_lock_state(db, submission, exam.id)

    return {
        "ok": True,
        "target": "question",
        "decision": decision,
        "message": llm_result.get("rubric_justification", new_feedback),
        "updates": {
            "question_number": request.question_number,
            "old_score": original_score,
            "new_score": new_score,
            "old_feedback": original_feedback,
            "new_feedback": new_feedback,
            "old_total": old_total,
            "new_total": new_total,
        },
        "lock_state": lock_state,
    }


async def _handle_overall_dispute(
    db: Session, exam: Exam, submission: Submission, request: DisputeRequest
):
    """Handle an overall exam dispute."""
    # Enforcement: block if any question-level regrades exist
    question_regrades_count = (
        db.query(Regrade)
        .join(Answer, Regrade.answer_id == Answer.id)
        .filter(Answer.submission_id == submission.id)
        .count()
    )
    if question_regrades_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Overall review is only available before disputing individual questions.",
        )

    # Enforcement: block if overall already submitted
    existing_overall = db.query(SubmissionRegrade).filter(
        SubmissionRegrade.submission_id == submission.id
    ).first()
    if existing_overall:
        raise HTTPException(status_code=409, detail="Overall dispute already submitted for this attempt.")

    # Gather all questions, rubrics, answers
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    old_total = _compute_submission_total(db, submission)

    # Build the big context string for the LLM
    qa_parts = []
    for q in questions:
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id,
        ).first()
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()

        score = float(answer.llm_score) if answer and answer.llm_score is not None else 0.0
        feedback = answer.llm_feedback if answer else "No feedback"
        rubric_text = rubric.rubric_text if rubric else "No rubric"
        student_answer = answer.student_answer if answer else "No answer"

        qa_parts.append(
            f"--- Question {q.q_index} ---\n"
            f"Question: {q.prompt}\n"
            f"Rubric: {rubric_text}\n"
            f"Student Answer: {student_answer}\n"
            f"Original Score: {score}\n"
            f"Original Feedback: {feedback}\n"
        )

    questions_and_answers = "\n".join(qa_parts)

    # Snapshot old results
    old_results = []
    for q in questions:
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id,
        ).first()
        old_results.append({
            "q_index": q.q_index,
            "score": float(answer.llm_score) if answer and answer.llm_score is not None else None,
            "feedback": answer.llm_feedback if answer else None,
        })

    # Call LLM
    try:
        llm_result = await adjudicate_dispute_overall(
            questions_and_answers=questions_and_answers,
            student_argument=request.argument,
            total_old=old_total,
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"DEBUG: Unexpected error in overall dispute LLM call: {exc}")
        raise HTTPException(status_code=503, detail="AI service error. Please try again.")

    decision = llm_result["decision"]
    explanation = llm_result.get("overall_explanation", "No explanation provided.")

    # Apply updates if decision is "update"
    if decision == "update":
        q_map = {q.q_index: q for q in questions}
        for upd in llm_result.get("question_updates", []):
            q_num = upd.get("question_number")
            if q_num and q_num in q_map:
                q = q_map[q_num]
                answer = db.query(Answer).filter(
                    Answer.submission_id == submission.id,
                    Answer.question_id == q.id,
                ).first()
                if answer:
                    answer.llm_score = float(upd["score_new"])
                    if upd.get("feedback_new"):
                        answer.llm_feedback = upd["feedback_new"]

    new_total = _compute_submission_total(db, submission)

    # Build new results snapshot
    new_results = []
    for q in questions:
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id,
        ).first()
        new_results.append({
            "q_index": q.q_index,
            "score": float(answer.llm_score) if answer and answer.llm_score is not None else None,
            "feedback": answer.llm_feedback if answer else None,
        })

    # Insert SubmissionRegrade row
    sub_regrade = SubmissionRegrade(
        submission_id=submission.id,
        student_argument=request.argument,
        decision=decision,
        explanation=explanation,
        old_total_score=int(old_total),
        new_total_score=int(new_total),
        old_results_json=json.dumps(old_results),
        new_results_json=json.dumps(new_results),
        model_name=TOGETHER_AI_MODEL,
    )
    db.add(sub_regrade)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"DEBUG: DB error saving overall regrade: {exc}")
        raise HTTPException(status_code=409, detail="Could not save dispute — it may already exist.")

    lock_state = _build_lock_state(db, submission, exam.id)

    return {
        "ok": True,
        "target": "overall",
        "decision": decision,
        "message": explanation,
        "updates": {
            "question_number": None,
            "old_score": None,
            "new_score": None,
            "old_feedback": None,
            "new_feedback": None,
            "old_total": old_total,
            "new_total": new_total,
        },
        "lock_state": lock_state,
    }


def _compute_submission_total(db: Session, submission: Submission) -> float:
    """Compute the total score for a submission from its answers."""
    answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
    total = 0.0
    for a in answers:
        if a.instructor_edited and a.instructor_score is not None:
            total += float(a.instructor_score)
        elif a.llm_score is not None:
            total += float(a.llm_score)
    return round(total, 2)


# ============================================================================
# Assigned Exam Dispute Endpoints
# ============================================================================

def resolve_assigned_submission(db: Session, exam_id: int, student: Student):
    """Resolve exam + latest graded submission for an assigned exam dispute.
    Returns (exam, submission) tuple.
    Raises HTTPException if not found or invalid.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify this is an assigned exam (not a practice exam)
    if exam.student_id is not None:
        raise HTTPException(status_code=400, detail="This endpoint is only for assigned exams, not practice exams")
    
    # Get the latest submission for this student and exam
    submission = db.query(Submission).filter(
        Submission.exam_id == exam_id,
        Submission.student_id == student.id
    ).order_by(Submission.submitted_at.desc()).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found for this exam")
    
    # Verify submission is graded (has submitted_at)
    if submission.submitted_at is None:
        raise HTTPException(status_code=400, detail="Exam must be submitted before disputing")
    
    return exam, submission


class AssignedDisputeRequest(BaseModel):
    exam_id: int
    target: str  # 'question' or 'overall'
    question_number: Optional[int] = None
    argument: str


@router.get("/api/assigned/dispute/state", tags=["disputes"])
async def get_assigned_dispute_state(
    exam_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the current dispute state for an assigned exam submission."""
    if current_user.user_type != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    # Get student
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    exam, submission = resolve_assigned_submission(db, exam_id, student)
    
    # Get all disputes for this submission
    disputes = db.query(AssignedExamDispute).filter(
        AssignedExamDispute.submission_id == submission.id
    ).all()
    
    # Check for overall dispute
    overall_dispute = next((d for d in disputes if d.question_id is None), None)
    overall_used = overall_dispute is not None
    
    # Get disputed question IDs
    disputed_question_ids = [d.question_id for d in disputes if d.question_id is not None]
    
    # Get questions to determine count
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    num_questions = len(questions)
    
    # Map question IDs to question numbers (q_index)
    disputed_questions = []
    for q in questions:
        if q.id in disputed_question_ids:
            disputed_questions.append(q.q_index)
    
    return {
        "overall_used": overall_used,
        "disputed_questions": sorted(disputed_questions),
        "num_questions": num_questions,
        "submission_id": submission.id,
    }


@router.post("/api/assigned/dispute", tags=["disputes"])
async def submit_assigned_dispute(
    request: AssignedDisputeRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Submit a grade dispute for an assigned exam (sends notification to instructor)."""
    if current_user.user_type != "student":
        raise HTTPException(status_code=403, detail="Only students can submit disputes")
    
    # Get student
    if current_user.user_type == "student" and current_user.student_id:
        student = db.query(Student).filter(Student.id == current_user.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found for user")
    else:
        student = get_or_create_student(db, current_user.username, name=current_user.username)
    
    exam, submission = resolve_assigned_submission(db, request.exam_id, student)
    
    # Validate target
    if request.target not in ("question", "overall"):
        raise HTTPException(status_code=400, detail="target must be 'question' or 'overall'")
    
    # Check for existing overall dispute
    if request.target == "overall":
        existing = db.query(AssignedExamDispute).filter(
            AssignedExamDispute.submission_id == submission.id,
            AssignedExamDispute.question_id.is_(None)
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Overall dispute already submitted for this exam")
        question_id = None
    else:
        # Question dispute
        if request.question_number is None:
            raise HTTPException(status_code=400, detail="question_number is required for question disputes")
        
        questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
        num_questions = len(questions)
        
        if request.question_number < 1 or request.question_number > num_questions:
            raise HTTPException(status_code=400, detail=f"question_number must be between 1 and {num_questions}")
        
        # Find the question
        question = next((q for q in questions if q.q_index == request.question_number), None)
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {request.question_number} not found")
        
        # Check for existing dispute for this question
        existing = db.query(AssignedExamDispute).filter(
            AssignedExamDispute.submission_id == submission.id,
            AssignedExamDispute.question_id == question.id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="You can only dispute each question once.")
        
        question_id = question.id
    
    # Check for overall dispute (blocks question disputes)
    overall_exists = db.query(AssignedExamDispute).filter(
        AssignedExamDispute.submission_id == submission.id,
        AssignedExamDispute.question_id.is_(None)
    ).first()
    if overall_exists:
        raise HTTPException(status_code=409, detail="Overall dispute already submitted; disputes locked for this attempt.")
    
    # Create dispute record
    dispute = AssignedExamDispute(
        submission_id=submission.id,
        question_id=question_id,
        student_argument=request.argument,
        status="pending",
    )
    db.add(dispute)
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"DEBUG: DB error saving dispute: {exc}")
        raise HTTPException(status_code=500, detail="Could not save dispute. Please try again.")
    
    return {
        "ok": True,
        "target": request.target,
        "message": "Your dispute has been submitted. The instructor will review it and respond.",
        "dispute_id": dispute.id,
    }


@router.get("/api/instructor/disputes", tags=["instructor"])
async def get_instructor_disputes(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all pending disputes for exams created by the current instructor."""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can access this endpoint")
    
    # Get instructor
    instructor = get_or_create_instructor_for_user(db, current_user)
    
    # Get all disputes for exams created by this instructor
    # Join through submission -> exam -> instructor
    disputes = db.query(AssignedExamDispute).join(
        Submission, AssignedExamDispute.submission_id == Submission.id
    ).join(
        Exam, Submission.exam_id == Exam.id
    ).filter(
        Exam.instructor_id == instructor.id,
        AssignedExamDispute.status == "pending"
    ).order_by(AssignedExamDispute.created_at.desc()).all()
    
    disputes_data = []
    for dispute in disputes:
        submission = dispute.submission
        exam = submission.exam
        student = submission.student
        
        # Get question info if it's a question dispute
        question_info = None
        if dispute.question_id:
            question = db.query(Question).filter(Question.id == dispute.question_id).first()
            if question:
                question_info = {
                    "question_number": question.q_index,
                    "prompt": question.prompt,
                }
        
        disputes_data.append({
            "dispute_id": dispute.id,
            "exam_id": exam.id,
            "exam_title": exam.title or exam.domain,
            "student_id": student.id,
            "student_name": student.name or student.student_id,
            "submission_id": submission.id,
            "question_id": dispute.question_id,
            "question_info": question_info,
            "target": "question" if dispute.question_id else "overall",
            "student_argument": dispute.student_argument,
            "created_at": dispute.created_at.isoformat() if dispute.created_at else None,
        })
    
    return {
        "disputes": disputes_data,
        "count": len(disputes_data),
    }


@router.get("/api/instructor/submission/{submission_id}", tags=["instructor"])
async def get_submission_details(
    submission_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get submission details with answers for instructor review (used for disputes)"""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can view submissions")
    
    # Get submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Get exam and verify ownership
    exam = db.query(Exam).filter(Exam.id == submission.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    instructor = get_or_create_instructor_for_user(db, current_user)
    if exam.instructor_id != instructor.id:
        raise HTTPException(status_code=403, detail="You can only view submissions for your own exams")
    
    # Get student
    student = db.query(Student).filter(Student.id == submission.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get all questions for this exam, ordered by q_index
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    answers_data = []
    for q in questions:
        # Get answer for this question
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == q.id
        ).first()
        
        if answer:
            answers_data.append({
                "question_id": q.id,
                "question_number": q.q_index,
                "question_prompt": q.prompt,
                "student_answer": answer.student_answer,
                "llm_score": float(answer.llm_score) if answer.llm_score is not None else None,
                "llm_feedback": answer.llm_feedback or "",
                "points_possible": float(q.points_possible),
                "instructor_edited": bool(answer.instructor_edited) if answer.instructor_edited is not None else False,
                "instructor_score": float(answer.instructor_score) if answer.instructor_score is not None else None,
            })
    
    return {
        "submission_id": submission.id,
        "exam_id": exam.id,
        "exam_title": exam.title or exam.domain,
        "student_id": student.id,
        "student_name": student.name or student.student_id,
        "answers": answers_data,
    }


class ResolveDisputeRequest(BaseModel):
    instructor_response: str
    instructor_decision: str  # 'approved', 'rejected', 'partially_approved'


@router.put("/api/instructor/disputes/{dispute_id}/resolve", tags=["instructor"])
async def resolve_dispute(
    dispute_id: int,
    request: ResolveDisputeRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Resolve a dispute (instructor only)."""
    if current_user.user_type != "instructor":
        raise HTTPException(status_code=403, detail="Only instructors can resolve disputes")
    
    if request.instructor_decision not in ("approved", "rejected", "partially_approved"):
        raise HTTPException(status_code=400, detail="instructor_decision must be 'approved', 'rejected', or 'partially_approved'")
    
    # Get dispute
    dispute = db.query(AssignedExamDispute).filter(AssignedExamDispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    if dispute.status != "pending":
        raise HTTPException(status_code=400, detail="Dispute has already been resolved")
    
    # Verify instructor owns the exam
    submission = dispute.submission
    exam = submission.exam
    instructor = get_or_create_instructor_for_user(db, current_user)
    
    if exam.instructor_id != instructor.id:
        raise HTTPException(status_code=403, detail="You can only resolve disputes for your own exams")
    
    # Update dispute
    dispute.status = "resolved"
    dispute.instructor_response = request.instructor_response
    dispute.instructor_decision = request.instructor_decision
    dispute.resolved_at = datetime.utcnow()
    dispute.resolved_by = instructor.id
    
    # If approved and it's a question dispute, update the answer grade
    if request.instructor_decision == "approved" and dispute.question_id:
        answer = db.query(Answer).filter(
            Answer.submission_id == submission.id,
            Answer.question_id == dispute.question_id
        ).first()
        if answer:
            # For now, we'll just mark it as instructor-reviewed
            # The instructor can manually update the grade using the existing grade update endpoint
            pass
    
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"DEBUG: DB error resolving dispute: {exc}")
        raise HTTPException(status_code=500, detail="Could not resolve dispute. Please try again.")
    
    return {
        "success": True,
        "message": "Dispute resolved successfully",
        "dispute_id": dispute.id,
    }