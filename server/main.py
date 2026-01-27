"""
FastAPI server for Essay Testing and Evaluation System
Handles question generation, student responses, and AI-powered grading
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import json
import os
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app without default root route
app = FastAPI(
    title="Essay Testing System", 
    version="1.0.0", 
    docs_url="/docs", 
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"REQUEST: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"RESPONSE: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the base directory (parent of server directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_STATIC_DIR = os.path.join(BASE_DIR, "client", "static")
CLIENT_HTML_DIR = os.path.join(BASE_DIR, "client")

# Mount static files (frontend) - must be after routes to avoid conflicts
# Note: We'll mount this after defining the root route

# Configuration
TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY", "tgp_v1_pMCB-qUW938Aww7f-PUcrwi_u_qzgxmDBlfSCaCbwrw")
TOGETHER_AI_API_URL = "https://api.together.xyz/v1/chat/completions"
# Using a serverless model that's available on Together.ai
# Common serverless models (try these if one doesn't work):
# - mistralai/Mixtral-8x7B-Instruct-v0.1 (most commonly available)
# - meta-llama/Llama-2-70b-chat-hf
# - Qwen/Qwen2.5-72B-Instruct
# - NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO
TOGETHER_AI_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"  # Serverless model - commonly available

# In-memory storage (in production, use a database)
exams_storage: Dict[str, Dict] = {}
student_responses_storage: Dict[str, Dict] = {}
disputes_storage: Dict[str, Dict] = {}  # Key: f"{exam_id}_{question_id}", Value: dispute data


# Data Models
class QuestionRequest(BaseModel):
    domain: str
    professor_instructions: Optional[str] = None
    num_questions: int = 1


class QuestionData(BaseModel):
    question_id: str
    background_info: str
    question_text: str
    grading_rubric: Dict[str, Any]
    domain_info: Optional[str] = None


class StudentResponse(BaseModel):
    exam_id: str
    question_id: str
    response_text: str
    time_spent_seconds: Optional[int] = None


class GradeResult(BaseModel):
    question_id: str
    scores: Dict[str, float]
    total_score: float
    explanation: str
    feedback: str


class DisputeRequest(BaseModel):
    exam_id: str
    question_id: str
    complaint_text: str


# Prompt Templates
QUESTION_GENERATION_TEMPLATE = """You are an expert educator creating essay exam questions in the domain of: {domain}

{professor_instructions}

CRITICAL: You MUST create EXACTLY {num_questions} DIFFERENT essay questions. Each question must be on a DIFFERENT topic within {domain}.

Your task is to return a JSON ARRAY containing exactly {num_questions} question objects. Each question object must have this EXACT structure:
{{
    "background_info": "A comprehensive information sheet about the topic that may be displayed to students as background context",
    "question_text": "The essay question that students will answer",
    "grading_rubric": {{
        "dimensions": [
            {{
                "name": "Dimension name (e.g., 'Understanding of Core Concepts')",
                "description": "What this dimension evaluates",
                "max_points": 10,
                "criteria": [
                    "Criterion 1 for full points",
                    "Criterion 2 for partial points",
                    "Criterion 3 for minimal points"
                ]
            }}
        ],
        "total_points": 30
    }},
    "domain_info": "Specific domain knowledge students should demonstrate in their answer"
}}

REQUIRED OUTPUT FORMAT - You MUST return a JSON ARRAY (starts with [ and ends with ]):
[
  {{
    "background_info": "First question background info...",
    "question_text": "First question text...",
    "grading_rubric": {{
      "dimensions": [...],
      "total_points": 30
    }},
    "domain_info": "First question domain info..."
  }},
  {{
    "background_info": "Second question background info...",
    "question_text": "Second question text...",
    "grading_rubric": {{
      "dimensions": [...],
      "total_points": 30
    }},
    "domain_info": "Second question domain info..."
  }}{additional_questions}
]

Return ONLY the JSON array. No text before [ and no text after ]. The array must contain exactly {num_questions} objects.
"""

GRADING_TEMPLATE = """You are an expert educator grading a student's essay response.

Question: {question_text}

Grading Rubric:
{grading_rubric}

Background Information Provided to Student:
{background_info}

Domain Knowledge Expected:
{domain_info}

Student's Response:
{student_response}

Time Spent: {time_spent} seconds

Your task is to grade this response according to the rubric. Evaluate the student's answer along each dimension in the rubric.

Return a JSON object with this exact structure:
{{
    "scores": {{
        "Dimension Name 1": <score out of max_points>,
        "Dimension Name 2": <score out of max_points>
    }},
    "total_score": <sum of all dimension scores>,
    "explanation": "Detailed explanation of why the student received these scores, referencing specific parts of their answer and the rubric criteria",
    "feedback": "Constructive feedback for the student on how to improve their answer"
}}

Return ONLY valid JSON, no additional text before or after.
"""

DISPUTE_ASSESSMENT_TEMPLATE = """You are an expert educator reviewing a student's dispute of their grade.

Original Question: {question_text}

Grading Rubric:
{grading_rubric}

Student's Original Response:
{student_response}

Original Grade:
{original_grade}

Original Grading Explanation:
{original_explanation}

Student's Complaint/Dispute:
{complaint_text}

Time Since Grading: {time_since_grading}

Your task is to assess the validity of the student's dispute. Consider:
1. Does the student make valid points about the grading?
2. Are there factual errors in the original grading?
3. Did the grader miss important aspects of the student's response?
4. Is the complaint logical and well-reasoned, or is it emotional/defensive?
5. Does the student provide specific evidence from their response or the rubric?

Return a JSON object with this exact structure:
{{
    "is_valid": <true or false>,
    "validity_score": <0.0 to 1.0, where 1.0 is completely valid>,
    "assessment": "Detailed assessment of the dispute's validity, explaining why it is or isn't valid",
    "recommendation": "Recommendation: 'regrade' if the dispute is valid and regrading is warranted, 'review' if professor review is needed, or 'reject' if the dispute is invalid",
    "key_points": ["Point 1 about the dispute", "Point 2 about the dispute"],
    "suggested_action": "Specific action to take based on the dispute"
}}

Return ONLY valid JSON, no additional text before or after.
"""


async def call_together_ai(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Call Together.ai API to get LLM response"""
    headers = {
        "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": TOGETHER_AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000  # Increased for multiple questions
    }
    
    try:
        print(f"DEBUG: Calling Together.ai API with model: {TOGETHER_AI_MODEL}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(TOGETHER_AI_API_URL, headers=headers, json=payload)
            print(f"DEBUG: API Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                print(f"DEBUG: API Error response: {error_text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Together.ai API error: {error_text}"
                )
            
            result = response.json()
            if "choices" not in result or len(result["choices"]) == 0:
                print(f"DEBUG: Unexpected API response format: {result}")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from Together.ai API"
                )
            
            content = result["choices"][0]["message"]["content"]
            print(f"DEBUG: Received response from LLM ({len(content)} chars)")
            return content
    except httpx.TimeoutException:
        print("DEBUG: Request to Together.ai timed out")
        raise HTTPException(status_code=500, detail="Request to LLM timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        print(f"DEBUG: HTTP error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=500,
            detail=f"Together.ai API HTTP error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        print(f"DEBUG: Unexpected error calling Together.ai: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling potential markdown code blocks and extra text"""
    text = text.strip()
    print(f"DEBUG: Extracting JSON from response (first 200 chars: {text[:200]})")
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Find the closing ```
        closing_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                closing_idx = i
                break
        if closing_idx > 0:
            text = "\n".join(lines[1:closing_idx])
        else:
            text = "\n".join(lines[1:])
        print("DEBUG: Removed markdown code block markers")
    
    # Check if it's an array or object
    array_start = text.find("[")
    object_start = text.find("{")
    
    # Determine start position and what we're looking for
    if array_start != -1 and (object_start == -1 or array_start < object_start):
        # It's an array
        start_idx = array_start
        start_char = '['
        end_char = ']'
        print("DEBUG: Detected JSON array")
    elif object_start != -1:
        # It's an object
        start_idx = object_start
        start_char = '{'
        end_char = '}'
        print("DEBUG: Detected JSON object")
    else:
        # Try to find JSON in the text - maybe it's wrapped in text
        print(f"DEBUG: No clear JSON start found. Full text preview: {text[:500]}")
        # Try to find any JSON-like structure
        if '[' in text or '{' in text:
            # Try to find the first occurrence of either
            if '[' in text:
                array_start = text.find('[')
            if '{' in text:
                object_start = text.find('{')
            if array_start != -1 and (object_start == -1 or array_start < object_start):
                start_idx = array_start
                start_char = '['
                end_char = ']'
                print("DEBUG: Found JSON array after searching")
            elif object_start != -1:
                start_idx = object_start
                start_char = '{'
                end_char = '}'
                print("DEBUG: Found JSON object after searching")
            else:
                raise ValueError(f"No JSON array or object found in response. Text starts with: {text[:100]}")
        else:
            raise ValueError(f"No JSON array or object found in response. Text starts with: {text[:100]}")
    
    # Count brackets/braces to find the matching closing
    count = 0
    end_idx = start_idx
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == start_char:
                count += 1
            elif char == end_char:
                count -= 1
                if count == 0:
                    end_idx = i + 1
                    break
    
    if count != 0:
        # If we couldn't find matching brackets, try the old method
        print(f"DEBUG: Warning - brace/bracket count mismatch. Count: {count}, looking for {end_char}")
        end_idx = text.rfind(end_char) + 1
        if end_idx <= start_idx:
            # Last resort: show what we found
            print(f"DEBUG: Could not find matching {end_char}. Text around start: {text[max(0, start_idx-50):start_idx+200]}")
            raise ValueError(f"Could not find complete JSON {start_char}{end_char}. Unmatched brackets (count: {count})")
        else:
            print(f"DEBUG: Using last {end_char} as end point (fallback method)")
    
    json_str = text[start_idx:end_idx]
    print(f"DEBUG: Extracted JSON string ({len(json_str)} chars)")
    
    try:
        # Try to parse just the JSON part, ignoring any extra text after it
        parsed = json.loads(json_str)
        print(f"DEBUG: Successfully parsed JSON (type: {type(parsed).__name__})")
        return parsed
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parse error: {e}")
        print(f"DEBUG: Problematic JSON string (first 500 chars): {json_str[:500]}")
        # Try to fix common issues
        import re
        # Fix escaped underscores and other common escape issues
        json_str_fixed = json_str.replace('\\_', '_')  # Fix escaped underscores
        json_str_fixed = re.sub(r',\s*}', '}', json_str_fixed)  # Remove trailing commas
        json_str_fixed = re.sub(r',\s*]', ']', json_str_fixed)  # Remove trailing commas in arrays
        try:
            parsed = json.loads(json_str_fixed)
            print(f"DEBUG: Successfully parsed JSON after fixing escape issues (type: {type(parsed).__name__})")
            return parsed
        except json.JSONDecodeError as e2:
            print(f"DEBUG: Still failed after fixing: {e2}")
            raise ValueError(f"Invalid JSON in LLM response: {str(e)}")


@app.get("/test", tags=["test"])
async def test_route():
    """Test route to verify server is working"""
    print("=" * 50)
    print("TEST ROUTE HIT!")
    print("=" * 50)
    return {"message": "Test route works!", "server": "essay-testing-system", "app_title": app.title}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve the main frontend page"""
    print("=" * 50)
    print("ROOT ROUTE HIT!")
    print("=" * 50)
    html_path = os.path.join(CLIENT_HTML_DIR, "index.html")
    print(f"DEBUG: Serving root route. HTML path: {html_path}")
    print(f"DEBUG: File exists: {os.path.exists(html_path)}")
    print(f"DEBUG: BASE_DIR: {BASE_DIR}")
    
    if not os.path.exists(html_path):
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Frontend not found</h1>
            <p>Looking for: {html_path}</p>
            <p>Base dir: {BASE_DIR}</p>
            <p>Current working dir: {os.getcwd()}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=404)
    
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"DEBUG: Successfully read HTML file ({len(content)} chars)")
            return HTMLResponse(content=content)
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error loading frontend</h1>
            <p>Error: {str(e)}</p>
            <p>Path: {html_path}</p>
        </body>
        </html>
        """
        print(f"DEBUG: Error reading file: {e}")
        return HTMLResponse(content=error_html, status_code=500)


@app.post("/api/generate-questions")
async def generate_questions(request: QuestionRequest):
    """Generate essay questions using LLM"""
    print(f"DEBUG: Generate questions request - Domain: {request.domain}, Questions: {request.num_questions}")
    try:
        # Complete the prompt template with additional question placeholders
        additional_questions = ""
        if request.num_questions > 2:
            # Add comma-separated question templates for clarity
            for i in range(3, request.num_questions + 1):
                additional_questions += f",\n  {{\n    \"background_info\": \"Question {i} background info...\",\n    \"question_text\": \"Question {i} text...\",\n    \"grading_rubric\": {{\n      \"dimensions\": [...],\n      \"total_points\": 30\n    }},\n    \"domain_info\": \"Question {i} domain info...\"\n  }}"
        
        prompt = QUESTION_GENERATION_TEMPLATE.format(
            domain=request.domain,
            professor_instructions=request.professor_instructions or "No specific instructions provided.",
            num_questions=request.num_questions,
            additional_questions=additional_questions
        )
        print(f"DEBUG: Prompt created ({len(prompt)} chars)")
        print(f"DEBUG: Requesting {request.num_questions} question(s)")
        
        # Call LLM
        system_prompt = f"You are an expert educator. You MUST return a JSON array with exactly {request.num_questions} question objects. Do NOT return a single object. Return an array."
        llm_response = await call_together_ai(
            prompt,
            system_prompt=system_prompt
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
        # The LLM should return an array, but handle both cases
        if isinstance(question_data, dict):
            # Single question returned as object - this shouldn't happen but handle it
            print(f"DEBUG: WARNING - LLM returned single question object instead of array!")
            print(f"DEBUG: Requested {request.num_questions} questions but got 1 object")
            # If we requested multiple questions, we need to generate more
            if request.num_questions > 1:
                print(f"DEBUG: Attempting to generate remaining {request.num_questions - 1} question(s)...")
                # Store the first question
                first_question = question_data
                question_data = [first_question]
                
                # Generate additional questions one by one
                for q_num in range(2, request.num_questions + 1):
                    try:
                        single_prompt = f"""You are an expert educator creating ONE essay exam question in the domain of: {request.domain}

{request.professor_instructions or "No specific instructions provided."}

Create question #{q_num} of {request.num_questions}. Make it DIFFERENT from previous questions.

Return a JSON object (not array) with this structure:
{{
    "background_info": "...",
    "question_text": "...",
    "grading_rubric": {{
        "dimensions": [{{"name": "...", "description": "...", "max_points": 10, "criteria": [...]}}],
        "total_points": 30
    }},
    "domain_info": "..."
}}

Return ONLY the JSON object, no array brackets."""
                        
                        single_response = await call_together_ai(
                            single_prompt,
                            system_prompt="You are an expert educator. Return a single JSON object, not an array."
                        )
                        single_question = extract_json_from_response(single_response)
                        if isinstance(single_question, dict):
                            question_data.append(single_question)
                            print(f"DEBUG: Generated question {q_num}/{request.num_questions}")
                        else:
                            print(f"DEBUG: Failed to generate question {q_num}")
                    except Exception as e:
                        print(f"DEBUG: Error generating additional question {q_num}: {e}")
            else:
                question_data = [question_data]
        elif isinstance(question_data, list):
            # Array returned - use as is
            print(f"DEBUG: LLM returned array with {len(question_data)} question(s)")
            if len(question_data) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="LLM returned an empty array. No questions were generated."
                )
            # If we requested more questions than received, generate the rest
            if len(question_data) < request.num_questions:
                print(f"DEBUG: Warning - requested {request.num_questions} questions but got {len(question_data)}")
                # Generate remaining questions (similar to above)
                for q_num in range(len(question_data) + 1, request.num_questions + 1):
                    try:
                        single_prompt = f"""You are an expert educator creating ONE essay exam question in the domain of: {request.domain}

{request.professor_instructions or "No specific instructions provided."}

Create question #{q_num} of {request.num_questions}. Make it DIFFERENT from previous questions.

Return a JSON object (not array) with this structure:
{{
    "background_info": "...",
    "question_text": "...",
    "grading_rubric": {{
        "dimensions": [{{"name": "...", "description": "...", "max_points": 10, "criteria": [...]}}],
        "total_points": 30
    }},
    "domain_info": "..."
}}

Return ONLY the JSON object, no array brackets."""
                        
                        single_response = await call_together_ai(
                            single_prompt,
                            system_prompt="You are an expert educator. Return a single JSON object, not an array. No additional text."
                        )
                        single_question = extract_json_from_response(single_response)
                        if isinstance(single_question, dict):
                            question_data.append(single_question)
                            print(f"DEBUG: Successfully generated question {q_num}/{request.num_questions}")
                        else:
                            print(f"DEBUG: Failed to parse question {q_num} - got type: {type(single_question)}")
                    except Exception as e:
                        print(f"DEBUG: Error generating additional question {q_num}: {e}")
                        import traceback
                        traceback.print_exc()
        else:
            # Unexpected type
            print(f"DEBUG: Unexpected response type: {type(question_data)}")
            question_data = [question_data]
        
        # Create exam with questions
        exam_id = str(uuid.uuid4())
        questions = []
        
        for idx, q_data in enumerate(question_data):
            if not isinstance(q_data, dict):
                print(f"DEBUG: Warning - question {idx} is not a dict: {type(q_data)}")
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
        
        print(f"DEBUG: Successfully created exam with {len(questions)} question(s)")
        return {
            "exam_id": exam_id,
            "questions": questions
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in generate_questions: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")


@app.get("/api/exam/{exam_id}")
async def get_exam(exam_id: str):
    """Get exam details"""
    if exam_id not in exams_storage:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exams_storage[exam_id]


@app.post("/api/submit-response")
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
        print(f"DEBUG: Calling LLM for grading question: {response.question_id}")
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON with accurate scores. Return ONLY a JSON object, no additional text."
        )
        
        # Parse grading result
        print(f"DEBUG: Received grading response ({len(llm_response)} chars)")
        try:
            grade_data = extract_json_from_response(llm_response)
            print(f"DEBUG: Successfully parsed grading response")
        except ValueError as e:
            print(f"DEBUG: Failed to extract JSON from grading response: {e}")
            print(f"DEBUG: Grading response preview: {llm_response[:500]}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse grading response as JSON: {str(e)}"
            )
        
        # Create grade result
        grade_result = {
            "question_id": response.question_id,
            "scores": grade_data.get("scores", {}),
            "total_score": grade_data.get("total_score", 0.0),
            "explanation": grade_data.get("explanation", ""),
            "feedback": grade_data.get("feedback", "")
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
        raise HTTPException(status_code=500, detail=f"Error grading response: {str(e)}")


@app.get("/api/response/{exam_id}/{question_id}")
async def get_response(exam_id: str, question_id: str):
    """Get stored student response and grade"""
    response_key = f"{exam_id}_{question_id}"
    if response_key not in student_responses_storage:
        raise HTTPException(status_code=404, detail="Response not found")
    return student_responses_storage[response_key]


@app.post("/api/dispute-grade")
async def dispute_grade(request: Request):
    """Submit a dispute for a graded question. Requires minimum time delay since grading."""
    print("=" * 50)
    print("DEBUG: dispute_grade function called!")
    print("=" * 50)
    try:
        # Parse request body manually to see what we're getting
        try:
            body = await request.json()
            print(f"DEBUG: Request body received: {body}")
            print(f"DEBUG: Body type: {type(body)}, Keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"DEBUG: Error parsing request body: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Invalid request body: {str(e)}")
        
        # Validate request data
        try:
            dispute = DisputeRequest(**body)
            print(f"DEBUG: Successfully created DisputeRequest object")
        except Exception as e:
            print(f"DEBUG: Validation error creating DisputeRequest: {e}")
            print(f"DEBUG: Body was: {body}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")
        
        print(f"DEBUG: Dispute request received - exam_id: {dispute.exam_id}, question_id: {dispute.question_id}")
        print(f"DEBUG: Complaint text length: {len(dispute.complaint_text)}")
        
        # Check if response exists
        response_key = f"{dispute.exam_id}_{dispute.question_id}"
        print(f"DEBUG: Looking for response with key: {response_key}")
        print(f"DEBUG: Available response keys: {list(student_responses_storage.keys())[:5]}...")  # Show first 5
        
        if response_key not in student_responses_storage:
            print(f"DEBUG: Response not found in storage")
            raise HTTPException(status_code=404, detail="Graded response not found")
        
        response_data = student_responses_storage[response_key]
        print(f"DEBUG: Found response data, submitted_at: {response_data.get('submitted_at')}")
        
        # Check time delay - require at least 30 seconds since grading (reduced for testing)
        # In production, this should be 1 hour (3600 seconds) to prevent emotional, immediate disputes
        submitted_at = datetime.fromisoformat(response_data["submitted_at"])
        time_since_grading = (datetime.now() - submitted_at).total_seconds()
        MIN_DISPUTE_DELAY_SECONDS = 30  # 30 seconds for testing (normally 3600 = 1 hour)
        
        print(f"DEBUG: Time since grading: {time_since_grading:.1f} seconds")
        print(f"DEBUG: Required delay: {MIN_DISPUTE_DELAY_SECONDS} seconds")
        
        if time_since_grading < MIN_DISPUTE_DELAY_SECONDS:
            seconds_remaining = MIN_DISPUTE_DELAY_SECONDS - time_since_grading
            error_msg = f"Disputes can only be submitted after at least {MIN_DISPUTE_DELAY_SECONDS} seconds have passed since grading. Please wait {int(seconds_remaining)} more second(s) before disputing."
            print(f"DEBUG: Time delay not met. Error: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Get exam and question data
        if dispute.exam_id not in exams_storage:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        exam = exams_storage[dispute.exam_id]
        question = None
        for q in exam["questions"]:
            if q["question_id"] == dispute.question_id:
                question = q
                break
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Prepare dispute assessment prompt
        rubric_str = json.dumps(question["grading_rubric"], indent=2)
        grade_data = response_data["grade"]
        original_grade_str = json.dumps(grade_data["scores"], indent=2)
        
        hours_since = time_since_grading / 3600
        
        prompt = DISPUTE_ASSESSMENT_TEMPLATE.format(
            question_text=question["question_text"],
            grading_rubric=rubric_str,
            student_response=response_data["response_text"],
            original_grade=original_grade_str,
            original_explanation=grade_data.get("explanation", ""),
            complaint_text=dispute.complaint_text,
            time_since_grading=f"{hours_since:.1f} hours"
        )
        
        # Call LLM for dispute assessment
        print(f"DEBUG: Assessing dispute for question: {dispute.question_id}")
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator reviewing grade disputes. Always return valid JSON. Be fair and objective in your assessment."
        )
        
        # Parse assessment result
        print(f"DEBUG: Received dispute assessment response ({len(llm_response)} chars)")
        try:
            assessment_data = extract_json_from_response(llm_response)
            print(f"DEBUG: Successfully parsed dispute assessment")
        except ValueError as e:
            print(f"DEBUG: Failed to extract JSON from dispute assessment: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse dispute assessment as JSON: {str(e)}"
            )
        
        # Create dispute record
        dispute_id = str(uuid.uuid4())
        dispute_record = {
            "dispute_id": dispute_id,
            "exam_id": dispute.exam_id,
            "question_id": dispute.question_id,
            "complaint_text": dispute.complaint_text,
            "submitted_at": datetime.now().isoformat(),
            "time_since_grading_hours": hours_since,
            "original_grade": grade_data,
            "assessment": {
                "is_valid": assessment_data.get("is_valid", False),
                "validity_score": assessment_data.get("validity_score", 0.0),
                "assessment": assessment_data.get("assessment", ""),
                "recommendation": assessment_data.get("recommendation", "review"),
                "key_points": assessment_data.get("key_points", []),
                "suggested_action": assessment_data.get("suggested_action", "")
            },
            "status": "pending_review"  # pending_review, regraded, rejected, resolved
        }
        
        # Store dispute
        disputes_storage[dispute_id] = dispute_record
        
        # If the dispute is valid and recommendation is to regrade, optionally regrade immediately
        # (In production, you might want to require professor approval first)
        if assessment_data.get("is_valid", False) and assessment_data.get("recommendation") == "regrade":
            print(f"DEBUG: Valid dispute detected - considering regrade")
            # For now, we'll mark it for regrade but not automatically regrade
            # The professor can review and approve regrading
            dispute_record["status"] = "pending_regrade"
            dispute_record["auto_regrade_eligible"] = True
        
        return {
            "dispute_id": dispute_id,
            "status": dispute_record["status"],
            "assessment": dispute_record["assessment"],
            "message": "Dispute submitted successfully. It will be reviewed by the professor."
        }
    
    except HTTPException as he:
        print(f"DEBUG: HTTPException in dispute_grade: {he.status_code} - {he.detail}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"DEBUG: Error processing dispute: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing dispute: {str(e)}")


@app.get("/api/disputes")
async def get_disputes(exam_id: Optional[str] = None):
    """Get all disputes, optionally filtered by exam_id. For professor review."""
    if exam_id:
        # Filter disputes for specific exam
        exam_disputes = [
            dispute for dispute in disputes_storage.values()
            if dispute["exam_id"] == exam_id
        ]
        return {"disputes": exam_disputes}
    else:
        # Return all disputes
        return {"disputes": list(disputes_storage.values())}


@app.get("/api/dispute/{dispute_id}")
async def get_dispute(dispute_id: str):
    """Get a specific dispute by ID"""
    if dispute_id not in disputes_storage:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return disputes_storage[dispute_id]


@app.post("/api/dispute/{dispute_id}/regrade")
async def regrade_from_dispute(dispute_id: str):
    """Regrade a question based on a valid dispute. Requires professor approval in production."""
    try:
        if dispute_id not in disputes_storage:
            raise HTTPException(status_code=404, detail="Dispute not found")
        
        dispute = disputes_storage[dispute_id]
        
        # Get the original response
        response_key = f"{dispute['exam_id']}_{dispute['question_id']}"
        if response_key not in student_responses_storage:
            raise HTTPException(status_code=404, detail="Original response not found")
        
        response_data = student_responses_storage[response_key]
        
        # Get exam and question
        if dispute['exam_id'] not in exams_storage:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        exam = exams_storage[dispute['exam_id']]
        question = None
        for q in exam["questions"]:
            if q["question_id"] == dispute['question_id']:
                question = q
                break
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Regrade using the same grading process
        rubric_str = json.dumps(question["grading_rubric"], indent=2)
        prompt = GRADING_TEMPLATE.format(
            question_text=question["question_text"],
            grading_rubric=rubric_str,
            background_info=question["background_info"],
            domain_info=question.get("domain_info", ""),
            student_response=response_data["response_text"],
            time_spent=response_data.get("time_spent_seconds", 0)
        )
        
        print(f"DEBUG: Regrading question {dispute['question_id']} based on dispute")
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Re-evaluate this response carefully, considering the student's dispute. Always return valid JSON."
        )
        
        # Parse new grade
        try:
            new_grade_data = extract_json_from_response(llm_response)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse regrade response: {str(e)}"
            )
        
        # Create new grade result
        new_grade = {
            "question_id": dispute['question_id'],
            "scores": new_grade_data.get("scores", {}),
            "total_score": new_grade_data.get("total_score", 0.0),
            "explanation": new_grade_data.get("explanation", ""),
            "feedback": new_grade_data.get("feedback", ""),
            "is_regrade": True,
            "original_grade": response_data["grade"],
            "regraded_at": datetime.now().isoformat(),
            "dispute_id": dispute_id
        }
        
        # Update response with new grade
        response_data["grade"] = new_grade
        response_data["regraded_at"] = datetime.now().isoformat()
        
        # Update dispute status
        dispute["status"] = "regraded"
        dispute["regraded_at"] = datetime.now().isoformat()
        dispute["new_grade"] = new_grade
        
        return {
            "message": "Question regraded successfully",
            "new_grade": new_grade,
            "dispute_id": dispute_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error regrading: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error regrading: {str(e)}")


# Mount static files after routes are defined
app.mount("/static", StaticFiles(directory=CLIENT_STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Starting server...")
    print(f"Registered routes: {[route.path for route in app.routes]}")
    print(f"App instance: {app}")
    print(f"App title: {app.title}")
    print("=" * 50)
    # Run on 0.0.0.0 to allow network access from other devices
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
