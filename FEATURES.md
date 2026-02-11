# Features History

## Latest Features (Current Session)

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
