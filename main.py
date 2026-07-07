"""
CapaBot - AI Resume Matcher
FastAPI + MySQL backend (single-file application).

Start: uvicorn main:app --reload
Docs:  http://127.0.0.1:8000/docs
"""

import os
import io
import re
import logging
from contextlib import asynccontextmanager
from typing import Optional

import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from dotenv import load_dotenv

import PyPDF2
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "capabot"),
}

# ──────────────────────────────────────────────────────────────────────────────
# MySQL Connection Pool
# ──────────────────────────────────────────────────────────────────────────────
db_pool: Optional[pooling.MySQLConnectionPool] = None


def ensure_database_exists() -> None:
    """
    Connect to MySQL without a database selected and run
    CREATE DATABASE IF NOT EXISTS, so the pool never hits
    'Unknown database' on first startup.
    """
    bootstrap_cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**bootstrap_cfg)
    cursor = conn.cursor()
    try:
        db = DB_CONFIG["database"]
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{db}`")
        # Create tables if they don't exist yet
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_skills (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                skill_name VARCHAR(100) NOT NULL UNIQUE,
                category   VARCHAR(50)  NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_recommendations (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                skill_name       VARCHAR(100) NOT NULL,
                course_name      VARCHAR(200) NOT NULL,
                course_platform  VARCHAR(100) NOT NULL,
                course_url       VARCHAR(500) NOT NULL,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_name)
                    REFERENCES technical_skills(skill_name)
                    ON UPDATE CASCADE ON DELETE CASCADE
            )
        """)
        conn.commit()
        logger.info("Database '%s' and tables are ready.", db)
    finally:
        cursor.close()
        conn.close()


def create_db_pool() -> pooling.MySQLConnectionPool:
    """Create and return a MySQL connection pool (size 5)."""
    return pooling.MySQLConnectionPool(pool_name="capabot_pool", pool_size=5, **DB_CONFIG)


def get_connection():
    """Get a connection from the pool."""
    if db_pool is None:
        raise RuntimeError("Database pool is not initialised.")
    return db_pool.get_connection()


# ──────────────────────────────────────────────────────────────────────────────
# Seed Data  (inserted on first startup via INSERT IGNORE)
# ──────────────────────────────────────────────────────────────────────────────
SKILLS_SEED = [
    # Programming Languages
    ("python","programming"), ("java","programming"), ("javascript","programming"),
    ("typescript","programming"), ("c","programming"), ("c++","programming"),
    ("c#","programming"), ("go","programming"), ("rust","programming"),
    ("kotlin","programming"), ("swift","programming"), ("ruby","programming"),
    ("php","programming"), ("scala","programming"), ("r","programming"),
    ("bash","programming"), ("dart","programming"),
    # Web Frontend
    ("html","web_frontend"), ("css","web_frontend"), ("react","web_frontend"),
    ("angular","web_frontend"), ("vue","web_frontend"), ("nextjs","web_frontend"),
    ("svelte","web_frontend"), ("jquery","web_frontend"), ("bootstrap","web_frontend"),
    ("tailwind","web_frontend"), ("redux","web_frontend"), ("graphql","web_frontend"),
    ("rest api","web_frontend"), ("webpack","web_frontend"),
    # Web Backend
    ("django","web_backend"), ("flask","web_backend"), ("fastapi","web_backend"),
    ("node","web_backend"), ("express","web_backend"), ("spring","web_backend"),
    ("spring boot","web_backend"), ("laravel","web_backend"), ("rails","web_backend"),
    ("nestjs","web_backend"),
    # Databases
    ("sql","database"), ("mysql","database"), ("postgresql","database"),
    ("sqlite","database"), ("mongodb","database"), ("redis","database"),
    ("cassandra","database"), ("elasticsearch","database"), ("dynamodb","database"),
    ("oracle","database"), ("firebase","database"), ("supabase","database"),
    # DevOps
    ("docker","devops"), ("kubernetes","devops"), ("jenkins","devops"),
    ("github actions","devops"), ("terraform","devops"), ("ansible","devops"),
    ("nginx","devops"), ("linux","devops"), ("ci/cd","devops"),
    ("helm","devops"), ("prometheus","devops"), ("grafana","devops"),
    # Cloud
    ("aws","cloud"), ("azure","cloud"), ("gcp","cloud"), ("heroku","cloud"),
    ("vercel","cloud"), ("netlify","cloud"), ("s3","cloud"), ("ec2","cloud"),
    ("lambda","cloud"), ("rds","cloud"), ("ecs","cloud"), ("eks","cloud"),
    # Data Science
    ("pandas","data_science"), ("numpy","data_science"), ("matplotlib","data_science"),
    ("seaborn","data_science"), ("scipy","data_science"), ("tableau","data_science"),
    ("power bi","data_science"), ("excel","data_science"), ("data analysis","data_science"),
    ("statistics","data_science"), ("data visualization","data_science"),
    ("jupyter","data_science"),
    # ML / AI
    ("machine learning","ml_ai"), ("deep learning","ml_ai"), ("tensorflow","ml_ai"),
    ("pytorch","ml_ai"), ("keras","ml_ai"), ("scikit-learn","ml_ai"), ("nlp","ml_ai"),
    ("computer vision","ml_ai"), ("transformers","ml_ai"), ("xgboost","ml_ai"),
    ("lightgbm","ml_ai"), ("feature engineering","ml_ai"), ("mlflow","ml_ai"),
    # Mobile
    ("android","mobile"), ("ios","mobile"), ("flutter","mobile"),
    ("react native","mobile"), ("ionic","mobile"),
    # Testing
    ("unit testing","testing"), ("integration testing","testing"), ("pytest","testing"),
    ("junit","testing"), ("selenium","testing"), ("cypress","testing"),
    ("jest","testing"), ("postman","testing"),
    # Security
    ("cybersecurity","security"), ("oauth","security"), ("jwt","security"),
    ("ssl/tls","security"), ("owasp","security"), ("encryption","security"),
    # Tools & Practices
    ("git","tools"), ("github","tools"), ("jira","tools"), ("agile","tools"),
    ("scrum","tools"), ("microservices","tools"), ("api design","tools"),
    ("system design","tools"), ("design patterns","tools"), ("solid principles","tools"),
    # Soft Skills
    ("communication","soft_skill"), ("teamwork","soft_skill"),
    ("problem solving","soft_skill"), ("leadership","soft_skill"),
    ("time management","soft_skill"), ("critical thinking","soft_skill"),
    ("adaptability","soft_skill"), ("collaboration","soft_skill"),
    ("creativity","soft_skill"), ("mentoring","soft_skill"),
    ("project management","soft_skill"),
]

COURSES_SEED = [
    # skill_name, course_name, platform, url
    ("python","Python for Everybody Specialization","Coursera","https://www.coursera.org/specializations/python"),
    ("python","Complete Python Bootcamp","Udemy","https://www.udemy.com/course/complete-python-bootcamp/"),
    ("java","Java Programming Masterclass","Udemy","https://www.udemy.com/course/java-the-complete-java-developer-course/"),
    ("java","Java Programming and Software Engineering Fundamentals","Coursera","https://www.coursera.org/specializations/java-programming"),
    ("javascript","The Complete JavaScript Course","Udemy","https://www.udemy.com/course/the-complete-javascript-course/"),
    ("javascript","JavaScript Algorithms and Data Structures","freeCodeCamp","https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"),
    ("typescript","Understanding TypeScript","Udemy","https://www.udemy.com/course/understanding-typescript/"),
    ("typescript","TypeScript Full Course","freeCodeCamp","https://www.youtube.com/watch?v=30LWjhZzg50"),
    ("react","React - The Complete Guide","Udemy","https://www.udemy.com/course/react-the-complete-guide-incl-redux/"),
    ("react","React Official Docs Tutorial","React Docs","https://react.dev/learn"),
    ("angular","Angular - The Complete Guide","Udemy","https://www.udemy.com/course/the-complete-guide-to-angular-2/"),
    ("vue","Vue JS 3 - The Complete Guide","Udemy","https://www.udemy.com/course/vuejs-2-the-complete-guide/"),
    ("node","Node.js - The Complete Guide","Udemy","https://www.udemy.com/course/nodejs-the-complete-guide/"),
    ("django","Python Django - The Practical Guide","Udemy","https://www.udemy.com/course/python-django-the-practical-guide/"),
    ("django","Django Official Tutorial","Django Docs","https://docs.djangoproject.com/en/stable/intro/tutorial01/"),
    ("fastapi","FastAPI Full Course","freeCodeCamp","https://www.youtube.com/watch?v=0sOvCWFmrtA"),
    ("fastapi","FastAPI Official Documentation","FastAPI Docs","https://fastapi.tiangolo.com/tutorial/"),
    ("flask","Flask Mega-Tutorial","Miguel Grinberg","https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world"),
    ("mysql","MySQL Tutorial for Beginners","Programming with Mosh","https://www.youtube.com/watch?v=7S_tz1z_5bA"),
    ("postgresql","Learn PostgreSQL Tutorial","freeCodeCamp","https://www.youtube.com/watch?v=qw--VYLpxG4"),
    ("mongodb","MongoDB - The Complete Developer Guide","Udemy","https://www.udemy.com/course/mongodb-the-complete-developers-guide/"),
    ("sql","SQL for Data Science","Coursera","https://www.coursera.org/learn/sql-for-data-science"),
    ("docker","Docker & Kubernetes: The Practical Guide","Udemy","https://www.udemy.com/course/docker-kubernetes-the-practical-guide/"),
    ("docker","Docker Tutorial for Beginners","TechWorld with Nana","https://www.youtube.com/watch?v=3c-iBn73dDE"),
    ("kubernetes","Kubernetes for Absolute Beginners","Udemy","https://www.udemy.com/course/learn-kubernetes/"),
    ("aws","AWS Certified Solutions Architect","Udemy","https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/"),
    ("aws","AWS Cloud Practitioner Essentials","AWS Training","https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/"),
    ("azure","AZ-900 Microsoft Azure Fundamentals","Microsoft Learn","https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/"),
    ("gcp","Google Cloud Digital Leader","Google Cloud","https://cloud.google.com/training/business#google-cloud-digital-leader"),
    ("machine learning","Machine Learning Specialization","Coursera (Andrew Ng)","https://www.coursera.org/specializations/machine-learning-introduction"),
    ("deep learning","Deep Learning Specialization","Coursera (deeplearning.ai)","https://www.coursera.org/specializations/deep-learning"),
    ("tensorflow","TensorFlow Developer Certificate","Coursera","https://www.coursera.org/professional-certificates/tensorflow-in-practice"),
    ("pytorch","PyTorch Official Tutorials","PyTorch","https://pytorch.org/tutorials/"),
    ("nlp","Natural Language Processing Specialization","Coursera","https://www.coursera.org/specializations/natural-language-processing"),
    ("nlp","Hugging Face NLP Course","Hugging Face","https://huggingface.co/learn/nlp-course/"),
    ("data analysis","Google Data Analytics Certificate","Coursera","https://www.coursera.org/professional-certificates/google-data-analytics"),
    ("pandas","Pandas for Data Analysis","Kaggle","https://www.kaggle.com/learn/pandas"),
    ("scikit-learn","ML with Python and Scikit-Learn","freeCodeCamp","https://www.youtube.com/watch?v=0B5eIE_1vpU"),
    ("git","Git & GitHub Crash Course","freeCodeCamp","https://www.youtube.com/watch?v=RGOj5yH7evk"),
    ("linux","The Linux Command Line","LinuxCommand.org","https://linuxcommand.org/tlcl.php"),
    ("agile","Agile Fundamentals: Including Scrum & Kanban","Udemy","https://www.udemy.com/course/agile-fundamentals-scrum-kanban-scrumban/"),
    ("scrum","Professional Scrum Master Certification","Scrum.org","https://www.scrum.org/assessments/professional-scrum-master-i-certification"),
    ("flutter","Flutter & Dart - The Complete Guide","Udemy","https://www.udemy.com/course/learn-flutter-dart-to-build-ios-android-apps/"),
    ("react native","React Native - The Practical Guide","Udemy","https://www.udemy.com/course/react-native-the-practical-guide/"),
    ("cybersecurity","Google Cybersecurity Certificate","Coursera","https://www.coursera.org/professional-certificates/google-cybersecurity"),
    ("graphql","How to GraphQL - Free Tutorial","HowToGraphQL","https://www.howtographql.com/"),
    ("terraform","HashiCorp Terraform Associate Certification","Udemy","https://www.udemy.com/course/terraform-beginner-to-advanced/"),
    ("design patterns","Refactoring Guru - Design Patterns","Refactoring Guru","https://refactoring.guru/design-patterns"),
    ("system design","System Design Primer (GitHub)","donnemartin","https://github.com/donnemartin/system-design-primer"),
    ("communication","Improving Communication Skills","Coursera (UPenn)","https://www.coursera.org/learn/wharton-communication-skills"),
    ("leadership","Inspirational Leadership","Coursera","https://www.coursera.org/learn/inspirational-leadership"),
    ("project management","Google Project Management Certificate","Coursera","https://www.coursera.org/professional-certificates/google-project-management"),
    ("redis","Redis University - Free Courses","Redis University","https://university.redis.com/"),
    ("elasticsearch","Complete Elasticsearch Masterclass","Udemy","https://www.udemy.com/course/elasticsearch-complete-guide/"),
    ("microservices","Microservices with Node and React","Udemy","https://www.udemy.com/course/microservices-with-node-js-and-react/"),
    ("ci/cd","The Complete GitHub Actions & Workflows Guide","Udemy","https://www.udemy.com/course/github-actions/"),
    ("power bi","Microsoft Power BI Learning Path","Microsoft Learn","https://learn.microsoft.com/en-us/training/powerplatform/power-bi"),
    ("tableau","Tableau Free Training Videos","Tableau","https://www.tableau.com/learn/training"),
    ("spring boot","Spring Boot Official Guides","Spring.io","https://spring.io/guides"),
    ("kotlin","Kotlin Official Documentation","Kotlin","https://kotlinlang.org/docs/getting-started.html"),
    ("swift","iOS & Swift - Complete Bootcamp","Udemy","https://www.udemy.com/course/ios-13-app-development-bootcamp/"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Database Helpers
# ──────────────────────────────────────────────────────────────────────────────

def seed_database() -> None:
    """
    Populate technical_skills and course_recommendations tables on first run.
    INSERT IGNORE means re-running never causes duplicate-key errors.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(
            "INSERT IGNORE INTO technical_skills (skill_name, category) VALUES (%s, %s)",
            SKILLS_SEED,
        )
        cursor.executemany(
            """INSERT IGNORE INTO course_recommendations
               (skill_name, course_name, course_platform, course_url)
               VALUES (%s, %s, %s, %s)""",
            COURSES_SEED,
        )
        conn.commit()
        logger.info("Seed complete — %d skills, %d courses.", len(SKILLS_SEED), len(COURSES_SEED))
    except Exception as exc:
        conn.rollback()
        logger.error("Seed failed: %s", exc)
        raise
    finally:
        cursor.close()
        conn.close()


def load_all_skills() -> list[str]:
    """Return every skill_name from the DB as a lowercase list."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT skill_name FROM technical_skills ORDER BY skill_name")
        return [row[0].lower() for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_courses_for_skill(skill: str) -> list[dict]:
    """Return up to 2 course rows for the given skill name."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT course_name, course_platform, course_url
               FROM course_recommendations
               WHERE skill_name = %s
               LIMIT 2""",
            (skill.lower(),),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_skill_category(skill: str) -> str:
    """Return the category of a skill, or 'unknown' if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT category FROM technical_skills WHERE skill_name = %s",
            (skill.lower(),),
        )
        row = cursor.fetchone()
        return row[0] if row else "unknown"
    finally:
        cursor.close()
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Text Extraction
# ──────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using PyPDF2."""
    pages = []
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    except Exception as exc:
        logger.warning("PDF extraction warning: %s", exc)
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX file using python-docx."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        logger.warning("DOCX extraction warning: %s", exc)
        return ""


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route extraction by file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    if ext in ("docx", "doc"):
        return extract_text_from_docx(file_bytes)
    if ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: .{ext}")


# ──────────────────────────────────────────────────────────────────────────────
# Skill Extraction & Matching
# ──────────────────────────────────────────────────────────────────────────────

def extract_skills_from_text(text: str, all_skills: list[str]) -> list[str]:
    """
    Match known DB skills against a text block using word-boundary regex.
    Returns a deduplicated list of matched skill names.
    """
    text_lower = text.lower()
    found = []
    for skill in all_skills:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def classify_missing_skills(missing: list[str]) -> dict[str, list[str]]:
    """Split a missing-skills list into hard skills and soft skills."""
    hard, soft = [], []
    for skill in missing:
        if get_skill_category(skill) == "soft_skill":
            soft.append(skill)
        else:
            hard.append(skill)
    return {"hard": hard, "soft": soft}


# ──────────────────────────────────────────────────────────────────────────────
# TF-IDF Cosine Similarity  (original logic preserved)
# ──────────────────────────────────────────────────────────────────────────────

def compute_match_score(resume_text: str, job_text: str) -> int:
    """
    Return a 0-100 integer match score using TF-IDF + cosine similarity.
    Unigrams and bigrams are used for richer matching.
    """
    if not resume_text.strip() or not job_text.strip():
        return 0
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
    score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(float(score) * 100)


# ──────────────────────────────────────────────────────────────────────────────
# Course Recommendation Builder
# ──────────────────────────────────────────────────────────────────────────────

def build_recommendations(missing_skills: list[str]) -> list[dict]:
    """
    For each missing skill (capped at 10), fetch courses from MySQL.
    Falls back to a Google search link when no course row exists.
    """
    recommendations = []
    for skill in missing_skills[:10]:
        courses = get_courses_for_skill(skill)
        if courses:
            c = courses[0]
            recommendations.append({
                "skill":       skill,
                "description": f"Improve your {skill} skills with this course.",
                "course":      c["course_url"],
                "course_name": c["course_name"],
                "platform":    c["course_platform"],
            })
        else:
            query = skill.replace(" ", "+")
            recommendations.append({
                "skill":       skill,
                "description": f"Search for {skill} tutorials to get started.",
                "course":      f"https://www.google.com/search?q={query}+tutorial",
                "course_name": f"{skill.title()} Learning Resources",
                "platform":    "Google Search",
            })
    return recommendations


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    logger.info("Starting CapaBot...")
    try:
        ensure_database_exists()          # CREATE DATABASE + tables if missing
        db_pool = create_db_pool()        # Now safe to open pool with the DB
        logger.info("MySQL connection pool created.")
        seed_database()                   # INSERT IGNORE skills + courses
        logger.info("Application ready.")
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        raise
    yield
    logger.info("Shutting down CapaBot.")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CapaBot Resume Matcher",
    version="2.0",
    description=(
        "AI-powered resume analysis and skill gap detection. "
        "Uses TF-IDF + Cosine Similarity for scoring and MySQL for skill/course data."
    ),
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def index(request: Request):
    """Serve the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze", tags=["Core"])
async def analyze(
    resume_text: Optional[str] = Form(None),
    job_text:    Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    job_file:    Optional[UploadFile] = File(None),
):
    """
    Analyze resume vs job description.

    - Accepts **text** or **file upload** (PDF / DOCX / TXT) for both inputs.
    - Returns match score, matching skills, missing skills (hard + soft), and course recommendations.
    """
    try:
        # ── Resolve resume text ─────────────────────────────────────────────
        if resume_file and resume_file.filename:
            resume_content = extract_text(await resume_file.read(), resume_file.filename)
        elif resume_text:
            resume_content = resume_text.strip()
        else:
            raise HTTPException(400, "Resume content is required.")

        # ── Resolve job description text ─────────────────────────────────────
        if job_file and job_file.filename:
            job_content = extract_text(await job_file.read(), job_file.filename)
        elif job_text:
            job_content = job_text.strip()
        else:
            raise HTTPException(400, "Job description is required.")

        if not resume_content or not job_content:
            raise HTTPException(400, "Both resume and job description must have content.")

        # ── Load skills from MySQL ───────────────────────────────────────────
        all_skills = load_all_skills()

        # ── Extract skills mentioned in each text ────────────────────────────
        resume_skills = set(extract_skills_from_text(resume_content, all_skills))
        job_skills    = set(extract_skills_from_text(job_content,    all_skills))

        matching = sorted(resume_skills & job_skills)
        missing  = sorted(job_skills - resume_skills)

        # ── Classify missing skills ──────────────────────────────────────────
        missing_classified = classify_missing_skills(missing)

        # ── TF-IDF match score ───────────────────────────────────────────────
        match_score = compute_match_score(resume_content, job_content)

        # ── Course recommendations ───────────────────────────────────────────
        all_missing     = missing_classified["hard"] + missing_classified["soft"]
        recommendations = build_recommendations(all_missing)

        return JSONResponse({
            "success":         True,
            "match_score":     match_score,
            "matching_skills": matching,
            "missing_skills":  missing_classified,
            "recommendations": recommendations,
        })

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error during /analyze")
        raise HTTPException(500, f"Analysis error: {exc}")


@app.get("/skills", tags=["Data"])
async def get_all_skills():
    """Return all skills stored in the database."""
    try:
        skills = load_all_skills()
        return JSONResponse({"success": True, "count": len(skills), "skills": skills})
    except Exception as exc:
        logger.exception("Error fetching skills")
        raise HTTPException(500, f"Failed to fetch skills: {exc}")


@app.get("/courses", tags=["Data"])
async def get_all_courses():
    """Return all course recommendations stored in the database."""
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT skill_name, course_name, course_platform, course_url "
                "FROM course_recommendations ORDER BY skill_name"
            )
            courses = cursor.fetchall()
            return JSONResponse({"success": True, "count": len(courses), "courses": courses})
        finally:
            cursor.close()
            conn.close()
    except Exception as exc:
        logger.exception("Error fetching courses")
        raise HTTPException(500, f"Failed to fetch courses: {exc}")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check — verifies the app and database are reachable."""
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return JSONResponse({
            "status":   "healthy",
            "service":  "CapaBot Resume Matcher",
            "version":  "2.0",
            "database": "connected",
        })
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            {"status": "unhealthy", "database": "disconnected", "error": str(exc)},
            status_code=503,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
