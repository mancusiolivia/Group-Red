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


# Prompt Templates
QUESTION_GENERATION_TEMPLATE = """You are an expert educator creating essay exam questions in the domain of: {domain}

{professor_instructions}

Your task is to create {num_questions} essay question(s) with associated grading rubrics. Use your knowledge of {domain} and any information provided above.

IMPORTANT: You must return a JSON array with {num_questions} question object(s). Each question object must have the following structure:
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

Return a JSON array with exactly {num_questions} question object(s) in this format:
[
  {{"background_info": "...", "question_text": "...", "grading_rubric": {{...}}, "domain_info": "..."}},
  {{"background_info": "...", "question_text": "...", "grading_rubric": {{...}}, "domain_info": "..."}},
  ...
]

Return ONLY valid JSON array, no additional text before or after.
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
        "max_tokens": 2000
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
    
    # Find the first complete JSON object by matching braces
    start_idx = text.find("{")
    if start_idx == -1:
        raise ValueError("No JSON object found in response")
    
    # Count braces to find the matching closing brace
    brace_count = 0
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
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
    
    if brace_count != 0:
        # If we couldn't find matching braces, try the old method
        end_idx = text.rfind("}") + 1
        if end_idx <= start_idx:
            raise ValueError("Could not find complete JSON object")
    
    json_str = text[start_idx:end_idx]
    print(f"DEBUG: Extracted JSON string ({len(json_str)} chars)")
    
    try:
        # Try to parse just the JSON part, ignoring any extra text after it
        parsed = json.loads(json_str)
        print("DEBUG: Successfully parsed JSON")
        return parsed
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parse error: {e}")
        print(f"DEBUG: Problematic JSON string (first 500 chars): {json_str[:500]}")
        # Try to fix common issues
        # Remove any trailing commas before closing braces/brackets
        import re
        json_str_fixed = re.sub(r',\s*}', '}', json_str)
        json_str_fixed = re.sub(r',\s*]', ']', json_str_fixed)
        try:
            return json.loads(json_str_fixed)
        except:
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
        # The LLM should return an array, but handle both cases
        if isinstance(question_data, dict):
            # Single question returned as object - convert to list
            print("DEBUG: LLM returned single question object, converting to list")
            question_data = [question_data]
        elif isinstance(question_data, list):
            # Array returned - use as is
            print(f"DEBUG: LLM returned array with {len(question_data)} question(s)")
            if len(question_data) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="LLM returned an empty array. No questions were generated."
                )
            # If we requested more questions than received, use what we got
            if len(question_data) < request.num_questions:
                print(f"DEBUG: Warning - requested {request.num_questions} questions but got {len(question_data)}")
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
        llm_response = await call_together_ai(
            prompt,
            system_prompt="You are an expert educator. Always return valid JSON with accurate scores."
        )
        
        # Parse grading result
        grade_data = extract_json_from_response(llm_response)
        
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
