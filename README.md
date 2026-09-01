# BIS Sahayak AI

**AI-powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers**

Built for Smart India Hackathon — Problem Statement ID **26107**
Organization: Ministry of Consumer Affairs, Food & Public Distribution (Department of Consumer Affairs)

BIS Sahayak AI is an evidence-grounded BIS intelligence assistant. It converts natural-language product and compliance questions into traceable, source-backed guidance — helping MSMEs, manufacturers, students, and consumers navigate BIS standards, certification, testing, and hallmarking requirements without needing to know an IS number in advance.

Every answer is grounded in retrieved BIS document evidence (via Retrieval-Augmented Generation) and comes with citations back to the standard, clause, and page it was sourced from. If the system can't find supporting evidence, it says so explicitly rather than guessing.

---

## Architecture
User
↓
Next.js Frontend (:3000)
↓
FastAPI Backend (:8000)
↓
BIS Knowledge / Retrieval Layer
↓
PostgreSQL + pgvector (:5432)
↓
Relevant BIS Evidence
↓
Gemini API
↓
Grounded Answer + Citations


**RAG pipeline (how a question gets answered):**
User Question → Query Embedding → pgvector Similarity Search
→ Relevant BIS Document Chunks → Gemini (evidence-only) → Grounded Answer + Citations


Gemini never answers from open-ended knowledge — it only ever sees the BIS evidence chunks retrieved for that specific question. A backend validation step also rejects any standard number Gemini returns that wasn't among the retrieved candidates, to prevent hallucinated citations.

---

## Features

- **Ask BIS** — conversational Q&A over BIS standards and services
- **Product → Standard Recommendation** — describe a product in plain language, get candidate applicable standards with evidence
- **Certification, Compliance & Testing Guidance** — grounded in retrieved BIS evidence
- **Laboratory Discovery** and **Hallmarking Assistance**
- **Source Citations** — standard number, clause/section, page, source URL
- **Insufficient-evidence handling** — explicitly says "I could not verify this from the available BIS sources" instead of guessing

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16.3.3, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| AI | Google Gemini |
| Database | PostgreSQL + pgvector, SQLAlchemy |
| Infra | Docker, Docker Compose |

---

## Prerequisites

Before you start, make sure you have installed:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Git](https://git-scm.com/downloads)
- (Optional, for local non-Docker backend dev) Python 3.11+ and Node.js 18+

---

## Getting Started (Fresh Clone)

### 1. Clone the repository

```bash
git clone https://github.com/Rohit4060/BIS-Sahayak.git
cd BIS-Sahayak
```

### 2. Set up environment variables

This project uses **two separate `.env` files** — see [Understanding the Two .env Files](#understanding-the-two-env-files) below for why.

**Root `.env`** (used by Docker Compose):

Create a file named `.env` in the project root with:

```env
POSTGRES_PASSWORD=your-chosen-db-password
GEMINI_API_KEY=your-gemini-api-key-here
```

**Backend `.env`** (used only if running the backend directly with Python, outside Docker):

```bash
cd backend
cp .env.example .env
```

Then open `backend/.env` and fill in your real `GEMINI_API_KEY` and `DATABASE_URL`.

> Never commit either `.env` file. Both are already covered by `.gitignore`.

### 3. Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in and click **Create API Key**.
3. Copy the key into both `.env` files' `GEMINI_API_KEY` field.

---

## Running the App with Docker

From the project root (where `docker-compose.yml` lives):

**Start everything (build + run):**

```bash
docker compose up --build
```

First run builds all three images (frontend, backend, postgres) — this can take a few minutes. Subsequent runs are much faster.

**Stop the app** (keeps your data):

```bash
docker compose down
```

**Restart after stopping:**

```bash
docker compose up
```

(No `--build` needed unless you changed dependencies or Dockerfiles.)

**Full reset (wipes database data too):**

```bash
docker compose down -v
```

Use this only if you want a completely clean database — it deletes the Postgres volume.

---

## URLs Once Running

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Postgres | localhost:5432 |

---

---

## Quick API Test

Once the stack is running, verify the chat endpoint works:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is BIS certification?"}'
```

> Note: with a small starting knowledge base, the assistant may correctly respond "I could not verify this from the available BIS sources" for questions outside its current document set — this is expected anti-hallucination behavior, not a bug.

## Understanding the Two .env Files

- **Root `.env`** → read by `docker-compose.yml` and injected into the containers. This is what the Dockerized app actually uses.
- **`backend/.env`** → read by `load_dotenv()` inside `main.py`/`init_db.py`, only relevant if a developer runs the FastAPI backend directly with Python (`uvicorn ...`) outside Docker, for local debugging.

If you're only ever running the app via `docker compose up`, you technically only need the root `.env`. But keep `backend/.env` set up too in case you need to run backend scripts (like the ones in `backend/scripts/`) directly.

---

## Docker Volumes Are Local — Important for Teammates

The GitHub repository contains **code only**. It does not contain your database's contents.

- Your PostgreSQL data lives in a Docker volume (`postgres_data`) **on your machine only**.
- If you ingest BIS PDFs and build up embeddings locally, that data does **not** automatically appear for your teammates when they pull from GitHub.
- Each teammate who clones the repo starts with an **empty database** and must run their own ingestion (see below) to populate it.
- A `bis_sahayak_backup.sql` file exists for sharing a database snapshot manually if needed — it is intentionally **git-ignored** and must be shared out-of-band (e.g. a shared drive), not committed.

If everyone needs the same data, the team should agree on a way to share `bis_sahayak_backup.sql` outside Git, then each person restores it locally.

---

## Adding BIS Documents (data/raw/)

The knowledge base is built from BIS PDFs placed in `data/raw/`.

1. Place BIS standard PDFs into the `data/raw/` folder.
2. Run the ingestion scripts in `backend/scripts/` to extract, chunk, and embed them into PostgreSQL (see script names below).
3. `data/raw/` and `data/processed/` are **git-ignored** — BIS PDFs are not committed to GitHub.

> **Important:** Only add BIS PDFs you are authorized to distribute within the team. Do not commit or share copyrighted BIS documents without distribution permission. This repo's `.gitignore` already prevents `data/raw/` and `data/processed/` from being committed, so PDFs placed there stay local to your machine.

---

## Verification / Test Scripts

There is no automated test suite (e.g. pytest) yet. The following are manual verification scripts in `backend/scripts/`, useful for checking that a specific part of the pipeline works after changes:

- `test_pdf_extraction.py` — verifies PDF text extraction
- `test_metadata_extraction.py` — verifies clause/section/metadata extraction
- `test_search.py` — verifies `/api/search` retrieval
- `test_standards_recommend.py` — verifies `/api/standards/recommend`

Run them with the backend's virtual environment active, from the `backend/` folder, e.g.:

```bash
cd backend
venv\Scripts\activate
python scripts\test_search.py
```

---

## Current Limitations

- Knowledge base currently contains a small initial set of BIS documents — this is the working pipeline proof, not the final scale. Architecture is designed to expand without structural changes.
- No automated (pytest-style) test suite yet — only the manual scripts above.
- Multilingual support is part of the product vision but not yet fully implemented in the current build.

---

## Team Git Workflow

1. Pull latest changes before starting work:
```bash
   git pull origin main
```
2. Create a feature branch:
```bash
   git checkout -b feature/your-feature-name
```
3. Commit with clear messages:
```bash
   git add .
   git commit -m "Add: short description of change"
```
4. Push your branch and open a Pull Request:
```bash
   git push origin feature/your-feature-name
```
5. Get at least one teammate to review before merging into `main`.
6. After merging, everyone should `git pull origin main` to stay in sync.

> Application/RAG logic is currently stable and verified — avoid modifying `backend/services/`, `database.py`, or core RAG logic without team discussion.

