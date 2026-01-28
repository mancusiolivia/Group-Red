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
const setupSection = document.getElementById('setup-section');
const examSection = document.getElementById('exam-section');
const resultsSection = document.getElementById('results-section');
const loginForm = document.getElementById('login-form');
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
const pastExamsContainer = document.getElementById('past-exams-container');
const pastExamsList = document.getElementById('past-exams-list');
const inProgressExamsContainer = document.getElementById('in-progress-exams-container');
const viewPastExamsButton = document.getElementById('view-past-exams');
const backToSetupButton = document.getElementById('back-to-setup');

// Event Listeners
if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
    console.log('DEBUG: Login form event listener attached');
} else {
    console.error('DEBUG: Login form not found!');
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
        showSection('setup-section');
        loadPastExams();
    });
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
    showSection('setup-section');
    
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
                showSection('setup-section');
                loadInProgressExams();
                loadPastExams();
            }
        } else {
            showSection('login-section');
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showSection('login-section');
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
        currentUser = data;
        
        // Update UI
        updateUserDisplay();
        console.log('DEBUG: About to show setup-section');
        showSection('setup-section');
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
    // Hide all sections
    const allSections = ['login-section', 'setup-section', 'exam-section', 'results-section', 'past-exams-section'];
    allSections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.remove('active');
            section.style.display = 'none';
        }
    });
    
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        section.style.display = 'block';
        console.log('DEBUG: Section displayed:', sectionId);
        
        // If showing setup section, ensure form is visible and load past exams
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
        
        // Show loading
        const loadingEl = document.getElementById('setup-loading');
        if (!loadingEl) {
            throw new Error('Loading element not found');
        }
        loadingEl.style.display = 'block';
        examSetupForm.style.display = 'none';
        
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
        if (examSetupForm) examSetupForm.style.display = 'block';
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
    
    // Return to homepage
    showSection('setup-section');
    // Reload in-progress exams to show updated progress
    loadInProgressExams();
    loadPastExams();
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
        // If no prompt data, just go to setup form
        showSection('setup-section');
        return;
    }
    
    // Pre-fill the form with prompt data (for user visibility)
    document.getElementById('domain').value = promptData.domain || '';
    document.getElementById('professor-instructions').value = promptData.professor_instructions || '';
    document.getElementById('num-questions').value = promptData.num_questions || 1;
    
    // Show setup section with loading state
    showSection('setup-section');
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
        displayPastExams(submittedExams);
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
        pastExamsContainer.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams found. Complete an exam to see it here!</p>';
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
        displayPastExamsList(submittedExams);
    } catch (error) {
        console.error('Error loading past exams:', error);
        pastExamsList.innerHTML = '<div class="error-message">Failed to load past exams. Please try again.</div>';
    }
}

// Display past exams in dedicated section
function displayPastExamsList(exams) {
    if (!pastExamsList) return;
    
    if (exams.length === 0) {
        pastExamsList.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No past exams found. Complete an exam to see it here!</p>';
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

// Initialize app
init();
