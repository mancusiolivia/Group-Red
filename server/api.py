"""
All API endpoints for the Essay Testing System
Handles all GET, POST, and other HTTP endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import uuid
import json
from datetime import datetime

from server.core.models import QuestionRequest, StudentResponse, GradingRequest
from server.core.llm_service import call_together_ai, extract_json_from_response, QUESTION_GENERATION_TEMPLATE, GRADING_TEMPLATE
from server.core.storage import exams_storage, student_responses_storage

router = APIRouter()


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
async def generate_questions(request: QuestionRequest):
    """Generate essay questions using LLM"""
    print(
        f"DEBUG: Generate questions request - Domain: {request.domain}, Questions: {request.num_questions}")
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
            print(
                f"DEBUG: Response type: {type(question_data)}, Is list: {isinstance(question_data, list)}")
            if isinstance(question_data, list):
                print(
                    f"DEBUG: Number of questions in response: {len(question_data)}")
        except ValueError as e:
            print(f"DEBUG: JSON extraction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse LLM response as JSON. The AI may not have returned valid JSON. Error: {str(e)}"
            )

        # Handle multiple questions or single question
        # The LLM should return an array, but handle both cases
        if isinstance(question_data, dict):
            # Single question returned as object - convert to list
            print("DEBUG: LLM returned single question object, converting to list")
            question_data = [question_data]
        elif isinstance(question_data, list):
            # Array returned - use as is
            print(
                f"DEBUG: LLM returned array with {len(question_data)} question(s)")
            if len(question_data) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="LLM returned an empty array. No questions were generated."
                )
            # If we requested more questions than received, use what we got
            if len(question_data) < request.num_questions:
                print(
                    f"DEBUG: Warning - requested {request.num_questions} questions but got {len(question_data)}")
        else:
            # Unexpected type
            print(f"DEBUG: Unexpected response type: {type(question_data)}")
            question_data = [question_data]

        # Create exam with questions
        exam_id = str(uuid.uuid4())
        questions = []

        for idx, q_data in enumerate(question_data):
            if not isinstance(q_data, dict):
                print(
                    f"DEBUG: Warning - question {idx} is not a dict: {type(q_data)}")
                continue

            question_id = str(uuid.uuid4())
            question_obj = {
                "question_id": question_id,
                "background_info": q_data.get("background_info", ""),
                "question_text": q_data.get("question_text", ""),
                "grading_rubric": q_data.get("grading_rubric", {}),
                "domain_info": q_data.get("domain_info", "")
            }
            questions.append(question_obj)

        if len(questions) == 0:
            raise HTTPException(
                status_code=500,
                detail="No valid questions were generated from the LLM response."
            )

        # Store exam
        exams_storage[exam_id] = {
            "exam_id": exam_id,
            "domain": request.domain,
            "created_at": datetime.now().isoformat(),
            "questions": questions
        }

        print(
            f"DEBUG: Successfully created exam with {len(questions)} question(s)")
        return {
            "exam_id": exam_id,
            "questions": questions
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(
            f"DEBUG: Unexpected error in generate_questions: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error generating questions: {str(e)}")


# ============================================================================
# Exam Endpoints
# ============================================================================

@router.get("/api/exam/{exam_id}", tags=["exams"])
async def get_exam(exam_id: str):
    """Get exam details"""
    if exam_id not in exams_storage:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exams_storage[exam_id]


# ============================================================================
# Response Submission and Grading Endpoints
# ============================================================================

@router.post("/api/submit-response", tags=["responses"])
async def submit_response(response: StudentResponse):
    """Submit student response and get graded result"""
    try:
        # Get exam and question data
        if response.exam_id not in exams_storage:
            raise HTTPException(status_code=404, detail="Exam not found")

        exam = exams_storage[response.exam_id]
        question = None
        for q in exam["questions"]:
            if q["question_id"] == response.question_id:
                question = q
                break

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Prepare grading prompt
        rubric_str = json.dumps(question["grading_rubric"], indent=2)
        prompt = GRADING_TEMPLATE.format(
            question_text=question["question_text"],
            grading_rubric=rubric_str,
            background_info=question["background_info"],
            domain_info=question.get("domain_info", ""),
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

        # Create grade result with v2 fields
        grade_result = {
            "question_id": response.question_id,
            "scores": grade_data.get("scores", {}),
            "total_score": grade_data.get("total_score", 0.0),
            "explanation": grade_data.get("explanation", ""),
            "feedback": grade_data.get("feedback", ""),
            # New v2 fields for detailed rubric breakdown and annotations
            "rubric_breakdown": grade_data.get("rubric_breakdown", []),
            "annotations": grade_data.get("annotations", [])
        }

        # Store response and grade
        response_key = f"{response.exam_id}_{response.question_id}"
        student_responses_storage[response_key] = {
            "exam_id": response.exam_id,
            "question_id": response.question_id,
            "response_text": response.response_text,
            "time_spent_seconds": response.time_spent_seconds,
            "grade": grade_result,
            "submitted_at": datetime.now().isoformat()
        }

        return grade_result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error grading response: {str(e)}")


@router.post("/grading", tags=["grading"])
async def grade_with_rubric(request: GradingRequest):
    """Grade a student response using the stored rubric for an exam/question"""
    try:
        # Get exam and question data from storage
        if request.exam_id not in exams_storage:
            raise HTTPException(status_code=404, detail="Exam not found")

        exam = exams_storage[request.exam_id]
        question = None
        for q in exam["questions"]:
            if q["question_id"] == request.question_id:
                question = q
                break

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Prepare grading prompt using stored rubric
        rubric_str = json.dumps(question["grading_rubric"], indent=2)
        prompt = GRADING_TEMPLATE.format(
            question_text=question["question_text"],
            grading_rubric=rubric_str,
            background_info=question["background_info"],
            domain_info=question.get("domain_info", ""),
            student_response=request.student_response,
            time_spent=request.time_spent_seconds or 0
        )

        # Call LLM for grading
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON with accurate scores."
        )

        # Parse grading result
        grade_data = extract_json_from_response(llm_response)

        # Create and return grade result with v2 fields
        grade_result = {
            "scores": grade_data.get("scores", {}),
            "total_score": grade_data.get("total_score", 0.0),
            "explanation": grade_data.get("explanation", ""),
            "feedback": grade_data.get("feedback", ""),
            # New v2 fields for detailed rubric breakdown and annotations
            "rubric_breakdown": grade_data.get("rubric_breakdown", []),
            "annotations": grade_data.get("annotations", [])
        }

        return grade_result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(
            f"DEBUG: Unexpected error in grade_with_rubric: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error grading response: {str(e)}")


@router.get("/api/response/{exam_id}/{question_id}", tags=["responses"])
async def get_response(exam_id: str, question_id: str):
    """Get stored student response and grade"""
    response_key = f"{exam_id}_{question_id}"
    if response_key not in student_responses_storage:
        raise HTTPException(status_code=404, detail="Response not found")
    return student_responses_storage[response_key]
