# Devil's Advocate

**Devil's Advocate** is a voice-based AI application that stress-tests business ideas through live spoken debate. You pitch your idea; the AI argues against it — challenging your market assumptions, unit economics, competitive positioning, and core logic in real time.

Built as a submission for the **Google Gemini Live Agent Challenge** and as the foundation of a **UIST research project** comparing AI debate feedback against traditional peer review.

**Live demo:** [devils-advocate-ec48b.web.app](https://devils-advocate-ec48b.web.app)

---

## Features

### Live Voice Debate
Powered by the Gemini Live API (`gemini-2.5-flash-native-audio-latest`), the agent conducts a fully spoken, bidirectional conversation with real-time audio streaming and interruption support. The agent alternates between **Challenge Mode** (attacking a claim with specific data) and **Question Mode** (forcing the user to confront an unexamined assumption).

### RAG-Grounded Challenges
A ChromaDB vector store (ephemeral, in-process) is seeded at startup with a curated knowledge base covering startup failure patterns, market sizing benchmarks, business model tradeoffs, and competition dynamics. Each turn, relevant chunks are retrieved and injected into the agent's context. Users can also upload their own pitch documents (PDF or `.txt`) which are chunked and merged into their session's corpus.

### Google Search Grounding
The agent has native access to Google Search via Gemini's tool support, allowing it to cite real competitor funding, actual market size figures, and recent data rather than hallucinating statistics.

### Claim Classification & Argument Tracker
After each user turn, `gemini-2.5-flash-lite` classifies the response as `DEFENDED`, `CONCEDED`, `NEW_CLAIM`, or `DEFLECTED` with a 1–10 strength score. The frontend renders a live Argument Tracker showing the last 5 classified turns with color-coded status.

### Post-Debate Report
At session end, the backend runs a judge pass and a full report generation pass concurrently. The report includes an overall score (1–10), verdict, strengths, weaknesses, the sharpest moment from the founder, the biggest gap that went unanswered, and concrete next steps.

### Live Transcript
Full transcript display with four speaker types: agent, user, reasoning (Gemini thinking tokens), and buffered partial streaming for both sides.

### Firebase Auth & Data Logging
Supports anonymous sign-in, Google, and GitHub OAuth. Session data (transcripts, claim events, interruption counts, final reports) is logged to Firestore. Anonymous users have their uploaded files deleted from Firebase Storage at session end. Consent toggle defaults to on; if consent is not given, data is permanently deleted on finalization.

### Rate Limiting & Input Validation
IP-based connection rate limiting, per-session audio chunk throttling, claim sanitization (500 char max, control character stripping, whitespace normalization), and Firebase ID token verification on every session start.

---

## Architecture

```
frontend/          React + Vite (Firebase Hosting)
  src/
    App.jsx                   # Main UI, audio pipeline, socket client
    hooks/useDebateSession.js # Audio scheduling, agent interrupt logic
    useDocumentUpload.js      # Firebase Storage upload/list/delete
    firebase.js               # Firebase SDK init

backend/           FastAPI + python-socketio (Cloud Run)
  main.py                     # Socket event handlers, session lifecycle
  gemini_client.py            # Gemini Live API wrapper
  prompts.py                  # System prompt + RAG context builder
  claim_tracker.py            # Per-turn classification via Flash Lite
  report.py                   # Post-debate report + judge generation
  session_state.py            # Turn history, claim events, session ID
  storage_utils.py            # Firebase Storage download + PDF extraction
  firebase_logger.py          # Firestore session logging
  validation.py               # Input sanitization
  rate_limiter.py             # IP + session rate limiting
  rag/
    base.py                   # RAGBackend ABC (swap-ready for Vertex AI)
    chroma_backend.py         # ChromaDB ephemeral implementation
  knowledge_base/             # Static .txt files loaded at startup

tests/
  backend/                    # pytest-asyncio integration + unit tests
```

**Infrastructure:** Cloud Run (backend, `--min-instances 0`), Firebase Hosting (frontend), Firestore (session logs), Firebase Storage (user uploads), Secret Manager (credentials), Cloud Build (CI/CD).

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Cloud project with the following enabled:
  - Gemini API (with a valid API key)
  - Firebase (Auth, Firestore, Storage)
  - Firebase Admin SDK service account key

---

### 1. Clone the repo

```bash
git clone https://github.com/josephstefurak/devils-advocate.git
cd devils-advocate
```

---

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_KEY_PATH=./firebase_key.json
FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
```

Place your Firebase Admin SDK service account JSON at `backend/firebase_key.json`.

Start the server:

```bash
uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
```

---

### 3. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
VITE_BACKEND_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

Start the dev server:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

### 4. Running Tests

```bash
# From repo root
pip install -r requirements-dev.txt
pytest -v
```

---

## Deployment

### Backend → Cloud Run

```bash
gcloud builds submit --config cloudbuild.yaml
```

Secrets (`GEMINI_API_KEY`, `firebase_key.json`) are managed via Secret Manager and mounted at runtime.

### Frontend → Firebase Hosting

```bash
cd frontend
npm run build
firebase deploy --only hosting
```

---

## Environment Variables Reference

| Variable | Location | Description |
|---|---|---|
| `GEMINI_API_KEY` | Backend `.env` / Secret Manager | Gemini API key |
| `FIREBASE_KEY_PATH` | Backend `.env` | Path to Firebase Admin SDK JSON |
| `FIREBASE_STORAGE_BUCKET` | Backend `.env` | Firebase Storage bucket name |
| `VITE_BACKEND_URL` | Frontend `.env.local` | Backend WebSocket URL |
| `VITE_FIREBASE_*` | Frontend `.env.local` | Firebase web app config values |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | FastAPI, python-socketio |
| AI | Gemini Live API (`gemini-2.5-flash-native-audio-latest`), Gemini Flash Lite |
| Vector Store | ChromaDB (ephemeral) |
| Auth & Storage | Firebase Auth, Firebase Storage |
| Database | Firestore |
| Hosting | Cloud Run (backend), Firebase Hosting (frontend) |
| CI/CD | Cloud Build, Secret Manager |

---

## License

MIT