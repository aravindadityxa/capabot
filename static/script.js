let matchChart = null;

// Switch between text and file input
function switchInput(type, inputType) {
    const textInput = document.getElementById(`${type}-text-input`);
    const fileInput = document.getElementById(`${type}-file-input`);
    
    if (inputType === 'text') {
        textInput.classList.remove('hidden');
        fileInput.classList.add('hidden');
    } else {
        textInput.classList.add('hidden');
        fileInput.classList.remove('hidden');
    }
}

// Analyze match function - FIXED
async function analyzeMatch() {
    const resumeText = document.getElementById('resume-text').value;
    const jobText = document.getElementById('job-text').value;
    
    // Validate input
    if (!resumeText.trim() || !jobText.trim()) {
        alert('Please provide both resume and job description.');
        return;
    }
    
    // Show loading
    showLoading(true);
    
    try {
        // Use FormData instead of JSON
        const formData = new FormData();
        formData.append('resume_text', resumeText);
        formData.append('job_text', jobText);
        
        console.log('Sending analysis request...');
        
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
            // Let browser set Content-Type automatically for FormData
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayResults(result);
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
    displaySkills('missing-hard-skills', data.missing_skills, 'missing-hard');
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Update match score with chart
function updateMatchScore(score) {
    const scoreElement = document.getElementById('match-score');
    const feedbackElement = document.getElementById('match-feedback');
    
    scoreElement.textContent = `${score}%`;
    
    // Set feedback based on score
    let feedback = '';
    if (score >= 80) {
        feedback = 'Excellent match! You have most required skills.';
    } else if (score >= 60) {
        feedback = 'Good match! Consider developing a few more skills.';
    } else if (score >= 40) {
        feedback = 'Moderate match. Focus on developing key missing skills.';
    } else {
        feedback = 'Low match. Significant skill development needed.';
    }
    feedbackElement.textContent = feedback;
    
    // Create simple chart
    const ctx = document.getElementById('matchChart').getContext('2d');
    
    if (matchChart) {
        matchChart.destroy();
    }
    
    matchChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: ['#8A2BE2', 'rgba(255, 255, 255, 0.1)'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
}

// Display skills list
function displaySkills(containerId, skills, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (skills.length === 0) {
        container.innerHTML = '<div class="skill-item">No skills found</div>';
        return;
    }
    
    skills.forEach((skill, index) => {
        const skillElement = document.createElement('div');
        skillElement.className = `skill-item ${type}`;
        skillElement.textContent = skill;
        skillElement.style.animationDelay = `${index * 0.1}s`;
        container.appendChild(skillElement);
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
    document.getElementById('resume-text').value = `Python developer with 3 years experience in web development using React and Django. Strong problem-solving skills and team collaboration. Experience with database management using SQL.`;

    document.getElementById('job-text').value = `Looking for Python Developer with React experience. Machine Learning knowledge preferred. Strong communication skills required. AWS experience is a plus.`;
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    console.log('CapaBot 40% MVP initialized!');
    
    // Add sample data for demo
    addSampleData();
    
    // Initialize tabs
    switchInput('resume', 'text');
    switchInput('job', 'text');
});