// Global state
let currentExam = null;
let currentQuestionIndex = 0;
let studentResponses = {};

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

// Event Listeners
examSetupForm.addEventListener('submit', handleExamSetup);
prevButton.addEventListener('click', () => navigateQuestion(-1));
nextButton.addEventListener('click', () => navigateQuestion(1));
submitExamButton.addEventListener('click', handleSubmitExam);
newExamButton.addEventListener('click', () => {
    resetApp();
    showSection('setup-section');
});

// Initialize
function init() {
    showSection('setup-section');
}

// Show specific section
function showSection(sectionId) {
    setupSection.classList.remove('active');
    examSection.classList.remove('active');
    resultsSection.classList.remove('active');
    setupSection.style.display = 'none';
    examSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    const section = document.getElementById(sectionId);
    section.classList.add('active');
    section.style.display = 'block';
}

// Handle exam setup form submission
async function handleExamSetup(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const setupData = {
        domain: formData.get('domain'),
        professor_instructions: formData.get('professor-instructions') || null,
        num_questions: parseInt(formData.get('num-questions'))
    };
    
    // Show loading
    document.getElementById('setup-loading').style.display = 'block';
    examSetupForm.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/generate-questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(setupData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate questions');
        }
        
        const data = await response.json();
        currentExam = data;
        currentQuestionIndex = 0;
        studentResponses = {};
        
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
        showError('Failed to generate questions: ' + error.message);
        document.getElementById('setup-loading').style.display = 'none';
        examSetupForm.style.display = 'block';
    }
}

// Display exam
function displayExam() {
    if (!currentExam) return;
    
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
    currentExam = null;
    currentQuestionIndex = 0;
    studentResponses = {};
}

// Initialize app
init();
