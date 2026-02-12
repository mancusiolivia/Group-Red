# Features History

## Latest Features (Current Session)

### Centralized Setup Script
- **Master Setup Script**: Created `setup.py` that runs all database migrations and setup steps automatically
- **One-Command Setup**: Reduced setup from 8+ commands to just 1-2 commands
- **Cross-Platform Support**: Added `setup.bat` for Windows and `setup.sh` for Linux/Mac
- **Automatic Migrations**: All database migrations run automatically in correct order
- **Idempotent Operations**: All setup steps are safe to run multiple times
- **Error Handling**: Clear error messages and summary at the end of setup
- **Migration Scripts Included**:
  - Database initialization
  - Class name column migration
  - Time limit fields migration
  - Instructor grading fields migration
  - Number of questions column migration
  - Prevent tab switching column migration
  - User seeding
  - Class assignments
- **Documentation**: Updated README with simplified setup instructions

### Instructor Grade Editing and Feedback
- **Manual Grade Override**: Instructors can manually edit AI-generated grades for any student answer
- **Custom Feedback**: Instructors can provide personalized feedback that overrides or supplements AI feedback
- **Grade Editing UI**: Edit interface in student exam answers view with score input and feedback textarea
- **Regrade Tracking**: System tracks when grades are manually edited with timestamps
- **Student Visibility**: Students see "✓ Instructor Regraded" badges and instructor feedback in their results
- **Score Calculation**: System automatically uses instructor scores when available, falling back to AI scores
- **Database**: Added `instructor_edited`, `instructor_score`, `instructor_feedback`, and `instructor_edited_at` fields to `answers` table
- **Migration Script**: `add_instructor_grading_fields.py` adds required database columns

### View Student Answers from Student Details
- **Clickable Exam Items**: Exam items in student details view are clickable to view full answers
- **Comprehensive Answer View**: Instructors can view all student answers, scores, and feedback in one modal
- **Question-by-Question Review**: Each question shows background info, student answer, AI feedback, and instructor feedback
- **Score Display**: Shows both AI scores and instructor-edited scores with clear indicators
- **Edit Integration**: Direct access to grade editing from the answer view modal

### Student Dashboard Improvements
- **Graded Exams Section**: New section in Dashboard tab showing all completed and graded exams
- **Separated Views**: Assigned Exams tab now only shows in-progress/not started exams
- **Score Display**: Graded exams show scores and percentages with color coding
- **Cleaner Interface**: Removed duplicate in-progress exams section (now only in Practice Exams tab)
- **Better Organization**: Clear separation between active exams and completed exams

### Assigned Exams System
- **Instructor Assignment**: Instructors can assign exams to specific students or entire classes
- **Student View**: Students see assigned exams in a dedicated "Assigned Exams" tab
- **Status Tracking**: Exams show status (Not Started, In Progress, Completed)
- **Review Before Assignment**: Instructors can review exam questions and rubrics before assigning
- **Time Limit Setting**: Option to set time limits when assigning exams
- **Tab Switching Prevention**: Option to enable anti-cheating protection when assigning exams
- **Restricted Actions**: Students cannot leave or regenerate questions for assigned exams
- **Results Display**: Assigned exam results only show "Back to Dashboard" button (no practice exam options)

### Anti-Cheating: Tab Switching Prevention
- **Checkbox option** in Assign Exam modal to enable tab switching prevention
- **Warning system**: Students receive one warning on first tab switch, exam auto-submits on second switch
- **Detection**: Uses Page Visibility API and window blur events to detect tab/window switches
- **Database**: Added `prevent_tab_switching` field to `exams` table
- **UI**: Time limit prompt modal includes tab switching warning when enabled

### Assigned Exam Restrictions
- **Leave Exam button**: Hidden for assigned exams (only visible for practice exams)
- **Regenerate Questions button**: Hidden for assigned exams
- **Results page**: Assigned exams only show "Back to Dashboard" button (practice exam buttons hidden)

### UI Improvements
- **Navigation layout**: Previous and Next buttons grouped together on the right, question counter centered
- **Timer display**: Shows time remaining with color-coded warnings (red < 5 min, yellow < 15 min)

### Time Limit Feature (Enhanced)
- **Time limit setting**: Checkbox and input field in Assign Exam modal
- **Timer display**: Real-time countdown shown during exam
- **Auto-submit**: Exam automatically submits when time expires
- **Prompt modal**: Custom HTML modal (replaces browser popup) with time limit information

### Due Date Feature
- **Due date assignment**: Teachers can set a due date and time when assigning exams (similar to time limits)
- **Student visibility**: Students see due dates in their assigned exams list with clear formatting
- **Overdue indication**: Overdue exams are highlighted in red with "(Overdue)" label
- **Auto-submission**: Overdue exams are automatically submitted if they have answers
- **Auto-grading**: Any ungraded answers for overdue exams are automatically graded using the LLM
- **Filtering**: Overdue exams are automatically filtered out from "Assigned Exams" and appear in "Graded Exams" section
- **Overdue badge**: Completed overdue exams show "Overdue" status badge instead of "Completed" in graded exams
- **Database**: Added `due_date` field to `exams` table (nullable DateTime)
- **Migration script**: `add_due_date_field.py` adds the due_date column to exams table
- **Setup integration**: Due date migration included in master setup script

## Previous Features

### Exam Review Before Assignment
- Instructors can review exam questions and rubrics before assigning to students
- Review modal displays all questions with grading rubrics formatted for readability

### Edit Exam Functionality
- Instructors can edit exam details and regenerate questions
- Replaces old exam with new version

### Exam Results Display
- Improved formatting for grading rubrics in review and results views
- Consistent black text styling across all views
