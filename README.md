# Essay Testing System

A FastAPI-based web application for generating AI-powered essay exam questions and automatically grading student responses using the Together.ai LLM API.

## Features

- **Question Generation**: AI-powered essay question generation with customizable domains and professor instructions
- **Interactive Exam Interface**: User-friendly web interface for taking exams
- **AI-Powered Grading**: Automatic grading of student responses with detailed feedback
- **Grading Rubrics**: Custom rubrics generated for each question with multiple evaluation dimensions
- **Database Storage**: SQLite database for persistent storage of exams, questions, and student responses

## Quick Start

**New to the project?** See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for a complete step-by-step setup guide.

### Basic Setup

1. **Install dependencies:**
```bash
pip install -r server/requirements.txt
```

2. **Set up environment variables:**

   Create a `.env` file in the project root with your API key:
   ```
   TOGETHER_AI_API_KEY=your_api_key_here
   ```
   **Note:** The `.env` file is automatically ignored by git. Contact Olivia if you need an API key.

3. **Create login users (REQUIRED for first-time setup):**
   
   After cloning, you **must** run the seed script to create login accounts:
   ```bash
   python server/database/seed_data.py
   ```
   
   This creates test accounts:
   - `admin` / `admin123` (instructor)
   - `student1` / `password123` (student)
   - `student2` / `password123` (student)
   - `testuser` / `test123` (student)

4. **Start the server:**

   **Option 1 (Recommended):** Use the run script:
   ```bash
   python3 run_server.py
   ```
   
   **Option 2:** Run main.py directly:
   ```bash
   python3 server/main.py
   ```
   
   **Option 3:** Use uvicorn directly:
   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8000
   ```

5. **Access the application:**
   ```
   http://localhost:8000
   ```
   
   Log in with one of the test accounts created in step 3.

**Note:** The database (`data/app.db`) is automatically created on first server startup. No database server installation needed!

## Project Structure

```
Group-Red/
├── client/                    # Frontend files
│   ├── index.html            # Main HTML page
│   └── static/               # Static assets
│       ├── css/
│       │   └── style.css     # Stylesheet
│       └── js/
│           └── app.js         # Frontend JavaScript
├── server/                    # Backend server
│   ├── main.py               # FastAPI application setup
│   ├── api.py                # All API endpoints
│   ├── frontend.py           # Frontend serving
│   ├── core/                 # Core utilities
│   │   ├── config.py        # Configuration
│   │   ├── models.py        # Data models
│   │   ├── database.py       # Database connection and initialization
│   │   ├── db_models.py      # SQLAlchemy ORM models
│   │   ├── storage.py        # Legacy storage (for reference)
│   │   ├── llm_service.py   # LLM API functions
│   │   └── middleware.py    # Custom middleware
│   └── requirements.txt      # Python dependencies
├── run_server.py             # Simple script to run the server
├── prompts/                   # Prompt templates
│   ├── coding_prompts.md
│   ├── design_prompts.md
│   └── documentation_prompts.md
├── .env.example              # Environment variable template
├── README.md                 # This file
└── PROJECT_MANUAL.md         # Detailed documentation
```

## API Endpoints

- `GET /` - Serves the main frontend page
- `POST /api/generate-questions` - Generate essay questions using AI
- `GET /api/exam/{exam_id}` - Get exam details
- `POST /api/submit-response` - Submit student response and get graded
- `GET /api/response/{exam_id}/{question_id}` - Get stored student response

## Documentation

See `PROJECT_MANUAL.md` for detailed documentation including:
- Planning
- Design Documentation
- Testing
- Security

## Security Note

⚠️ **IMPORTANT**: Never commit API keys to version control. Use environment variables instead. The `.env` file is already in `.gitignore`.
