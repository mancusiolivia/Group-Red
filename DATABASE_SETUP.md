# Database Setup Guide

This project uses SQLite for data persistence. The database schema matches the ERD design for the Essay Testing System.

## Quick Start

### 1. Initialize the Database

Run the initialization script to create the database and all tables:

```bash
python server/database/init.py
```

This will create the database file at: `data/essay_testing.db`

### 2. Connect with DBeaver

1. Open DBeaver
2. Click **New Database Connection** (or press `Ctrl+Shift+N`)
3. Select **SQLite** from the list
4. In the **Path** field, browse to or enter:
   ```
   C:\Capstone Project\Group-Red\data\essay_testing.db
   ```
5. Click **Test Connection** to verify
6. Click **Finish**

You should now see the database in DBeaver with all tables:
- `instructors`
- `students`
- `exams`
- `questions`
- `rubrics`
- `submissions`
- `answers`
- `regrades`
- `audit_events`

## Database Schema

The database schema is defined in two places:

1. **SQLAlchemy Models**: `server/core/db_models.py` (used by the application)
2. **SQL Reference**: `server/database/schema.sql` (for reference/viewing in DBeaver)

### Tables Overview

- **instructors**: Stores instructor information
- **students**: Stores student information
- **exams**: Stores exam metadata and configuration
- **questions**: Stores questions for each exam
- **rubrics**: Stores grading rubrics for each question
- **submissions**: Tracks student exam submissions
- **answers**: Stores student answers and LLM grading results
- **regrades**: Stores regrade requests and results
- **audit_events**: Audit trail for system events

### Relationships

- `exams.instructor_id` → `instructors.id`
- `questions.exam_id` → `exams.id`
- `rubrics.question_id` → `questions.id`
- `submissions.exam_id` → `exams.id`
- `submissions.student_id` → `students.id`
- `answers.submission_id` → `submissions.id`
- `answers.question_id` → `questions.id`
- `regrades.answer_id` → `answers.id`

## Using the Database in Code

The application uses SQLAlchemy ORM for database access. See `server/core/database.py` for connection utilities.

### Example Usage

```python
from server.core.database import get_db_session
from server.core.db_models import Exam, Question

# Using context manager
with get_db_session() as db:
    exam = Exam(
        instructor_id=1,
        domain="Cybersecurity",
        title="Midterm Exam"
    )
    db.add(exam)
    db.flush()  # To get the exam.id
    
    question = Question(
        exam_id=exam.id,
        q_index=1,
        prompt="What is cybersecurity?",
        points_possible=10.0
    )
    db.add(question)
    # Context manager automatically commits
```

### In FastAPI Routes

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from server.core.database import get_db

@router.get("/api/exams")
async def get_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).all()
    return exams
```

## Database Location

The database file is stored at:
```
Group-Red/data/essay_testing.db
```

**Note**: Make sure to add `data/essay_testing.db` to your `.gitignore` if you don't want to commit test data.

## Troubleshooting

### Database file not found
- Run `python server/database/init.py` to create it
- Check that the `data/` directory exists

### Import errors
- Make sure you're running scripts from the project root
- Ensure SQLAlchemy is installed: `pip install -r server/requirements.txt`

### Connection errors in DBeaver
- Verify the database file path is correct
- Check file permissions (make sure the file is not locked by another process)
- Try closing and reopening DBeaver

## Next Steps

After setting up the database, you can:
1. Update `server/core/storage.py` to use database instead of in-memory dicts
2. Update API routes in `server/api.py` to use database queries
3. Add seed data or migrations as needed
