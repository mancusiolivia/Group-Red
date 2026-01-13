# Essay Testing System

A FastAPI-based web application for generating AI-powered essay exam questions and automatically grading student responses using the Together.ai LLM API.

## Features

- **Question Generation**: AI-powered essay question generation with customizable domains and professor instructions
- **Interactive Exam Interface**: User-friendly web interface for taking exams
- **AI-Powered Grading**: Automatic grading of student responses with detailed feedback
- **Grading Rubrics**: Custom rubrics generated for each question with multiple evaluation dimensions
- **Response Storage**: In-memory storage of exams and student responses

## Setup

1. Install dependencies:
```bash
pip install -r server/requirements.txt
```

2. Set up environment variables:

   **⚠️ Important:** When you clone this repository, you will need to set up `.env` file with your API key:
   ```
   TOGETHER_AI_API_KEY=your_api_key_here
   ```
   If you lost the key, let Olivia know.
   
   **Note:** The `.env` file is automatically ignored by git, so each developer needs to create their own with their own API key.

3. Start the server:
```bash
python3 server/main.py
```

   Or using uvicorn:
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

4. Open the website:
```
http://localhost:8000
```

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
│   ├── main.py               # FastAPI application
│   └── requirements.txt      # Python dependencies
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
