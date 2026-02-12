// Global state
let currentExam = null;
let currentQuestionIndex = 0;
let studentResponses = {};
let originalPrompt = null; // Store the original prompt used to generate questions
let currentResults = null;          // grading results array for Results pagination
let currentResultsQuestionIndex = 0; // index of the currently-shown result question

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
const resultsPrevBtn = document.getElementById('results-prev-question');
const resultsNextBtn = document.getElementById('results-next-question');
if (resultsPrevBtn) resultsPrevBtn.addEventListener('click', () => navigateResultsQuestion(-1));
if (resultsNextBtn) resultsNextBtn.addEventListener('click', () => navigateResultsQuestion(1));

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

// ---------------------------------------------------------------------------
// Results pagination  (mirrors the exam-taking question navigation pattern)
// ---------------------------------------------------------------------------

// Display grading results — static header + paginated per-question section
function displayResults(results) {
    currentResults = results;
    currentResultsQuestionIndex = 0;

    // --- Compute totals for the overall summary ---
    let totalScore = 0;
    let maxScore = 0;
    results.forEach((result) => {
        if (result.error) return;
        const question = currentExam.questions.find(q => q.question_id === result.question_id);
        totalScore += result.total_score || 0;
        maxScore += question?.grading_rubric?.total_points || 0;
    });

    // --- Static header: Overall Summary (always visible) ---
    // Use results-header if it exists (new HTML), fall back to results-container (old cached HTML)
    const header = document.getElementById('results-header') || document.getElementById('results-container');
    if (header) {
        header.innerHTML = '';
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
                    <div class="value">${maxScore ? ((totalScore / maxScore) * 100).toFixed(1) : '0'}%</div>
                </div>
            `;
            header.appendChild(summary);
        }
    }

    // --- Render the first question and set up nav ---
    updateResultsQuestionCounter();
    updateResultsNavigationButtons();
    renderResultsQuestion(currentResultsQuestionIndex);
}

// Render one result question into the paginated container
function renderResultsQuestion(index) {
    // Use results-question-container if it exists (new HTML), fall back to results-container (old cached HTML)
    const container = document.getElementById('results-question-container') || document.getElementById('results-container');
    if (!currentResults || !container) return;
    const result = currentResults[index];
    if (!result) return;

    // Error result
    if (result.error) {
        container.innerHTML = `
            <div class="error-message">
                <h3>Question ${index + 1} - Error</h3>
                <p>${escapeHtml(result.error)}</p>
            </div>
        `;
        container.scrollTop = 0;
        return;
    }

    const question = currentExam.questions.find(q => q.question_id === result.question_id);
    const rubricBreakdownHtml = buildRubricBreakdownHtml(result.rubric_breakdown || []);
    const studentResponseHtml = buildStudentResponseHtml(result, question);
    const issuesListHtml = buildIssuesListHtml(result.annotations || []);

    container.innerHTML = `
        <div class="grade-result" id="results-question-card">
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

            ${rubricBreakdownHtml}

            ${studentResponseHtml}

            ${issuesListHtml}

            <div class="explanation-box">
                <h4>Grading Explanation</h4>
                <p>${escapeHtml(result.explanation || 'No explanation provided.')}</p>
            </div>

            <div class="feedback-box">
                <h4>Feedback</h4>
                <p>${escapeHtml(result.feedback || 'No feedback provided.')}</p>
            </div>
        </div>
    `;

    // Wire up annotation highlight → issue-card scroll within this card
    const card = container.querySelector('#results-question-card');
    if (card) setupHighlightClickHandlers(card);

    // Reset scroll position of the paginated container to top
    container.scrollTop = 0;
}

// Navigate between result questions (prev / next)
function navigateResultsQuestion(direction) {
    if (!currentResults || currentResults.length === 0) return;
    const newIndex = currentResultsQuestionIndex + direction;
    if (newIndex < 0 || newIndex >= currentResults.length) return;

    currentResultsQuestionIndex = newIndex;
    renderResultsQuestion(currentResultsQuestionIndex);
    updateResultsQuestionCounter();
    updateResultsNavigationButtons();
}

// Update Results prev/next button disabled state
function updateResultsNavigationButtons() {
    const prevBtn = document.getElementById('results-prev-question');
    const nextBtn = document.getElementById('results-next-question');
    if (prevBtn) prevBtn.disabled = !currentResults || currentResults.length === 0 || currentResultsQuestionIndex === 0;
    if (nextBtn) nextBtn.disabled = !currentResults || currentResults.length === 0 || currentResultsQuestionIndex === currentResults.length - 1;
}

// Update "Question X of Y" counter in Results
function updateResultsQuestionCounter() {
    const el = document.getElementById('results-question-counter');
    if (!el) return;
    const total = currentResults ? currentResults.length : 0;
    el.textContent = total ? `Question ${currentResultsQuestionIndex + 1} of ${total}` : 'Question 1 of 1';
}

// Build rubric breakdown panels HTML
function buildRubricBreakdownHtml(rubricBreakdown) {
    if (!rubricBreakdown || rubricBreakdown.length === 0) {
        return '';
    }
    
    const panelsHtml = rubricBreakdown.map(dim => {
        const markdownsHtml = dim.markdowns && dim.markdowns.length > 0
            ? `<div class="rubric-section">
                <h5>Mark-downs</h5>
                <div class="rubric-markdowns">
                    <ul>
                        ${dim.markdowns.map(md => `<li>${escapeHtml(md)}</li>`).join('')}
                    </ul>
                </div>
            </div>`
            : '';
        
        const improvementsHtml = dim.improvements && dim.improvements.length > 0
            ? `<div class="rubric-section">
                <h5>Improvements</h5>
                <div class="rubric-improvements">
                    <ul>
                        ${dim.improvements.map(imp => `<li>${escapeHtml(imp)}</li>`).join('')}
                    </ul>
                </div>
            </div>`
            : '';
        
        return `
            <div class="rubric-panel">
                <div class="rubric-panel-header">
                    <h4>${escapeHtml(dim.dimension)}</h4>
                    <span class="rubric-panel-score">${dim.score}/${dim.max_score}</span>
                </div>
                <div class="rubric-section">
                    <h5>Criteria</h5>
                    <div class="rubric-criteria">${escapeHtml(dim.criteria || '')}</div>
                </div>
                ${markdownsHtml}
                ${improvementsHtml}
            </div>
        `;
    }).join('');
    
    return `<div class="rubric-panels">${panelsHtml}</div>`;
}

// Build student response HTML with annotations highlighted
function buildStudentResponseHtml(result, question) {
    // Get the original response text from studentResponses
    const responseData = studentResponses[result.question_id];
    if (!responseData || !responseData.response_text) {
        return '';
    }
    
    const originalText = responseData.response_text;
    const annotations = result.annotations || [];
    
    // If no annotations, just show the plain text
    if (annotations.length === 0) {
        return `
            <div class="student-response-section">
                <h4>Your Response</h4>
                <div class="student-response-text">${escapeHtml(originalText)}</div>
            </div>
        `;
    }
    
    // Highlight the response text with annotations
    const highlightedText = highlightResponseText(originalText, annotations);
    
    return `
        <div class="student-response-section">
            <h4>Your Response</h4>
            <div class="student-response-text">${highlightedText}</div>
        </div>
    `;
}

// Highlight response text with annotation quotes
function highlightResponseText(text, annotations) {
    if (!annotations || annotations.length === 0) {
        return escapeHtml(text);
    }
    
    // Create a list of quotes to find with their annotation data
    const quotesToFind = annotations.map(ann => ({
        quote: ann.quote,
        id: ann.id,
        severity: ann.severity
    })).filter(q => q.quote && q.quote.trim());
    
    // Sort by quote length (longest first) to handle overlapping quotes
    quotesToFind.sort((a, b) => b.quote.length - a.quote.length);
    
    // Build normalised text + index map once for Tier 2/3 matching
    const { normStr: normText, origIndices } = buildIndexMap(text);
    const normTextLower = normText.toLowerCase();

    // Track which parts of the text have been highlighted
    let highlightedRanges = [];
    let replacements = [];
    
    quotesToFind.forEach(quoteData => {
        const quote = quoteData.quote;
        let startIdx = -1;
        let endIdx = -1;

        // --- Tier 1: exact match (fast path) ---
        startIdx = text.indexOf(quote);
        if (startIdx !== -1) {
            endIdx = startIdx + quote.length;
        }

        // --- Tier 2: normalised match ---
        if (startIdx === -1) {
            const normQuote = normalizeForMatch(quote);
            const normPos = normText.indexOf(normQuote);
            if (normPos !== -1) {
                startIdx = origIndices[normPos];
                // Map the end position: find the original index that corresponds
                // to the last character of the normalised match, then +1
                const normEnd = normPos + normQuote.length - 1;
                endIdx = (normEnd + 1 < origIndices.length)
                    ? origIndices[normEnd + 1]
                    : text.length;
            }
        }

        // --- Tier 3: case-insensitive normalised match ---
        if (startIdx === -1) {
            const normQuoteLower = normalizeForMatch(quote).toLowerCase();
            const normPos = normTextLower.indexOf(normQuoteLower);
            if (normPos !== -1) {
                startIdx = origIndices[normPos];
                const normEnd = normPos + normQuoteLower.length - 1;
                endIdx = (normEnd + 1 < origIndices.length)
                    ? origIndices[normEnd + 1]
                    : text.length;
            }
        }

        // All tiers failed — skip this annotation
        if (startIdx === -1) {
            console.warn(`Quote not found in response: "${quote.substring(0, 50)}..."`);
            return;
        }
        
        // Check if this range overlaps with existing highlights
        const overlaps = highlightedRanges.some(range => 
            (startIdx >= range.start && startIdx < range.end) ||
            (endIdx > range.start && endIdx <= range.end) ||
            (startIdx <= range.start && endIdx >= range.end)
        );
        
        if (!overlaps) {
            highlightedRanges.push({ start: startIdx, end: endIdx });
            replacements.push({
                start: startIdx,
                end: endIdx,
                id: quoteData.id,
                severity: quoteData.severity,
                quote: text.substring(startIdx, endIdx) // always use original text
            });
        }
    });
    
    // Sort replacements by position (reverse order for easier replacement)
    replacements.sort((a, b) => b.start - a.start);
    
    // Apply replacements from end to start to preserve indices
    let result = text;
    replacements.forEach(rep => {
        const before = result.substring(0, rep.start);
        const highlighted = result.substring(rep.start, rep.end);
        const after = result.substring(rep.end);
        
        const className = rep.severity === 'red' ? 'hl-red' : 'hl-yellow';
        result = before + 
            `<span class="${className}" data-issue-id="${escapeHtml(rep.id)}">${escapeHtml(highlighted)}</span>` + 
            after;
    });
    
    // Escape any remaining plain text (that's not inside spans)
    // Since we've already added spans, we need to escape carefully
    // Actually, let's rebuild this more carefully
    return escapeHtmlPreserveHighlights(text, replacements);
}

// Escape HTML while preserving highlight spans
function escapeHtmlPreserveHighlights(text, replacements) {
    if (replacements.length === 0) {
        return escapeHtml(text);
    }
    
    // Sort replacements by start position
    replacements.sort((a, b) => a.start - b.start);
    
    let result = '';
    let lastEnd = 0;
    
    replacements.forEach(rep => {
        // Add escaped text before this replacement
        if (rep.start > lastEnd) {
            result += escapeHtml(text.substring(lastEnd, rep.start));
        }
        
        // Add the highlighted span
        const className = rep.severity === 'red' ? 'hl-red' : 'hl-yellow';
        result += `<span class="${className}" data-issue-id="${escapeHtml(rep.id)}">${escapeHtml(rep.quote)}</span>`;
        
        lastEnd = rep.end;
    });
    
    // Add any remaining text after the last replacement
    if (lastEnd < text.length) {
        result += escapeHtml(text.substring(lastEnd));
    }
    
    return result;
}

// Build issues list HTML
function buildIssuesListHtml(annotations) {
    if (!annotations || annotations.length === 0) {
        return '';
    }
    
    const issuesHtml = annotations.map(ann => `
        <div class="issue-card severity-${ann.severity}" id="issue-${escapeHtml(ann.id)}">
            <div class="issue-card-header">
                <span class="issue-badge ${ann.severity}">${ann.severity === 'red' ? 'Major' : 'Minor'}</span>
                <span class="issue-dimension">${escapeHtml(ann.dimension)}</span>
            </div>
            <div class="issue-quote">"${escapeHtml(ann.quote)}"</div>
            <div class="issue-explanation">${escapeHtml(ann.explanation)}</div>
            <div class="issue-suggestion">${escapeHtml(ann.suggestion)}</div>
        </div>
    `).join('');
    
    return `
        <div class="issues-section">
            <h4>Issues Found</h4>
            <div class="issues-list">${issuesHtml}</div>
        </div>
    `;
}

// Setup click handlers for highlight -> issue card scroll
function setupHighlightClickHandlers(container) {
    const highlights = container.querySelectorAll('.hl-red, .hl-yellow');
    
    highlights.forEach(highlight => {
        highlight.addEventListener('click', function() {
            const issueId = this.dataset.issueId;
            const issueCard = container.querySelector(`#issue-${issueId}`);
            
            if (issueCard) {
                // Remove active class from all highlights
                highlights.forEach(h => h.classList.remove('active'));
                // Add active class to clicked highlight
                this.classList.add('active');
                
                // Scroll to issue card
                issueCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Add flash animation
                issueCard.classList.remove('flash');
                void issueCard.offsetWidth; // Trigger reflow
                issueCard.classList.add('flash');
            }
        });
    });
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Normalize a string for fuzzy matching: collapse whitespace, replace
// smart quotes / dashes with their ASCII equivalents, and trim.
function normalizeForMatch(str) {
    return str
        .replace(/[\u2018\u2019]/g, "'")   // curly single quotes → '
        .replace(/[\u201C\u201D]/g, '"')    // curly double quotes → "
        .replace(/[\u2013\u2014]/g, '-')    // en-dash / em-dash  → -
        .replace(/\s+/g, ' ')              // collapse whitespace runs
        .trim();
}

// Build a normalised version of `text` together with a mapping array so that
// each position in the normalised string can be traced back to the original.
// Returns { normStr, origIndices } where origIndices[i] is the index in
// `text` that produced position i in normStr.
function buildIndexMap(text) {
    let normStr = '';
    const origIndices = [];
    let inWhitespace = false;

    for (let i = 0; i < text.length; i++) {
        let ch = text[i];

        // Replace smart quotes / dashes with ASCII equivalents
        if (ch === '\u2018' || ch === '\u2019') ch = "'";
        else if (ch === '\u201C' || ch === '\u201D') ch = '"';
        else if (ch === '\u2013' || ch === '\u2014') ch = '-';

        // Collapse whitespace runs into a single space
        if (/\s/.test(ch)) {
            if (!inWhitespace && normStr.length > 0) {
                normStr += ' ';
                origIndices.push(i);
            }
            inWhitespace = true;
        } else {
            normStr += ch;
            origIndices.push(i);
            inWhitespace = false;
        }
    }

    // Trim trailing space if present
    if (normStr.endsWith(' ')) {
        normStr = normStr.slice(0, -1);
        origIndices.pop();
    }

    return { normStr, origIndices };
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
    originalPrompt = null;
    currentResults = null;
    currentResultsQuestionIndex = 0;
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
}

// Initialize app
init();
