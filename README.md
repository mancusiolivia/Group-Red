# Essay Testing System

A FastAPI-based web application for generating AI-powered essay exam questions and automatically grading student responses using the Together.ai LLM API.

## Features

- **Question Generation**: AI-powered essay question generation with customizable domains and professor instructions
- **Interactive Exam Interface**: User-friendly web interface for taking exams
- **AI-Powered Grading**: Automatic grading of student responses with detailed feedback
- **Grading Rubrics**: Custom rubrics generated for each question with multiple evaluation dimensions
- **Database Storage**: SQLite database for persistent storage of exams, questions, and student responses

## Quick Start

After cloning the repository, follow these steps in order:

1. Install dependencies
2. Set up environment variables
3. Initialize the database
4. Run database migrations (if needed)
5. Create login users
6. Assign classes to students (for instructor features)
7. Start the server

See the [Setup](#setup) section below for detailed instructions.

## Setup

**Follow these steps in order:**

### Complete Setup Sequence

For a fresh installation, run these commands in sequence:

```bash
# 1. Install dependencies
pip install -r server/requirements.txt

# 2. Create .env file with your API key
# (Create .env file manually with: TOGETHER_AI_API_KEY=your_key_here)

# 3. Initialize database
python server/database/init.py

# 4. Add class_name column (migration)
python server/database/add_class_name_column.py

# 5. Seed initial users
python server/database/seed_data.py

# 6. Assign classes to students
python server/database/assign_classes_to_students.py

# 7. Start the server
python run_server.py
```

**Note:** On some systems, use `python3` instead of `python`.

### Detailed Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r server/requirements.txt
   ```
   
   **Or on some systems:**
   ```bash
   pip3 install -r server/requirements.txt
   ```

2. **Set up environment variables:**
   
   **⚠️ Important:** When you clone this repository, you will need to set up `.env` file with your API key:
   ```
   TOGETHER_AI_API_KEY=your_api_key_here
   ```
   If you lost the key, let Olivia know.
   
   **Note:** The `.env` file is automatically ignored by git, so each developer needs to create their own with their own API key.

3. **Initialize the database:**
   
   **✅ No database server needed!** This project uses SQLite (a file-based database).
   
   Initialize the database schema:
   ```bash
   python server/database/init.py
   ```
   
   **Or on some systems:**
   ```bash
   python3 server/database/init.py
   ```
   
   This will create the database file (`app.db`) in the `data/` folder and set up all required tables.
   
   **Note:** The database initialization automatically handles some migrations (like adding `number_of_questions` column), but you may need to run additional migration scripts for existing databases (see below).

4. **Run database migrations (if needed):**
   
   If you're setting up a fresh database or need to add missing columns, run these migration scripts:
   
   **Add class_name column to students table:**
   ```bash
   python server/database/add_class_name_column.py
   ```
   
   **Or on some systems:**
   ```bash
   python3 server/database/add_class_name_column.py
   ```
   
   **Note:** These scripts are idempotent (safe to run multiple times) and will skip if the columns already exist.

5. **Create login users:**
   
   **⚠️ IMPORTANT - Create Login Users:**
   
   After initializing the database, you **must** run the seed data script to create initial login users:
   ```bash
   python server/database/seed_data.py
   ```
   
   **Or on some systems:**
   ```bash
   python3 server/database/seed_data.py
   ```
   
   This will create the following test accounts:
   
   | Username | Password | Type |
   |----------|----------|------|
   | `admin` | `admin123` | Instructor |
   | `student1` | `password123` | Student |
   | `student2` | `password123` | Student |
   | `testuser` | `test123` | Student |
   
   **Note:** You only need to run this once after cloning. The script is idempotent (safe to run multiple times).
   
   For a complete list of credentials, see `CREDENTIALS.txt`.

6. **Assign classes to students:**
   
   **⚠️ IMPORTANT - For Instructor Dashboard:**
   
   To enable the instructor class selection feature, assign CS-related classes to all students:
   ```bash
   python server/database/assign_classes_to_students.py
   ```
   
   **Or on some systems:**
   ```bash
   python3 server/database/assign_classes_to_students.py
   ```
   
   This script will:
   - Assign mock CS classes (CS101, CS201, CS301, etc.) to all students
   - Distribute students evenly across 10 different CS courses
   - Exclude instructor accounts from class assignments
   
   **Note:** This script is idempotent and can be run multiple times. It will update existing class assignments.

7. **Start the server:**

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

8. **Access the Application:**
   ```
   http://localhost:8000
   ```
   
   Log in with one of the test accounts created in step 5 (e.g., `admin` / `admin123` or `student1` / `password123`).
   
   The server will automatically start and be available at `http://localhost:8000`. You can also access the API documentation at `http://localhost:8000/docs`.

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

## Database Setup Scripts

The following scripts are available for database setup and maintenance:

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `init.py` | Creates database schema and tables | First time setup |
| `add_class_name_column.py` | Adds `class_name` column to students table | After `init.py` (migration) |
| `seed_data.py` | Creates default users (admin, student1, etc.) | After `init.py` |
| `assign_classes_to_students.py` | Assigns CS classes to all students | After `seed_data.py` (for instructor features) |
| `add_number_of_questions_column.py` | Adds `number_of_questions` column to exams table | Usually handled automatically by `init_db()` |

**Note:** All scripts are idempotent (safe to run multiple times). They will skip operations if data already exists.

## Login Credentials

After running `python server/database/seed_data.py`, the following test accounts are available:

| Username | Password | Type |
|----------|----------|------|
| `admin` | `admin123` | Instructor |
| `student1` | `password123` | Student |
| `student2` | `password123` | Student |
| `testuser` | `test123` | Student |

For a complete list of credentials, see `CREDENTIALS.txt`.

### Instructor Dashboard Classes

After running `assign_classes_to_students.py`, students will be assigned to one of these CS classes:
- CS101 - Introduction to Computer Science
- CS201 - Data Structures and Algorithms
- CS301 - Software Engineering
- CS401 - Database Systems
- CS501 - Machine Learning
- CS202 - Object-Oriented Programming
- CS302 - Web Development
- CS402 - Computer Networks
- CS502 - Artificial Intelligence
- CS103 - Programming Fundamentals

Students are distributed evenly across these classes for testing purposes.

## Security Note

⚠️ **IMPORTANT**: Never commit API keys to version control. Use environment variables instead. The `.env` file is already in `.gitignore`.
