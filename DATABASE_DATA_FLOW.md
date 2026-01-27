# Database Data Flow - Question Storage and Retrieval

## ✅ CONFIRMED: All question data is pulled from SQL database

This document confirms that all question data flows through the SQL database.

---

## 1. Question Generation & Storage (POST /api/generate-questions)

**Location:** `server/api.py` lines 260-295

### Database Operations:
1. **Exam stored in database:**
   ```python
   exam = Exam(
       instructor_id=instructor.id,
       domain=request.domain,
       title=f"{request.domain} Exam",
       ...
   )
   db.add(exam)
   db.flush()  # Get exam.id
   ```

2. **Each Question stored in database:**
   ```python
   question = Question(
       exam_id=exam.id,
       q_index=idx + 1,
       prompt=q_data.get("question_text", ""),
       points_possible=total_points
   )
   db.add(question)
   db.flush()  # Get question.id
   ```

3. **Each Rubric stored in database:**
   ```python
   rubric = Rubric(
       question_id=question.id,
       rubric_text=rubric_text
   )
   db.add(rubric)
   ```

4. **All changes committed:**
   ```python
   db.commit()  # Line 295 - Saves everything to database
   ```

**Tables Used:**
- `exams` table
- `questions` table
- `rubrics` table

---

## 2. Viewing Past Exams (GET /api/my-exams)

**Location:** `server/api.py` lines 338-406

### Database Queries:
1. **Get submissions from database:**
   ```python
   submissions = db.query(Submission).filter(
       Submission.student_id == student_id
   ).order_by(Submission.started_at.desc()).all()
   ```

2. **Get exam from database:**
   ```python
   exam = db.query(Exam).filter(Exam.id == exam_id).first()
   ```

3. **Get answers from database:**
   ```python
   answers = db.query(Answer).filter(Answer.submission_id == submission.id).all()
   ```

4. **Get questions from database:**
   ```python
   question = db.query(Question).filter(Question.id == answer.question_id).first()
   question_count = db.query(Question).filter(Question.exam_id == exam_id).count()
   ```

**Tables Queried:**
- `submissions` table
- `exams` table
- `answers` table
- `questions` table

---

## 3. Viewing Exam Results (GET /api/exam/{exam_id}/my-results)

**Location:** `server/api.py` lines 409-490

### Database Queries:
1. **Get exam from database:**
   ```python
   exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
   ```

2. **Get submission from database:**
   ```python
   submission = db.query(Submission).filter(
       Submission.exam_id == exam_id_int,
       Submission.student_id == student.id
   ).order_by(Submission.started_at.desc()).first()
   ```

3. **Get ALL questions from database:**
   ```python
   questions = db.query(Question).filter(Question.exam_id == exam.id)
       .order_by(Question.q_index).all()
   ```

4. **Get rubric for each question from database:**
   ```python
   rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
   ```

5. **Get answer for each question from database:**
   ```python
   answer = db.query(Answer).filter(
       Answer.submission_id == submission.id,
       Answer.question_id == q.id
   ).first()
   ```

**Tables Queried:**
- `exams` table
- `submissions` table
- `questions` table (ALL questions for the exam)
- `rubrics` table (for each question)
- `answers` table (for each question)

---

## 4. Getting Exam Details (GET /api/exam/{exam_id})

**Location:** `server/api.py` lines 572-613

### Database Queries:
1. **Get exam from database:**
   ```python
   exam = db.query(Exam).filter(Exam.id == exam_id_int).first()
   ```

2. **Get questions from database:**
   ```python
   questions = db.query(Question).filter(Question.exam_id == exam.id)
       .order_by(Question.q_index).all()
   ```

3. **Get rubrics from database:**
   ```python
   rubric = db.query(Rubric).filter(Rubric.question_id == q.id).first()
   ```

**Tables Queried:**
- `exams` table
- `questions` table
- `rubrics` table

---

## Summary

✅ **All question data is stored in SQL database** when generated  
✅ **All question data is retrieved from SQL database** when viewing exams  
✅ **No data is stored in memory or session** - everything persists in database  
✅ **Database tables used:**
   - `exams` - Stores exam metadata
   - `questions` - Stores all question text and metadata
   - `rubrics` - Stores grading rubrics for each question
   - `answers` - Stores student answers
   - `submissions` - Links students to exams

---

## Database Schema Reference

See `server/database/schema.sql` for the complete database schema.

All questions are stored with:
- `id` (primary key)
- `exam_id` (foreign key to exams table)
- `q_index` (question order: 1, 2, 3...)
- `prompt` (the question text)
- `points_possible` (maximum points)
- `created_at` (timestamp)
