<p align="center">
  <img src="logo.svg" width="90" height="90" alt="Fluid AI Logo" />
</p>

<h1 align="center">🌊 Fluid AI — Autonomous Research Plan & Proposal Synthesis Engine</h1>

<p align="center">
  <strong>An enterprise-grade autonomous agent pipeline that plans, researches, reflects, and generates client-ready Microsoft Word (.docx) and Adobe PDF documents with zero human intervention.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Model-Groq%20Llama%203.3%2070B-6366f1?style=for-the-badge&logo=meta" alt="Llama 3.3 70B" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Dual%20Export-.DOCX%20%2B%20.PDF-f43f5e?style=for-the-badge" alt="Dual Export" />
  <img src="https://img.shields.io/badge/Architecture-Autonomous%20Multi--Step%20Agent-38bdf8?style=for-the-badge" alt="Architecture" />
</p>

---

## 💡 The USP (Unique Selling Proposition)

Standard AI tools generate flat, shallow text from a single prompt. If an API rate-limit occurs, the generation fails. If the output misses key metrics, it goes unnoticed.

**Fluid AI delivers the 4-Stage Autonomous Pipeline**:

1. **Stage 1: Autonomous Multi-Step Planning**  
   The agent decomposes vague natural language prompts into a structured execution plan (4–7 ordered phases: `analyze`, `research`, `generate`, `structure`, `review`).
2. **Stage 2: Resilient Context-Carrying Execution**  
   Each phase runs independently with dedicated context propagation and **exponential backoff retry logic** (1s base, 30s max, 3 attempts), preventing pipeline breakage from transient API rate limits.
3. **Stage 3: Autonomous Quality Reflection & Critique**  
   The generated draft undergoes automated critique against completeness, structure, and quality thresholds (minimum score 7/10). If deficient, an automated refinement pass is executed before export.
4. **Stage 4: Dual Enterprise Compilation (.docx & .pdf)**  
   Transforms raw outputs into styled, executive-ready **Microsoft Word (.docx)** and **Adobe PDF** documents formatted with branded typography, section headings, styled tables, and metadata.

---

## 🏗️ Architectural Flow

```text
User Request (NLP)
      │
      ▼
┌─────────────────────────┐
│  1. Autonomous Planner  │ ──► Decomposes task into 4–7 phased steps
└─────────────────────────┘
      │
      ▼
┌─────────────────────────┐
│  2. Stepwise Executor   │ ──► Step-by-step LLM reasoning + Context chaining
└─────────────────────────┘     (With Exponential Backoff Retry)
      │
      ▼
┌─────────────────────────┐
│ 3. Reflection Reviewer  │ ──► Quality verification (Score >= 7.0/10)
└─────────────────────────┘     (Auto-refinement triggered if below threshold)
      │
      ▼
┌─────────────────────────┐
│  4. Dual Document Engine│ ──► Generates styled .DOCX + Native / Fallback .PDF
└─────────────────────────┘
      │
      ▼
Client-Ready Deliverable (.docx & .pdf)
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/saranasai-21/Fluid-AI-Research-plan-Proposal-generator.git
cd Fluid-AI-Research-plan-Proposal-generator
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Add your free Groq API key in `.env`:
```env
GROQ_API_KEY=gsk_your_key_here
```
*(Get a free key at [console.groq.com/keys](https://console.groq.com/keys))*

### 3. Run Locally (Python)
```bash
# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Server
uvicorn main:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🐳 Docker Deployment

Run with Docker in a single command:
```bash
docker-compose up --build
```
The application will be live at `http://localhost:8000`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the web generation studio dashboard |
| `POST` | `/agent` | Runs the full 4-stage autonomous pipeline |
| `GET` | `/documents` | Catalogs all generated Word and PDF files |
| `GET` | `/documents/{filename}` | Downloads a generated `.docx` or compiles `.pdf` on-the-fly |
| `POST` | `/api/update-key` | Hot-swaps the Groq API key dynamically |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## 🧪 Automated Testing

Execute the test suite:
```bash
pytest test_agent.py -v
```
