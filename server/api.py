"""
All API endpoints for the Essay Testing System
Handles all GET, POST, and other HTTP endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import json
from datetime import datetime

from server.core.models import QuestionRequest, StudentResponse
from server.core.llm_service import call_together_ai, extract_json_from_response, QUESTION_GENERATION_TEMPLATE, GRADING_TEMPLATE
from server.core.database import get_db
from server.core.db_models import (
    Instructor, Student, Exam, Question, Rubric,
    Submission, Answer
)
from server.core.config import TOGETHER_AI_MODEL

router = APIRouter()


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
async def generate_questions(request: QuestionRequest, db: Session = Depends(get_db)):
    """Generate essay questions using LLM and store in database"""
    print(f"DEBUG: Generate questions request - Domain: {request.domain}, Questions: {request.num_questions}")
    try:
        # Complete the prompt template
        prompt = QUESTION_GENERATION_TEMPLATE.format(
            domain=request.domain,
            professor_instructions=request.professor_instructions or "No specific instructions provided.",
            num_questions=request.num_questions
        )
        print(f"DEBUG: Prompt created ({len(prompt)} chars)")
        
        # Call LLM
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON."
        )
        
        # Parse LLM response
        try:
            question_data = extract_json_from_response(llm_response)
            print(f"DEBUG: Successfully parsed JSON response")
            print(f"DEBUG: Response type: {type(question_data)}, Is list: {isinstance(question_data, list)}")
            if isinstance(question_data, list):
                print(f"DEBUG: Number of questions in response: {len(question_data)}")
        except ValueError as e:
            print(f"DEBUG: JSON extraction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse LLM response as JSON. The AI may not have returned valid JSON. Error: {str(e)}"
            )
        
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
                print(f"DEBUG: Warning - requested {request.num_questions} questions but got {len(question_data)}")
        else:
            print(f"DEBUG: Unexpected response type: {type(question_data)}")
            question_data = [question_data]
        
        # Get or create default instructor
        instructor = get_or_create_default_instructor(db)
        
        # Create exam in database
        exam = Exam(
            instructor_id=instructor.id,
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
                print(f"DEBUG: Warning - question {idx} is not a dict: {type(q_data)}")
                continue
            
            # Calculate total points from rubric
            rubric_data = q_data.get("grading_rubric", {})
            total_points = rubric_data.get("total_points", 10.0)
            
            question = Question(
                exam_id=exam.id,
                q_index=idx + 1,  # 1-indexed
                prompt=q_data.get("question_text", ""),
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
        
        print(f"DEBUG: Successfully created exam {exam.id} with {len(questions_list)} question(s)")
        return {
            "exam_id": str(exam.id),  # Convert to string for compatibility
            "questions": questions_list
        }
    
    except HTTPException as e:
        # Re-raise HTTP exceptions as-is (already user-friendly)
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Unexpected error in generate_questions: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating questions. Please try again."
        )


# ============================================================================
# Exam Endpoints
# ============================================================================

@router.get("/api/exam/{exam_id}", tags=["exams"])
async def get_exam(exam_id: str, db: Session = Depends(get_db)):
    """Get exam details from database"""
    try:
        exam_id_int = int(exam_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id format")
    
    exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Load questions with rubrics
    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.q_index).all()
    
    questions_list = []
    for q in questions:
        rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
        rubric_data = {}
        if rubric:
            try:
                rubric_data = json.loads(rubric.rubric_text)
            except:
                rubric_data = {"text": rubric.rubric_text}
        
        questions_list.append({
            "question_id": str(q.id),
            "background_info": "",  # Not stored in DB currently
            "question_text": q.prompt,
            "grading_rubric": rubric_data,
            "domain_info": ""  # Not stored in DB currently
        })
    
    return {
        "exam_id": str(exam.id),
        "domain": exam.domain,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "questions": questions_list
    }


# ============================================================================
# Response Submission and Grading Endpoints
# ============================================================================

@router.post("/api/submit-response", tags=["responses"])
async def submit_response(response: StudentResponse, db: Session = Depends(get_db)):
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
            background_info="",  # Not stored currently
            domain_info="",  # Not stored currently
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
        
        # Create or get student (using a default student_id if not provided)
        # In a real app, you'd get this from authentication
        student_id_str = "student_001"  # TODO: Get from request/auth
        student = get_or_create_student(db, student_id_str)
        
        # Create or get submission
        submission = db.query(Submission).filter(
            Submission.exam_id == exam_id_int,
            Submission.student_id == student.id
        ).order_by(Submission.started_at.desc()).first()
        
        if not submission:
            submission = Submission(
                exam_id=exam_id_int,
                student_id=student.id,
                started_at=datetime.utcnow(),
                submitted_at=datetime.utcnow()
            )
            db.add(submission)
            db.flush()
        
        # Create answer record
        answer = Answer(
            submission_id=submission.id,
            question_id=question_id_int,
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
async def get_response(exam_id: str, question_id: str, db: Session = Depends(get_db)):
    """Get stored student response and grade from database"""
    try:
        exam_id_int = int(exam_id)
        question_id_int = int(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid exam_id or question_id format")
    
    # Find the most recent answer for this exam/question
    # In a real app, you'd filter by student_id from auth
    answer = db.query(Answer).join(Submission).filter(
        Submission.exam_id == exam_id_int,
        Answer.question_id == question_id_int
    ).order_by(Answer.graded_at.desc()).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Response not found")
    
    return {
        "exam_id": exam_id,
        "question_id": question_id,
        "response_text": answer.student_answer,
        "time_spent_seconds": None,  # Not stored currently
        "grade": {
            "question_id": question_id,
            "scores": {},  # Could parse from feedback if needed
            "total_score": float(answer.llm_score) if answer.llm_score else 0.0,
            "explanation": "",
            "feedback": answer.llm_feedback or ""
        },
        "submitted_at": answer.graded_at.isoformat() if answer.graded_at else None
    }
