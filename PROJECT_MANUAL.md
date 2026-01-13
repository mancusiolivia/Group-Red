# Project Manual: FastAPI LLM Backend

## Table of Contents
1. [Planning](#planning)
2. [Design Documentation](#design-documentation)
3. [Testing](#testing)
4. [Security](#security)

---

## Planning

### Project Overview
This project implements a FastAPI-based backend server that provides HTTP endpoints for interacting with a Large Language Model (LLM) via the Together.ai API. The system allows clients to send prompts to the LLM and retrieve responses through RESTful API endpoints.

### Objectives
- **Primary Goal**: Create a RESTful API server for LLM interactions
- **Key Features**:
  - POST endpoint to send prompts to LLM and receive responses
  - GET endpoint to retrieve all previous interaction results
  - Default prompt handling when user doesn't provide input
  - Result storage and retrieval functionality

### Project Structure
```
Project Demo/
├── api_server.py          # FastAPI application with HTTP endpoints
├── llm_service.py         # LLM API interaction service
├── test_server.sh         # Automated testing script
├── requirements.txt       # Python dependencies
└── PROJECT_MANUAL.md      # This documentation
```

### Technology Stack
- **Framework**: FastAPI (Python web framework)
- **LLM Service**: Together.ai API
- **Testing**: Bash script with curl commands
- **Language**: Python 3.x

### Development Workflow
1. Start FastAPI server: `uvicorn api_server:app`
2. Test endpoints manually via browser or curl
3. Run automated tests: `./test_server.sh`
4. View results in browser: `http://localhost:8000/projectdemo`

---

## Design Documentation

### Architecture Overview

#### High-Level Architecture
```
┌─────────────┐
│   Client    │ (Browser, curl, frontend app)
│  (Frontend) │
└──────┬──────┘
       │ HTTP Requests
       ▼
┌─────────────────────────────────────┐
│      api_server.py                  │
│  ┌───────────────────────────────┐  │
│  │  GET /                        │  │
│  │  GET /projectdemo             │  │
│  │  POST /projectdemo            │  │
│  └──────────────┬────────────────┘  │
│                 │                    │
│                 ▼                    │
│  ┌───────────────────────────────┐  │
│  │  In-Memory Storage            │  │
│  │  project_demo_results: []     │  │
│  └───────────────────────────────┘  │
└─────────────────┬───────────────────┘
                  │ Function calls
                  ▼
┌─────────────────────────────────────┐
│      llm_service.py                 │
│  ┌───────────────────────────────┐  │
│  │  call_llm(prompt)             │  │
│  └──────────────┬────────────────┘  │
└─────────────────┬───────────────────┘
                  │ API calls
                  ▼
┌─────────────────────────────────────┐
│      Together.ai LLM API            │
└─────────────────────────────────────┘
```

### Component Design

#### 1. api_server.py
**Purpose**: HTTP API server that handles client requests

**Responsibilities**:
- Handle HTTP GET and POST requests
- Route requests to appropriate handlers
- Store results from POST requests
- Return JSON responses to clients
- Error handling and validation

**Key Components**:
- `FastAPI app`: Main application instance
- `project_demo_results`: In-memory storage for POST request results
- `ProjectDemoRequest`: Pydantic model for request validation

**Endpoints**:
- `GET /`: Root endpoint for server status
- `GET /projectdemo`: Retrieve all stored POST results
- `POST /projectdemo`: Send prompt to LLM and get response

**Data Flow**:
1. Client sends POST request with optional prompt
2. Endpoint validates request and determines prompt (default or user-provided)
3. Calls `llm_service.call_llm()` with the prompt
4. Stores result in `project_demo_results`
5. Returns JSON response to client

#### 2. llm_service.py
**Purpose**: Service layer for LLM API interactions

**Responsibilities**:
- Initialize Together.ai client
- Make API calls to Together.ai LLM
- Handle streaming responses
- Process and return LLM responses
- Error handling for API failures

**Key Components**:
- `API_KEY`: Together.ai API key
- `MODEL`: Default LLM model to use
- `client`: Together API client instance
- `call_llm(prompt, model)`: Main function to call LLM

**Function Design**:
```python
def call_llm(prompt: str, model: str = MODEL) -> str:
    """
    Calls the LLM API with the given prompt.
    Returns the LLM's response as a string.
    Handles streaming responses and aggregates chunks.
    """
```

**Error Handling**:
- Catches exceptions from API calls
- Raises descriptive exceptions for debugging
- Allows calling code to handle errors appropriately

#### 3. test_server.sh
**Purpose**: Automated testing script for API endpoints

**Responsibilities**:
- Verify dependencies are installed
- Check if server is running
- Test all endpoints with various scenarios
- Provide clear test results and summaries
- Guide users on how to fix issues

**Test Coverage**:
- Dependency check
- Server status check
- GET endpoint tests
- POST endpoint tests (3 scenarios)
- Result retrieval tests

### Data Models

#### ProjectDemoRequest
```python
class ProjectDemoRequest(BaseModel):
    prompt: str | None = None
```
- Optional prompt field
- Allows empty body or empty string
- Used for POST request validation

#### Result Entry
```python
{
    "timestamp": "ISO format datetime",
    "prompt_used": "The prompt that was sent to LLM",
    "response": "LLM's response text",
    "response_length": 123  # Character count
}
```

### Request/Response Formats

#### POST /projectdemo Request
```json
{
    "prompt": "what is Python?"  // Optional
}
```
Or empty body: `{}`

#### POST /projectdemo Response
```json
{
    "response": "Python is a programming language..."
}
```

#### GET /projectdemo Response
```json
{
    "total_results": 2,
    "results": [
        {
            "timestamp": "2025-01-06T10:30:00.123456",
            "prompt_used": "user did not enter a prompt",
            "response": "I'm ready to help...",
            "response_length": 150
        }
    ]
}
```

---

## Testing

### Testing Strategy

#### Manual Testing
**GET Endpoints**:
- Browser: Navigate to `http://localhost:8000/` or `http://localhost:8000/projectdemo`
- Command line: `curl http://localhost:8000/projectdemo`

**POST Endpoints**:
- Browser DevTools: Use fetch() in console
- Command line: Use curl commands
- FastAPI Docs: Visit `http://localhost:8000/docs` for interactive testing

#### Automated Testing
**Script**: `test_server.sh`

**Test Cases Covered**:

1. **Dependency Check**
   - Verifies fastapi, uvicorn, together packages are installed
   - Exits with instructions if missing

2. **Server Status Check**
   - Verifies server is running on port 8000
   - Provides instructions to start server if not running

3. **GET / Endpoint Test**
   - Tests root endpoint
   - Validates JSON response format

4. **POST /projectdemo Test Cases**:
   - **Case 1**: Empty body `{}` → Should use default prompt
   - **Case 2**: User-provided prompt → Should use user's prompt
   - **Case 3**: Empty string prompt `""` → Should use default prompt

5. **GET /projectdemo Test**
   - Verifies all POST results are stored and retrievable
   - Checks response includes total_results and results array

### Running Tests

#### Automated Testing
```bash
# Make script executable (first time only)
chmod +x test_server.sh

# Run tests
./test_server.sh
```

#### Manual Testing Examples

**Test POST with custom prompt**:
```bash
curl -X POST http://localhost:8000/projectdemo \
  -H "Content-Type: application/json" \
  -d '{"prompt": "what is Python?"}'
```

**Test GET to view results**:
```bash
curl http://localhost:8000/projectdemo
```

**Test in browser**:
- GET: `http://localhost:8000/projectdemo`
- POST: Use FastAPI docs at `http://localhost:8000/docs`

### Test Results Interpretation

**Success Indicators**:
- ✓ All HTTP status codes are 200
- ✓ JSON responses are valid
- ✓ POST requests store results correctly
- ✓ GET requests retrieve all stored results

**Failure Handling**:
- Script shows which test failed
- Provides HTTP status codes for debugging
- Suggests checking server terminal for errors

### Testing Best Practices

1. **Always start server before testing**: `uvicorn api_server:app`
2. **Run automated tests after code changes**
3. **Test edge cases**: Empty prompts, long prompts, special characters
4. **Verify response formats match documentation**
5. **Check server logs for errors during testing**

---

## Security

### Security Considerations

#### 1. API Key Security
**Current Implementation**:
- API key is hardcoded in `llm_service.py`
- ❌ **RISK**: API key is exposed in source code

**Recommendations**:
```python
# Use environment variables instead
import os
API_KEY = os.getenv('TOGETHER_API_KEY')

# Or use a secrets management system
# Example: python-dotenv
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv('TOGETHER_API_KEY')
```

**Best Practices**:
- ✅ Never commit API keys to version control
- ✅ Use `.env` files (add to `.gitignore`)
- ✅ Use environment variables in production
- ✅ Rotate API keys regularly
- ✅ Use different keys for dev/staging/production

#### 2. Input Validation
**Current Implementation**:
- ✅ Uses Pydantic models for request validation
- ✅ Checks for empty strings and None values
- ⚠️ No length limits on prompts

**Recommendations**:
```python
class ProjectDemoRequest(BaseModel):
    prompt: str | None = None
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if v and len(v) > 10000:  # Example limit
            raise ValueError('Prompt too long')
        return v
```

**Additional Validations Needed**:
- ✅ Maximum prompt length
- ✅ Character encoding validation
- ✅ SQL injection prevention (if adding database later)
- ✅ XSS prevention for stored data

#### 3. Rate Limiting
**Current Implementation**:
- ❌ No rate limiting implemented

**Recommendations**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/projectdemo")
@limiter.limit("10/minute")  # Limit to 10 requests per minute
async def projectDemo(request: Request, ...):
    ...
```

**Rate Limiting Strategy**:
- Limit requests per IP address
- Limit requests per API key (if implementing authentication)
- Prevent DDoS attacks
- Protect against abuse

#### 4. Error Handling
**Current Implementation**:
- ✅ Basic error handling with try/except
- ✅ Returns 500 status code on errors
- ⚠️ Error messages may expose internal details

**Recommendations**:
```python
# Don't expose internal error details to clients
except Exception as e:
    logger.error(f"Internal error: {str(e)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}  # Generic message
    )
```

**Error Handling Best Practices**:
- ✅ Log detailed errors server-side
- ✅ Return generic error messages to clients
- ✅ Use appropriate HTTP status codes
- ✅ Don't expose stack traces to clients

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
- ⚠️ No CORS configuration (may block frontend requests)

**Recommendations**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 7. Authentication & Authorization
**Current Implementation**:
- ❌ No authentication required
- ❌ No authorization checks

**Recommendations for Production**:
- Implement API key authentication
- Use JWT tokens for user sessions
- Implement role-based access control (RBAC)
- Add request signing for sensitive operations

### Security Checklist

#### Development
- [ ] API keys stored in environment variables (not in code)
- [ ] `.env` file added to `.gitignore`
- [ ] Input validation implemented
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

### Security Resources

1. **OWASP Top 10**: Common web vulnerabilities
2. **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
3. **Together.ai Security**: Check Together.ai documentation for API security best practices

---

## Appendix

### File Dependencies

```
api_server.py
├── Requires: FastAPI, JSONResponse, BaseModel
├── Imports: llm_service.call_llm
└── Uses: datetime, typing

llm_service.py
├── Requires: together package
└── No dependencies on api_server.py (independent service)

test_server.sh
├── Requires: curl, python3
└── Tests: api_server.py endpoints
```

### Common Commands

**Start Server**:
```bash
uvicorn api_server:app
# With auto-reload (development):
uvicorn api_server:app --reload
```

**Install Dependencies**:
```bash
pip install -r requirements.txt
```

**Run Tests**:
```bash
./test_server.sh
```

**View API Documentation**:
```
http://localhost:8000/docs
```

### Troubleshooting

**Server won't start**:
- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check for syntax errors in Python files

**Tests fail**:
- Ensure server is running before running tests
- Check server terminal for error messages
- Verify API key is valid

**API key issues**:
- Verify API key is correct in environment variable or llm_service.py
- Check Together.ai account status
- Verify API key has necessary permissions

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-06  
**Maintained By**: Project Team
