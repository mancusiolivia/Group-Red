-- SQL Schema for Essay Testing System Database
-- This file is for reference and can be used with DBeaver
-- The actual database is initialized using SQLAlchemy (see init.py)

-- Note: SQLite syntax is used here. Some features may differ in other databases.

-- ============================================================================
-- Tables
-- ============================================================================

-- Users table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    user_type VARCHAR NOT NULL DEFAULT 'student',  -- 'student' or 'instructor'
    student_id INTEGER,  -- Foreign key to students table if user_type is 'student'
    instructor_id INTEGER,  -- Foreign key to instructors table if user_type is 'instructor'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (instructor_id) REFERENCES instructors(id)
);

-- Instructors table
CREATE TABLE IF NOT EXISTS instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE,
    domain_expertise TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    email VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Exams table
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id INTEGER NOT NULL,
    domain VARCHAR NOT NULL,
    title VARCHAR,
    instructions_to_llm TEXT,
    number_of_questions INTEGER,
    time_limit_minutes INTEGER,
    prevent_tab_switching INTEGER DEFAULT 0,
    model_name VARCHAR,
    temperature REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES instructors(id)
);

-- Questions table
-- Each exam has multiple questions, each with a unique q_index (1, 2, 3, ...)
-- Each question can have multiple answers (from different submissions), 
-- but each submission has exactly one answer per question (one-to-one within a submission)
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    q_index INTEGER NOT NULL,  -- 1, 2, 3... ordering within exam
    prompt TEXT NOT NULL,
    background_info TEXT,  -- Background information displayed to students
    model_answer TEXT,
    points_possible REAL NOT NULL DEFAULT 1.0,
    difficulty VARCHAR,  -- Individual question difficulty: 'easy', 'medium', 'hard' (for mixed exams)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    UNIQUE(exam_id, q_index)  -- Each exam has unique question indices
);

-- Rubrics table
CREATE TABLE IF NOT EXISTS rubrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL UNIQUE,
    rubric_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    started_at TIMESTAMP,  -- NULL until student actually starts the exam
    submitted_at TIMESTAMP,  -- NULL until submitted
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    FOREIGN KEY (student_id) REFERENCES students(id)
);

-- Answers table
-- One-to-one mapping: Each question can have exactly one answer per submission
-- The UNIQUE constraint on (submission_id, question_id) ensures this mapping
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,  -- One-to-one: one answer per question_id
    student_answer TEXT NOT NULL,
    llm_score REAL,
    llm_feedback TEXT,
    graded_at TIMESTAMP,
    grading_model_name VARCHAR,
    grading_temperature REAL,
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (question_id) REFERENCES questions(id),
    UNIQUE(submission_id, question_id)  -- Ensures exact one-to-one mapping: one answer per question per submission
);

-- Regrades table
CREATE TABLE IF NOT EXISTS regrades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL UNIQUE,
    student_argument TEXT NOT NULL,
    regrade_score REAL,
    regrade_feedback TEXT,
    regraded_at TIMESTAMP,
    regrade_model_name VARCHAR,
    regrade_temperature REAL,
    FOREIGN KEY (answer_id) REFERENCES answers(id)
);

-- Submission regrades table (overall exam-level disputes)
-- One overall dispute per submission; UNIQUE(submission_id) enforces this
CREATE TABLE IF NOT EXISTS submission_regrades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL UNIQUE,
    student_argument TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('keep','update')),
    explanation TEXT NOT NULL,
    old_total_score INTEGER,
    new_total_score INTEGER,
    old_results_json TEXT,
    new_results_json TEXT,
    model_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
);

-- Audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_type VARCHAR NOT NULL,
    actor_id INTEGER,
    action VARCHAR NOT NULL,
    entity_type VARCHAR,
    entity_id INTEGER,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes (for performance)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_submission_exam_student_started 
    ON submissions(exam_id, student_id, started_at);

CREATE INDEX IF NOT EXISTS idx_answer_submission_question 
    ON answers(submission_id, question_id);

-- ============================================================================
-- Notes for DBeaver:
-- ============================================================================
-- 1. This schema is automatically created when you run: python server/database/init.py
-- 2. To view in DBeaver, create a new SQLite connection pointing to:
--    data/essay_testing.db (relative to project root)
-- 3. The SQLAlchemy ORM models in server/core/db_models.py match this schema
