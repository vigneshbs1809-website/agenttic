# Literature Intelligence Platform — Setup & Installation Guide

This guide provides step-by-step instructions for installing, configuring, and executing the **Literature Intelligence Platform** on a local machine (Windows 11, Linux, or macOS) with **8 GB RAM and no dedicated GPU**.

---

## 1. Prerequisites & System Requirements

### Hardware Requirements
- **Memory:** 8 GB RAM minimum.
- **CPU:** 4 physical cores or higher (Intel Core i5/i7 8th Gen+, AMD Ryzen 3000+, or Apple Silicon).
- **Disk Space:** 5 GB free disk space (accounting for Ollama model weights).

### Software Requirements
- **Python:** 3.10, 3.11, or 3.12 (64-bit).
- **Node.js:** v18.0.0 or higher (LTS recommended) + `npm`.
- **Git:** Git 2.30+.
- **Ollama:** Latest Ollama release ([ollama.com](https://ollama.com/download)).

---

## 2. Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/Literature-Intelligence-Platform.git
cd Literature-Intelligence-Platform
```

### Step 2: Configure Environment Variables
Copy the `.env.example` file to create your local `.env`:
```bash
cp .env.example .env
```
Default settings are pre-tuned for an 8 GB RAM envelope:
```ini
DATABASE_URL="sqlite:///./backend/data/literature.db"
CHROMA_PERSIST_DIR="./backend/data/chromadb"
PDF_STORAGE_DIR="./backend/data/PDFs"
OLLAMA_BASE_URL="http://127.0.0.1:11434"
OLLAMA_LLM_MODEL="qwen3:1.7b"
OLLAMA_EMBED_MODEL="nomic-embed-text"
MAX_CHUNK_TOKENS=512
CHUNK_OVERLAP_TOKENS=64
RETRIEVAL_TOP_K=5
```

---

## 3. Python Virtual Environment & Backend Setup

### Step 1: Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Backend Dependencies
Upgrade `pip` and install all required packages:
```bash
python -m pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy pymupdf chromadb pydantic pydantic-settings httpx requests psutil reportlab python-docx networkx
```

### Step 3: Initialize Database & Directories
Verify that the database tables and data directories initialize cleanly:
```bash
python -c "from backend.app.core.database import init_db; init_db()"
```
This automatically creates `backend/data/literature.db` and the required upload directories.

---

## 4. Ollama Local LLM & Embedding Setup

The platform uses lightweight, 4-bit quantized local models via Ollama.

### Step 1: Install and Start Ollama
Ensure the Ollama background daemon is running:
- **Windows / macOS:** Launch the Ollama tray application.
- **Linux:** Run `systemctl start ollama` or `ollama serve`.

Test connectivity in your terminal:
```bash
curl http://127.0.0.1:11434/api/tags
```

### Step 2: Pull Required Quantized Models
Download the primary generation LLM and the dense embedding model:
```bash
# 1. Primary Reasoning LLM (1.7B parameters, ~1.4 GB RAM)
ollama pull qwen3:1.7b

# (Alternative ultra-lightweight LLM: qwen2.5:1.5b)
# ollama pull qwen2.5:1.5b

# 2. Dense Vector Embedding Model (768 dimensions, ~280 MB RAM)
ollama pull nomic-embed-text
```

> **Note on Offline Fallback:** If Ollama is not installed or offline, the platform's non-blocking fallback engine automatically activates. It provides deterministic, L2-normalized 768-dimensional embeddings and evidence synthesis without crashing or hanging.

---

## 5. Frontend Setup

### Step 1: Install Node Dependencies
Open a separate terminal window, navigate to `frontend/`, and install dependencies:
```bash
cd frontend
npm install
```

### Step 2: Build Verification
Ensure the TypeScript compilation and Vite build succeed:
```bash
npm run build
```

---

## 6. Running the Application

### Start the FastAPI Backend
From the repository root (with `venv` activated):
```bash
# Windows / Linux / macOS
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **System Health Diagnostics:** `http://127.0.0.1:8000/api/system/status`

### Start the React Frontend
In a second terminal:
```bash
cd frontend
npm run dev
```
- **Web Interface:** `http://localhost:5173`

---

## 7. Verification & Sanity Check

Run the comprehensive end-to-end verification script to confirm all 21 capabilities:
```bash
python backend/audit_full_suite.py
```
Expected output:
```
AUDIT COMPLETED SUCCESSFULLY: 21 OF 21 ITEMS VERIFIED
Total Execution Time: < 10s
RAM Utilization: Safe within 8 GB envelope
```

---

## 8. Troubleshooting

| Issue | Cause | Resolution |
|:---|:---|:---|
| `Ollama connection failed` | Ollama daemon not running | Launch Ollama or execute `ollama serve`. The platform will automatically use grounded heuristic fallback in the meantime. |
| `FastAPI port 8000 in use` | Another process is bound to port 8000 | Terminate the process or launch with `--port 8001` and update `.env`. |
| `PyMuPDF build error on pip install` | Outdated pip | Run `python -m pip install --upgrade pip` and retry `pip install pymupdf`. |
| `CORS Error in Browser` | Frontend running on non-standard port | Verify `CORS_ORIGINS` in `.env` includes your frontend origin. |
