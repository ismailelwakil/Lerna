# Environment Setup & Prerequisites: Academic OS

## Prerequisites

- **Python:** 3.11, 3.12, or 3.13
- **Node.js:** v18.0.0 or higher (v20+ recommended)
- **Package Managers:** `pip` (Python) and `npm` (Node)

---

## 1. Python AI Service & API Setup

### Step 1: Create Virtual Environment
```bash
# From repository root or ai-service/
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install PyTorch (CPU-optimized)
To prevent downloading heavy CUDA binaries if GPU is not needed:
```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
```

### Step 3: Install Dependencies
```bash
pip install -r ai-service/requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp ai-service/.env.example ai-service/.env
```
Ensure `GEMINI_API_KEY` and `TAVILY_API_KEY` are populated.

### Step 5: Start Backend API
```bash
# Run FastAPI thin backend integration facade
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at: `http://localhost:8000/docs`.

---

## 2. React Frontend Setup

### Step 1: Navigate to Frontend Directory
```bash
cd frontend
```

### Step 2: Install Node Packages
```bash
npm install
```

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default content:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_STUDENT_ID=student-001
```

### Step 4: Run Development Server
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 3. Running Both Services Concurrently

For a streamlined local development workflow:
- **Terminal 1 (Backend API):** `uvicorn api.main:app --port 8000 --reload`
- **Terminal 2 (React Frontend):** `cd frontend && npm run dev`
- **Terminal 3 (Reference Streamlit QA App):** `streamlit run ai-service/app/streamlit_app.py --server.port 8501`
