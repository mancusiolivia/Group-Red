// Global state
let currentExam = null;
let currentQuestionIndex = 0;
let studentResponses = {};
let originalPrompt = null; // Store the original prompt used to generate questions

// API base URL
const API_BASE = '/api';

// DOM Elements
const setupSection = document.getElementById('setup-section');
const examSection = document.getElementById('exam-section');
const resultsSection = document.getElementById('results-section');
const examSetupForm = document.getElementById('exam-setup-form');
const questionsContainer = document.getElementById('questions-container');
const prevButton = document.getElementById('prev-question');
const nextButton = document.getElementById('next-question');
const submitExamButton = document.getElementById('submit-exam');
const newExamButton = document.getElementById('new-exam');
const retryQuestionButton = document.getElementById('retry-question');
const regenerateQuestionsButton = document.getElementById('regenerate-questions');
const regenerateQuestionsExamButton = document.getElementById('regenerate-questions-exam');

// Event Listeners
if (examSetupForm) {
    examSetupForm.addEventListener('submit', handleExamSetup);
    console.log('DEBUG: Form event listener attached');
} else {
    console.error('DEBUG: exam-setup-form element not found!');
}
prevButton.addEventListener('click', () => navigateQuestion(-1));
nextButton.addEventListener('click', () => navigateQuestion(1));
submitExamButton.addEventListener('click', handleSubmitExam);
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
    }
});
retryQuestionButton.addEventListener('click', handleRetryQuestion);
regenerateQuestionsButton.addEventListener('click', handleRegenerateQuestions);
regenerateQuestionsExamButton.addEventListener('click', handleRegenerateQuestions);

// Initialize
function init() {
    showSection('setup-section');
}

// Show specific section
function showSection(sectionId) {
    console.log('DEBUG: Showing section:', sectionId);
    setupSection.classList.remove('active');
    examSection.classList.remove('active');
    resultsSection.classList.remove('active');
    setupSection.style.display = 'none';
    examSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        section.style.display = 'block';
        console.log('DEBUG: Section displayed:', sectionId);
        
        // If showing setup section, ensure form is visible
        if (sectionId === 'setup-section') {
            const form = document.getElementById('exam-setup-form');
            const loading = document.getElementById('setup-loading');
            if (form) form.style.display = 'block';
            if (loading) loading.style.display = 'none';
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

// Display exam
function displayExam() {
    if (!currentExam) return;
    
    // Reset submit button to original state
    if (submitExamButton) {
        submitExamButton.disabled = false;
        submitExamButton.textContent = 'Submit All Responses';
    }
    
    // Update header
    document.getElementById('exam-domain').textContent = currentExam.questions[0]?.domain || 'Exam';
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
    `;
    
    // Add input listener
    const textarea = card.querySelector(`#response-${question.question_id}`);
    textarea.addEventListener('input', (e) => {
        const questionId = e.target.dataset.questionId;
        if (!studentResponses[questionId].start_time) {
            studentResponses[questionId].start_time = Date.now();
        }
        studentResponses[questionId].response_text = e.target.value;
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
        
        // Display results
        displayResults(results);
        showSection('results-section');
        
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
            <p><strong>Question:</strong> ${escapeHtml(question.question_text)}</p>
            
            <div class="score-breakdown">
                ${Object.entries(result.scores || {}).map(([dim, score]) => `
                    <div class="score-item">
                        <div class="label">${escapeHtml(dim)}</div>
                        <div class="value">${score.toFixed(1)}</div>
                    </div>
                `).join('')}
            </div>
            
            <div class="total-score">
                <div class="label">Total Score</div>
                <div class="value">${(result.total_score || 0).toFixed(1)} / ${question?.grading_rubric?.total_points || 0}</div>
            </div>
            
            <div class="explanation-box">
                <h4>Grading Explanation</h4>
                <p>${escapeHtml(result.explanation || 'No explanation provided.')}</p>
            </div>
            
            <div class="feedback-box">
                <h4>Feedback</h4>
                <p>${escapeHtml(result.feedback || 'No feedback provided.')}</p>
            </div>
        `;
        container.appendChild(resultCard);
    });
    
    // Add overall summary
    if (results.length > 1) {
        const summary = document.createElement('div');
        summary.className = 'grade-result';
        summary.innerHTML = `
            <h3>Overall Summary</h3>
            <div class="total-score">
                <div class="label">Total Score</div>
                <div class="value">${totalScore.toFixed(1)} / ${maxScore}</div>
            </div>
            <div class="total-score" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                <div class="label">Percentage</div>
                <div class="value">${((totalScore / maxScore) * 100).toFixed(1)}%</div>
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

// Handle retry question - go back to exam with same questions but clear responses
function handleRetryQuestion() {
    if (!currentExam) {
        showError('No exam to retry. Please create a new exam.');
        return;
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

// Initialize app
init();
