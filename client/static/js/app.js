// Global state
let currentExam = null;
let currentQuestionIndex = 0;
let studentResponses = {};
let originalPrompt = null; // Store the original prompt used to generate questions
let currentUser = null; // Store current user info

// API base URL
const API_BASE = '/api';

// localStorage keys
const STORAGE_KEY_EXAM = 'current_exam';
const STORAGE_KEY_RESPONSES = 'student_responses';
const STORAGE_KEY_QUESTION_INDEX = 'current_question_index';
const STORAGE_KEY_PROMPT = 'original_prompt';

// Save exam state to localStorage
function saveExamState() {
    if (!currentUser || !currentExam) return;
    
    const state = {
        exam: currentExam,
        responses: studentResponses,
        questionIndex: currentQuestionIndex,
        prompt: originalPrompt,
        userId: currentUser.id,
        timestamp: Date.now()
    };
    
    try {
        localStorage.setItem(`${STORAGE_KEY_EXAM}_${currentUser.id}`, JSON.stringify(currentExam));
        localStorage.setItem(`${STORAGE_KEY_RESPONSES}_${currentUser.id}`, JSON.stringify(studentResponses));
        localStorage.setItem(`${STORAGE_KEY_QUESTION_INDEX}_${currentUser.id}`, currentQuestionIndex.toString());
        if (originalPrompt) {
            localStorage.setItem(`${STORAGE_KEY_PROMPT}_${currentUser.id}`, JSON.stringify(originalPrompt));
        }
    } catch (error) {
        console.error('Error saving exam state:', error);
    }
}

// Load exam state from localStorage
function loadExamState() {
    if (!currentUser) return null;
    
    try {
        const examData = localStorage.getItem(`${STORAGE_KEY_EXAM}_${currentUser.id}`);
        const responsesData = localStorage.getItem(`${STORAGE_KEY_RESPONSES}_${currentUser.id}`);
        const questionIndexData = localStorage.getItem(`${STORAGE_KEY_QUESTION_INDEX}_${currentUser.id}`);
        const promptData = localStorage.getItem(`${STORAGE_KEY_PROMPT}_${currentUser.id}`);
        
        if (!examData) return null;
        
        return {
            exam: JSON.parse(examData),
            responses: responsesData ? JSON.parse(responsesData) : {},
            questionIndex: questionIndexData ? parseInt(questionIndexData) : 0,
            prompt: promptData ? JSON.parse(promptData) : null
        };
    } catch (error) {
        console.error('Error loading exam state:', error);
        return null;
    }
}

// Clear exam state from localStorage
function clearExamState() {
    if (!currentUser) return;
    
    try {
        localStorage.removeItem(`${STORAGE_KEY_EXAM}_${currentUser.id}`);
        localStorage.removeItem(`${STORAGE_KEY_RESPONSES}_${currentUser.id}`);
        localStorage.removeItem(`${STORAGE_KEY_QUESTION_INDEX}_${currentUser.id}`);
        localStorage.removeItem(`${STORAGE_KEY_PROMPT}_${currentUser.id}`);
    } catch (error) {
        console.error('Error clearing exam state:', error);
    }
}

// DOM Elements
const loginSection = document.getElementById('login-section');
const instructorLoginSection = document.getElementById('instructor-login-section');
const setupSection = document.getElementById('setup-section');
const examSection = document.getElementById('exam-section');
const resultsSection = document.getElementById('results-section');
const loginForm = document.getElementById('login-form');
const instructorLoginForm = document.getElementById('instructor-login-form');
const examSetupForm = document.getElementById('exam-setup-form');
const questionsContainer = document.getElementById('questions-container');
const prevButton = document.getElementById('prev-question');
const nextButton = document.getElementById('next-question');
const submitExamButton = document.getElementById('submit-exam');
const leaveExamButton = document.getElementById('leave-exam');
const newExamButton = document.getElementById('new-exam');
const retryQuestionButton = document.getElementById('retry-question');
const regenerateQuestionsButton = document.getElementById('regenerate-questions');
const regenerateQuestionsExamButton = document.getElementById('regenerate-questions-exam');
const logoutButton = document.getElementById('logout-btn');
const logoutButtonResults = document.getElementById('logout-btn-results');
const logoutButtonPast = document.getElementById('logout-btn-past');
const currentUserSpan = document.getElementById('current-user');
const currentUserSpanResults = document.getElementById('current-user-results');
const currentUserSpanPast = document.getElementById('current-user-past');
const loginError = document.getElementById('login-error');
const instructorLoginError = document.getElementById('instructor-login-error');
const pastExamsContainer = document.getElementById('past-exams-container');
const pastExamsList = document.getElementById('past-exams-list');
const inProgressExamsContainer = document.getElementById('in-progress-exams-container');
const viewPastExamsButton = document.getElementById('view-past-exams');
const backToSetupButton = document.getElementById('back-to-setup');
const pastExamsSearch = document.getElementById('past-exams-search');
const pastExamsSort = document.getElementById('past-exams-sort');
const practicePastExamsSearch = document.getElementById('practice-past-exams-search');
const practicePastExamsSort = document.getElementById('practice-past-exams-sort');

// Store all past exams data for filtering/sorting
let allPastExams = [];
let allPracticePastExams = [];
const instructorLoginLink = document.getElementById('instructor-login-link');
const backToStudentLoginLink = document.getElementById('back-to-student-login');

// Student Dashboard Elements
const dashboardInProgressContainer = document.getElementById('dashboard-in-progress-exams');
const assignedNotificationsContainer = document.getElementById('assigned-exams-notifications');
const assignedBadge = document.getElementById('assigned-exams-badge');
const assignedExamsContainer = document.getElementById('assigned-exams-container');

// Instructor Dashboard Elements
const classSelectionSection = document.getElementById('class-selection-section');
const classDashboardSection = document.getElementById('class-dashboard-section');
const classesList = document.getElementById('classes-list');
const selectedClassName = document.getElementById('selected-class-name');
const changeClassBtn = document.getElementById('change-class-btn');
const instructorUsernameDisplay = document.getElementById('instructor-username-display');
const studentsList = document.getElementById('students-list');
const examsList = document.getElementById('exams-list');
const studentSearch = document.getElementById('student-search');
const assignExamModal = document.getElementById('assign-exam-modal');
const closeAssignModal = document.getElementById('close-assign-modal');
const cancelAssign = document.getElementById('cancel-assign');
const confirmAssign = document.getElementById('confirm-assign');
const createExamBtn = document.getElementById('create-exam-btn');
const instructorCreateExamModal = document.getElementById('instructor-create-exam-modal');
const instructorExamSetupForm = document.getElementById('instructor-exam-setup-form');
const closeInstructorCreateModal = document.getElementById('close-instructor-create-modal');
const cancelInstructorCreate = document.getElementById('cancel-instructor-create');
const instructorSetupLoading = document.getElementById('instructor-setup-loading');
// confirmCreate removed - now using review step
const assignExamSelect = document.getElementById('assign-exam-select');
const assignStudentsList = document.getElementById('assign-students-list');
const instructorLogoutBtn = document.getElementById('instructor-logout');
const studentDetailsModal = document.getElementById('student-details-modal');
const studentDetailsContent = document.getElementById('student-details-content');
const closeStudentDetailsModal = document.getElementById('close-student-details-modal');
const closeStudentDetails = document.getElementById('close-student-details');

// Store selected class
let selectedClass = null;

// Event Listeners
if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
    console.log('DEBUG: Login form event listener attached');
} else {
    console.error('DEBUG: Login form not found!');
}

if (instructorLoginForm) {
    instructorLoginForm.addEventListener('submit', handleInstructorLogin);
}

if (instructorLoginLink) {
    instructorLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        showInstructorLogin();
    });
}

if (backToStudentLoginLink) {
    backToStudentLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        showStudentLogin();
    });
}
if (examSetupForm) {
    examSetupForm.addEventListener('submit', handleExamSetup);
    console.log('DEBUG: Form event listener attached');
} else {
    console.error('DEBUG: exam-setup-form element not found!');
}
if (logoutButton) {
    logoutButton.addEventListener('click', handleLogout);
}
if (logoutButtonResults) {
    logoutButtonResults.addEventListener('click', handleLogout);
}
if (logoutButtonPast) {
    logoutButtonPast.addEventListener('click', handleLogout);
}
if (viewPastExamsButton) {
    viewPastExamsButton.addEventListener('click', () => showPastExamsSection());
}
if (backToSetupButton) {
    backToSetupButton.addEventListener('click', () => {
        showSection('student-dashboard-section');
        showTab('dashboard');
        loadAssignedExams();
        loadDashboardInProgressExams();
    });
}

// Past exams filter and sort event listeners
if (pastExamsSearch) {
    pastExamsSearch.addEventListener('input', applyPastExamsFilterAndSort);
}

if (pastExamsSort) {
    pastExamsSort.addEventListener('change', applyPastExamsFilterAndSort);
}

// Practice tab past exams filter and sort event listeners
if (practicePastExamsSearch) {
    practicePastExamsSearch.addEventListener('input', applyPracticePastExamsFilterAndSort);
}

if (practicePastExamsSort) {
    practicePastExamsSort.addEventListener('change', applyPracticePastExamsFilterAndSort);
}

prevButton.addEventListener('click', () => navigateQuestion(-1));
nextButton.addEventListener('click', () => navigateQuestion(1));
submitExamButton.addEventListener('click', handleSubmitExam);
if (leaveExamButton) {
    leaveExamButton.addEventListener('click', handleLeaveExam);
}
newExamButton.addEventListener('click', () => {
    console.log('DEBUG: Create New Exam button clicked');
    resetApp();
    showSection('student-dashboard-section');
    showTab('practice');
    
    // Ensure form is visible and ready
    const form = document.getElementById('exam-setup-form');
    const loading = document.getElementById('setup-loading');
    
    if (form) {
        form.style.display = 'block';
        form.reset();
        console.log('DEBUG: Form reset and made visible');
    }
    
    if (loading) {
        loading.style.display = 'none';
        loading.classList.remove('show');
    }
    
    // showTab('practice') already loads the practice exams data
});
retryQuestionButton.addEventListener('click', handleRetryQuestion);
regenerateQuestionsButton.addEventListener('click', handleRegenerateQuestions);
regenerateQuestionsExamButton.addEventListener('click', handleRegenerateQuestions);

// Initialize
async function init() {
    // Check if user is already logged in
    await checkAuth();
}

// Check authentication status
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/me`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            currentUser = await response.json();
            updateUserDisplay();
            
            // Check for saved exam state
            const savedState = loadExamState();
            if (savedState && savedState.exam) {
                // Restore exam state
                currentExam = savedState.exam;
                studentResponses = savedState.responses;
                currentQuestionIndex = savedState.questionIndex;
                originalPrompt = savedState.prompt;
                
                // Restore domain if needed
                if (!currentExam.domain && originalPrompt) {
                    currentExam.domain = originalPrompt.domain;
                }
                
                showSection('exam-section');
                displayExam();
            } else {
                showSection('student-dashboard-section');
                showTab('practice');
                loadPracticeExams();
                loadDashboardInProgressExams();
            }
        } else {
            showSection('login-section');
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showSection('login-section');
    }
}

// Show instructor login page
function showInstructorLogin() {
    if (loginSection) loginSection.style.display = 'none';
    if (instructorLoginSection) {
        instructorLoginSection.style.display = 'flex';
        instructorLoginSection.classList.add('active');
    }
}

// Show student login page
function showStudentLogin() {
    if (instructorLoginSection) {
        instructorLoginSection.style.display = 'none';
        instructorLoginSection.classList.remove('active');
    }
    if (loginSection) {
        loginSection.style.display = 'flex';
        loginSection.classList.add('active');
    }
}

// Handle login
async function handleLogin(e) {
    e.preventDefault();
    console.log('DEBUG: Login form submitted');
    
    const formData = new FormData(e.target);
    const loginData = {
        username: formData.get('username'),
        password: formData.get('password')
    };
    
    console.log('DEBUG: Login attempt for:', loginData.username);
    
    // Clear previous errors
    if (loginError) {
        loginError.style.display = 'none';
        loginError.textContent = '';
    }
    
    try {
        console.log('DEBUG: Sending login request to', `${API_BASE}/login`);
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(loginData)
        });
        
        console.log('DEBUG: Login response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('DEBUG: Login failed:', error);
            throw new Error(error.detail || 'Login failed');
        }
        
        const data = await response.json();
        console.log('DEBUG: Login successful, user data:', data);
        
        // Check if user is trying to login as student but is an instructor
        if (data.user_type === 'instructor') {
            throw new Error('Please use the Instructor Login page to sign in.');
        }
        
        currentUser = data;
        
        // Update UI
        updateUserDisplay();
        console.log('DEBUG: About to show student-dashboard-section');
        showSection('student-dashboard-section');
        // Load dashboard data
        setTimeout(() => {
            loadAssignedExams();
            loadDashboardInProgressExams();
        }, 100);
        loginForm.reset();
        // Load exams after login (non-blocking)
        setTimeout(() => {
            loadInProgressExams();
            loadPastExams();
        }, 100);
        console.log('DEBUG: Login complete, setup section should be visible');
        
    } catch (error) {
        console.error('DEBUG: Login error:', error);
        if (loginError) {
            loginError.textContent = error.message;
            loginError.style.display = 'block';
        }
    }
}

// Handle instructor login
async function handleInstructorLogin(e) {
    e.preventDefault();
    console.log('DEBUG: Instructor login form submitted');
    
    const formData = new FormData(e.target);
    const loginData = {
        username: formData.get('username'),
        password: formData.get('password')
    };
    
    console.log('DEBUG: Instructor login attempt for:', loginData.username);
    
    // Clear previous errors
    if (instructorLoginError) {
        instructorLoginError.style.display = 'none';
        instructorLoginError.textContent = '';
    }
    
    try {
        console.log('DEBUG: Sending instructor login request to', `${API_BASE}/login`);
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(loginData)
        });
        
        console.log('DEBUG: Instructor login response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('DEBUG: Instructor login failed:', error);
            throw new Error(error.detail || 'Login failed');
        }
        
        const data = await response.json();
        console.log('DEBUG: Instructor login successful, user data:', data);
        
        // Check if user is trying to login as instructor but is a student
        if (data.user_type !== 'instructor') {
            throw new Error('This account is not an instructor account. Please use the Student Login page.');
        }
        
        currentUser = data;
        
        // Update UI - Show instructor dashboard
        updateUserDisplay();
        console.log('DEBUG: About to show instructor-dashboard-section');
        showSection('instructor-dashboard-section');
        instructorLoginForm.reset();
        
        // Update instructor username display
        if (instructorUsernameDisplay && currentUser) {
            instructorUsernameDisplay.textContent = currentUser.username;
        }
        
        // Load classes for selection
        loadClasses();
        console.log('DEBUG: Instructor login complete');
        
    } catch (error) {
        console.error('DEBUG: Instructor login error:', error);
        if (instructorLoginError) {
            instructorLoginError.textContent = error.message;
            instructorLoginError.style.display = 'block';
        }
    }
}

// Handle logout
async function handleLogout() {
    try {
        await fetch(`${API_BASE}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        currentUser = null;
        resetApp();
        showSection('login-section');
        
    } catch (error) {
        console.error('Logout error:', error);
        // Still show login page even if logout request fails
        currentUser = null;
        resetApp();
        showSection('login-section');
    }
}

// Update user display
function updateUserDisplay() {
    const userText = `Logged in as: ${currentUser.username}`;
    if (currentUserSpan && currentUser) {
        currentUserSpan.textContent = userText;
        currentUserSpan.style.display = 'block';
    }
    if (currentUserSpanResults && currentUser) {
        currentUserSpanResults.textContent = userText;
        currentUserSpanResults.style.display = 'block';
    }
    if (currentUserSpanPast && currentUser) {
        currentUserSpanPast.textContent = userText;
        currentUserSpanPast.style.display = 'block';
    }
}

// Show specific section
function showSection(sectionId) {
    console.log('DEBUG: Showing section:', sectionId);
    // Hide all sections including login sections
    const allSections = ['login-section', 'instructor-login-section', 'setup-section', 'student-dashboard-section', 'exam-section', 'results-section', 'past-exams-section', 'instructor-dashboard-section'];
    allSections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.remove('active');
            if (id === 'login-section' || id === 'instructor-login-section') {
                section.style.display = 'none';
            } else {
                section.style.display = 'none';
            }
        }
    });
    
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        if (sectionId === 'login-section' || sectionId === 'instructor-login-section') {
            section.style.display = 'flex';
        } else {
            section.style.display = 'block';
        }
        console.log('DEBUG: Section displayed:', sectionId);
        
        // If showing student dashboard, load dashboard data
        if (sectionId === 'student-dashboard-section') {
            loadAssignedExams();
            loadDashboardInProgressExams();
            // Show dashboard tab by default
            showTab('dashboard');
        }
        
        // If showing setup section (legacy), ensure form is visible and load past exams
        if (sectionId === 'setup-section') {
            const form = document.getElementById('exam-setup-form');
            const loading = document.getElementById('setup-loading');
            if (form) form.style.display = 'block';
            if (loading) loading.style.display = 'none';
            // Reload in-progress exams to show updated progress
            loadInProgressExams();
            loadPastExams();
        }
    } else {
        console.error('DEBUG: Section not found:', sectionId);
    }
}

// Handle exam setup form submission
async function handleExamSetup(e) {
    e.preventDefault();
    console.log('DEBUG: Form submitted!');
    
    try {
        const formData = new FormData(e.target);
        const setupData = {
            domain: formData.get('domain'),
            professor_instructions: formData.get('professor-instructions') || null,
            num_questions: parseInt(formData.get('num-questions'))
        };
        
        console.log('DEBUG: Form data collected:', setupData);
        
        // Validate data
        if (!setupData.domain || !setupData.domain.trim()) {
            throw new Error('Domain is required');
        }
        
        // Make sure we're on the practice tab FIRST
        showSection('student-dashboard-section');
        showTab('practice');
        
        // THEN show loading (after tab is set up)
        const loadingEl = document.getElementById('setup-loading');
        if (!loadingEl) {
            throw new Error('Loading element not found');
        }
        examSetupForm.style.display = 'none';
        loadingEl.style.display = 'block';
        
        console.log('DEBUG: handleExamSetup - Starting exam generation request...', setupData);
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.log('DEBUG: Request timeout - aborting');
            controller.abort();
        }, 150000); // 150 second timeout (2.5 minutes)
        
        console.log('DEBUG: Sending fetch request to', `${API_BASE}/generate-questions`);
        const response = await fetch(`${API_BASE}/generate-questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(setupData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('DEBUG: Received response:', response.status, response.statusText);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('DEBUG: Response error:', error);
            throw new Error(error.detail || 'Failed to generate questions');
        }
        
        const data = await response.json();
        currentExam = data;
        // Store domain in exam object for easy access
        currentExam.domain = setupData.domain;
        currentQuestionIndex = 0;
        studentResponses = {};
        
        // Store the original prompt data for display on results page
        originalPrompt = {
            domain: setupData.domain,
            professor_instructions: setupData.professor_instructions,
            num_questions: setupData.num_questions
        };
        
        // Initialize responses
        data.questions.forEach(q => {
            studentResponses[q.question_id] = {
                response_text: '',
                time_spent_seconds: 0,
                start_time: Date.now()
            };
        });
        
        // Save exam state to localStorage
        saveExamState();
        
        // Show exam section
        showSection('exam-section');
        displayExam();
        
    } catch (error) {
        console.error('DEBUG: Error in handleExamSetup:', error);
        console.error('DEBUG: Error stack:', error.stack);
        if (error.name === 'AbortError') {
            console.error('DEBUG: Request was aborted (timeout)');
            showError('Request timed out. The question generation is taking longer than expected. Please try again.');
        } else {
            console.error('DEBUG: Request failed:', error.message);
            showError('Failed to generate questions: ' + error.message);
        }
        const loadingEl = document.getElementById('setup-loading');
        if (loadingEl) loadingEl.style.display = 'none';
        if (examSetupForm) {
            examSetupForm.style.display = 'block';
            // Make sure we're on the practice tab
            showSection('student-dashboard-section');
            showTab('practice');
        }
    }
}

// Handle leaving exam (return to homepage)
function handleLeaveExam() {
    // Save current state before leaving
    if (currentExam && currentQuestionIndex >= 0) {
        // Save current response time
        const currentQuestion = currentExam.questions[currentQuestionIndex];
        if (currentQuestion && studentResponses[currentQuestion.question_id]?.start_time) {
            const timeSpent = Math.floor((Date.now() - studentResponses[currentQuestion.question_id].start_time) / 1000);
            studentResponses[currentQuestion.question_id].time_spent_seconds += timeSpent;
            studentResponses[currentQuestion.question_id].start_time = null;
        }
        
        // Save state to localStorage
        saveExamState();
    }
    
    // Reset form/loading state when leaving exam
    const form = document.getElementById('exam-setup-form');
    const loading = document.getElementById('setup-loading');
    if (form) {
        form.style.display = 'block';
    }
    if (loading) {
        loading.style.display = 'none';
    }
    
    // Return to dashboard
    showSection('student-dashboard-section');
    showTab('dashboard');
    // Reload dashboard data
    loadAssignedExams();
    loadDashboardInProgressExams();
}

// Display exam
async function displayExam() {
    if (!currentExam) return;
    
    // Start the exam (create submission record in database)
    try {
        const examId = currentExam.exam_id;
        if (examId) {
            await fetch(`${API_BASE}/exam/${examId}/start`, {
                method: 'POST',
                credentials: 'include'
            });
        }
    } catch (error) {
        console.error('Error starting exam:', error);
        // Don't block display if this fails
    }
    
    // Reset submit button to original state
    if (submitExamButton) {
        submitExamButton.disabled = false;
        submitExamButton.textContent = 'Submit All Responses';
    }
    
    // Update header with domain/topic
    const domain = currentExam.domain || currentExam.questions[0]?.domain_info || originalPrompt?.domain || '';
    const examTitle = domain ? `${domain} Exam` : 'Exam';
    document.getElementById('exam-domain').textContent = examTitle;
    updateQuestionCounter();
    
    // Display all questions
    questionsContainer.innerHTML = '';
    currentExam.questions.forEach((question, index) => {
        const questionCard = createQuestionCard(question, index);
        questionsContainer.appendChild(questionCard);
    });
    
    // Show current question
    showQuestion(currentQuestionIndex);
    updateNavigationButtons();
    
    // Update progress bar if we're viewing this exam
    updateProgressBar();
}

// Create question card
function createQuestionCard(question, index) {
    const card = document.createElement('div');
    card.className = 'question-card';
    card.id = `question-${index}`;
    card.style.display = index === currentQuestionIndex ? 'block' : 'none';
    
    card.innerHTML = `
        <h3>Question ${index + 1}</h3>
        <div class="background-info">
            <h4>Background Information</h4>
            <p>${escapeHtml(question.background_info)}</p>
        </div>
        <div class="question-content">
            <h4>Essay Question:</h4>
            <p>${escapeHtml(question.question_text)}</p>
        </div>
        <div class="rubric-info">
            <h4>Grading Rubric</h4>
            <p>Your answer will be evaluated on the following dimensions:</p>
            <ul>
                ${question.grading_rubric.dimensions?.map(dim => 
                    `<li><strong>${dim.name}</strong> (${dim.max_points} points): ${dim.description}</li>`
                ).join('') || '<li>See rubric details</li>'}
            </ul>
        </div>
        <div class="form-group">
            <label for="response-${question.question_id}">Your Answer:</label>
            <textarea 
                id="response-${question.question_id}" 
                class="response-textarea"
                placeholder="Type your essay response here..."
                data-question-id="${question.question_id}"
            >${studentResponses[question.question_id]?.response_text || ''}</textarea>
        </div>
        ${studentResponses[question.question_id]?.llm_score !== null && studentResponses[question.question_id]?.llm_score !== undefined ? `
        <div class="grade-display" style="margin-top: 15px; padding: 15px; background: #f0f9ff; border-left: 4px solid #3182ce; border-radius: 4px;">
            <h4 style="margin: 0 0 10px 0; color: #1e40af;">Grade Received</h4>
            <div style="font-size: 1.2em; font-weight: bold; color: #1e40af; margin-bottom: 10px;">
                Score: ${studentResponses[question.question_id].llm_score.toFixed(1)} / ${question.points_possible || 10}
            </div>
            ${studentResponses[question.question_id].llm_feedback ? `
            <div style="margin-top: 10px;">
                <strong>Feedback:</strong>
                <p style="margin: 5px 0 0 0; color: #374151;">${escapeHtml(studentResponses[question.question_id].llm_feedback)}</p>
            </div>
            ` : ''}
        </div>
        ` : ''}
    `;
    
    // Add input listener
    const textarea = card.querySelector(`#response-${question.question_id}`);
    textarea.addEventListener('input', (e) => {
        const questionId = e.target.dataset.questionId;
        if (!studentResponses[questionId].start_time) {
            studentResponses[questionId].start_time = Date.now();
        }
        studentResponses[questionId].response_text = e.target.value;
        // Save state whenever user types
        saveExamState();
        // Update progress bar in in-progress exams section
        updateProgressBar();
    });
    
    return card;
}

// Show specific question
function showQuestion(index) {
    currentExam.questions.forEach((q, i) => {
        const card = document.getElementById(`question-${i}`);
        if (card) {
            card.style.display = i === index ? 'block' : 'none';
        }
    });
    currentQuestionIndex = index;
    updateNavigationButtons();
    updateQuestionCounter();
}

// Navigate between questions
function navigateQuestion(direction) {
    const newIndex = currentQuestionIndex + direction;
    if (newIndex >= 0 && newIndex < currentExam.questions.length) {
        // Save current response time
        const currentQuestion = currentExam.questions[currentQuestionIndex];
        if (studentResponses[currentQuestion.question_id]?.start_time) {
            const timeSpent = Math.floor((Date.now() - studentResponses[currentQuestion.question_id].start_time) / 1000);
            studentResponses[currentQuestion.question_id].time_spent_seconds += timeSpent;
            studentResponses[currentQuestion.question_id].start_time = null;
        }
        
        showQuestion(newIndex);
        
        // Start timer for new question
        const newQuestion = currentExam.questions[newIndex];
        if (!studentResponses[newQuestion.question_id].start_time) {
            studentResponses[newQuestion.question_id].start_time = Date.now();
        }
        
        // Save state after navigation
        saveExamState();
    }
}

// Update navigation buttons
function updateNavigationButtons() {
    prevButton.disabled = currentQuestionIndex === 0;
    nextButton.disabled = currentQuestionIndex === currentExam.questions.length - 1;
}

// Update question counter
function updateQuestionCounter() {
    document.getElementById('question-counter').textContent = 
        `Question ${currentQuestionIndex + 1} of ${currentExam.questions.length}`;
}

// Update progress bar in in-progress exams section when text is typed
function updateProgressBar() {
    if (!currentExam || !currentUser) return;
    
    // Count questions with text input
    const questionsWithText = Object.values(studentResponses || {}).filter(
        response => response.response_text && response.response_text.trim().length > 0
    ).length;
    
    const totalQuestions = currentExam.questions ? currentExam.questions.length : 0;
    const progressPercentage = totalQuestions > 0 ? Math.round((questionsWithText / totalQuestions) * 100) : 0;
    
    // Update progress bar if it exists in the in-progress exams section
    const progressBar = document.getElementById(`progress-bar-${currentExam.exam_id}`);
    const progressText = document.getElementById(`progress-text-${currentExam.exam_id}`);
    
    if (progressBar) {
        progressBar.style.width = `${progressPercentage}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${progressPercentage}% Complete`;
    }
    
    // Also update the "In Progress" count text
    const examCard = document.querySelector(`.in-progress-exam[data-exam-id="${currentExam.exam_id}"]`);
    if (examCard) {
        const metaSpan = examCard.querySelector('.past-exam-meta span:last-child');
        if (metaSpan && metaSpan.textContent.includes('In Progress:')) {
            metaSpan.innerHTML = `<strong>In Progress:</strong> ${questionsWithText} / ${totalQuestions}`;
        }
    }
}

// Handle exam submission
async function handleSubmitExam() {
    if (!confirm('Are you sure you want to submit all responses? This will grade your answers.')) {
        return;
    }
    
    // Save current response time
    const currentQuestion = currentExam.questions[currentQuestionIndex];
    if (studentResponses[currentQuestion.question_id]?.start_time) {
        const timeSpent = Math.floor((Date.now() - studentResponses[currentQuestion.question_id].start_time) / 1000);
        studentResponses[currentQuestion.question_id].time_spent_seconds += timeSpent;
        studentResponses[currentQuestion.question_id].start_time = null;
    }
    
    submitExamButton.disabled = true;
    submitExamButton.textContent = 'Grading...';
    
    try {
        const gradingPromises = currentExam.questions.map(async (question) => {
            const response = studentResponses[question.question_id];
            if (!response.response_text.trim()) {
                return {
                    question_id: question.question_id,
                    error: 'No response provided'
                };
            }
            
            try {
                const apiResponse = await fetch(`${API_BASE}/submit-response`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        exam_id: currentExam.exam_id,
                        question_id: question.question_id,
                        response_text: response.response_text,
                        time_spent_seconds: response.time_spent_seconds
                    })
                });
                
                if (!apiResponse.ok) {
                    const error = await apiResponse.json();
                    throw new Error(error.detail || 'Grading failed');
                }
                
                return await apiResponse.json();
            } catch (error) {
                return {
                    question_id: question.question_id,
                    error: error.message
                };
            }
        });
        
        const results = await Promise.all(gradingPromises);
        
        // ALWAYS mark the exam as submitted (moves it to Past Exams)
        // Wait a brief moment to ensure all submit-response calls have committed
        await new Promise(resolve => setTimeout(resolve, 200));
        
        let submitSuccess = false;
        try {
            console.log(`Attempting to mark exam ${currentExam.exam_id} as submitted...`);
            const submitResponse = await fetch(`${API_BASE}/exam/${currentExam.exam_id}/submit`, {
                method: 'POST',
                credentials: 'include'
            });
            
            if (!submitResponse.ok) {
                const errorData = await submitResponse.json().catch(() => ({ detail: 'Failed to mark exam as submitted' }));
                console.error('Error marking exam as submitted:', submitResponse.status, errorData.detail || 'Unknown error');
                // Retry once after a longer delay
                await new Promise(resolve => setTimeout(resolve, 500));
                const retryResponse = await fetch(`${API_BASE}/exam/${currentExam.exam_id}/submit`, {
                    method: 'POST',
                    credentials: 'include'
                });
                if (retryResponse.ok) {
                    submitSuccess = true;
                    console.log('Exam successfully marked as submitted on retry');
                } else {
                    console.error('Retry also failed to mark exam as submitted');
                }
            } else {
                submitSuccess = true;
                const result = await submitResponse.json().catch(() => ({}));
                console.log('Exam successfully marked as submitted:', result);
            }
        } catch (error) {
            console.error('Error marking exam as submitted:', error);
            // Try one more time
            try {
                await new Promise(resolve => setTimeout(resolve, 500));
                const retryResponse = await fetch(`${API_BASE}/exam/${currentExam.exam_id}/submit`, {
                    method: 'POST',
                    credentials: 'include'
                });
                if (retryResponse.ok) {
                    submitSuccess = true;
                    console.log('Exam successfully marked as submitted on retry after error');
                }
            } catch (retryError) {
                console.error('Retry also failed:', retryError);
            }
        }
        
        // Always refresh exam lists after submission attempt
        setTimeout(() => {
            loadInProgressExams();
            loadPastExams();
        }, 300);
        
        // Store exam data before clearing (needed for retry)
        const examDataForRetry = {
            exam: currentExam,
            prompt: originalPrompt
        };
        
        // Display results
        displayResults(results);
        showSection('results-section');
        
        // Don't clear exam state yet - keep it for retry functionality
        // Only clear localStorage, but keep currentExam in memory for retry
        if (currentUser) {
            try {
                localStorage.removeItem(`${STORAGE_KEY_EXAM}_${currentUser.id}`);
                localStorage.removeItem(`${STORAGE_KEY_RESPONSES}_${currentUser.id}`);
                localStorage.removeItem(`${STORAGE_KEY_QUESTION_INDEX}_${currentUser.id}`);
                localStorage.removeItem(`${STORAGE_KEY_PROMPT}_${currentUser.id}`);
            } catch (error) {
                console.error('Error clearing localStorage:', error);
            }
        }
        
        // Store exam data for retry in a separate key
        if (currentUser && examDataForRetry.exam) {
            try {
                localStorage.setItem(`retry_exam_${currentUser.id}`, JSON.stringify(examDataForRetry));
            } catch (error) {
                console.error('Error saving retry exam data:', error);
            }
        }
        
    } catch (error) {
        showError('Failed to submit exam: ' + error.message);
        submitExamButton.disabled = false;
        submitExamButton.textContent = 'Submit All Responses';
    }
}

// Display grading results
function displayResults(results) {
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    
    let totalScore = 0;
    let maxScore = 0;
    
    results.forEach((result, index) => {
        if (result.error) {
            container.innerHTML += `
                <div class="error-message">
                    <h3>Question ${index + 1} - Error</h3>
                    <p>${result.error}</p>
                </div>
            `;
            return;
        }
        
        const question = currentExam.questions.find(q => q.question_id === result.question_id);
        totalScore += result.total_score || 0;
        maxScore += question?.grading_rubric?.total_points || 0;
        
        const resultCard = document.createElement('div');
        resultCard.className = 'grade-result';
        resultCard.innerHTML = `
            <h3>Question ${index + 1}</h3>
            
            <div class="question-content">
                <h4>ESSAY QUESTION:</h4>
                <p>${escapeHtml(question.question_text)}</p>
            </div>
            
            <div class="score-breakdown-section">
                <h4>SCORE BREAKDOWN</h4>
                <div class="score-breakdown">
                    ${Object.entries(result.scores || {}).map(([dim, score]) => `
                        <div class="score-item">
                            <div class="label">${escapeHtml(dim)}</div>
                            <div class="value">${score.toFixed(1)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="total-score-section">
                <h4>TOTAL SCORE</h4>
                <div class="total-score-value">${(result.total_score || 0).toFixed(1)} / ${question?.grading_rubric?.total_points || 0}</div>
            </div>
            
            <div class="explanation-box">
                <h4>GRADING EXPLANATION</h4>
                <p>${escapeHtml(result.explanation || 'No explanation provided.')}</p>
            </div>
            
            <div class="feedback-box">
                <h4>FEEDBACK</h4>
                <p>${escapeHtml(result.feedback || 'No feedback provided.')}</p>
            </div>
        `;
        container.appendChild(resultCard);
    });
    
    // Add overall summary
    if (results.length > 1) {
        const summary = document.createElement('div');
        summary.className = 'grade-result';
        const percentage = maxScore > 0 ? ((totalScore / maxScore) * 100) : 0;
        summary.innerHTML = `
            <h3>Overall Summary</h3>
            <div class="overall-summary-container">
                <div class="total-score-section">
                    <h4>TOTAL SCORE</h4>
                    <div class="total-score-value" style="color: #000000 !important;">${totalScore.toFixed(1)} / ${maxScore}</div>
                </div>
                <div class="total-score-section">
                    <h4>PERCENTAGE</h4>
                    <div class="total-score-value" style="color: #000000 !important;">${percentage.toFixed(1)}%</div>
                </div>
            </div>
        `;
        container.insertBefore(summary, container.firstChild);
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function resetApp() {
    console.log('DEBUG: Resetting app...');
    clearExamState();
    currentExam = null;
    currentQuestionIndex = 0;
    studentResponses = {};
    originalPrompt = null;
    
    // Reset form state
    const form = document.getElementById('exam-setup-form');
    if (form) {
        form.reset();
        form.style.display = 'block';
    }
    
    // Hide loading indicator
    const loading = document.getElementById('setup-loading');
    if (loading) {
        loading.style.display = 'none';
    }
    
    // Reset submit button to original state
    if (submitExamButton) {
        submitExamButton.disabled = false;
        submitExamButton.textContent = 'Submit All Responses';
    }
    
    console.log('DEBUG: App reset complete');
}

// Handle retry exam - go back to exam with same questions but clear responses
async function handleRetryQuestion() {
    // Try to get exam from current state first
    let examToRetry = currentExam;
    let promptToRetry = originalPrompt;
    let examIdToFetch = null;
    
    // If not in memory, try to load from localStorage
    if (!examToRetry && currentUser) {
        try {
            const retryData = localStorage.getItem(`retry_exam_${currentUser.id}`);
            if (retryData) {
                const parsed = JSON.parse(retryData);
                examToRetry = parsed.exam;
                promptToRetry = parsed.prompt;
                examIdToFetch = parsed.exam?.exam_id;
            }
        } catch (error) {
            console.error('Error loading retry exam data:', error);
        }
    } else if (examToRetry && examToRetry.exam_id) {
        examIdToFetch = examToRetry.exam_id;
    }
    
    // If we have an exam_id and questions are missing background_info, try to fetch from server
    if (examIdToFetch && examToRetry && examToRetry.questions) {
        const missingBackgroundInfo = examToRetry.questions.some(q => !q.background_info || q.background_info === "");
        
        if (missingBackgroundInfo) {
            try {
                // Try to get exam results which includes background_info
                const response = await fetch(`${API_BASE}/exam/${examIdToFetch}/my-results`, {
                    credentials: 'include'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    // Update questions with background_info from server
                    const questionMap = {};
                    data.questions_with_answers.forEach(q => {
                        questionMap[q.question_id] = q.background_info || "";
                    });
                    
                    // Update examToRetry questions with background_info
                    examToRetry.questions.forEach(q => {
                        if (questionMap[q.question_id] !== undefined) {
                            q.background_info = questionMap[q.question_id];
                        }
                    });
                }
            } catch (error) {
                console.error('Error fetching exam background_info:', error);
                // Continue with exam from localStorage if fetch fails
            }
        }
    }
    
    if (!examToRetry || !examToRetry.questions || examToRetry.questions.length === 0) {
        showError('No exam to retry. Please create a new exam.');
        return;
    }
    
    // Ensure all questions have background_info (even if empty string)
    examToRetry.questions.forEach(q => {
        if (q.background_info === undefined || q.background_info === null) {
            q.background_info = "";
        }
    });
    
    // Restore exam data
    currentExam = examToRetry;
    if (!originalPrompt && promptToRetry) {
        originalPrompt = promptToRetry;
    }
    
    // Reset responses but keep the same exam
    currentQuestionIndex = 0;
    studentResponses = {};
    
    // Reset submit button state
    submitExamButton.disabled = false;
    submitExamButton.textContent = 'Submit All Responses';
    
    // Initialize fresh responses for all questions
    currentExam.questions.forEach(q => {
        studentResponses[q.question_id] = {
            response_text: '',
            time_spent_seconds: 0,
            start_time: Date.now()
        };
    });
    
    // Save state
    saveExamState();
    
    // Go back to exam section
    showSection('exam-section');
    displayExam();
}

// Handle regenerate questions - automatically regenerate with same settings
async function handleRegenerateQuestions() {
    // Use original prompt if available, otherwise use current exam data
    const promptData = originalPrompt || (currentExam ? {
        domain: currentExam.domain,
        professor_instructions: null,
        num_questions: currentExam.questions?.length || 1
    } : null);
    
    if (!promptData || !promptData.domain) {
        // If no prompt data, just go to practice tab
        showSection('student-dashboard-section');
        showTab('practice');
        return;
    }
    
    // Pre-fill the form with prompt data (for user visibility)
    document.getElementById('domain').value = promptData.domain || '';
    document.getElementById('professor-instructions').value = promptData.professor_instructions || '';
    document.getElementById('num-questions').value = promptData.num_questions || 1;
    
    // Show practice tab with loading state
    showSection('student-dashboard-section');
    showTab('practice');
    document.getElementById('setup-loading').style.display = 'block';
    examSetupForm.style.display = 'none';
    
    // Automatically submit the form to regenerate questions
    const setupData = {
        domain: promptData.domain,
        professor_instructions: promptData.professor_instructions || null,
        num_questions: promptData.num_questions || 1
    };
    
    try {
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 150000); // 150 second timeout (2.5 minutes)
        
        const response = await fetch(`${API_BASE}/generate-questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(setupData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate questions');
        }
        
        const data = await response.json();
        currentExam = data;
        // Store domain in exam object for easy access
        currentExam.domain = setupData.domain;
        currentQuestionIndex = 0;
        studentResponses = {};
        
        // Update the original prompt data
        originalPrompt = {
            domain: setupData.domain,
            professor_instructions: setupData.professor_instructions,
            num_questions: setupData.num_questions
        };
        
        // Initialize responses
        data.questions.forEach(q => {
            studentResponses[q.question_id] = {
                response_text: '',
                time_spent_seconds: 0,
                start_time: Date.now()
            };
        });
        
        // Show exam section with new questions
        showSection('exam-section');
        displayExam();
        
    } catch (error) {
        console.error('DEBUG: Error in handleRegenerateQuestions:', error);
        if (error.name === 'AbortError') {
            console.error('DEBUG: Request was aborted (timeout)');
            showError('Request timed out. The question generation is taking longer than expected. Please try again.');
        } else {
            console.error('DEBUG: Request failed:', error.message);
            showError('Failed to regenerate questions: ' + error.message);
        }
        document.getElementById('setup-loading').style.display = 'none';
        examSetupForm.style.display = 'block';
    }
}

// Load in-progress exams
async function loadInProgressExams() {
    if (!inProgressExamsContainer) {
        console.log('DEBUG: inProgressExamsContainer not found, skipping loadInProgressExams');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/my-exams/in-progress`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            console.log('DEBUG: Failed to load in-progress exams, status:', response.status);
            inProgressExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No in-progress exams found.</p>';
            return;
        }
        
        const data = await response.json();
        displayInProgressExams(data.exams || []);
    } catch (error) {
        console.error('Error loading in-progress exams:', error);
        if (inProgressExamsContainer) {
            inProgressExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Unable to load in-progress exams.</p>';
        }
    }
}

// Display past exams in Practice tab
function displayPastExams(exams) {
    if (!pastExamsContainer) return;
    
    if (exams.length === 0) {
        const searchTerm = practicePastExamsSearch ? practicePastExamsSearch.value.trim() : '';
        if (searchTerm) {
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No exams match your search. Try different keywords.</p>';
        } else {
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams. Complete an exam to see it here!</p>';
        }
        return;
    }
    
    const examsHTML = exams.map(exam => {
        const submittedDate = exam.submitted_at ? new Date(exam.submitted_at).toLocaleDateString() : 'Not submitted';
        const scoreColor = exam.percentage >= 70 ? '#28a745' : exam.percentage >= 50 ? '#ffc107' : '#dc3545';
        
        return `
            <div class="past-exam-card" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                <div class="past-exam-header">
                    <h3>${escapeHtml(exam.title)}</h3>
                    <span class="past-exam-date">${submittedDate}</span>
                </div>
                <div class="past-exam-info">
                    <div class="past-exam-meta">
                        <span><strong>Domain:</strong> ${escapeHtml(exam.domain)}</span>
                        <span><strong>Questions:</strong> ${exam.question_count}</span>
                    </div>
                    <div class="past-exam-score" style="color: ${scoreColor};">
                        <strong>Score:</strong> ${exam.total_score} / ${exam.max_score} (${exam.percentage}%)
                    </div>
                </div>
                <button class="btn btn-primary view-exam-btn" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                    View Exam
                </button>
            </div>
        `;
    }).join('');
    
    pastExamsContainer.innerHTML = examsHTML;
    
    // Add event listeners to view buttons
    pastExamsContainer.querySelectorAll('.view-exam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const examId = e.target.dataset.examId;
            const submissionId = e.target.dataset.submissionId;
            viewPastExam(examId, submissionId);
        });
    });
}

// Display in-progress exams
function displayInProgressExams(exams) {
    if (!inProgressExamsContainer) return;
    
    if (exams.length === 0) {
        inProgressExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No in-progress exams. Start a new exam to begin!</p>';
        return;
    }
    
    const examsHTML = exams.map(exam => {
        const startedDate = exam.started_at ? new Date(exam.started_at).toLocaleDateString() : 'Unknown';
        
        // Check localStorage for saved responses to count questions with text input
        let questionsWithText = exam.answered_count || 0;
        if (currentUser) {
            try {
                const savedState = loadExamState();
                if (savedState && savedState.exam && savedState.exam.exam_id === exam.exam_id) {
                    // Count questions that have text input (even if not submitted)
                    questionsWithText = Object.values(savedState.responses || {}).filter(
                        response => response.response_text && response.response_text.trim().length > 0
                    ).length;
                }
            } catch (error) {
                console.error('Error checking localStorage for progress:', error);
            }
        }
        
        const progressBar = exam.question_count > 0 ? Math.round((questionsWithText / exam.question_count) * 100) : 0;
        
        return `
            <div class="past-exam-card in-progress-exam" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                <div class="past-exam-header">
                    <h3>${escapeHtml(exam.title)}</h3>
                    <span class="past-exam-date">Started: ${startedDate}</span>
                </div>
                <div class="past-exam-info">
                    <div class="past-exam-meta">
                        <span><strong>Domain:</strong> ${escapeHtml(exam.domain)}</span>
                        <span><strong>Questions:</strong> ${exam.question_count}</span>
                        <span><strong>In Progress:</strong> ${questionsWithText} / ${exam.question_count}</span>
                    </div>
                    <div class="progress-bar-container" style="margin-top: 10px; background: #e2e8f0; border-radius: 4px; height: 8px; overflow: hidden;">
                        <div class="progress-bar" id="progress-bar-${exam.exam_id}" style="width: ${progressBar}%; background: #3182ce; height: 8px; border-radius: 4px; transition: width 0.3s ease;"></div>
                    </div>
                    <div style="text-align: center; margin-top: 5px; color: #4a5568; font-size: 0.9em;" id="progress-text-${exam.exam_id}">${progressBar}% Complete</div>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button class="btn btn-primary view-exam-btn resume-exam-btn" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}" style="flex: 1;">
                        Resume Exam
                    </button>
                    <button class="btn btn-danger delete-exam-btn" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                        Remove
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    inProgressExamsContainer.innerHTML = examsHTML;
    
    // Add event listeners to resume buttons
    inProgressExamsContainer.querySelectorAll('.resume-exam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const examId = e.target.dataset.examId;
            resumeExam(examId);
        });
    });
    
    // Add event listeners to delete buttons
    inProgressExamsContainer.querySelectorAll('.delete-exam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const examId = e.target.dataset.examId;
            deleteInProgressExam(examId);
        });
    });
}

// Delete an in-progress exam
async function deleteInProgressExam(examId) {
    if (!confirm('Are you sure you want to remove this exam from your in-progress list? This will delete all your progress on this exam.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/exam/${examId}/in-progress`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete exam');
        }
        
        // If this is the current exam, clear the state
        if (currentExam && currentExam.exam_id === examId) {
            clearExamState();
            currentExam = null;
            studentResponses = {};
            currentQuestionIndex = 0;
            originalPrompt = null;
        } else {
            // Also clear localStorage for this exam if it exists
            if (currentUser) {
                try {
                    const savedState = loadExamState();
                    if (savedState && savedState.exam && savedState.exam.exam_id === examId) {
                        clearExamState();
                    }
                } catch (error) {
                    console.error('Error clearing localStorage:', error);
                }
            }
        }
        
        // Reload in-progress exams to reflect the deletion
        loadInProgressExams();
        
    } catch (error) {
        console.error('Error deleting in-progress exam:', error);
        showError('Failed to remove exam: ' + error.message);
    }
}

// Resume an in-progress exam
// Make resumeExam globally accessible
window.resumeExam = resumeExam;

// View exam results for a completed exam
window.viewExamResults = async function(examId) {
    try {
        // Get exam results for current user
        const response = await fetch(`${API_BASE}/exam/${examId}/my-results`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load exam results');
        }
        
        const examData = await response.json();
        
        // Display results
        displayPastExamResults(examData);
        showSection('results-section');
        
    } catch (error) {
        console.error('Error viewing exam results:', error);
        showError('Failed to load exam results: ' + error.message);
    }
};

async function resumeExam(examId) {
    try {
        // First try to load from localStorage
        const savedState = loadExamState();
        if (savedState && savedState.exam && savedState.exam.exam_id === examId) {
            // Restore from localStorage
            currentExam = savedState.exam;
            studentResponses = savedState.responses;
            currentQuestionIndex = savedState.questionIndex;
            originalPrompt = savedState.prompt;
            
            // Restore domain if needed
            if (!currentExam.domain && originalPrompt) {
                currentExam.domain = originalPrompt.domain;
            }
            
            showSection('exam-section');
            displayExam();
            return;
        }
        
        // If not in localStorage, fetch from server
        const response = await fetch(`${API_BASE}/exam/${examId}/resume`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load exam');
        }
        
        const data = await response.json();
        
        // Reconstruct exam object
        currentExam = {
            exam_id: data.exam_id,
            domain: data.domain,
            title: data.title,
            questions: data.questions.map(q => ({
                question_id: q.question_id,
                background_info: q.background_info || '',
                question_text: q.question_text,
                grading_rubric: q.grading_rubric
            }))
        };
        
        // Restore responses from existing answers (including grade information)
        studentResponses = {};
        currentQuestionIndex = 0;
        
        data.questions.forEach((q, index) => {
            // Store both the answer text and grade information if available
            const answerData = q.existing_answer_data || {};
            studentResponses[q.question_id] = {
                response_text: q.existing_answer || '',
                time_spent_seconds: 0,
                start_time: null,
                // Store grade information for display
                llm_score: answerData.llm_score || null,
                llm_feedback: answerData.llm_feedback || null,
                graded_at: answerData.graded_at || null
            };
            
            // Set current question index to first unanswered question
            if (!q.existing_answer && currentQuestionIndex === 0) {
                currentQuestionIndex = index;
            }
        });
        
        originalPrompt = {
            domain: data.domain,
            professor_instructions: null,
            num_questions: data.questions.length
        };
        
        // Start the exam (ensure submission exists)
        try {
            await fetch(`${API_BASE}/exam/${data.exam_id}/start`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Error starting exam on resume:', error);
        }
        
        // Save state
        saveExamState();
        
        // Show exam section
        showSection('exam-section');
        displayExam();
        
    } catch (error) {
        console.error('Error resuming exam:', error);
        showError('Failed to resume exam: ' + error.message);
    }
}

// Start an assigned exam (for exams that haven't been started yet)
async function startAssignedExam(examId) {
    try {
        // First, start the exam (create/update submission record)
        const startResponse = await fetch(`${API_BASE}/exam/${examId}/start`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!startResponse.ok) {
            throw new Error('Failed to start exam');
        }
        
        // Then load the exam data (same as resume, but for a fresh start)
        const response = await fetch(`${API_BASE}/exam/${examId}/resume`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load exam');
        }
        
        const data = await response.json();
        
        // Reconstruct exam object
        currentExam = {
            exam_id: data.exam_id,
            domain: data.domain,
            title: data.title,
            questions: data.questions.map(q => ({
                question_id: q.question_id,
                background_info: q.background_info || '',
                question_text: q.question_text,
                grading_rubric: q.grading_rubric
            }))
        };
        
        // Initialize responses (empty for new exam)
        studentResponses = {};
        currentQuestionIndex = 0;
        
        data.questions.forEach((q, index) => {
            studentResponses[q.question_id] = {
                response_text: q.existing_answer || '',
                time_spent_seconds: 0,
                start_time: null,
                llm_score: q.existing_answer_data?.llm_score || null,
                llm_feedback: q.existing_answer_data?.llm_feedback || null,
                graded_at: q.existing_answer_data?.graded_at || null
            };
        });
        
        originalPrompt = {
            domain: data.domain,
            professor_instructions: null,
            num_questions: data.questions.length
        };
        
        // Save state
        saveExamState();
        
        // Show exam section
        showSection('exam-section');
        displayExam();
        
        // Refresh the assigned exams list to update status
        loadAssignedExamsList();
        loadAssignedExams();
        
    } catch (error) {
        console.error('Error starting assigned exam:', error);
        showError('Failed to start exam: ' + error.message);
    }
}

// Make it available globally
window.startAssignedExam = startAssignedExam;

// Load past exams
async function loadPastExams() {
    if (!pastExamsContainer) {
        console.log('DEBUG: pastExamsContainer not found, skipping loadPastExams');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/my-exams`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            // Don't throw error, just log it - past exams are optional
            console.log('DEBUG: Failed to load past exams, status:', response.status);
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams found. Complete an exam to see it here!</p>';
            return;
        }
        
        const data = await response.json();
        // Show exams that are fully submitted (submitted_at is set and not null)
        const submittedExams = (data.exams || []).filter(exam => 
            exam.submitted_at !== null && exam.submitted_at !== undefined && exam.submitted_at !== ''
        );
        
        // Store all exams for filtering/sorting
        allPracticePastExams = submittedExams;
        
        // Apply current filter and sort
        applyPracticePastExamsFilterAndSort();
    } catch (error) {
        console.error('Error loading past exams:', error);
        // Don't break the page if past exams fail to load
        if (pastExamsContainer) {
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Unable to load past exams.</p>';
        }
    }
}

// Display past exams
function displayPastExams(exams) {
    if (!pastExamsContainer) return;
    
    if (exams.length === 0) {
        const searchTerm = practicePastExamsSearch ? practicePastExamsSearch.value.trim() : '';
        if (searchTerm) {
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No exams match your search. Try different keywords.</p>';
        } else {
            pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams found. Complete an exam to see it here!</p>';
        }
        return;
    }
    
    const examsHTML = exams.map(exam => {
        const submittedDate = exam.submitted_at ? new Date(exam.submitted_at).toLocaleDateString() : 'Not submitted';
        const scoreColor = exam.percentage >= 70 ? '#28a745' : exam.percentage >= 50 ? '#ffc107' : '#dc3545';
        
        return `
            <div class="past-exam-card" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                <div class="past-exam-header">
                    <h3>${escapeHtml(exam.title)}</h3>
                    <span class="past-exam-date">${submittedDate}</span>
                </div>
                <div class="past-exam-info">
                    <div class="past-exam-meta">
                        <span><strong>Domain:</strong> ${escapeHtml(exam.domain)}</span>
                        <span><strong>Questions:</strong> ${exam.question_count}</span>
                    </div>
                    <div class="past-exam-score" style="color: ${scoreColor};">
                        <strong>Score:</strong> ${exam.total_score} / ${exam.max_score} (${exam.percentage}%)
                    </div>
                </div>
                <button class="btn btn-primary view-exam-btn" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                    View Exam
                </button>
            </div>
        `;
    }).join('');
    
    pastExamsContainer.innerHTML = examsHTML;
    
    // Add event listeners to view buttons
    pastExamsContainer.querySelectorAll('.view-exam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const examId = e.target.dataset.examId;
            const submissionId = e.target.dataset.submissionId;
            viewPastExam(examId, submissionId);
        });
    });
}

// Filter and sort past exams in Practice tab
function applyPracticePastExamsFilterAndSort() {
    if (!pastExamsContainer) return;
    
    let filteredExams = [...allPracticePastExams];
    
    // Apply text filter
    const searchTerm = practicePastExamsSearch ? practicePastExamsSearch.value.toLowerCase().trim() : '';
    if (searchTerm) {
        filteredExams = filteredExams.filter(exam => {
            const title = (exam.title || '').toLowerCase();
            const domain = (exam.domain || '').toLowerCase();
            const submittedDate = exam.submitted_at ? new Date(exam.submitted_at).toLocaleDateString().toLowerCase() : '';
            const searchText = `${title} ${domain} ${submittedDate}`;
            return searchText.includes(searchTerm);
        });
    }
    
    // Apply sort
    const sortValue = practicePastExamsSort ? practicePastExamsSort.value : 'date-desc';
    filteredExams.sort((a, b) => {
        switch (sortValue) {
            case 'date-desc':
                const dateA = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
                const dateB = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
                return dateB - dateA; // Newest first
            case 'date-asc':
                const dateA2 = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
                const dateB2 = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
                return dateA2 - dateB2; // Oldest first
            case 'title-asc':
                return (a.title || '').localeCompare(b.title || '');
            case 'title-desc':
                return (b.title || '').localeCompare(a.title || '');
            case 'score-desc':
                return (b.percentage || 0) - (a.percentage || 0);
            case 'score-asc':
                return (a.percentage || 0) - (b.percentage || 0);
            default:
                return 0;
        }
    });
    
    // Display filtered and sorted exams
    displayPastExams(filteredExams);
}

// Show past exams section
function showPastExamsSection() {
    showSection('past-exams-section');
    loadPastExamsList();
    // Also refresh in-progress exams to remove any that are now completed
    loadInProgressExams();
}

// Load past exams for the dedicated section
async function loadPastExamsList() {
    if (!pastExamsList) return;
    
    try {
        const response = await fetch(`${API_BASE}/my-exams`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load past exams');
        }
        
        const data = await response.json();
        // Show exams that are fully submitted (submitted_at is set and not null)
        const submittedExams = (data.exams || []).filter(exam => 
            exam.submitted_at !== null && exam.submitted_at !== undefined && exam.submitted_at !== ''
        );
        
        // Store all exams for filtering/sorting
        allPastExams = submittedExams;
        
        // Apply current filter and sort
        applyPastExamsFilterAndSort();
    } catch (error) {
        console.error('Error loading past exams:', error);
        pastExamsList.innerHTML = '<div class="error-message">Failed to load past exams. Please try again.</div>';
    }
}

// Filter and sort past exams
function applyPastExamsFilterAndSort() {
    if (!pastExamsList) return;
    
    let filteredExams = [...allPastExams];
    
    // Apply text filter
    const searchTerm = pastExamsSearch ? pastExamsSearch.value.toLowerCase().trim() : '';
    if (searchTerm) {
        filteredExams = filteredExams.filter(exam => {
            const title = (exam.title || '').toLowerCase();
            const domain = (exam.domain || '').toLowerCase();
            const submittedDate = exam.submitted_at ? new Date(exam.submitted_at).toLocaleDateString().toLowerCase() : '';
            const searchText = `${title} ${domain} ${submittedDate}`;
            return searchText.includes(searchTerm);
        });
    }
    
    // Apply sort
    const sortValue = pastExamsSort ? pastExamsSort.value : 'date-desc';
    filteredExams.sort((a, b) => {
        switch (sortValue) {
            case 'date-desc':
                const dateA = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
                const dateB = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
                return dateB - dateA; // Newest first
            case 'date-asc':
                const dateA2 = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
                const dateB2 = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
                return dateA2 - dateB2; // Oldest first
            case 'title-asc':
                return (a.title || '').localeCompare(b.title || '');
            case 'title-desc':
                return (b.title || '').localeCompare(a.title || '');
            case 'score-desc':
                return (b.percentage || 0) - (a.percentage || 0);
            case 'score-asc':
                return (a.percentage || 0) - (b.percentage || 0);
            default:
                return 0;
        }
    });
    
    // Display filtered and sorted exams
    displayPastExamsList(filteredExams);
}

// Display past exams in dedicated section
function displayPastExamsList(exams) {
    if (!pastExamsList) return;
    
    if (exams.length === 0) {
        const searchTerm = pastExamsSearch ? pastExamsSearch.value.trim() : '';
        if (searchTerm) {
            pastExamsList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No exams match your search. Try different keywords.</p>';
        } else {
            pastExamsList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams found. Complete an exam to see it here!</p>';
        }
        return;
    }
    
    const examsHTML = exams.map(exam => {
        const submittedDate = exam.submitted_at ? new Date(exam.submitted_at).toLocaleDateString() : 'Not submitted';
        const scoreColor = exam.percentage >= 70 ? '#28a745' : exam.percentage >= 50 ? '#ffc107' : '#dc3545';
        
        return `
            <div class="past-exam-card" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                <div class="past-exam-header">
                    <h3>${escapeHtml(exam.title)}</h3>
                    <span class="past-exam-date">${submittedDate}</span>
                </div>
                <div class="past-exam-info">
                    <div class="past-exam-meta">
                        <span><strong>Domain:</strong> ${escapeHtml(exam.domain)}</span>
                        <span><strong>Questions:</strong> ${exam.question_count}</span>
                    </div>
                    <div class="past-exam-score" style="color: ${scoreColor};">
                        <strong>Score:</strong> ${exam.total_score} / ${exam.max_score} (${exam.percentage}%)
                    </div>
                </div>
                <button class="btn btn-primary view-exam-btn" data-exam-id="${exam.exam_id}" data-submission-id="${exam.submission_id}">
                    View Exam
                </button>
            </div>
        `;
    }).join('');
    
    pastExamsList.innerHTML = examsHTML;
    
    // Add event listeners to view buttons
    pastExamsList.querySelectorAll('.view-exam-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const examId = e.target.dataset.examId;
            const submissionId = e.target.dataset.submissionId;
            viewPastExam(examId, submissionId);
        });
    });
}

// View a specific past exam
async function viewPastExam(examId, submissionId) {
    try {
        // Get exam results for current user
        const response = await fetch(`${API_BASE}/exam/${examId}/my-results`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load exam');
        }
        
        const examData = await response.json();
        
        // Display results
        displayPastExamResults(examData);
        showSection('results-section');
        
    } catch (error) {
        console.error('Error viewing past exam:', error);
        showError('Failed to load exam: ' + error.message);
    }
}

// Display past exam results
function displayPastExamResults(examData) {
    const container = document.getElementById('results-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Reconstruct exam object for retry functionality
    const reconstructedExam = {
        exam_id: examData.exam_id,
        domain: examData.domain,
        title: examData.exam_title || examData.title || `${examData.domain} Exam`,
        questions: examData.questions_with_answers.map((item, index) => ({
            question_id: item.question_id || `q_${index}`,
            background_info: item.background_info || "",
            question_text: item.question_text,
            grading_rubric: item.grading_rubric || {
                dimensions: [],
                total_points: item.points_possible || 0
            }
        }))
    };
    
    // Store exam data for retry
    if (currentUser && reconstructedExam && reconstructedExam.questions.length > 0) {
        try {
            const retryData = {
                exam: reconstructedExam,
                prompt: {
                    domain: examData.domain,
                    professor_instructions: null,
                    num_questions: examData.questions_with_answers.length
                }
            };
            localStorage.setItem(`retry_exam_${currentUser.id}`, JSON.stringify(retryData));
        } catch (error) {
            console.error('Error saving retry exam data:', error);
        }
    }
    
    let totalScore = 0;
    let maxScore = 0;
    
    examData.questions_with_answers.forEach((item, index) => {
        const question = item;
        const answer = question.answer;
        
        if (answer && answer.llm_score !== null) {
            totalScore += answer.llm_score;
        }
        maxScore += question.points_possible;
        
        const resultCard = document.createElement('div');
        resultCard.className = 'grade-result';
        
        const scoreColor = answer && answer.llm_score !== null 
            ? (answer.llm_score / question.points_possible >= 0.7 ? '#28a745' : answer.llm_score / question.points_possible >= 0.5 ? '#ffc107' : '#dc3545')
            : '#666';
        
        resultCard.innerHTML = `
            <h3>Question ${index + 1}</h3>
            
            <div class="question-content">
                <h4>ESSAY QUESTION:</h4>
                <p>${escapeHtml(question.question_text)}</p>
            </div>
            
            ${answer ? `
                <div class="answer-display">
                    <h4>YOUR ANSWER:</h4>
                    <p>${escapeHtml(answer.response_text)}</p>
                </div>
                
                <div class="total-score-section">
                    <h4>SCORE</h4>
                    <div class="total-score-value" style="color: ${scoreColor};">
                        ${answer.llm_score !== null ? answer.llm_score.toFixed(1) : 'N/A'} / ${question.points_possible}
                    </div>
                </div>
                
                ${answer.llm_feedback ? `
                    <div class="feedback-box">
                        <h4>FEEDBACK</h4>
                        <p>${escapeHtml(answer.llm_feedback)}</p>
                    </div>
                ` : ''}
            ` : '<div class="no-answer"><p>No answer submitted for this question.</p></div>'}
        `;
        container.appendChild(resultCard);
    });
    
    // Add overall summary
    const summary = document.createElement('div');
    summary.className = 'grade-result';
    const overallPercentage = maxScore > 0 ? (totalScore / maxScore * 100) : 0;
    
    summary.innerHTML = `
        <h3>Overall Summary</h3>
        <div class="overall-summary-container">
            <div class="total-score-section">
                <h4>TOTAL SCORE</h4>
                <div class="total-score-value" style="color: #000000 !important;">${totalScore.toFixed(1)} / ${maxScore.toFixed(1)}</div>
            </div>
            <div class="total-score-section">
                <h4>PERCENTAGE</h4>
                <div class="total-score-value" style="color: #000000 !important;">${overallPercentage.toFixed(1)}%</div>
            </div>
        </div>
    `;
    container.insertBefore(summary, container.firstChild);
}

// ============================================================================
// Instructor Dashboard Functions
// ============================================================================

let allStudents = [];
let allExams = [];

// Instructor Dashboard Functions
async function loadClasses() {
    if (!classesList) return;
    
    try {
        const response = await fetch(`${API_BASE}/instructor/classes`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load classes');
        }
        
        const data = await response.json();
        const classes = data.classes || [];
        
        if (classes.length === 0) {
            classesList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No classes found. Students need to have a class_name assigned.</p>';
            return;
        }
        
        // Render class cards
        classesList.innerHTML = classes.map(className => {
            // Format class name: "CS101" -> "CS 101", "CS201" -> "CS 201", etc.
            let formattedName = className;
            if (className.startsWith('CS') && className.length > 2 && !className.startsWith('CS ')) {
                formattedName = 'CS ' + className.substring(2);
            }
            return `
                <div class="class-card" onclick="selectClass('${escapeHtml(className)}')">
                    <div class="class-card-icon">💻</div>
                    <h3>${escapeHtml(formattedName)}</h3>
                    <p>View students and manage exams</p>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading classes:', error);
        classesList.innerHTML = '<div class="error-message">Failed to load classes. Please try again.</div>';
    }
}

function selectClass(className) {
    selectedClass = className;
    
    // Hide class selection, show dashboard
    if (classSelectionSection) classSelectionSection.style.display = 'none';
    if (classDashboardSection) classDashboardSection.style.display = 'block';
    if (selectedClassName) selectedClassName.textContent = className;
    
    // Load students and exams for this class
    loadAllStudents();
    loadInstructorExams();
}

function changeClass() {
    selectedClass = null;
    
    // Show class selection, hide dashboard
    if (classSelectionSection) classSelectionSection.style.display = 'block';
    if (classDashboardSection) classDashboardSection.style.display = 'none';
    
    // Reload classes
    loadClasses();
}

// Make selectClass globally accessible
window.selectClass = selectClass;

// Load all students
async function loadAllStudents() {
    if (!studentsList) return;
    
    if (!selectedClass) {
        studentsList.innerHTML = '<div class="loading-text">Please select a class first</div>';
        return;
    }
    
    try {
        studentsList.innerHTML = '<div class="loading-text">Loading students...</div>';
        
        const response = await fetch(`${API_BASE}/instructor/students?class_name=${encodeURIComponent(selectedClass)}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load students');
        }
        
        const data = await response.json();
        allStudents = data.students || [];
        
        if (allStudents.length === 0) {
            studentsList.innerHTML = '<div class="loading-text">No students found in the system</div>';
            return;
        }
        
        renderStudents(allStudents);
    } catch (error) {
        console.error('Error loading students:', error);
        studentsList.innerHTML = `<div class="loading-text" style="color: #e53e3e;">Error loading students: ${error.message}</div>`;
    }
}

// Render students list
function renderStudents(students) {
    if (!studentsList) return;
    
    if (students.length === 0) {
        studentsList.innerHTML = '<div class="loading-text">No students found</div>';
        return;
    }
    
    studentsList.innerHTML = students.map(student => `
        <div class="student-card" data-student-id="${student.id}">
            <div class="student-info">
                <div>
                    <div class="student-name">${student.name}</div>
                    <div class="student-id">ID: ${student.student_id}</div>
                    ${student.email ? `<div class="student-email">${student.email}</div>` : ''}
                </div>
            </div>
            <div class="student-assignments">
                <span class="assignment-badge">${student.assigned_exams_count || 0} Exam${(student.assigned_exams_count || 0) !== 1 ? 's' : ''} Assigned</span>
            </div>
        </div>
    `).join('');
    
    // Add click handlers for student cards
    document.querySelectorAll('.student-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.student-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            
            // Get student ID and show details
            const studentId = card.getAttribute('data-student-id');
            if (studentId) {
                loadStudentDetails(parseInt(studentId));
            }
        });
    });
}

// Load and display student details
async function loadStudentDetails(studentId) {
    if (!studentDetailsModal || !studentDetailsContent) return;
    
    try {
        studentDetailsContent.innerHTML = '<div class="loading-text">Loading student information...</div>';
        studentDetailsModal.style.display = 'flex';
        
        const response = await fetch(`${API_BASE}/instructor/students/${studentId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load student details');
        }
        
        const data = await response.json();
        const student = data.student;
        const exams = data.exams || [];
        
        // Build student details HTML (FERPA compliant - only educational info)
        // Match the styling of student cards for consistency
        let html = `
            <div class="student-details-header">
                <div class="student-info">
                    <div>
                        <div class="student-name">${escapeHtml(student.name)}</div>
                        <div class="student-id">ID: ${escapeHtml(student.student_id)}</div>
                        ${student.email ? `<div class="student-email">${escapeHtml(student.email)}</div>` : ''}
                        ${student.class_name ? `<div class="student-class" style="color: #718096; font-size: 0.85rem; margin-top: 4px;">Class: ${escapeHtml(student.class_name)}</div>` : ''}
                    </div>
                </div>
                <div class="student-assignments">
                    <span class="assignment-badge">${data.total_exams_assigned || 0} Exam${(data.total_exams_assigned || 0) !== 1 ? 's' : ''} Assigned</span>
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <h4 style="color: #2d3748; font-size: 1rem; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;">Exam Statistics</h4>
            </div>
            
            <div class="student-stats">
                <div class="stat-card">
                    <div class="stat-value">${data.completed_exams || 0}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.in_progress_exams || 0}</div>
                    <div class="stat-label">In Progress</div>
                </div>
            </div>
            
            <div class="student-exams-section">
                <h4>Exam Performance</h4>
        `;
        
        if (exams.length === 0) {
            html += '<p style="text-align: center; color: #666; padding: 20px;">No exams assigned yet.</p>';
        } else {
            html += '<div class="student-exams-list">';
            exams.forEach(exam => {
                const scoreColor = exam.is_completed 
                    ? (exam.percentage >= 70 ? '#28a745' : exam.percentage >= 50 ? '#ffc107' : '#dc3545')
                    : '#718096';
                const statusBadge = exam.is_completed 
                    ? '<span class="exam-status-badge completed">Completed</span>'
                    : exam.is_in_progress
                    ? '<span class="exam-status-badge in-progress">In Progress</span>'
                    : '<span class="exam-status-badge not-started">Not Started</span>';
                
                html += `
                    <div class="student-exam-item">
                        <div class="student-exam-header">
                            <div>
                                <strong>${escapeHtml(exam.exam_title)}</strong>
                                ${statusBadge}
                            </div>
                            ${exam.is_completed ? `<div class="exam-score" style="color: ${scoreColor};">
                                <strong>${exam.total_score} / ${exam.max_score}</strong> (${exam.percentage}%)
                            </div>` : ''}
                        </div>
                        <div class="student-exam-details">
                            <span>Domain: ${escapeHtml(exam.domain)}</span>
                            <span>Questions: ${exam.question_count}</span>
                            ${exam.started_at ? `<span>Started: ${new Date(exam.started_at).toLocaleDateString()}</span>` : ''}
                            ${exam.submitted_at ? `<span>Submitted: ${new Date(exam.submitted_at).toLocaleDateString()}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        html += '</div>';
        studentDetailsContent.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading student details:', error);
        studentDetailsContent.innerHTML = `<div class="error-message">Error loading student details: ${error.message}</div>`;
    }
}

// Close student details modal
function closeStudentDetailsModalFunc() {
    if (studentDetailsModal) {
        studentDetailsModal.style.display = 'none';
    }
}

// Load instructor's exams
async function loadInstructorExams() {
    if (!examsList) return;
    
    try {
        examsList.innerHTML = '<div class="loading-text">Loading exams...</div>';
        
        const response = await fetch(`${API_BASE}/instructor/exams`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load exams');
        }
        
        const data = await response.json();
        allExams = data.exams || [];
        
        if (allExams.length === 0) {
            examsList.innerHTML = '<div class="loading-text">No exams found. Create your first exam!</div>';
            return;
        }
        
        renderExams(allExams);
    } catch (error) {
        console.error('Error loading exams:', error);
        examsList.innerHTML = `<div class="loading-text" style="color: #e53e3e;">Error loading exams: ${error.message}</div>`;
    }
}

// Render exams list
function renderExams(exams) {
    if (!examsList) return;
    
    if (exams.length === 0) {
        examsList.innerHTML = '<div class="loading-text">No exams found. Create your first exam!</div>';
        return;
    }
    
    examsList.innerHTML = exams.map(exam => `
        <div class="exam-card" data-exam-id="${exam.id}">
            <div class="exam-title">${exam.title || 'Untitled Exam'}</div>
            <div class="exam-domain">${exam.domain}</div>
            <div class="exam-meta">
                <span>${exam.questions_count || 0} Questions</span>
                <span>${exam.submissions_count || 0} Assignment${(exam.submissions_count || 0) !== 1 ? 's' : ''}</span>
                <span>Created: ${new Date(exam.created_at).toLocaleDateString()}</span>
            </div>
            <div class="exam-actions-card">
                <button class="btn-assign" onclick="openAssignModal(${exam.id})" ${(exam.questions_count || 0) === 0 ? 'disabled title="Generate questions first"' : ''}>Assign to Students</button>
            </div>
        </div>
    `).join('');
}

// Open assign exam modal
window.openAssignModal = function(examId) {
    if (!assignExamModal || !assignExamSelect || !assignStudentsList) return;
    
    // Populate exam select
    assignExamSelect.innerHTML = '<option value="">Choose an exam...</option>';
    allExams.forEach(exam => {
        const option = document.createElement('option');
        option.value = exam.id;
        option.textContent = exam.title || `Exam ${exam.id}`;
        option.selected = exam.id === examId;
        assignExamSelect.appendChild(option);
    });
    
    // Populate students list with checkboxes
    assignStudentsList.innerHTML = allStudents.map(student => `
        <div class="assign-student-item">
            <input type="checkbox" id="student-${student.id}" value="${student.id}">
            <label for="student-${student.id}">${student.name} (${student.student_id})</label>
        </div>
    `).join('');
    
    assignExamModal.style.display = 'flex';
};

// Open create exam modal (Instructor)
function openInstructorCreateExamModal() {
    if (instructorCreateExamModal) {
        instructorCreateExamModal.style.display = 'flex';
        if (instructorExamSetupForm) {
            instructorExamSetupForm.style.display = 'block';
        }
        if (instructorSetupLoading) {
            instructorSetupLoading.style.display = 'none';
        }
    }
}

// Close create exam modal (Instructor)
function closeInstructorCreateExamModal() {
    if (instructorCreateExamModal) {
        instructorCreateExamModal.style.display = 'none';
        // Reset form
        if (instructorExamSetupForm) {
            instructorExamSetupForm.reset();
            instructorExamSetupForm.style.display = 'block';
        }
        if (instructorSetupLoading) {
            instructorSetupLoading.style.display = 'none';
        }
    }
}

// Handle exam setup for instructor (EXACTLY SAME AS STUDENT VERSION)
async function handleInstructorExamSetup(e) {
    e.preventDefault();
    console.log('DEBUG: Instructor exam form submitted!');
    
    try {
        const formData = new FormData(e.target);
        const setupData = {
            domain: formData.get('domain'),
            professor_instructions: formData.get('professor-instructions') || null,
            num_questions: parseInt(formData.get('num-questions'))
        };
        
        console.log('DEBUG: Instructor form data collected:', setupData);
        
        // Validate data
        if (!setupData.domain || !setupData.domain.trim()) {
            throw new Error('Domain is required');
        }
        
        // Show loading
        if (!instructorSetupLoading) {
            throw new Error('Loading element not found');
        }
        if (instructorExamSetupForm) {
            instructorExamSetupForm.style.display = 'none';
        }
        instructorSetupLoading.style.display = 'block';
        
        console.log('DEBUG: handleInstructorExamSetup - Starting exam generation request...', setupData);
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.log('DEBUG: Request timeout - aborting');
            controller.abort();
        }, 150000); // 150 second timeout (2.5 minutes)
        
        console.log('DEBUG: Sending fetch request to', `${API_BASE}/generate-questions`);
        // SAME API ENDPOINT AS STUDENT VERSION
        const response = await fetch(`${API_BASE}/generate-questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include', // Include credentials for instructor authentication
            body: JSON.stringify(setupData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('DEBUG: Received response:', response.status, response.statusText);
        
        if (!response.ok) {
            let error;
            try {
                error = await response.json();
            } catch {
                const errorText = await response.text();
                error = { detail: errorText || `HTTP ${response.status}: ${response.statusText}` };
            }
            console.error('DEBUG: Response error:', error);
            throw new Error(error.detail || 'Failed to generate questions');
        }
        
        const data = await response.json();
        console.log('DEBUG: Exam created successfully:', data);
        
        // Close modal and refresh exams list
        closeInstructorCreateExamModal();
        loadInstructorExams();
        
        alert('Exam created successfully! You can now assign it to students.');
        
    } catch (error) {
        console.error('DEBUG: Error in handleInstructorExamSetup:', error);
        console.error('DEBUG: Error stack:', error.stack);
        if (error.name === 'AbortError') {
            console.error('DEBUG: Request was aborted (timeout)');
            alert('Request timed out. The question generation is taking longer than expected. Please try again.');
        } else {
            console.error('DEBUG: Request failed:', error.message);
            alert('Failed to generate questions: ' + error.message);
        }
        // Show form again on error
        if (instructorExamSetupForm) {
            instructorExamSetupForm.style.display = 'block';
        }
        if (instructorSetupLoading) {
            instructorSetupLoading.style.display = 'none';
        }
    }
}

// Close assign modal
function closeAssignModalFunc() {
    if (assignExamModal) {
        assignExamModal.style.display = 'none';
    }
}


// Handle exam assignment
async function handleAssignExam() {
    const examId = assignExamSelect.value;
    const selectedStudents = Array.from(assignStudentsList.querySelectorAll('input[type="checkbox"]:checked'))
        .map(cb => parseInt(cb.value));
    
    if (!examId) {
        alert('Please select an exam');
        return;
    }
    
    if (selectedStudents.length === 0) {
        alert('Please select at least one student');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/instructor/assign-exam`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                exam_id: parseInt(examId),
                student_ids: selectedStudents
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to assign exam');
        }
        
        const data = await response.json();
        alert(data.message || `Exam assigned to ${selectedStudents.length} student(s) successfully!`);
        closeAssignModalFunc();
        // Reload data to show updated assignment counts
        loadAllStudents();
        loadInstructorExams();
    } catch (error) {
        console.error('Error assigning exam:', error);
        alert(`Error: ${error.message || 'Failed to assign exam. Please try again.'}`);
    }
}


// Search students
if (studentSearch) {
    studentSearch.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filtered = allStudents.filter(student => 
            student.name.toLowerCase().includes(searchTerm) ||
            student.student_id.toLowerCase().includes(searchTerm) ||
            (student.email && student.email.toLowerCase().includes(searchTerm))
        );
        renderStudents(filtered);
    });
}

// ============================================================================
// Student Dashboard Functions
// ============================================================================

// Load assigned exams for dashboard notifications (top card)
async function loadAssignedExams() {
    if (!assignedNotificationsContainer && !assignedBadge) return;

    try {
        if (assignedNotificationsContainer) {
            assignedNotificationsContainer.innerHTML = '<div class="loading">Loading assigned exams...</div>';
        }

        const response = await fetch(`${API_BASE}/my-exams/assigned`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load assigned exams');
        }

        const data = await response.json();
        const exams = data.exams || [];

        if (assignedBadge) {
            assignedBadge.textContent = exams.length;
        }

        if (!assignedNotificationsContainer) return;

        if (exams.length === 0) {
            assignedNotificationsContainer.innerHTML = '<div class="loading-text">No assigned exams</div>';
            return;
        }

        assignedNotificationsContainer.innerHTML = exams.map(exam => {
            const isCompleted = !!exam.submitted_at;
            // Rely on backend's is_in_progress flag (which checks for answers)
            const isInProgress = exam.is_in_progress === true;
            const isNew = !isCompleted && !isInProgress;

            const statusClass = isNew ? 'new' : isInProgress ? 'in-progress' : 'completed';
            const statusText = isNew ? 'Start' : isInProgress ? 'In Progress' : 'Completed';

            return `
                <div class="notification-item ${isNew ? 'new' : ''}">
                    <div class="notification-info">
                        <div class="notification-title">${exam.title}</div>
                        <div class="notification-meta">
                            ${exam.domain} • ${exam.question_count || 0} Questions
                            ${exam.instructor_name ? `• Instructor: ${exam.instructor_name}` : '• Instructor: Not specified'}
                            ${exam.class_name ? `• Class: ${exam.class_name}` : '• Class: Not assigned'}
                            ${exam.started_at ? `• Started: ${new Date(exam.started_at).toLocaleDateString()}` : ''}
                        </div>
                        <span class="exam-item-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="notification-actions">
                        ${isInProgress
                            ? `<button class="btn btn-primary btn-sm" onclick="resumeExam('${exam.exam_id}')">Continue</button>`
                            : isCompleted
                                ? `<button class="btn btn-secondary btn-sm" onclick="viewExamResults('${exam.exam_id}')">View Results</button>`
                                : `<button class="btn btn-primary btn-sm" onclick="startAssignedExam('${exam.exam_id}')">Start Exam</button>`
                        }
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading assigned exams:', error);
        if (assignedNotificationsContainer) {
            assignedNotificationsContainer.innerHTML = '<div class="loading-text" style="color:#e53e3e;">Error loading assigned exams</div>';
        }
    }
}

// Load assigned exams for the Assigned Exams tab
async function loadAssignedExamsList() {
    if (!assignedExamsContainer) return;

    try {
        assignedExamsContainer.innerHTML = '<div class="loading">Loading assigned exams...</div>';

        const response = await fetch(`${API_BASE}/my-exams/assigned`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load assigned exams');
        }

        const data = await response.json();
        const exams = data.exams || [];

        if (exams.length === 0) {
            assignedExamsContainer.innerHTML = '<div class="loading-text">No assigned exams. Your instructor will assign exams here.</div>';
            return;
        }

        // Debug: log exam data to see what we're receiving
        console.log('Assigned exams data:', exams);

        assignedExamsContainer.innerHTML = exams.map(exam => {
            const isCompleted = !!exam.submitted_at;
            // Rely on backend's is_in_progress flag (which checks for answers)
            const isInProgress = exam.is_in_progress === true;
            const isNew = !isCompleted && !isInProgress;

            const statusClass = isNew ? 'new' : isInProgress ? 'in-progress' : 'completed';
            const statusText = isNew ? 'Start' : isInProgress ? 'In Progress' : 'Completed';

            return `
                <div class="exam-list-item ${isNew ? 'new' : ''}">
                    <div class="exam-item-info">
                        <div class="exam-item-title">${exam.title}</div>
                        <div class="exam-item-domain">${exam.domain}</div>
                        <div class="exam-item-meta">
                            <span>${exam.question_count || 0} Questions</span>
                            ${exam.instructor_name ? `<span>Instructor: ${exam.instructor_name}</span>` : '<span>Instructor: Not specified</span>'}
                            ${exam.class_name ? `<span>Class: ${exam.class_name}</span>` : '<span>Class: Not assigned</span>'}
                            ${exam.started_at ? `<span>Started: ${new Date(exam.started_at).toLocaleDateString()}</span>` : ''}
                            ${exam.submitted_at ? `<span>Submitted: ${new Date(exam.submitted_at).toLocaleDateString()}</span>` : ''}
                        </div>
                        <span class="exam-item-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="exam-item-actions">
                        ${isInProgress
                            ? `<button class="btn btn-primary" onclick="resumeExam('${exam.exam_id}')">Continue Exam</button>`
                            : isCompleted
                                ? `<button class="btn btn-secondary" onclick="viewExamResults('${exam.exam_id}')">View Results</button>`
                                : `<button class="btn btn-primary" onclick="startAssignedExam('${exam.exam_id}')">Start Exam</button>`
                        }
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading assigned exams (list):', error);
        assignedExamsContainer.innerHTML = '<div class="loading-text" style="color:#e53e3e;">Error loading assigned exams</div>';
    }
}

// Load in-progress exams for the dashboard card
async function loadDashboardInProgressExams() {
    if (!dashboardInProgressContainer) return;

    try {
        dashboardInProgressContainer.innerHTML = '<div class="loading">Loading in-progress exams...</div>';

        const response = await fetch(`${API_BASE}/my-exams/in-progress`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load in-progress exams');
        }

        const data = await response.json();
        const exams = data.exams || [];

        if (exams.length === 0) {
            dashboardInProgressContainer.innerHTML = '<div class="loading-text">No in-progress exams. Start a new exam to begin!</div>';
            return;
        }

        dashboardInProgressContainer.innerHTML = exams.map(exam => `
            <div class="exam-list-item">
                <div class="exam-item-info">
                    <div class="exam-item-title">${exam.title}</div>
                    <div class="exam-item-domain">${exam.domain}</div>
                    <div class="exam-item-meta">
                        <span>${exam.answered_count}/${exam.question_count} Questions Answered</span>
                        <span>Progress: ${exam.progress_percentage}%</span>
                        ${exam.started_at ? `<span>Started: ${new Date(exam.started_at).toLocaleDateString()}</span>` : ''}
                    </div>
                    <span class="exam-item-status in-progress">In Progress</span>
                </div>
                <div class="exam-item-actions">
                    <button class="btn btn-primary" onclick="resumeExam('${exam.exam_id}')">Continue Exam</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading in-progress exams for dashboard:', error);
        dashboardInProgressContainer.innerHTML = '<div class="loading-text" style="color:#e53e3e;">Error loading in-progress exams</div>';
    }
}

// ============================================================================
// Student Dashboard Tab Functions
// ============================================================================

// Tab navigation
window.showTab = function(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const tabContent = document.getElementById(`${tabName}-tab`);
    const tabBtn = document.querySelector(`[data-tab="${tabName}"]`);
    
    if (tabContent) {
        tabContent.classList.add('active');
    }
    if (tabBtn) {
        tabBtn.classList.add('active');
    }
    
    // Load data for specific tabs
    if (tabName === 'practice') {
        const form = document.getElementById('exam-setup-form');
        const loading = document.getElementById('setup-loading');
        
        // Only reset form/loading if we're not actively generating
        // Active generation = loading is block AND form is none
        if (form && loading) {
            const isGenerating = loading.style.display === 'block' && 
                                (form.style.display === 'none' || form.style.display === '');
            
            if (!isGenerating) {
                // Not generating, so show form and hide loading
                form.style.display = 'block';
                loading.style.display = 'none';
            }
            // If generating, leave it as is (loading visible, form hidden)
        }
        
        // Load exactly like the original setup section
        loadInProgressExams();
        loadPastExams();
    } else if (tabName === 'assigned') {
        loadAssignedExamsList();
    }
};

// Event listeners for tab buttons
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = e.target.getAttribute('data-tab');
            if (tabName) {
                showTab(tabName);
            }
        });
    });
});

// Event listeners for instructor dashboard
if (changeClassBtn) {
    changeClassBtn.addEventListener('click', changeClass);
}

if (closeAssignModal) {
    closeAssignModal.addEventListener('click', closeAssignModalFunc);
}

if (cancelAssign) {
    cancelAssign.addEventListener('click', closeAssignModalFunc);
}

if (confirmAssign) {
    confirmAssign.addEventListener('click', handleAssignExam);
}

// Instructor create exam modal handlers
if (createExamBtn) {
    createExamBtn.addEventListener('click', openInstructorCreateExamModal);
}

if (closeInstructorCreateModal) {
    closeInstructorCreateModal.addEventListener('click', closeInstructorCreateExamModal);
}

if (cancelInstructorCreate) {
    cancelInstructorCreate.addEventListener('click', closeInstructorCreateExamModal);
}

if (instructorExamSetupForm) {
    instructorExamSetupForm.addEventListener('submit', handleInstructorExamSetup);
}

// Close instructor create exam modal when clicking outside
if (instructorCreateExamModal) {
    instructorCreateExamModal.addEventListener('click', (e) => {
        if (e.target === instructorCreateExamModal) {
            closeInstructorCreateExamModal();
        }
    });
}

// Instructor create exam modal handlers
if (createExamBtn) {
    createExamBtn.addEventListener('click', openInstructorCreateExamModal);
}

if (closeInstructorCreateModal) {
    closeInstructorCreateModal.addEventListener('click', closeInstructorCreateExamModal);
}

if (cancelInstructorCreate) {
    cancelInstructorCreate.addEventListener('click', closeInstructorCreateExamModal);
}

if (instructorExamSetupForm) {
    instructorExamSetupForm.addEventListener('submit', handleInstructorExamSetup);
}

// Close instructor create exam modal when clicking outside
if (instructorCreateExamModal) {
    instructorCreateExamModal.addEventListener('click', (e) => {
        if (e.target === instructorCreateExamModal) {
            closeInstructorCreateExamModal();
        }
    });
}

if (closeStudentDetailsModal) {
    closeStudentDetailsModal.addEventListener('click', closeStudentDetailsModalFunc);
}

if (closeStudentDetails) {
    closeStudentDetails.addEventListener('click', closeStudentDetailsModalFunc);
}

if (studentDetailsModal) {
    studentDetailsModal.addEventListener('click', (e) => {
        if (e.target === studentDetailsModal) {
            closeStudentDetailsModalFunc();
        }
    });
}

if (instructorLogoutBtn) {
    instructorLogoutBtn.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE}/logout`, {
                method: 'POST',
                credentials: 'include'
            });
            currentUser = null;
            showSection('login-section');
        } catch (error) {
            console.error('Logout error:', error);
            currentUser = null;
            showSection('login-section');
        }
    });
}

// Close modals when clicking outside
if (assignExamModal) {
    assignExamModal.addEventListener('click', (e) => {
        if (e.target === assignExamModal) {
            closeAssignModalFunc();
        }
    });
}


// Initialize app
init();
