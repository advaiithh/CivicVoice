# 🏛️ CivicVoice — Multilingual Voice-First Citizen Welfare Assistant

> **Luminix'26 Hackathon Project**  
> *Transforming citizen welfare discovery: From complex portal searching to natural, spoken conversation.*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB.svg?style=flat&logo=react)](https://react.dev/)
[![ReportLab](https://img.shields.io/badge/PDF_Engine-ReportLab-FF6F00.svg?style=flat)](https://www.reportlab.com/)
[![Web Speech API](https://img.shields.io/badge/Voice-Web_Speech_%26_Synthesis-4285F4.svg?style=flat)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
[![Indic Languages](https://img.shields.io/badge/Languages-8_Indian_Languages-EA580C.svg?style=flat)](https://india.gov.in)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 💡 The Core Idea: Inverting Welfare Access

Most citizens who qualify for government welfare schemes never receive them — not because the schemes don't exist, but because discovery, language barriers, and complex paperwork create massive hurdles.

- ❌ **The Traditional Model:** A citizen must know the exact scheme name in advance, navigate complex English/Hindi portals, understand legalese, and fill out lengthy forms. If they don't know a scheme exists, they get nothing.
- ✅ **CivicVoice's Model:** The citizen simply describes their life situation in their own mother tongue (*"I am a small farmer, my daughter is in 10th grade, we live in a village with a kutcha house"*). CivicVoice listens, extracts structured facts, checks them against authentic eligibility rules, proactively clarifies missing details, surfaces matching central/state schemes, and generates **official pre-filled PDF application forms**.

---

## ✨ Key Winning Features

### 1. 🇮🇳 Native Multilingual Experience (8 Indian Languages)
- **Full UI & Voice Localization:** Supports **Hindi (`hi-IN`), Tamil (`ta-IN`), Telugu (`te-IN`), Kannada (`kn-IN`), Malayalam (`ml-IN`), Marathi (`mr-IN`), Bengali (`bn-IN`), and English (`en-IN`)**.
- **End-to-End Voice Loop:** Speech-to-Text via Web Speech API and spoken audio readback via `SpeechSynthesis` in matching native accents.

### 2. 🧠 Persistent Citizen Memory Across Calls
- Citizens never explain themselves twice. Keyed by **mobile number** in SQLite, CivicVoice restores all previously verified attributes (occupation, family size, landholding, income bracket, caste category, residence) and merges new facts seamlessly.

### 3. 🎯 Proactive Clarifying Dialogue (`POST /api/followup`)
- Rather than showing a dead-end "Needs More Info" badge for schemes marked `"possible"`, CivicVoice identifies the **single highest-leverage missing fact** (e.g. household income or daughter's age) that would unlock the maximum number of schemes.
- Presents natural clarifying questions with **one-click quick reply option chips** or voice replies.

### 4. ⚖️ 100% Grounded & Explainable ("Why You Qualify")
- Every eligibility verdict is deterministic and cites the **exact statutory Gazette clause** it originates from.
- Interactive **"Why You Qualify" transparency breakdown** displays criterion-by-criterion checks (`✅ Satisfied`, `⏳ Missing`, `❌ Contradicted`) with direct links to authentic government portals (`pmkisan.gov.in`, `pmjay.gov.in`, `pmayg.nic.in`, etc.).

### 5. 📄 Official Printable PDF Application Forms
- Built with `ReportLab` to produce clean, pre-filled printable government application forms featuring:
  - Official Jan Seva Kendra header & Application Reference Number (`CV-YYYYMMDD-XXXX`).
  - Applicant Situation & Verified Particulars Table.
  - Welfare Scheme Details & Statutory Eligibility Clause.
  - Document Checklist with verification check boxes `[  ]`.
  - Statutory Declaration & Citizen Signature Block.

### 6. 📊 Aggregate Civic Impact Dashboard (`GET /api/stats`)
- Live impact counter showing registered citizens, confirmed scheme matches, and estimated economic welfare unlocked in **₹ Lakhs**.

### 7. 🛡️ 100% Zero-Key Resilience
- Works out-of-the-box without requiring paid API keys!
- Automatically utilizes **Local Ollama** (`qwen2.5:3b` / `mistral:7b`) if running locally, and features a built-in zero-dependency **Smart Indic Heuristic NLP Engine** ensuring guaranteed uptime during hackathon judging.

---

## 🏗️ System Architecture

```
                       Citizen Speaks or Types in Native Language
                                            │
                                            ▼
                           [Browser Web Speech Recognition]
                                            │
                                            ▼
                              [Frontend: React 18 + Vite]
                                            │
                       POST /api/process { phone, text, lang }
                                            │
                                            ▼
                               [FastAPI Backend: main.py]
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
    [Local Ollama / Claude API]                              [Heuristic Indic NLP Engine]
               │                                                         │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                  Extracted Facts JSON
                                            │
                                            ▼
                   [Persistent SQLite Memory: citizens table (phone)]
                                            │
                                            ▼
                      [Deterministic Rule Engine: evaluate_scheme()]
                        Evaluates 12+ real central welfare schemes
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
       "Confirmed Eligible"                                     "Possible / Needs Info"
               │                                                         │
               ▼                                                         ▼
     • Quoted Gazette Clause                                   • POST /api/followup
     • Why You Qualify Breakdown                               • Interactive Clarification
     • GET /api/draft/pdf (ReportLab)                          • Quick Selection Chips
     • Browser SpeechSynthesis Voice Output
```

---

## 📂 Repository Structure

```
CivicVoice/
├── backend/
│   ├── main.py              # FastAPI service: NLP extraction, rule engine, PDF generator, /api/followup
│   ├── schemes.json         # Real Indian welfare schemes with rules, benefits, clauses & official URLs
│   ├── test_api.py          # Automated verification test suite for all endpoints
│   ├── requirements.txt     # Python dependencies (FastAPI, ReportLab, uvicorn, python-dotenv)
│   └── .env.example         # Optional environment configuration
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React application with speech I/O & dynamic views
│   │   ├── translations.js  # Full UI translations for 8 Indian languages
│   │   ├── index.css        # Civic trust design system stylesheet
│   │   └── main.jsx         # Vite root entry
│   ├── index.html           # HTML template with Google Fonts
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration with backend API proxy
├── .gitignore               # Clean git exclusions (db, cache, node_modules)
└── README.md                # Project documentation & pitch guide
```

---

## 🚀 Getting Started Locally

### Prerequisites
- **Python 3.10+**
- **Node.js 18+ & npm**

---

### Step 1: Start the Backend

```bash
# 1. Navigate to backend directory
cd backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run FastAPI server
python -m uvicorn main:app --reload --port 8000
```
> Backend runs at `http://localhost:8000`  
> Interactive Swagger API docs: `http://localhost:8000/docs`

---

### Step 2: Start the Frontend

In a separate terminal:

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install frontend packages
npm install

# 3. Launch Vite development server
npm run dev
```
> Frontend runs at `http://localhost:5173`

---

## 🧪 Automated Testing

Run the comprehensive test suite to verify all endpoints, memory persistence, rule breakdowns, and PDF generation:

```bash
cd backend
python test_api.py
```

Expected output:
```text
--- 1. Testing GET /api/health ---
Health response: {'status': 'ok', 'schemes_loaded': 12}
--- 2. Testing POST /api/process (Farmer Citizen) ---
PM-KISAN status: confirmed
Sukanya Samriddhi status: confirmed
--- 3. Testing Memory Persistence across calls ---
Merged profile correctly preserved old & new facts
--- 4. Testing POST /api/followup ---
Follow-up question generated successfully
--- 5. Testing GET /api/draft/pdf (ReportLab generation) ---
PDF generated successfully! (Valid %PDF-1.4 header)
--- 6. Testing POST /api/translate ---
Translation response OK
--- 7. Testing GET /api/stats ---
Aggregate stats OK
>>> ALL BACKEND TESTS PASSED! <<<
```

---

## 📋 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status & total schemes loaded |
| `POST` | `/api/process` | Ingests `{ phone, text }`, extracts facts, merges memory, returns matches |
| `GET` | `/api/profile/{phone}` | Retrieves stored citizen profile & re-evaluated scheme matches |
| `POST` | `/api/followup` | Identifies missing criteria & generates proactive clarifying question |
| `POST` | `/api/translate` | Translates text for speech synthesis readback in native languages |
| `POST` | `/api/draft` | Generates formatted plain-text application draft |
| `GET` | `/api/draft/pdf` | Streams printable, formal ReportLab application PDF (`?phone=...&scheme_id=...`) |
| `GET` | `/api/stats` | Real-time aggregate civic metrics (citizens, matches, welfare value) |

---

## 🎯 60-Second Judge Demo Script

1. **Language Choice:** Open `http://localhost:5173` and select your preferred Indian language (e.g. **हिंदी** or **தமிழ்**). Notice the entire portal dynamically localizes.
2. **One-Click Citizen Profile:** Click **"🌾 Farmer with Daughter"** under *Quick Demo Profiles*.
3. **Instant Discovery:** Click **"Check What I Qualify For"**. Notice **PM-KISAN** and **Sukanya Samriddhi Yojana** confirm immediately with quoted Gazette clauses.
4. **Proactive Dialogue:** Scroll to the green follow-up card: *"CivicVoice Needs 1 Quick Detail"*. Click the quick chip **"BPL Ration Card Holder"**. Notice **Ayushman Bharat (₹5L cover)** and **PMAY-G (₹1.2L housing)** instantly upgrade to confirmed!
5. **Persistent Memory:** Notice the blue banner confirming that returning citizens retain all facts across calls without repeating themselves.
6. **Transparency:** Click **"▼ Why You Qualify"** to reveal rule-by-rule checks (`✅ Satisfied`, `⏳ Missing`).
7. **Official PDF:** Click **"📄 Download Official Form (PDF)"** to open the pre-filled official application form.
8. **Audio Readback:** Click **"🔊 Listen"** on any card to hear native voice output.
9. **Impact Metric:** Click **"📊 Impact Stats"** in the top navbar to showcase aggregate welfare unlocked.

---

## 👥 Team CivicVoice

- **Event:** Luminix'26 Hackathon
- **Track:** Multilingual Voice Assistant for Government Services
- **Repository:** [https://github.com/advaiithh/CivicVoice](https://github.com/advaiithh/CivicVoice)
