let currentResumeText = '';
let currentJobText = '';
let currentAnalysisData = null;
let chatHistory = [];

// Initialize chatbot
function initChatbot() {
    const toggleBtn = document.getElementById('chatbot-toggle');
    const closeBtn = document.getElementById('chatbot-close');
    const sendBtn = document.getElementById('chatbot-send');
    const chatInput = document.getElementById('chatbot-input');
    const chatContainer = document.getElementById('chatbot-container');

    // Toggle chatbot visibility
    toggleBtn.addEventListener('click', () => {
        chatContainer.classList.toggle('show');
    });

    closeBtn.addEventListener('click', () => {
        chatContainer.classList.remove('show');
    });

    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);

    // Send message on Enter (with Shift for new line)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Update current data when analysis is done
    window.addEventListener('analysisComplete', (event) => {
        currentAnalysisData = event.detail;
        updateContextData();
    });
}

// Update context data from current inputs
function updateContextData() {
    currentResumeText = document.getElementById('resume-text').value;
    currentJobText = document.getElementById('job-text').value;
    
    // Get file names if uploaded
    const resumeFile = document.getElementById('resume-file').files[0];
    const jobFile = document.getElementById('job-file').files[0];
    
    if (resumeFile) {
        currentResumeText += `\n[Uploaded file: ${resumeFile.name}]`;
    }
    
    if (jobFile) {
        currentJobText += `\n[Uploaded file: ${jobFile.name}]`;
    }
}

// Send message to chatbot
async function sendMessage() {
    const input = document.getElementById('chatbot-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    input.value = '';
    input.style.height = 'auto';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        // Get context for the AI
        const context = getChatContext();
        
        // Call backend to get AI response
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                context: context,
                history: chatHistory.slice(-10) // Last 10 messages for context
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (data.success) {
            addMessage(data.response, 'bot');
            chatHistory.push({ role: 'user', content: message });
            chatHistory.push({ role: 'assistant', content: data.response });
        } else {
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator();
        addMessage('Sorry, I\'m having trouble connecting. Please check your internet connection.', 'bot');
    }
}

// Quick question function
function quickQuestion(question) {
    const input = document.getElementById('chatbot-input');
    input.value = question;
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    sendMessage();
}

// Add message to chat UI
function addMessage(content, sender) {
    const messagesContainer = document.getElementById('chatbot-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.innerHTML = `
        <div class="message-content">${content.replace(/\n/g, '<br>')}</div>
        <div class="message-time">${time}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatbot-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Get context for AI response
function getChatContext() {
    const context = {
        hasResume: !!currentResumeText.trim(),
        hasJob: !!currentJobText.trim(),
        hasAnalysis: !!currentAnalysisData,
        resumePreview: currentResumeText.substring(0, 500),
        jobPreview: currentJobText.substring(0, 500),
        analysis: currentAnalysisData
    };
    
    return context;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initChatbot);

// Export functions for use in main script
window.quickQuestion = quickQuestion;
