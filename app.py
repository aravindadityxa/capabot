from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

app = Flask(__name__)

# Basic skills database
SKILLS_DB = ['python', 'javascript', 'java', 'react', 'html', 'css', 'sql', 'aws', 'docker', 'machine learning', 'communication', 'leadership', 'teamwork', 'problem solving']

def calculate_similarity(resume_text, job_text):
    """Basic similarity calculation"""
    if not resume_text or not job_text:
        return 0
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        texts = [resume_text, job_text]
        tfidf_matrix = vectorizer.fit_transform(texts)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(similarity[0][0] * 100, 2)
    except:
        return 0

def extract_skills(text):
    """Basic skill extraction"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in SKILLS_DB:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get data from form (not JSON)
        resume_text = request.form.get('resume_text', '')
        job_text = request.form.get('job_text', '')
        
        print(f"Received resume: {resume_text[:100]}...")  # Debug
        print(f"Received job: {job_text[:100]}...")        # Debug
        
        # Basic validation
        if not resume_text.strip() or not job_text.strip():
            return jsonify({
                'success': False, 
                'error': 'Please provide both resume and job description'
            })
        
        # Calculate similarity
        match_score = calculate_similarity(resume_text, job_text)
        
        # Extract skills
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_text)
        
        # Find matches
        matching_skills = list(set(resume_skills) & set(job_skills))
        missing_skills = list(set(job_skills) - set(resume_skills))
        
        result = {
            'success': True,
            'match_score': match_score,
            'matching_skills': matching_skills,
            'missing_skills': missing_skills,
            'recommendations': []
        }
        
        print(f"Analysis complete: {match_score}% match")  # Debug
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {e}")  # Debug
        return jsonify({
            'success': False, 
            'error': f'Analysis failed: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)