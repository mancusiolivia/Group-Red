# FastAPI LLM Backend Project

A FastAPI-based backend server that provides HTTP endpoints for interacting with a Large Language Model (LLM) via the Together.ai API.

## Features

- POST endpoint to send prompts to LLM and receive responses
- GET endpoint to retrieve all previous interaction results
- Default prompt handling when user doesn't provide input
- Result storage and retrieval functionality

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create a `.env` file):
```
TOGETHER_API_KEY=your_api_key_here
```

3. Start the server:
```bash
uvicorn api_server:app
```

4. View API documentation:
```
http://localhost:8000/docs
```

## Testing

Run automated tests:
```bash
./test_server.sh
```

## Project Structure

- `api_server.py` - FastAPI application with HTTP endpoints
- `llm_service.py` - LLM API interaction service
- `test_server.sh` - Automated testing script
- `requirements.txt` - Python dependencies

## Documentation

See `PROJECT_MANUAL.md` for detailed documentation including:
- Planning
- Design Documentation
- Testing
- Security

## Security Note

⚠️ **IMPORTANT**: Never commit API keys to version control. Use environment variables instead.
