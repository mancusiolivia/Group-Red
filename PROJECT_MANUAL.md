# Project Manual: Essay Testing System

## Table of Contents
1. [Planning](#planning)
2. [Design Documentation](#design-documentation)
3. [Testing](#testing)
4. [Security](#security)

---

## Planning

### Project Overview
This project implements a FastAPI-based web application for generating AI-powered essay exam questions and automatically grading student responses. The system uses the Together.ai LLM API to create customized essay questions with grading rubrics and provides intelligent feedback on student submissions.

### Objectives
- **Primary Goal**: Create an AI-powered essay testing and grading system
- **Key Features**:
  - AI-powered question generation with customizable domains
  - Interactive web interface for taking exams
  - Automatic grading with detailed feedback
  - Custom grading rubrics for each question
  - In-memory storage of exams and responses

### Project Structure
```
Group-Red/
├── client/                    # Frontend files
│   ├── index.html            # Main HTML page
│   └── static/              # Static assets
│       ├── css/
│       │   └── style.css    # Stylesheet
│       └── js/
│           └── app.js        # Frontend JavaScript
├── server/                   # Backend server
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Python dependencies
├── prompts/                  # Prompt templates
│   ├── coding_prompts.md
│   ├── design_prompts.md
│   └── documentation_prompts.md
├── .env.example             # Environment variable template
├── README.md                # Quick start guide
└── PROJECT_MANUAL.md        # This documentation
```

### Technology Stack
- **Framework**: FastAPI (Python web framework)
- **LLM Service**: Together.ai API (Mistral Mixtral-8x7B-Instruct)
- **Frontend**: HTML, CSS, JavaScript
- **Language**: Python 3.x

### Development Workflow
1. Start FastAPI server: `python3 server/main.py`
2. Open browser: `http://localhost:8000`
3. Create exam with domain and questions
4. Take exam and submit responses
5. View AI-generated grades and feedback

---

## Design Documentation

### Architecture Overview

#### High-Level Architecture
```
┌─────────────┐
│   Browser   │ (Frontend: client/index.html)
│  (Client)   │
└──────┬──────┘
       │ HTTP Requests
       ▼
┌─────────────────────────────────────┐
│      server/main.py                  │
│  ┌───────────────────────────────┐  │
│  │  GET /                        │  │
│  │  POST /api/generate-questions │  │
│  │  GET /api/exam/{exam_id}      │  │
│  │  POST /api/submit-response    │  │
│  │  GET /api/response/{id}      │  │
│  └──────────────┬────────────────┘  │
│                 │                    │
│                 ▼                    │
│  ┌───────────────────────────────┐  │
│  │  In-Memory Storage            │  │
│  │  exams_storage: {}            │  │
│  │  student_responses_storage: {}│  │
│  └───────────────────────────────┘  │
└─────────────────┬───────────────────┘
                  │ API calls
                  ▼
┌─────────────────────────────────────┐
│      Together.ai LLM API            │
│  (Mistral Mixtral-8x7B-Instruct)   │
└─────────────────────────────────────┘
```

### Component Design

#### 1. server/main.py
**Purpose**: FastAPI server that handles all backend logic

**Responsibilities**:
- Serve frontend HTML and static files
- Generate essay questions using AI
- Grade student responses using AI
- Store exams and responses in memory
- Handle HTTP requests and responses
- Error handling and validation

**Key Components**:
- `FastAPI app`: Main application instance
- `exams_storage`: In-memory dictionary for exams
- `student_responses_storage`: In-memory dictionary for responses
- `call_together_ai()`: Function to call Together.ai API
- `extract_json_from_response()`: Parse JSON from LLM responses

**Endpoints**:
- `GET /`: Serve main frontend page
- `POST /api/generate-questions`: Generate essay questions
- `GET /api/exam/{exam_id}`: Get exam details
- `POST /api/submit-response`: Submit and grade response
- `GET /api/response/{exam_id}/{question_id}`: Get stored response

**Data Flow - Question Generation**:
1. Client sends POST request with domain, instructions, and number of questions
2. Server creates prompt using `QUESTION_GENERATION_TEMPLATE`
3. Calls `call_together_ai()` to get LLM response
4. Parses JSON response to extract questions
5. Stores exam in `exams_storage`
6. Returns exam_id and questions to client

**Data Flow - Grading**:
1. Client sends POST request with exam_id, question_id, and response text
2. Server retrieves exam and question data
3. Creates grading prompt using `GRADING_TEMPLATE`
4. Calls `call_together_ai()` to get LLM grading
5. Parses JSON response to extract scores and feedback
6. Stores response and grade in `student_responses_storage`
7. Returns grade result to client

#### 2. client/index.html
**Purpose**: Frontend HTML interface

**Responsibilities**:
- Display exam setup form
- Show questions during exam
- Display grading results
- Handle user interactions
- Communicate with backend API

**Key Sections**:
- Setup Section: Form to create new exam
- Exam Section: Interface for taking exam
- Results Section: Display grades and feedback

#### 3. client/static/js/app.js
**Purpose**: Frontend JavaScript logic

**Responsibilities**:
- Handle form submissions
- Make API calls to backend
- Update UI based on responses
- Navigate between questions
- Display results

#### 4. client/static/css/style.css
**Purpose**: Styling for the frontend

**Responsibilities**:
- Define visual appearance
- Responsive design
- UI component styling

### Data Models

#### QuestionRequest
```python
class QuestionRequest(BaseModel):
    domain: str
    professor_instructions: Optional[str] = None
    num_questions: int = 1
```

#### QuestionData
```python
class QuestionData(BaseModel):
    question_id: str
    background_info: str
    question_text: str
    grading_rubric: Dict[str, Any]
    domain_info: Optional[str] = None
```

#### StudentResponse
```python
class StudentResponse(BaseModel):
    exam_id: str
    question_id: str
    response_text: str
    time_spent_seconds: Optional[int] = None
```

#### GradeResult
```python
class GradeResult(BaseModel):
    question_id: str
    scores: Dict[str, float]
    total_score: float
    explanation: str
    feedback: str
```

### Request/Response Formats

#### POST /api/generate-questions Request
```json
{
    "domain": "Computer Science",
    "professor_instructions": "Focus on algorithms and data structures",
    "num_questions": 2
}
```

#### POST /api/generate-questions Response
```json
{
    "exam_id": "uuid-here",
    "questions": [
        {
            "question_id": "uuid-here",
            "background_info": "Information about the topic...",
            "question_text": "Explain the time complexity of...",
            "grading_rubric": {
                "dimensions": [...],
                "total_points": 30
            },
            "domain_info": "Expected knowledge..."
        }
    ]
}
```

#### POST /api/submit-response Request
```json
{
    "exam_id": "uuid-here",
    "question_id": "uuid-here",
    "response_text": "Student's essay answer...",
    "time_spent_seconds": 1200
}
```

#### POST /api/submit-response Response
```json
{
    "question_id": "uuid-here",
    "scores": {
        "Understanding of Core Concepts": 8.5,
        "Clarity of Explanation": 7.0
    },
    "total_score": 15.5,
    "explanation": "Detailed explanation of scores...",
    "feedback": "Constructive feedback for improvement..."
}
```

---

## Testing

### Testing Strategy

#### Manual Testing
**Web Interface**:
1. Start server: `python3 server/main.py`
2. Open browser: `http://localhost:8000`
3. Create exam with different domains
4. Test question generation
5. Submit responses and verify grading
6. Check results display

**API Endpoints**:
- Use FastAPI docs: `http://localhost:8000/docs`
- Use curl commands
- Use browser DevTools Network tab

#### Manual Testing Examples

**Test Question Generation**:
```bash
curl -X POST http://localhost:8000/api/generate-questions \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "History",
    "num_questions": 1
  }'
```

**Test Response Submission**:
```bash
curl -X POST http://localhost:8000/api/submit-response \
  -H "Content-Type: application/json" \
  -d '{
    "exam_id": "exam-uuid",
    "question_id": "question-uuid",
    "response_text": "Student answer here..."
  }'
```

**Test in Browser**:
- Visit `http://localhost:8000` for interactive testing
- Use FastAPI docs at `http://localhost:8000/docs` for API testing

### Test Results Interpretation

**Success Indicators**:
- ✓ Server starts without errors
- ✓ Frontend loads correctly
- ✓ Questions generate successfully
- ✓ Responses submit and get graded
- ✓ Results display properly

**Failure Handling**:
- Check server terminal for error messages
- Verify API key is set in `.env` file
- Check network tab in browser DevTools
- Verify Together.ai API is accessible

---

## Security

### Security Considerations

#### 1. API Key Security
**Current Implementation**:
- API key loaded from `.env` file
- ✅ `.env` file is in `.gitignore`
- ✅ `.env.example` provided as template

**Best Practices**:
- ✅ Never commit API keys to version control
- ✅ Use `.env` files (already in `.gitignore`)
- ✅ Use environment variables in production
- ✅ Rotate API keys regularly
- ✅ Use different keys for dev/staging/production

#### 2. Input Validation
**Current Implementation**:
- ✅ Uses Pydantic models for request validation
- ✅ Validates exam_id and question_id existence
- ⚠️ No length limits on response text

**Recommendations**:
- Add maximum length validation for responses
- Validate domain names
- Sanitize user input
- Add rate limiting

#### 3. Rate Limiting
**Current Implementation**:
- ❌ No rate limiting implemented

**Recommendations**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/generate-questions")
@limiter.limit("10/minute")
async def generate_questions(...):
    ...
```

#### 4. Error Handling
**Current Implementation**:
- ✅ Basic error handling with try/except
- ✅ Returns appropriate HTTP status codes
- ⚠️ Error messages may expose internal details

**Recommendations**:
- Log detailed errors server-side
- Return generic error messages to clients
- Don't expose stack traces
- Use appropriate HTTP status codes

#### 5. Data Storage Security
**Current Implementation**:
- ⚠️ In-memory storage (data lost on server restart)
- ⚠️ No data encryption
- ⚠️ No access control

**Recommendations for Production**:
- Use database with encryption at rest
- Implement access control and authentication
- Use HTTPS for all communications
- Implement data retention policies
- Consider PII (Personally Identifiable Information) handling

#### 6. CORS (Cross-Origin Resource Sharing)
**Current Implementation**:
- ✅ CORS configured to allow all origins (development)
- ⚠️ Should be restricted in production

**Recommendations**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Security Checklist

#### Development
- [x] API keys stored in environment variables (not in code)
- [x] `.env` file added to `.gitignore`
- [x] Input validation implemented
- [ ] Error handling doesn't expose internal details
- [ ] Basic rate limiting implemented

#### Production
- [ ] HTTPS enabled (TLS/SSL certificates)
- [ ] Authentication required
- [ ] Rate limiting enforced
- [ ] Database with encryption at rest
- [ ] Regular security audits
- [ ] API key rotation policy
- [ ] Monitoring and logging
- [ ] CORS properly configured
- [ ] DDoS protection
- [ ] Regular dependency updates

---

## Appendix

### File Dependencies

```
server/main.py
├── Requires: FastAPI, httpx, pydantic, python-dotenv
├── Uses: client/index.html (serves as frontend)
├── Uses: client/static/ (serves CSS and JS)
└── Uses: .env file (for API key)

client/index.html
├── Requires: client/static/css/style.css
└── Requires: client/static/js/app.js

client/static/js/app.js
└── Calls: /api/* endpoints
```

### Common Commands

**Start Server**:
```bash
python3 server/main.py
# Or with uvicorn:
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

**Install Dependencies**:
```bash
pip install -r server/requirements.txt
```

**View API Documentation**:
```
http://localhost:8000/docs
```

**View Website**:
```
http://localhost:8000
```

### Troubleshooting

**Server won't start**:
- Check if port 8000 is already in use
- Verify all dependencies are installed: `pip install -r server/requirements.txt`
- Check for syntax errors in Python files
- Verify `.env` file exists with `TOGETHER_AI_API_KEY`

**Frontend not loading**:
- Verify `client/index.html` exists
- Check server terminal for error messages
- Verify static files are in `client/static/`

**API key issues**:
- Verify API key is correct in `.env` file
- Check Together.ai account status
- Verify API key has necessary permissions
- Ensure `.env` file is in project root

**Questions not generating**:
- Check Together.ai API status
- Verify API key is valid
- Check server terminal for error messages
- Try a different model in `server/main.py`

---

**Document Version**: 2.0  
**Last Updated**: 2025-01-06  
**Maintained By**: Project Team
