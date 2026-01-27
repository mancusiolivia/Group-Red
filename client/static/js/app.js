// Global state
let currentExam = null;
let currentQuestionIndex = 0;
let studentResponses = {};
let originalPrompt = null; // Store the original prompt used to generate questions
let gradingResults = {};  // Store grading results with timestamps
let disputes = {};  // Store dispute data
let examTimer = null;  // Exam timer interval
let examTimeRemaining = null;  // Time remaining in seconds
let examTimeLimit = null;  // Total time limit in seconds
let disputeUpdateTimers = {};  // Timers for updating dispute buttons

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
examSetupForm.addEventListener('submit', handleExamSetup);
prevButton.addEventListener('click', () => navigateQuestion(-1));
nextButton.addEventListener('click', () => navigateQuestion(1));
submitExamButton.addEventListener('click', handleSubmitExam);
newExamButton.addEventListener('click', () => {
    resetApp();
    showSection('setup-section');
});
retryQuestionButton.addEventListener('click', handleRetryQuestion);
regenerateQuestionsButton.addEventListener('click', handleRegenerateQuestions);
regenerateQuestionsExamButton.addEventListener('click', handleRegenerateQuestions);


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
        if (error.name === 'AbortError') {
            showError('Request timed out. The question generation is taking longer than expected. Please try again.');
        } else {
            showError('Failed to generate questions: ' + error.message);
        }
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
    
    // Start exam timer (optional - can be set per exam)
    // For now, we'll use a default 2 hours per question, or no limit if not set
    if (currentExam.time_limit_seconds) {
        startExamTimer(currentExam.time_limit_seconds);
    } else {
        // Default: 2 hours total for the exam
        const defaultTime = currentExam.questions.length * 7200; // 2 hours per question
        startExamTimer(defaultTime);
    }
    
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

// Start exam timer
function startExamTimer(totalSeconds) {
    // Clear any existing timer
    if (examTimer) {
        clearInterval(examTimer);
    }
    
    examTimeLimit = totalSeconds;
    examTimeRemaining = totalSeconds;
    
    const timerDisplay = document.getElementById('timer-display');
    if (!timerDisplay) return;
    
    // Update timer display immediately
    updateTimerDisplay();
    
    // Update every second
    examTimer = setInterval(() => {
        examTimeRemaining--;
        updateTimerDisplay();
        
        // Auto-submit when time runs out
        if (examTimeRemaining <= 0) {
            clearInterval(examTimer);
            alert('Time is up! Your exam will be submitted automatically.');
            handleSubmitExam();
        }
    }, 1000);
}

// Update timer display
function updateTimerDisplay() {
    const timerDisplay = document.getElementById('timer-display');
    if (!timerDisplay) return;
    
    if (examTimeRemaining === null) {
        timerDisplay.textContent = '--:--';
        return;
    }
    
    const hours = Math.floor(examTimeRemaining / 3600);
    const minutes = Math.floor((examTimeRemaining % 3600) / 60);
    const seconds = examTimeRemaining % 60;
    
    let display = '';
    if (hours > 0) {
        display = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
        display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    timerDisplay.textContent = display;
    
    // Change color when time is running low
    const timerContainer = document.getElementById('exam-timer');
    if (timerContainer) {
        if (examTimeRemaining < 300) { // Less than 5 minutes
            timerContainer.classList.add('timer-warning');
        } else {
            timerContainer.classList.remove('timer-warning');
        }
        
        if (examTimeRemaining < 60) { // Less than 1 minute
            timerContainer.classList.add('timer-critical');
        } else {
            timerContainer.classList.remove('timer-critical');
        }
    }
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
            <div class="textarea-wrapper">
                <textarea 
                    id="response-${question.question_id}" 
                    class="response-textarea"
                    placeholder="Type your essay response here..."
                    data-question-id="${question.question_id}"
                >${studentResponses[question.question_id]?.response_text || ''}</textarea>
                <div class="word-count" id="word-count-${question.question_id}">
                    <span class="word-count-label">Words:</span>
                    <span class="word-count-value">0</span>
                </div>
            </div>
        </div>
    `;
    
    // Add input listener with word count
    const textarea = card.querySelector(`#response-${question.question_id}`);
    const wordCountElement = card.querySelector(`#word-count-${question.question_id} .word-count-value`);
    
    // Update word count function
    const updateWordCount = () => {
        const questionId = textarea.dataset.questionId;
        if (!studentResponses[questionId].start_time) {
            studentResponses[questionId].start_time = Date.now();
        }
        studentResponses[questionId].response_text = textarea.value;
        
        // Calculate word count
        const text = textarea.value.trim();
        const wordCount = text === '' ? 0 : text.split(/\s+/).filter(word => word.length > 0).length;
        if (wordCountElement) {
            wordCountElement.textContent = wordCount;
        }
    };
    
    textarea.addEventListener('input', updateWordCount);
    textarea.addEventListener('paste', () => setTimeout(updateWordCount, 10));
    
    // Initialize word count
    updateWordCount();
    
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
        
        // Store results with timestamps for dispute checking
        results.forEach((result, index) => {
            if (!result.error) {
                const question = currentExam.questions.find(q => q.question_id === result.question_id);
                if (question) {
                    gradingResults[result.question_id] = {
                        ...result,
                        graded_at: new Date().toISOString(),
                        question_index: index
                    };
                }
            }
        });
        
        // Load existing disputes for this exam
        await loadDisputes();
        
        // Save state to localStorage
        saveStateToStorage();
        
        // Display results
        displayResults(results);
        showSection('results-section');
        
        // Start dispute button update timers
        startDisputeButtonTimers();
        
    } catch (error) {
        showError('Failed to submit exam: ' + error.message);
        submitExamButton.disabled = false;
        submitExamButton.textContent = 'Submit All Responses';
    }
}

// Display grading results
function displayResults(results) {
    const container = document.getElementById('results-container');
    if (!container) {
        console.error('Results container not found!');
        return;
    }
    
    if (!currentExam || !currentExam.questions) {
        console.error('Current exam or questions not found!', { currentExam });
        container.innerHTML = '<div class="error-message"><p>Error: Exam data not found. Please refresh the page.</p></div>';
        return;
    }
    
    try {
        container.innerHTML = '';
    } catch (error) {
        console.error('Error clearing results container:', error);
        return;
    }
    
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
        if (!question) {
            console.error(`Question not found for result: ${result.question_id}`);
            container.innerHTML += `
                <div class="error-message">
                    <h3>Question ${index + 1} - Error</h3>
                    <p>Question data not found</p>
                </div>
            `;
            return;
        }
        
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
            
            <div class="dispute-section" id="dispute-section-${result.question_id}">
                <div id="dispute-button-container-${result.question_id}">
                    ${getDisputeButton(result.question_id, result)}
                </div>
            </div>
        `;
        try {
            container.appendChild(resultCard);
        } catch (error) {
            console.error(`Error appending result card for question ${index + 1}:`, error);
        }
    });
    
    // Add overall summary
    if (results.length > 1) {
        try {
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
        } catch (error) {
            console.error('Error adding summary:', error);
        }
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
    // Clear exam timer
    if (examTimer) {
        clearInterval(examTimer);
        examTimer = null;
    }
    
    // Clear dispute update timers
    Object.values(disputeUpdateTimers).forEach(timer => clearInterval(timer));
    disputeUpdateTimers = {};
    
    examTimeRemaining = null;
    examTimeLimit = null;
    
    currentExam = null;
    currentQuestionIndex = 0;
    studentResponses = {};
<<<<<<< HEAD
    originalPrompt = null;
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
        const response = await fetch(`${API_BASE}/generate-questions`, {
=======
    gradingResults = {};
    disputes = {};
    
    // Clear saved state
    clearSavedState();
}


// Load disputes for current exam
async function loadDisputes() {
    try {
        const response = await fetch(`${API_BASE}/disputes?exam_id=${currentExam.exam_id}`);
        if (response.ok) {
            const data = await response.json();
            data.disputes.forEach(dispute => {
                disputes[dispute.dispute_id] = dispute;
            });
        }
    } catch (error) {
        console.error('Failed to load disputes:', error);
    }
}

// Dispute functionality
function getDisputeButton(questionId, result) {
    const gradingResult = gradingResults[questionId];
    if (!gradingResult) return '';
    
    // Check if enough time has passed (30 seconds = 30000 ms for testing)
    const gradedAt = new Date(gradingResult.graded_at);
    const timeSinceGrading = Date.now() - gradedAt.getTime();
    const delayRequired = 30000;  // 30 seconds in milliseconds (for testing)
    const canDispute = timeSinceGrading >= delayRequired;
    
    // Check if already disputed
    const existingDispute = Object.values(disputes).find(d => d.question_id === questionId);
    
    if (existingDispute) {
        try {
            const status = existingDispute.status || 'pending';
            const statusClass = status === 'regraded' ? 'success' : status === 'rejected' ? 'error' : 'pending';
            const complaintText = existingDispute.complaint_text || 'No complaint text available';
            const assessment = existingDispute.assessment || {};
            
            return `
                <div class="dispute-status dispute-${statusClass}">
                    <h4>Dispute Status: ${status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}</h4>
                    <p><strong>Your Complaint:</strong> ${escapeHtml(complaintText)}</p>
                    ${assessment.assessment ? `
                        <div class="assessment-box">
                            <p><strong>AI Assessment:</strong> ${escapeHtml(assessment.assessment)}</p>
                            ${assessment.validity_score !== undefined ? `<p><strong>Validity Score:</strong> ${(assessment.validity_score * 100).toFixed(1)}%</p>` : ''}
                            ${assessment.recommendation ? `<p><strong>Recommendation:</strong> ${escapeHtml(assessment.recommendation)}</p>` : ''}
                        </div>
                    ` : ''}
                    ${status === 'regraded' && existingDispute.new_grade ? `
                        <div class="regrade-result">
                            <h4>Regraded Result</h4>
                            <p><strong>New Score:</strong> ${existingDispute.new_grade.total_score.toFixed(1)}</p>
                            <p><strong>Previous Score:</strong> ${result.total_score.toFixed(1)}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (error) {
            console.error('Error rendering dispute status:', error);
            return '<p>Error displaying dispute status</p>';
        }
    }
    
    if (!canDispute) {
        const remainingMs = delayRequired - timeSinceGrading;
        const remainingSeconds = Math.ceil(remainingMs / 1000);
        return `
            <button class="btn btn-secondary" disabled>
                Dispute Grade (Available in ${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''})
            </button>
            <p class="dispute-info">Disputes can only be submitted after at least 30 seconds have passed since grading to ensure thoughtful, well-reasoned complaints.</p>
        `;
    }
    
    return `
        <button class="btn btn-warning dispute-btn" onclick="showDisputeModal('${questionId}')">
            Dispute This Grade
        </button>
        <p class="dispute-info">You can dispute this grade if you believe there was an error in the grading.</p>
    `;
}

// Show dispute modal
function showDisputeModal(questionId) {
    const result = gradingResults[questionId];
    if (!result) return;
    
    const question = currentExam.questions.find(q => q.question_id === questionId);
    if (!question) return;
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'dispute-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeDisputeModal()">&times;</span>
            <h2>Dispute Grade - Question ${result.question_index + 1}</h2>
            <div class="dispute-context">
                <h3>Question:</h3>
                <p>${escapeHtml(question.question_text)}</p>
                <h3>Your Response:</h3>
                <p>${escapeHtml(studentResponses[questionId]?.response_text || '')}</p>
                <h3>Current Grade:</h3>
                <p>Total Score: ${result.total_score.toFixed(1)} / ${question.grading_rubric.total_points}</p>
                <div class="score-breakdown">
                    ${Object.entries(result.scores || {}).map(([dim, score]) => `
                        <div class="score-item">
                            <div class="label">${escapeHtml(dim)}</div>
                            <div class="value">${score.toFixed(1)}</div>
                        </div>
                    `).join('')}
                </div>
                <h3>Grading Explanation:</h3>
                <p>${escapeHtml(result.explanation || '')}</p>
            </div>
            <form id="dispute-form-${questionId}">
                <div class="form-group">
                    <label for="dispute-complaint">Explain why you believe this grade is incorrect:</label>
                    <textarea 
                        id="dispute-complaint-${questionId}" 
                        name="complaint" 
                        rows="6" 
                        required
                        placeholder="Provide specific reasons, reference the rubric, and point to specific parts of your answer that you believe were not properly evaluated..."
                    ></textarea>
                </div>
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="closeDisputeModal()">Cancel</button>
                    <button type="submit" class="btn btn-warning">Submit Dispute</button>
                </div>
            </form>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    // Add form submit event listener
    const form = document.getElementById(`dispute-form-${questionId}`);
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            submitDispute(e, questionId);
        });
    }
}

// Close dispute modal
function closeDisputeModal() {
    const modal = document.getElementById('dispute-modal');
    if (modal) {
        modal.remove();
    }
}

// Submit dispute
async function submitDispute(e, questionId) {
    e.preventDefault();
    
    console.log('Submitting dispute for question:', questionId);
    
    const complaintTextElement = document.getElementById(`dispute-complaint-${questionId}`);
    if (!complaintTextElement) {
        console.error('Could not find complaint textarea');
        showError('Could not find complaint field. Please try again.');
        return;
    }
    
    const complaintText = complaintTextElement.value.trim();
    if (!complaintText) {
        showError('Please provide a reason for disputing the grade.');
        return;
    }
    
    const result = gradingResults[questionId];
    if (!result) {
        console.error('Could not find grading result for question:', questionId);
        showError('Could not find grading result.');
        return;
    }
    
    if (!currentExam || !currentExam.exam_id) {
        console.error('Current exam not found');
        showError('Exam information not found. Please refresh the page.');
        return;
    }
    
    const form = document.getElementById(`dispute-form-${questionId}`);
    const submitButton = form ? form.querySelector('button[type="submit"]') : null;
    
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = 'Submitting...';
    }
    
    try {
        console.log('Sending dispute request:', {
            exam_id: currentExam.exam_id,
            question_id: questionId,
            complaint_text: complaintText.substring(0, 50) + '...'
        });
        
        const response = await fetch(`${API_BASE}/dispute-grade`, {
>>>>>>> main
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
<<<<<<< HEAD
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
        if (error.name === 'AbortError') {
            showError('Request timed out. The question generation is taking longer than expected. Please try again.');
        } else {
            showError('Failed to regenerate questions: ' + error.message);
        }
        document.getElementById('setup-loading').style.display = 'none';
        examSetupForm.style.display = 'block';
    }
=======
            body: JSON.stringify({
                exam_id: currentExam.exam_id,
                question_id: questionId,
                complaint_text: complaintText
            })
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('Dispute submission error:', error);
            throw new Error(error.detail || 'Failed to submit dispute');
        }
        
        const disputeResult = await response.json();
        console.log('Dispute submitted successfully:', disputeResult);
        
        // Store dispute
        disputes[disputeResult.dispute_id] = {
            dispute_id: disputeResult.dispute_id,
            question_id: questionId,
            complaint_text: complaintText,
            status: disputeResult.status,
            assessment: disputeResult.assessment
        };
        
        // Close modal
        closeDisputeModal();
        
        // Save state
        saveStateToStorage();
        
        // Refresh results display to show dispute status
        try {
            const results = Object.values(gradingResults).sort((a, b) => a.question_index - b.question_index);
            displayResults(results);
            startDisputeButtonTimers(); // Restart timers
            
            // Show success message
            const recommendation = disputeResult.assessment?.recommendation || 'review';
            const message = recommendation === 'regrade' 
                ? 'The AI has determined your dispute is valid and recommends regrading.' 
                : 'Your dispute will be reviewed by the professor.';
            showSuccess(`Dispute submitted successfully! ${message}`);
        } catch (error) {
            console.error('Error refreshing results display:', error);
            showError('Dispute submitted but failed to update display. Please refresh the page.');
        }
        
    } catch (error) {
        console.error('Error submitting dispute:', error);
        showError('Failed to submit dispute: ' + error.message);
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Dispute';
        }
    }
}

// Show success message
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    document.querySelector('.container').insertBefore(successDiv, document.querySelector('.container').firstChild);
    
    setTimeout(() => {
        successDiv.remove();
    }, 5000);
}

// Start timers to update dispute buttons
function startDisputeButtonTimers() {
    // Clear existing timers
    Object.values(disputeUpdateTimers).forEach(timer => clearInterval(timer));
    disputeUpdateTimers = {};
    
    // Start timer for each graded question
    Object.keys(gradingResults).forEach(questionId => {
        const timer = setInterval(() => {
            const container = document.getElementById(`dispute-button-container-${questionId}`);
            if (container) {
                const gradingResult = gradingResults[questionId];
                if (gradingResult) {
                    const question = currentExam?.questions.find(q => q.question_id === questionId);
                    if (question) {
                        const result = gradingResults[questionId];
                        container.innerHTML = getDisputeButton(questionId, result);
                    }
                } else {
                    clearInterval(timer);
                    delete disputeUpdateTimers[questionId];
                }
            } else {
                clearInterval(timer);
                delete disputeUpdateTimers[questionId];
            }
        }, 1000); // Update every second
        
        disputeUpdateTimers[questionId] = timer;
    });
}

// Save state to localStorage
function saveStateToStorage() {
    try {
        const state = {
            currentExam: currentExam,
            gradingResults: gradingResults,
            disputes: disputes,
            currentSection: document.querySelector('.section.active')?.id || 'setup-section'
        };
        localStorage.setItem('essayTestingState', JSON.stringify(state));
    } catch (error) {
        console.error('Failed to save state:', error);
    }
}

// Load state from localStorage
function loadStateFromStorage() {
    try {
        const savedState = localStorage.getItem('essayTestingState');
        if (savedState) {
            const state = JSON.parse(savedState);
            
            // Restore state if we have grading results (meaning exam was completed)
            if (state.gradingResults && Object.keys(state.gradingResults).length > 0) {
                currentExam = state.currentExam;
                gradingResults = state.gradingResults;
                disputes = state.disputes || {};
                
                // Restore results view
                if (state.currentSection === 'results-section') {
                    const results = Object.values(gradingResults).sort((a, b) => a.question_index - b.question_index);
                    displayResults(results);
                    showSection('results-section');
                    startDisputeButtonTimers();
                    return true; // State restored
                }
            }
        }
    } catch (error) {
        console.error('Failed to load state:', error);
    }
    return false; // No state to restore
}

// Clear saved state
function clearSavedState() {
    localStorage.removeItem('essayTestingState');
>>>>>>> main
}

// Initialize app
function init() {
    // Try to load saved state
    const stateRestored = loadStateFromStorage();
    
    if (!stateRestored) {
        // No saved state, show setup section
        showSection('setup-section');
    }
}

// Clear state when creating new exam
examSetupForm.addEventListener('submit', () => {
    clearSavedState();
});

// Initialize app
init();
