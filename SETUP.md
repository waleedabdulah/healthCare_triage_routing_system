# Healthcare Triage System — Setup Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- A free Groq API key → https://console.groq.com

---

## Step 1: Python Environment

```bash
cd d:/AI_project
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt
```

---

## Step 2: Environment Variables

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

---

## Step 3: Build the RAG Knowledge Base (run once)

```bash
python scripts/ingest_knowledge_base.py
```

This loads the 10 medical protocol documents into ChromaDB.

---

## Step 4: Start the Backend

```bash
uvicorn src.api.main:app --reload --port 8000
```

Health check: http://localhost:8000/health

---

## Step 5: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Step 6: Run End-to-End Tests (optional)

```bash
# With backend running:
python scripts/test_graph.py
```

---

## Admin Dashboard

- Audit logs: http://localhost:8000/api/v1/admin/audit-logs
- Statistics: http://localhost:8000/api/v1/admin/stats

---

## Using Ollama (fully offline fallback)

```bash
# Install Ollama from https://ollama.com
ollama pull llama3.2
# In .env:
USE_OLLAMA=1
```
