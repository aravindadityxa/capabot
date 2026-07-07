# CapaBot — AI Resume Matcher

CapaBot analyzes a candidate's resume against a job description, produces a match score, identifies skill gaps, and recommends courses to close them. It runs completely offline — no external AI APIs required.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| Scoring | TF-IDF + Cosine Similarity (scikit-learn) |
| Database | MySQL |
| File Parsing | PyPDF2, python-docx |
| Frontend | HTML, CSS, JavaScript, Chart.js |

## Features

- Resume upload (PDF, DOCX, TXT) or paste text
- Job description upload or paste text
- Match score (0–100%) via TF-IDF + cosine similarity
- Matching skills, missing hard skills, missing soft skills
- Course recommendations from MySQL
- Swagger UI at `/docs`
- Health check at `/health`

## Prerequisites

- Python 3.11+
- MySQL 8.x running locally (or remote)

## Setup

**1. Clone and enter the project**
```
git clone https://github.com/aravindadityxa/capabot.git
cd capabot
```

**2. Create and activate a virtual environment**
```
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux
```

**3. Install dependencies**
```
pip install -r requirements.txt
```

**4. Configure environment variables**
```
copy .env.example .env     # Windows
cp .env.example .env       # macOS / Linux
```
Edit `.env` and set your MySQL credentials.

**5. Create the database schema**
```
mysql -u root -p < database.sql
```

**6. Run the application**
```
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.  
Swagger docs are at `http://127.0.0.1:8000/docs`.

> Skills and courses are seeded into MySQL automatically on first startup — no manual INSERT needed.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Main HTML UI |
| `POST` | `/analyze` | Analyze resume vs job description |
| `GET` | `/skills` | List all skills in the database |
| `GET` | `/courses` | List all course recommendations |
| `GET` | `/health` | Health check (app + DB status) |

## License

MIT
