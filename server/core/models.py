"""
Pydantic data models for request/response validation
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class QuestionRequest(BaseModel):
    """Request model for generating questions"""
    domain: str
    professor_instructions: Optional[str] = None
    num_questions: int = 1


class QuestionData(BaseModel):
    """Model for question data"""
    question_id: str
    background_info: str
    question_text: str
    grading_rubric: Dict[str, Any]
    domain_info: Optional[str] = None


class StudentResponse(BaseModel):
    """Request model for submitting student responses"""
    exam_id: str
    question_id: str
    response_text: str
    time_spent_seconds: Optional[int] = None


class GradeResult(BaseModel):
    """Model for grading results"""
    question_id: str
    scores: Dict[str, float]
    total_score: float
    explanation: str
    feedback: str
