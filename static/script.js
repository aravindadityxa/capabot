
let matchChart = null;

// Switch between text and file input
function switchInput(type, inputType) {
    const textInput = document.getElementById(`${type}-text-input`);
    const fileInput = document.getElementById(`${type}-file-input`);
    
    // Get the parent input-panel and find buttons within it
    const inputPanel = textInput.closest('.input-panel');
    const textBtn = inputPanel.querySelector('.tab-btn:nth-child(1)');
    const fileBtn = inputPanel.querySelector('.tab-btn:nth-child(2)');
    
    if (inputType === 'text') {
        textInput.classList.remove('hidden');
        fileInput.classList.add('hidden');
        textBtn.classList.add('active');
        fileBtn.classList.remove('active');
    } else {
        textInput.classList.add('hidden');
        fileInput.classList.remove('hidden');
        textBtn.classList.remove('active');
        fileBtn.classList.add('active');
    }
}

// Store analysis data globally for chatbot access
let globalAnalysisData = null;

// Analyze match function
async function analyzeMatch() {
    const resumeText = document.getElementById('resume-text').value;
    const jobText = document.getElementById('job-text').value;
    const resumeFile = document.getElementById('resume-file').files[0];
    const jobFile = document.getElementById('job-file').files[0];
    
    // Validate input
    if ((!resumeText && !resumeFile) || (!jobText && !jobFile)) {
        alert('Please provide both resume and job description information.');
        return;
    }
    
    // Show loading
    showLoading(true);
    
    try {
        const formData = new FormData();
        
        // Add text inputs if they exist
        if (resumeText) formData.append('resume_text', resumeText);
        if (jobText) formData.append('job_text', jobText);
        
        // Add file inputs if they exist
        if (resumeFile) formData.append('resume_file', resumeFile);
        if (jobFile) formData.append('job_file', jobFile);
        
        console.log('Sending analysis request...');
        
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
            // Don't set Content-Type header for FormData - browser will set it automatically with boundary
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            globalAnalysisData = result; // Store globally for chatbot
            displayResults(result);
            
            // Trigger analysis complete event for chatbot
            const event = new CustomEvent('analysisComplete', { 
                detail: result 
            });
            window.dispatchEvent(event);
            
            console.log('Analysis complete, data stored for chatbot:', result);
        } else {
            throw new Error(result.error || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('Analysis failed: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Display results
function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');
    
    // Update match score
    updateMatchScore(data.match_score);
    
    // Display skills
    displaySkills('matching-skills', data.matching_skills, 'matching');
    displaySkills('missing-hard-skills', data.missing_skills.hard, 'missing-hard');
    displaySkills('missing-soft-skills', data.missing_skills.soft, 'missing-soft');
    
    // Display recommendations
    displayRecommendations(data.recommendations);
    
    // Update chatbot context
    updateChatbotContext(data);
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Update chatbot context with analysis results
function updateChatbotContext(data) {
    // This will be used by the chatbot to access analysis data
    window.chatbotAnalysisData = data;
    console.log('Chatbot context updated with analysis data');
}

// Update match score with chart
function updateMatchScore(score) {
    const scoreElement = document.getElementById('match-score');
    const feedbackElement = document.getElementById('match-feedback');
    
    scoreElement.textContent = `${score}%`;
    
    // Set feedback based on score
    let feedback = '';
    let feedbackColor = '';
    
    if (score >= 80) {
        feedback = 'Excellent match! You have most required skills.';
        feedbackColor = '#4CAF50';
    } else if (score >= 60) {
        feedback = 'Good match! Consider developing a few more skills.';
        feedbackColor = '#FF9800';
    } else if (score >= 40) {
        feedback = 'Moderate match. Focus on developing key missing skills.';
        feedbackColor = '#FF5722';
    } else {
        feedback = 'Low match. Significant skill development needed.';
        feedbackColor = '#F44336';
    }
    
    feedbackElement.textContent = feedback;
    feedbackElement.style.color = feedbackColor;
    
    // Create or update chart
    const ctx = document.getElementById('matchChart').getContext('2d');
    
    if (matchChart) {
        matchChart.destroy();
    }
    
    // Determine chart color based on score
    let chartColor;
    if (score < 40) {
        chartColor = '#F44336';
    } else if (score < 60) {
        chartColor = '#FF9800';
    } else if (score < 80) {
        chartColor = '#4CAF50';
    } else {
        // Create gradient for high scores
        const gradient = ctx.createLinearGradient(0, 0, 200, 200);
        gradient.addColorStop(0, '#8A2BE2');
        gradient.addColorStop(1, '#FF69B4');
        chartColor = gradient;
    }
    
    matchChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [chartColor, 'rgba(255, 255, 255, 0.1)'],
                borderWidth: 0,
                borderRadius: 10,
                borderColor: 'rgba(255, 255, 255, 0.2)'
            }]
        },
        options: {
            cutout: '70%',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true,
                duration: 2000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// Display skills list
function displaySkills(containerId, skills, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (skills.length === 0) {
        const noSkillsElement = document.createElement('div');
        noSkillsElement.className = 'skill-item';
        noSkillsElement.textContent = 'No skills found in this category';
        noSkillsElement.style.opacity = '0.7';
        container.appendChild(noSkillsElement);
        return;
    }
    
    skills.forEach((skill, index) => {
        const skillElement = document.createElement('div');
        skillElement.className = `skill-item ${type}`;
        skillElement.textContent = skill.charAt(0).toUpperCase() + skill.slice(1); // Capitalize first letter
        skillElement.style.animationDelay = `${index * 0.1}s`;
        container.appendChild(skillElement);
    });
}

// Display recommendations
function displayRecommendations(recommendations) {
    const container = document.getElementById('recommendations-list');
    container.innerHTML = '';
    
    if (recommendations.length === 0) {
        const noRecElement = document.createElement('div');
        noRecElement.className = 'recommendation-item';
        noRecElement.textContent = 'No specific recommendations available. All required skills are present!';
        noRecElement.style.opacity = '0.7';
        container.appendChild(noRecElement);
        return;
    }
    
    recommendations.forEach((rec, index) => {
        const recElement = document.createElement('div');
        recElement.className = 'recommendation-item';
        recElement.style.animationDelay = `${index * 0.1}s`;
        
        recElement.innerHTML = `
            <h4>💡 ${rec.skill.charAt(0).toUpperCase() + rec.skill.slice(1)}</h4>
            <p>${rec.description}</p>
            <a href="${rec.course}" target="_blank" rel="noopener noreferrer">
                Explore Learning Resources →
            </a>
        `;
        
        container.appendChild(recElement);
    });
}

// Show/hide loading
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// Add sample data for testing
function addSampleData() {
    document.getElementById('resume-text').value = `Python Developer with 3 years of experience in web development using React and Django. 
Strong problem-solving skills and team collaboration. 
Experience with machine learning projects and database management using SQL and MongoDB.
Familiar with Git version control and basic AWS services.`;

    document.getElementById('job-text').value = `Looking for Senior Python Developer with React experience. 
Machine Learning knowledge preferred. 
Strong communication skills and AWS experience required. 
Experience with Docker and Kubernetes is a plus.
Knowledge of DevOps practices and CI/CD pipelines desired.`;
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    console.log('CapaBot initialized successfully!');
    
    // Add sample data for demo
    addSampleData();
    
    // Add event listeners for file inputs to update labels
    const resumeFileInput = document.getElementById('resume-file');
    const jobFileInput = document.getElementById('job-file');
    
    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', function(e) {
            const label = this.nextElementSibling;
            if (this.files.length > 0) {
                label.textContent = `📎 ${this.files[0].name}`;
                label.style.background = 'rgba(255, 255, 255, 0.1)';
                label.style.borderColor = 'rgba(255, 255, 255, 0.5)';
            } else {
                label.textContent = '📎 Choose PDF, DOCX, or TXT';
                label.style.background = 'rgba(255, 255, 255, 0.05)';
                label.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            }
        });
    }
    
    if (jobFileInput) {
        jobFileInput.addEventListener('change', function(e) {
            const label = this.nextElementSibling;
            if (this.files.length > 0) {
                label.textContent = `📎 ${this.files[0].name}`;
                label.style.background = 'rgba(255, 255, 255, 0.1)';
                label.style.borderColor = 'rgba(255, 255, 255, 0.5)';
            } else {
                label.textContent = '📎 Choose PDF, DOCX, or TXT';
                label.style.background = 'rgba(255, 255, 255, 0.05)';
                label.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            }
        });
    }
    
    // Test tab switching functionality
    console.log('Testing tab switching...');
    switchInput('resume', 'text');
    switchInput('job', 'text');
});

// Export functions for chatbot access
window.getAnalysisData = function() {
    return globalAnalysisData;
};

window.updateChatbotContext = updateChatbotContext;
