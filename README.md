# Devil's Advocate

**Devil's Advocate** is a live voice AI debate system for stress-testing startup ideas. A founder presents an idea, the agent pushes back in real time with grounded counterarguments, and the app finishes with a judge scorecard plus a post-debate report.

Built for the **Google Gemini Live Agent Challenge** and for **UIUC CS 568 (User-Centered Machine Learning)** as a research prototype exploring whether adversarial AI feedback improves early-stage startup refinement.

**Live deployment:** [devils-advocate-488918.web.app](https://devils-advocate-488918.web.app/)

**Architecture diagram:** [docs/arch_diagram.pdf](docs/arch_diagram.pdf)

## What The Product Does

- Runs a fully spoken, interruptible debate using the Gemini Live API.
- Grounds the agent with a startup knowledge base, uploaded founder documents, and Google Search.
- Tracks whether the founder defended, conceded, deflected, or introduced a new claim.
- Generates a judge scorecard and a post-debate gap analysis at the end of the session.
- Logs sessions to Firebase for research when consent is enabled.

## Architecture

High-level flow:

1. The React/Vite frontend handles auth, document uploads, mic capture, audio playback, transcript UI, scorecards, and report export.
2. The FastAPI + Socket.IO backend manages session lifecycle, validation, rate limiting, RAG retrieval, Gemini Live streaming, and post-debate evaluation.
3. Firebase Auth identifies the user, Firebase Storage stores uploaded files, and Firestore stores consented session logs.
4. Gemini Live powers the debate loop, while lighter Gemini models classify turns, summarize uploaded materials, and generate judge/report outputs.

Submission artifact:

- Upload [docs/arch_diagram.pdf](docs/arch_diagram.pdf) to the Devpost image gallery or file upload so judges can find it quickly.

## Repo Layout

```text
frontend/          React + Vite app
backend/           FastAPI + Socket.IO backend
tests/backend/     Backend unit and integration tests
docs/              Planning docs, submission requirements, architecture diagram
```

## New Contributor Setup

If you do not already have local credentials, ask a teammate for access to the shared project resources before you start.

You will need:

- Access to the shared Firebase project.
- Access to the shared Google Cloud project.
- The Firebase web app config values for the frontend.
- A Gemini API key, or confirmation of which shared key/project to use locally.
- A Firebase Admin SDK service account JSON for local backend access.
- Firestore and Firebase Storage access in the shared project.
- Firebase Auth provider setup for `Anonymous`, `Google`, and `GitHub`.
- Authorized Firebase Auth domains for `localhost`, `127.0.0.1`, and the deployed Hosting domains.

Recommended teammate handoff checklist:

1. Add you to the Firebase and Google Cloud projects.
2. Share the Firebase web app config values.
3. Share a local-use service account JSON with Firestore and Storage access.
4. Confirm the correct `FIREBASE_STORAGE_BUCKET` value.
5. Confirm the Gemini API key or local secret workflow.
6. Confirm that Google and GitHub auth providers are enabled in Firebase Auth.

## Local Development

### Prerequisites

- Python 3.11, 3.12, or 3.13
- [uv](https://docs.astral.sh/uv/) for Python environment management
- Node.js 18+
- npm

Optional but useful:

- Firebase CLI for Hosting deploys
- Google Cloud CLI for Cloud Run / Cloud Build work

Avoid Python 3.14 for now. `chromadb` in the current dependency set is not fully compatible with it in local tests.

### 1. Clone the Repo

```bash
git clone https://github.com/josephstefurak/devils-advocate.git
cd devils-advocate
```

### 2. Set Up The Backend With `uv`

Create a local virtual environment and install both runtime and test dependencies:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r backend/requirements.txt -r requirements-dev.txt
```

Create the backend environment file from the example:

```bash
cp backend/.env.example backend/.env
```

Update `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_KEY_PATH=./firebase_key.json
FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
```

Place the Firebase Admin SDK JSON at:

```text
backend/firebase_key.json
```

Start the backend:

```bash
cd backend
python -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
```

### 3. Set Up The Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Create the frontend environment file from the example:

```bash
cp .env.local.example .env.local
```

Update `frontend/.env.local`:

```env
VITE_BACKEND_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MEASUREMENT_ID=...
```

Start the frontend:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 4. Auth Requirements For Local Testing

If Google or GitHub sign-in does not work locally, check Firebase Auth before debugging the app code:

1. `Anonymous`, `Google`, and `GitHub` providers must be enabled.
2. `localhost` and `127.0.0.1` must be listed under Firebase Auth authorized domains.
3. Your Firebase web config must match the same project that owns the enabled auth providers.

## Local Verification

This repo does **not** have a CI/CD safety net for your branch, so validate locally before opening a PR.

Recommended local checks:

1. Run backend tests:

```bash
source .venv/bin/activate
python -m pytest -v
```

2. Run frontend tests:

```bash
cd frontend
npm test
```

3. Manual product checks:

- Start a debate with a typed claim only.
- Start a debate with uploaded documents only.
- Complete a full session and verify transcript, claim tracker, judge scorecard, share flow, and PDF export.
- Compare behavior against the deployed site at [devils-advocate-488918.web.app](https://devils-advocate-488918.web.app/), but treat local testing as the source of truth for branch validation.

## Deployment Notes

### Public Demo

The current team deployment used for demos and submission materials is:

- [https://devils-advocate-488918.web.app/](https://devils-advocate-488918.web.app/)

### Backend Deployment

This repo does not currently include a checked-in `cloudbuild.yaml` or a full CI/CD pipeline.

For Google Cloud deployment, coordinate with the team member who owns production access and ensure the following are configured:

- A Cloud Run service for the backend container built from [backend/Dockerfile](backend/Dockerfile).
- Secret management for `GEMINI_API_KEY`.
- A mounted or otherwise accessible Firebase Admin SDK key file at the path referenced by `FIREBASE_KEY_PATH`.
- Runtime environment variables including `FIREBASE_STORAGE_BUCKET`.
- CORS/auth settings aligned with the deployed frontend domains.

### Frontend Deployment

The frontend is deployed with Firebase Hosting using [firebase.json](firebase.json):

```bash
cd frontend
npm run build
firebase deploy --only hosting
```

## Submission Checklist

For the Gemini Live Agent Challenge / Devpost submission, make sure the repo supports:

- Public code repository with reproducible local setup instructions.
- Clear description of Gemini, Firebase, and Google Cloud usage.
- Architecture diagram: [docs/arch_diagram.pdf](docs/arch_diagram.pdf).
- Public demo link: [devils-advocate-488918.web.app](https://devils-advocate-488918.web.app/).
- Proof-of-deployment recording showing the deployed frontend plus the Google Cloud backend/service view.
- Demo video showing the real multimodal live-agent workflow, not mockups.

## Environment Variables Reference

| Variable | Location | Description |
|---|---|---|
| `GEMINI_API_KEY` | `backend/.env` | Gemini API key used by backend agent flows |
| `FIREBASE_KEY_PATH` | `backend/.env` | Path to local Firebase Admin SDK JSON |
| `FIREBASE_STORAGE_BUCKET` | `backend/.env` | Firebase Storage bucket for uploaded docs |
| `VITE_BACKEND_URL` | `frontend/.env.local` | Local backend URL |
| `VITE_FIREBASE_API_KEY` | `frontend/.env.local` | Firebase web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | `frontend/.env.local` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | `frontend/.env.local` | Firebase project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | `frontend/.env.local` | Firebase Storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | `frontend/.env.local` | Firebase messaging sender ID |
| `VITE_FIREBASE_APP_ID` | `frontend/.env.local` | Firebase app ID |
| `VITE_FIREBASE_MEASUREMENT_ID` | `frontend/.env.local` | Firebase Analytics measurement ID |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Firebase Web SDK |
| Backend | FastAPI, python-socketio |
| AI | Gemini Live API, Gemini Flash Lite |
| Retrieval | ChromaDB + uploaded document chunks |
| Auth / Storage | Firebase Auth, Firebase Storage |
| Logging | Firestore |
| Hosting | Firebase Hosting, Cloud Run |
| Local Python Workflow | `uv` + `requirements.txt` |

## License

MIT
