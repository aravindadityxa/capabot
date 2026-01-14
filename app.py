
from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import pandas as pd
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
import io
import os
import google.generativeai as genai
import json
from datetime import datetime

app = Flask(__name__)

# Configure Gemini API
# Get API key from environment variable or use placeholder
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE':
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_configured = True
else:
    gemini_configured = False
    print("⚠️ Gemini API key not configured. Chatbot will use fallback responses.")

# Try to load spaCy, but provide fallback
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        spacy_available = True
        print("✅ spaCy model loaded successfully")
    except OSError:
        print("⚠️ spaCy model not found. Using fallback skill extraction.")
        spacy_available = False
        nlp = None
except ImportError:
    print("⚠️ spaCy not installed. Using fallback skill extraction.")
    spacy_available = False
    nlp = None

# Enhanced skills database
SKILLS_DB = {
    'programming': ['python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'typescript', 'php'],
    'web': ['html', 'css', 'react', 'vue', 'angular', 'django', 'flask', 'node.js', 'express', 'spring', 'fastapi', 'laravel'],
    'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'dynamodb', 'cassandra'],
    'cloud': ['aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ansible', 'github actions'],
    'data_science': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'data analysis', 'nlp', 'computer vision'],
    'devops': ['git', 'github', 'gitlab', 'ci/cd', 'linux', 'bash', 'shell scripting', 'monitoring', 'logging'],
    'soft_skills': ['communication', 'leadership', 'teamwork', 'problem solving', 'creativity', 'time management', 'adaptability', 'critical thinking', 'collaboration']
}

# Flatten all skills for easier matching
ALL_SKILLS = []
for category in SKILLS_DB.values():
    ALL_SKILLS.extend(category)

COURSE_RECOMMENDATIONS = {
    'python': 'https://www.coursera.org/specializations/python',
    'javascript': 'https://www.udemy.com/course/the-complete-javascript-course/',
    'react': 'https://www.coursera.org/learn/react-basics',
    'machine learning': 'https://www.coursera.org/learn/machine-learning',
    'communication': 'https://www.coursera.org/learn/communication-skills',
    'aws': 'https://www.aws.training/Details/Curriculum?id=27070',
    'docker': 'https://www.udemy.com/course/docker-mastery/',
    'sql': 'https://www.coursera.org/learn/sql-data-science',
    'kubernetes': 'https://www.coursera.org/learn/google-kubernetes-engine',
    'node.js': 'https://www.coursera.org/learn/server-side-nodejs',
    'angular': 'https://www.coursera.org/specializations/angular',
    'vue': 'https://www.udemy.com/course/vuejs-2-the-complete-guide/',
    'django': 'https://www.coursera.org/learn/django-build-web-applications',
    'flask': 'https://www.udemy.com/course/python-flask-build-a-crud-web-app-using-flask/',
    'tensorflow': 'https://www.coursera.org/learn/introduction-tensorflow',
    'pytorch': 'https://www.coursera.org/projects/pytorch-basic-ml',
    'git': 'https://www.coursera.org/learn/introduction-git-github',
    'linux': 'https://www.coursera.org/learn/linux-fundamentals'
}

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_skills_advanced(text):
    """Advanced skill extraction using spaCy"""
    if not text or not spacy_available:
        return set()
    
    try:
        doc = nlp(text)
        found_skills = set()
        
        # Extract nouns and proper nouns that might be skills
        for token in doc:
            if (token.pos_ in ["NOUN", "PROPN"] and 
                token.text.lower() in ALL_SKILLS and 
                len(token.text) > 2):
                found_skills.add(token.text.lower())
        
        # Extract entities that might be skills
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT"]:
                skill_lower = ent.text.lower()
                if skill_lower in ALL_SKILLS:
                    found_skills.add(skill_lower)
        
        return found_skills
    except Exception as e:
        print(f"Advanced skill extraction failed: {e}")
        return set()

def extract_skills_basic(text):
    """Basic skill extraction using pattern matching"""
    if not text:
        return set()
    
    text_lower = text.lower()
    found_skills = set()
    
    # Direct skill matching
    for skill in ALL_SKILLS:
        if skill in text_lower:
            found_skills.add(skill)
    
    # Pattern-based extraction
    skill_patterns = [
        r'(?:experienced in|proficient in|knowledge of|skills in|expertise in)\s+([^.,]+)',
        r'(\w+\s+\w+)\s+(?:development|programming|engineering|framework)',
        r'(?:knowledge|experience)\s+(?:in|with)\s+([^.,]+)'
    ]
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            # Clean and extract potential skills
            words = match.strip().split()
            for word in words:
                word_clean = re.sub(r'[^a-zA-Z]', '', word).lower()
                if word_clean in ALL_SKILLS:
                    found_skills.add(word_clean)
    
    return found_skills

def extract_skills(text):
    """Main skill extraction function with fallback"""
    basic_skills = extract_skills_basic(text)
    
    if spacy_available:
        advanced_skills = extract_skills_advanced(text)
        return basic_skills.union(advanced_skills)
    else:
        return basic_skills

def calculate_similarity(resume_text, job_text):
    """Calculate similarity between resume and job description using TF-IDF"""
    if not resume_text or not job_text:
        return 0
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    
    try:
        # Combine texts and create matrix
        texts = [resume_text, job_text]
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        score = round(similarity[0][0] * 100, 2)
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    except Exception as e:
        print(f"Similarity calculation error: {e}")
        return 0

def recommend_skills(resume_skills, job_skills):
    """Find missing skills and provide recommendations"""
    missing_skills = job_skills - resume_skills
    recommendations = []
    
    for skill in missing_skills:
        course_link = COURSE_RECOMMENDATIONS.get(skill.lower())
        if course_link:
            recommendations.append({
                'skill': skill,
                'course': course_link,
                'description': f'Learn {skill} with recommended courses'
            })
        else:
            # Generic search link for skills not in our database
            search_query = skill.replace(' ', '+')
            recommendations.append({
                'skill': skill,
                'course': f'https://www.google.com/search?q=learn+{search_query}+course+online',
                'description': f'Search for {skill} courses online'
            })
    
    return recommendations

def categorize_skills(skills):
    """Categorize skills into hard and soft skills"""
    hard_skills = set()
    soft_skills = set()
    
    all_hard_skills = set()
    for category in ['programming', 'web', 'databases', 'cloud', 'data_science', 'devops']:
        all_hard_skills.update(SKILLS_DB[category])
    
    for skill in skills:
        if skill.lower() in SKILLS_DB['soft_skills']:
            soft_skills.add(skill)
        elif skill.lower() in all_hard_skills:
            hard_skills.add(skill)
        else:
            # Default to hard skills for unknown skills
            hard_skills.add(skill)
    
    return hard_skills, soft_skills

def generate_chat_response(user_message, context, chat_history):
    """Generate AI response using Gemini API"""
    try:
        # Prepare context information
        has_resume = context.get('hasResume', False)
        has_job = context.get('hasJob', False)
        has_analysis = context.get('hasAnalysis', False)
        analysis_data = context.get('analysis', {})
        
        # Build system prompt
        system_prompt = """You are CapaBot AI Assistant, a helpful career advisor specializing in resume analysis and job matching.
        
Your role is to help users understand their resume-job match, suggest improvements, and provide career advice."""

        # Add context-specific information
        if has_resume and has_job and has_analysis:
            match_score = analysis_data.get('match_score', 0)
            matching_skills = analysis_data.get('matching_skills', [])
            missing_hard = analysis_data.get('missing_skills', {}).get('hard', [])
            missing_soft = analysis_data.get('missing_skills', {}).get('soft', [])
            
            system_prompt += f"""
            
ANALYSIS RESULTS:
- Match Score: {match_score}%
- Matching Skills: {', '.join(matching_skills) if matching_skills else 'None'}
- Missing Hard Skills: {', '.join(missing_hard) if missing_hard else 'None'}
- Missing Soft Skills: {', '.join(missing_soft) if missing_soft else 'None'}

RESUME CONTEXT: {context.get('resumePreview', 'No resume content')[:500]}
JOB DESCRIPTION CONTEXT: {context.get('jobPreview', 'No job description content')[:500]}
"""
        elif has_resume or has_job:
            system_prompt += f"""
            
PARTIAL UPLOAD:
- {'Resume uploaded' if has_resume else 'No resume uploaded'}
- {'Job description uploaded' if has_job else 'No job description uploaded'}
- Resume preview: {context.get('resumePreview', 'No content')[:300]}
- Job preview: {context.get('jobPreview', 'No content')[:300]}
"""
        else:
            system_prompt += "\n\nNo resume or job description uploaded yet. Please upload both for personalized analysis."

        # Add guidelines
        system_prompt += """
        
GUIDELINES:
1. Be specific and actionable - give concrete advice
2. Reference the analysis results when available
3. If skills are missing, suggest specific learning resources
4. Provide encouragement and constructive feedback
5. Suggest next steps for improvement
6. Keep responses clear and concise
7. Ask clarifying questions if needed

USER QUESTION: """ + user_message

        # Add chat history if available
        if chat_history:
            system_prompt += "\n\nPREVIOUS CONVERSATION:\n" + chat_history

        # Generate response using Gemini API if configured
        if gemini_configured:
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(system_prompt)
                if response.text:
                    return response.text
                else:
                    return "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            except Exception as e:
                print(f"Gemini API error: {e}")
                # Fall through to fallback response
                pass
        
        # Fallback response if Gemini not configured or fails
        return generate_fallback_response(user_message, context, analysis_data)
            
    except Exception as e:
        print(f"Error in generate_chat_response: {e}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."

def generate_fallback_response(user_message, context, analysis_data):
    """Generate fallback response when Gemini API is not available"""
    user_message_lower = user_message.lower()
    
    if 'match' in user_message_lower or 'score' in user_message_lower:
        if context.get('hasAnalysis'):
            score = analysis_data.get('match_score', 0)
            if score >= 80:
                return f"Your match score is {score}%, which is excellent! You have most of the required skills. Focus on highlighting your matching skills in your resume and preparing for interviews."
            elif score >= 60:
                return f"Your match score is {score}%, which is good. You have many required skills but could improve in some areas. Review the missing skills section for specific areas to develop."
            elif score >= 40:
                return f"Your match score is {score}%, which is moderate. You have some relevant skills but significant gaps. Consider taking courses in the missing hard skills listed in your analysis."
            else:
                return f"Your match score is {score}%, which is low. You may need to develop more skills or target different positions. Review the recommendations section for specific learning resources."
        else:
            return "I don't have analysis results yet. Please upload both your resume and job description and click 'Analyze Match' first."
    
    elif 'skill' in user_message_lower or 'improve' in user_message_lower:
        if context.get('hasAnalysis'):
            missing_hard = analysis_data.get('missing_skills', {}).get('hard', [])
            missing_soft = analysis_data.get('missing_skills', {}).get('soft', [])
            
            response = "Based on your analysis:\n\n"
            if missing_hard:
                response += f"Missing Hard Skills: {', '.join(missing_hard)}\n"
            if missing_soft:
                response += f"Missing Soft Skills: {', '.join(missing_soft)}\n"
            
            if missing_hard or missing_soft:
                response += "\nI recommend:\n1. Focus on the top 2-3 missing skills first\n2. Check the recommendations section for learning resources\n3. Consider online courses or certifications\n4. Practice these skills in personal projects"
            else:
                response += "Great! No missing skills identified. Focus on strengthening your existing skills and gaining more experience."
            
            return response
        else:
            return "Please run an analysis first by uploading your resume and job description and clicking 'Analyze Match'."
    
    elif 'resume' in user_message_lower:
        if context.get('hasResume'):
            return "I can see you've uploaded a resume. For specific resume advice:\n1. Tailor your resume to highlight skills matching the job description\n2. Use quantifiable achievements\n3. Include relevant keywords from the job description\n4. Keep it concise (1-2 pages)\n5. Proofread carefully for errors"
        else:
            return "Please upload your resume first for personalized advice."
    
    elif 'job' in user_message_lower or 'description' in user_message_lower:
        if context.get('hasJob'):
            return "I can see you've uploaded a job description. To improve your match:\n1. Identify key requirements in the job description\n2. Match your skills to those requirements\n3. Address missing requirements in your resume or cover letter\n4. Research the company to understand their culture\n5. Prepare specific examples for each required skill"
        else:
            return "Please upload the job description first for personalized advice."
    
    else:
        return "I'm here to help with your resume and job matching questions! I can:\n1. Explain your match analysis results\n2. Suggest skill improvements\n3. Provide resume advice\n4. Help with job application strategies\n\nPlease upload your resume and job description, then click 'Analyze Match' for personalized assistance."

def format_chat_history(history):
    """Format chat history for context"""
    if not history:
        return ""
    
    formatted = ""
    for msg in history[-5:]:  # Last 5 messages for context
        role = "User" if msg.get('role') == 'user' else "Assistant"
        content = msg.get('content', '')
        formatted += f"{role}: {content}\n\n"
    
    return formatted

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Initialize variables
        resume_text = ''
        job_text = ''
        resume_file = None
        job_file = None
        
        # Check if request is JSON or FormData
        if request.content_type and 'application/json' in request.content_type:
            # Handle JSON request
            data = request.get_json()
            resume_text = data.get('resume_text', '')
            job_text = data.get('job_text', '')
        else:
            # Handle FormData request (for file uploads)
            resume_text = request.form.get('resume_text', '')
            job_text = request.form.get('job_text', '')
            resume_file = request.files.get('resume_file')
            job_file = request.files.get('job_file')
        
        # Process file uploads if they exist
        if resume_file and resume_file.filename:
            filename = resume_file.filename.lower()
            if filename.endswith('.pdf'):
                extracted_text = extract_text_from_pdf(resume_file)
                if not extracted_text.startswith('Error'):
                    resume_text = extracted_text
            elif filename.endswith(('.docx', '.doc')):
                extracted_text = extract_text_from_docx(resume_file)
                if not extracted_text.startswith('Error'):
                    resume_text = extracted_text
            elif filename.endswith('.txt'):
                resume_text = resume_file.read().decode('utf-8')
        
        if job_file and job_file.filename:
            filename = job_file.filename.lower()
            if filename.endswith('.pdf'):
                extracted_text = extract_text_from_pdf(job_file)
                if not extracted_text.startswith('Error'):
                    job_text = extracted_text
            elif filename.endswith(('.docx', '.doc')):
                extracted_text = extract_text_from_docx(job_file)
                if not extracted_text.startswith('Error'):
                    job_text = extracted_text
            elif filename.endswith('.txt'):
                job_text = job_file.read().decode('utf-8')
        
        # Validate we have content
        if not resume_text.strip() or not job_text.strip():
            return jsonify({
                'success': False,
                'error': 'Please provide both resume and job description content.'
            })
        
        # Extract skills
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_text)
        
        # Calculate similarity
        match_score = calculate_similarity(resume_text, job_text)
        
        # Categorize skills
        resume_hard, resume_soft = categorize_skills(resume_skills)
        job_hard, job_soft = categorize_skills(job_skills)
        
        # Find matching and missing skills
        matching_skills = resume_skills.intersection(job_skills)
        missing_hard_skills = job_hard - resume_hard
        missing_soft_skills = job_soft - resume_soft
        
        # Generate recommendations
        recommendations = recommend_skills(resume_skills, job_skills)
        
        # Prepare response
        result = {
            'success': True,
            'match_score': match_score,
            'resume_skills': {
                'hard': list(resume_hard),
                'soft': list(resume_soft)
            },
            'job_skills': {
                'hard': list(job_hard),
                'soft': list(job_soft)
            },
            'matching_skills': list(matching_skills),
            'missing_skills': {
                'hard': list(missing_hard_skills),
                'soft': list(missing_soft_skills)
            },
            'recommendations': recommendations,
            'spacy_available': spacy_available,
            'resume_preview': resume_text[:500] if resume_text else '',
            'job_preview': job_text[:500] if job_text else ''
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        })

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chatbot messages with Gemini API"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            })
        
        print(f"Chat request received: {user_message[:100]}...")
        print(f"Context has analysis: {context.get('hasAnalysis', False)}")
        
        # Format chat history
        formatted_history = format_chat_history(history)
        
        # Generate AI response
        ai_response = generate_chat_response(user_message, context, formatted_history)
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat(),
            'gemini_configured': gemini_configured
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'response': "I apologize, but I'm having trouble processing your request. Please try again.",
            'gemini_configured': gemini_configured
        })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    gemini_status = "configured" if gemini_configured else "not configured"
    
    return jsonify({
        'status': 'healthy',
        'service': 'CapaBot AI Resume Matcher',
        'spacy': spacy_available,
        'gemini_api': gemini_status,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
