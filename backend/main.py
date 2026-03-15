import asyncio
from email.mime import text
import os
from dotenv import load_dotenv
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gemini_client import GeminiLiveClient
from session_state import SessionState
from prompts import build_system_prompt, build_rag_context
from claim_tracker import classify_turn
from rag import rag
from report import generate_report, run_judge

from validation import sanitize_claim, validate_audio_chunk, validate_participant_id, MAX_CLAIM_LENGTH
from rate_limiter import limiter
from firebase_logger import SessionLogger
from storage_utils import download_and_extract, delete_user_files
from summary import summarize_documents
from firebase_admin import auth as fb_auth

import time

MAX_SESSION_DURATION = 20 * 60  # 20 minutes
MIN_TURNS_FOR_REPORT = 2  # require at least 2 user and 2 agent turns to generate report

load_dotenv()

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI()
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=[
        'https://devils-advocate-ec48b.web.app',
        'https://devils-advocate-ec48b.firebaseapp.com',
        'https://devils-advocate-488918.web.app',
        'http://localhost:5173'
    ]
)
socket_app = socketio.ASGIApp(sio, app)

app.add_middleware(CORSMiddleware,
    allow_origins=[
        'https://devils-advocate-ec48b.web.app',
        'https://devils-advocate-ec48b.firebaseapp.com',
        'https://devils-advocate-488918.web.app',
        'http://localhost:5173'
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Active sessions store ──────────────────────────────────────────
# { socket_id: { gemini: GeminiLiveClient, state: SessionState } }
sessions = {}
last_retrieval = {}

# ── Socket events ──────────────────────────────────────────────────
@sio.event
async def connect(sid, environ):
    ip = environ.get('HTTP_X_FORWARDED_FOR', environ.get('REMOTE_ADDR', 'unknown'))
    if not limiter.check_connection(ip):
        print(f"Rate limit: too many connections from {ip}")
        return False  # returning False rejects the connection
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid, reason=None):
    print(f"Client disconnected: {sid}, reason: {reason}")
    limiter.clear_sid(sid)
    session = sessions.pop(sid, None)
    if session:
        rag.delete_participant(session['participant_id'])  # add this
        await session['gemini'].close()

@sio.event
async def start_session(sid, data):

    if not limiter.check_session_start(sid):
        await sio.emit('error', {'message': 'Too many sessions started. Please wait.'}, to=sid)
        return

    claim_raw = (data.get('claim') or '').strip()
    document_paths = data.get('documentPaths', [])
    if not claim_raw and not document_paths:
        await sio.emit('error', {'message': 'Enter your position or upload documents to get started.'}, to=sid)
        return
    try:
        claim = sanitize_claim(claim_raw) if claim_raw else ''
    except ValueError as e:
        await sio.emit('error', {'message': str(e)}, to=sid)
        return

    await sio.emit('session_status', {'step': 'Authenticating...'}, to=sid)
    id_token = data.get('idToken', '')
    try:
        decoded = fb_auth.verify_id_token(id_token)
        uid = decoded['uid']
        is_anonymous = decoded.get('firebase', {}).get('sign_in_provider') == 'anonymous'
    except Exception:
        await sio.emit('error', {'message': 'Authentication failed.'}, to=sid)
        return

    try:
        participant_id = validate_participant_id(uid)
    except ValueError as e:
        await sio.emit('error', {'message': 'Invalid session identity.'}, to=sid)
        return

    print(f"Starting session for {sid}, uid: {uid}, anonymous: {is_anonymous}, claim: {claim or '(from documents)'}")

    state = SessionState(user_claim=claim)
    system_prompt = build_system_prompt(claim)

    logger = SessionLogger(
        session_id=state.session_id,
        user_claim=claim,
        uid=uid,
        is_anonymous=is_anonymous
    )

    async def on_audio(audio_b64):
        await sio.emit('agent_audio', audio_b64, to=sid)

    async def on_text(text, partial=False):
        if partial:
            await sio.emit('transcript_partial', {'speaker': 'agent', 'text': text}, to=sid)
        else:
            state.add_turn('agent', text)
            await sio.emit('transcript', {'speaker': 'agent', 'text': text}, to=sid)
            logger.log_turn('agent', text, state.turn_count)

    async def on_user_text(text, partial=False):
        if partial:
            await sio.emit('transcript_partial', {'speaker': 'user', 'text': text}, to=sid)
        else:
            state.add_turn('user', text)
            await sio.emit('transcript', {'speaker': 'user', 'text': text}, to=sid)
            logger.log_turn('user', text, state.turn_count)
            async def on_claim_result(result):
                state.add_claim_event(text, result)
                await sio.emit('claim_update', result, to=sid)
                logger.log_claim_event(result)
            asyncio.create_task(classify_turn(
                original_claim=state.user_claim,
                context=state.get_recent_context(n=6),
                user_turn=text,
                on_result=on_claim_result
            ))

    async def on_reasoning(text):
        await sio.emit('transcript', {'speaker': 'reasoning', 'text': text}, to=sid)

    async def on_interrupted():
        await sio.emit('agent_interrupted', to=sid)
        logger.log_interruption()

    # 1. Load and embed documents first so RAG is ready before agent speaks
    await sio.emit('session_status', {'step': 'Loading your documents...'}, to=sid)
    doc_texts, doc_metas = [], []
    if document_paths:
        doc_texts, doc_metas = await asyncio.get_event_loop().run_in_executor(
            None, download_and_extract, document_paths
        )
        print(f"[Session] Ingesting {len(doc_texts)} user document chunks for {uid}")
        # If user didn't type a claim, derive it from the document text
        if not claim:
            if not doc_texts:
                await sio.emit('error', {
                    'message': 'Could not extract text from your documents. Try adding a short description above or upload different files.'
                }, to=sid)
                return
            try:
                await sio.emit('session_status', {'step': 'Summarizing your materials...'}, to=sid)
                claim = await summarize_documents(doc_texts)
                if len(claim) > MAX_CLAIM_LENGTH:
                    claim = claim[:MAX_CLAIM_LENGTH - 3].rstrip() + "..."
            except Exception as e:
                print(f"[Session] Summary failed: {e}")
                await sio.emit('error', {
                    'message': 'Could not summarize your documents. Try adding a short description above.'
                }, to=sid)
                return
            state = SessionState(user_claim=claim)
            system_prompt = build_system_prompt(claim)
            logger = SessionLogger(
                session_id=state.session_id,
                user_claim=claim,
                uid=uid,
                is_anonymous=is_anonymous
            )
    rag.ingest_documents(participant_id, texts=doc_texts, metadatas=doc_metas)

    # 2. Connect Gemini
    await sio.emit('session_status', {'step': 'Connecting to debate engine...'}, to=sid)
    gemini = GeminiLiveClient(
        system_prompt=system_prompt,
        on_text=on_text,
        on_audio=on_audio,
        on_user_text=on_user_text,
        on_reasoning=on_reasoning,
        on_interrupted=on_interrupted
    )
    await gemini.connect()

    # 3. Retrieve RAG context using the claim as the seed query and inject
    #    before the first turn so the opening challenge can reference documents
    await sio.emit('session_status', {'step': 'Preparing your opponent...'}, to=sid)
    rag_context = rag.retrieve(participant_id, claim, n_results=5)
    if rag_context:
        await gemini.send_context(build_rag_context(rag_context))

    # 4. Show claim in transcript and send to agent — now fully context-aware
    await sio.emit('transcript', {'speaker': 'user', 'text': claim}, to=sid)
    await gemini.session.send_client_content(
        turns=[{"role": "user", "parts": [{"text": claim}]}],
        turn_complete=True
    )

    sessions[sid] = {
        'gemini': gemini,
        'state': state,
        'participant_id': participant_id,
        'is_anonymous': is_anonymous,
        'document_paths': document_paths,
        'logger': logger,
        'started_at': time.time(),
        'consent': True,
    }
    await sio.emit('session_ready', to=sid)

@sio.event
async def audio_chunk(sid, data):
    if sid not in sessions:
        return
    
    if not limiter.check_audio_chunk(sid):
        return  # silently drop — don't emit error on every chunk

    try:
        audio_bytes = validate_audio_chunk(data)
    except ValueError:
        return  # silently drop bad chunks

    session = sessions[sid]

    if time.time() - session['started_at'] > MAX_SESSION_DURATION:
        await sio.emit('error', {'message': 'Session time limit reached.'}, to=sid)
        await end_session(sid)
        return


    gemini = session['gemini']
    if not gemini.running:
        print(f"Dropping chunk — gemini not running for {sid}")
        return

    # Inject RAG context once per new user turn
    current_turn = session['state'].turn_count
    if last_retrieval.get(sid) != current_turn and current_turn > 0:
        last_retrieval[sid] = current_turn
        recent = session['state'].get_recent_context(n=2)
        rag_context = rag.retrieve(session['participant_id'], recent, n_results=5)
        if rag_context:
            msg = build_rag_context(rag_context)
            await gemini.send_context(msg)

    await gemini.send_audio(audio_bytes)

@sio.event
async def end_session(sid):
    session = sessions.pop(sid, None)
    if session is None:
        return

    rag.delete_participant(session['participant_id'])

    # Delete uploaded files for anonymous users
    if session.get('is_anonymous'):
        await asyncio.get_event_loop().run_in_executor(
            None, delete_user_files, session['participant_id']
        )
    await session['gemini'].close()
    state = session['state']

    if state.turn_count < MIN_TURNS_FOR_REPORT:
        await sio.emit('debate_report', None, to=sid)
        session['logger'].finalize(consent_given=session['consent'])
        await sio.disconnect(sid)
        return

    # Run judge and report concurrently
    judge_result, report = await asyncio.gather(
        run_judge(state),
        generate_report(state)
    )

    if judge_result:
        await sio.emit('judge_result', judge_result, to=sid)
        session['logger'].log_judge(judge_result)

    if report:
        await sio.emit('debate_report', report, to=sid)
        session['logger'].log_report(report)

    session['logger'].finalize(consent_given=session['consent'])
    await sio.disconnect(sid)
    print(f"Session ended. Turns: {len(state.turns)}")

@sio.event
async def set_consent(sid, data):
    if sid not in sessions:
        return
    sessions[sid]['consent'] = data.get('consent', True)
    print(f"Consent updated for {sid}: {sessions[sid]['consent']}")

# ── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)