import asyncio
import os
import time
import re

from dotenv import load_dotenv
load_dotenv()

import socketio
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from gemini_client import GeminiLiveClient
from session_state import SessionState
from prompts import build_system_prompt, build_rag_context
from rag import rag
from report import generate_report
from judges import build_judge_panel, run_live_judge_update, run_judge_panel, merge_verdicts
from google import genai as genai_client

from validation import (
    sanitize_claim,
    validate_audio_chunk,
    validate_document_paths,
    validate_participant_id,
    MAX_CLAIM_LENGTH,
)
from rate_limiter import limiter
from feedback import FeedbackSubmissionRequest, build_feedback_record
from firebase_logger import SessionLogger, save_post_debate_feedback
from storage_utils import download_and_extract, delete_user_files
from summary import summarize_documents
from firebase_admin import auth as fb_auth
from voice_selector import assign_voice

MAX_SESSION_DURATION = 3 * 60  # 3 minutes
MIN_TURNS_FOR_REPORT = 2  # require at least 2 user and 2 agent turns to generate report

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI()
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=[
        'https://devils-advocate-ec48b.web.app',
        'https://devils-advocate-ec48b.firebaseapp.com',
        'https://devils-advocate-488918.web.app',
        'http://localhost:5173',
        'http://localhost'
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
# { socket_id: { gemini: GeminiLiveClient, state: SessionState, judges: dict[str, OpenAIClient] } }
sessions = {}
last_retrieval = {}
missing_session_chunk_notified = set()


def finalize_session_logger(session, reason: str):
    logger = session.get('logger')
    if not logger:
        return

    consent = session.get('consent', True)
    try:
        logger.finalize(consent_given=consent)
    except Exception as e:
        print(f"Logging error ({reason} finalize): {e}")


def cancel_session_timeout(session):
    timeout_task = session.get('timeout_task')
    if not timeout_task or timeout_task.done():
        return
    if timeout_task is asyncio.current_task():
        return
    timeout_task.cancel()


async def enforce_session_time_limit(sid):
    await asyncio.sleep(MAX_SESSION_DURATION)
    if sid not in sessions:
        return
    await sio.emit('error', {'message': 'Session time limit reached.'}, to=sid)
    await end_session(sid)

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
    last_retrieval.pop(sid, None)
    missing_session_chunk_notified.discard(sid)
    session = sessions.pop(sid, None)
    if session:
        cancel_session_timeout(session)
        try:
            rag.delete_participant(session['participant_id'])
        except Exception as e:
            print(f"RAG cleanup error on disconnect: {e}")
        if session.get('is_anonymous'):
            await asyncio.get_event_loop().run_in_executor(
                None, delete_user_files, session['participant_id']
            )
        try:
            await session['gemini'].close()
        except Exception as e:
            print(f"Gemini close error on disconnect: {e}")
        finalize_session_logger(session, "disconnect")


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)        # italic
    text = re.sub(r'`(.*?)`', r'\1', text)          # inline code
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headers
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullets
    return text.strip()

@sio.event
async def pause_session(sid):
    if sid in sessions:
        sessions[sid]['paused'] = True

@sio.event
async def resume_session(sid):
    if sid in sessions:
        sessions[sid]['paused'] = False



@sio.event
async def start_session(sid, data):

    if not limiter.check_session_start(sid):
        await sio.emit('error', {'message': 'Too many sessions started. Please wait.'}, to=sid)
        return

    claim_raw = (data.get('claim') or '').strip()
    document_paths_raw = data.get('documentPaths', [])
    stage = data.get('stage', 'late') if data.get('stage') in ('early', 'late') else 'late'
    if not claim_raw and not document_paths_raw:
        await sio.emit(
            'error',
            {'message': 'Claim is empty. Enter your position or upload documents to get started.'},
            to=sid
        )
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

    try:
        document_paths = validate_document_paths(document_paths_raw, participant_id)
    except ValueError:
        await sio.emit('error', {'message': 'Invalid uploaded document reference.'}, to=sid)
        return

    print(f"Starting session for {sid}, uid: {uid}, anonymous: {is_anonymous}, claim: {claim or '(from documents)'}")

    try:
        state = SessionState(user_claim=claim, stage=stage)
        system_prompt = build_system_prompt(claim, stage=stage)

        logger = SessionLogger(
            session_id=state.session_id,
            user_claim=claim,
            uid=uid,
            is_anonymous=is_anonymous,
            stage=stage,
        )
        voice = assign_voice(state.session_id, logger)
        async def on_audio(audio_b64):
            if not sessions.get(sid, {}).get('paused', False):
                await sio.emit('agent_audio', audio_b64, to=sid)

        async def on_text(text, partial=False):
            
            if partial:
                await sio.emit('transcript_partial', {'speaker': 'agent', 'text': text}, to=sid)
            else:
                text = strip_markdown(text)
                state.add_turn('agent', text)
                await sio.emit('transcript', {'speaker': 'agent', 'text': text}, to=sid)
                try:
                    logger.log_turn('agent', text, state.turn_count)
                except Exception as e:
                    print(f"Logging error (on_text): {e}")

        async def on_user_text(text, partial=False):
            if partial:
                await sio.emit('transcript_partial', {'speaker': 'user', 'text': text}, to=sid)
            else:
                state.add_turn('user', text)
                await sio.emit('transcript', {'speaker': 'user', 'text': text}, to=sid)
                try:
                    logger.log_turn('user', text, state.turn_count)
                except Exception as e:
                    print(f"Logging error (on_user_text): {e}")

                async def _judge_turn(user_text):
                    judges = sessions.get(sid, {}).get('judges')
                    if not judges:
                        return
                    result = await run_live_judge_update(judges, state, user_text)
                    if result:
                        state.add_judge_update(user_text, result)
                        await sio.emit('claim_update', result, to=sid)
                        try:
                            logger.log_judge_update(result)
                        except Exception as e:
                            print(f"Logging error (_judge_turn): {e}")

                asyncio.create_task(_judge_turn(text))

        async def on_reasoning(text):
            #await sio.emit('transcript', {'speaker': 'reasoning', 'text': text}, to=sid)
            pass  # for now we're not surfacing reasoning events in the UI

        async def on_interrupted():
            await sio.emit('agent_interrupted', to=sid)
            try:
                logger.log_interruption()
            except Exception as e:
                print(f"Logging error (on_interrupted): {e}")

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
                    claim = (await summarize_documents(doc_texts)).strip()
                    if len(claim) > MAX_CLAIM_LENGTH:
                        claim = claim[:MAX_CLAIM_LENGTH - 3].rstrip() + "..."
                    claim = sanitize_claim(claim)
                except Exception as e:
                    print(f"[Session] Summary failed: {e}")
                    await sio.emit('error', {
                        'message': 'Could not summarize your documents. Try adding a short description above.'
                    }, to=sid)
                    return
                state = SessionState(user_claim=claim, stage=stage)
                system_prompt = build_system_prompt(claim, stage=stage)
                logger = SessionLogger(
                    session_id=state.session_id,
                    user_claim=claim,
                    uid=uid,
                    is_anonymous=is_anonymous,
                    stage=stage,
                )
        await asyncio.get_event_loop().run_in_executor(
            None, rag.ingest_documents, participant_id, doc_texts, doc_metas
        )

        async def on_error(message):
            await sio.emit('error', {'message': message}, to=sid)

        # 2. Connect Gemini
        await sio.emit('session_status', {'step': 'Connecting to debate engine...'}, to=sid)
        gemini = GeminiLiveClient(
            system_prompt=system_prompt,
            on_text=on_text,
            on_audio=on_audio,
            on_user_text=on_user_text,
            on_reasoning=on_reasoning,
            on_interrupted=on_interrupted,
            on_error=on_error,
            voice_name=voice,
        )
        await gemini.connect()

        # 3. Retrieve RAG context using the claim as the seed query and inject
        #    before the first turn so the opening challenge can reference documents
        await sio.emit('session_status', {'step': 'Preparing your opponent...'}, to=sid)
        rag_context = rag.retrieve(participant_id, claim, n_results=5)
        if rag_context:
            await gemini.send_context(build_rag_context(rag_context))

        # 4. Build judge panel for this session's stage
        judge_panel = build_judge_panel(stage)

        # 5. Show claim in transcript and send to agent — now fully context-aware
        sessions[sid] = {
            'gemini': gemini,
            'state': state,
            'judges': judge_panel,
            'participant_id': participant_id,
            'is_anonymous': is_anonymous,
            'document_paths': document_paths,
            'logger': logger,
            'started_at': time.time(),
            'consent': True,
            'paused': False,
            'stage': stage,
        }
        sessions[sid]['timeout_task'] = asyncio.create_task(enforce_session_time_limit(sid))

        await asyncio.sleep(0.1) # slight delay to ensure client is ready for incoming messages

        await sio.emit('transcript', {'speaker': 'user', 'text': claim}, to=sid)
        await gemini.session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": claim}]}],
            turn_complete=True
        )

        
        await sio.emit(
            'session_ready',
            {
                'sessionId': state.session_id,
                'maxDurationSeconds': MAX_SESSION_DURATION,
            },
            to=sid,
        )
    finally:
        if document_paths and sid not in sessions:
            print(f"[start_session] Setup failed for {sid}; cleaning up uploaded files for {uid}")
            await asyncio.get_event_loop().run_in_executor(
                None, delete_user_files, uid
            )

@sio.event
async def audio_chunk(sid, data):
    if sid not in sessions:
        if sid not in missing_session_chunk_notified:
            print(f"Dropping chunk — {sid} not in sessions")
            missing_session_chunk_notified.add(sid)
        return
    
    if not limiter.check_audio_chunk(sid):
        print(f"Rate limit dropping chunk for {sid}")  # ← add
        return

    try:
        audio_bytes = validate_audio_chunk(data)
    except ValueError as e:
        print(f"Invalid audio chunk from {sid}: {e}")  # ← add
        return

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
        recent = session['state'].get_recent_context(n=4)
        rag_context = rag.retrieve(session['participant_id'], recent, n_results=8)
        if rag_context:
            msg = build_rag_context(rag_context)
            await gemini.send_context(msg)

    await gemini.send_audio(audio_bytes)

async def with_retry(coro_fn, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            msg = str(e)
            if '429' in msg and attempt < max_retries:
                match = re.search(r'retry in (\d+(?:\.\d+)?)s', msg, re.IGNORECASE)
                delay = float(match.group(1)) if match else 30.0
                print(f"429 quota hit, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise e

@sio.event
async def end_session(sid):
    session = sessions.pop(sid, None)
    if session is None:
        return

    cancel_session_timeout(session)
    last_retrieval.pop(sid, None)

    try:
        rag.delete_participant(session['participant_id'])
    except Exception as e:
        print(f"RAG cleanup error: {e}")

    # Delete uploaded files for anonymous users
    if session.get('is_anonymous'):
        await asyncio.get_event_loop().run_in_executor(
            None, delete_user_files, session['participant_id']
        )
    try:
        await session['gemini'].close()
    except Exception as e:
        print(f"Gemini close error: {e}")

    state = session['state']

    if state.turn_count < MIN_TURNS_FOR_REPORT:
        await sio.emit('debate_report', None, to=sid)
        try:
            session['logger'].log_report_status("skipped", "short_session")
        except Exception as e:
            print(f"Logging error (short report status): {e}")
        finalize_session_logger(session, "short_session")
        await sio.disconnect(sid)
        return

    judges = session.get('judges', {})
    verdicts = []
    report = None

    try:
        verdicts = await with_retry(lambda: run_judge_panel(judges, state))
    except Exception as e:
        print(f"Judge panel failed after retries: {e}")

    merged = await merge_verdicts(verdicts)
    consensus = merged.get("consensus") if merged else None

    if consensus:
        await sio.emit('judge_result', consensus, to=sid)
        session['logger'].log_judge(merged)

    try:
        report = await with_retry(lambda: generate_report(state, verdicts))
    except Exception as e:
        print(f"Report failed after retries: {e}")

    judge_updates_list = state.to_dict()["judge_updates"]
    payload = {**report, "claim_events": judge_updates_list} if report else None
    await sio.emit('debate_report', payload, to=sid)  # always emits — fixes spinner hang
    if report:
        session['logger'].log_report(report)
    else:
        try:
            session['logger'].log_report_status("missing", "generation_failed_or_timeout")
        except Exception as e:
            print(f"Logging error (report status): {e}")

    finalize_session_logger(session, "end_session")
    await sio.disconnect(sid)
    print(f"Session ended. Turns: {len(state.turns)}")

@sio.event
async def set_consent(sid, data):
    if sid not in sessions:
        return
    sessions[sid]['consent'] = data.get('consent', True)
    print(f"Consent updated for {sid}: {sessions[sid]['consent']}")


@app.post("/session_feedback")
async def session_feedback(request: Request):
    try:
        payload = FeedbackSubmissionRequest.model_validate(await request.json())
    except ValidationError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid feedback payload.", "details": jsonable_encoder(exc.errors())},
        )
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    try:
        decoded = fb_auth.verify_id_token(payload.idToken)
        uid = decoded["uid"]
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Authentication failed."})

    try:
        feedback_record = build_feedback_record(payload.feedback)
        save_post_debate_feedback(payload.sessionId, uid, feedback_record)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})

    return JSONResponse(content={"ok": True})

# ── REST: extract a claim summary from uploaded documents ──────────
_genai = genai_client.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.post("/extract_claim")
async def extract_claim(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    id_token = data.get("idToken", "")
    document_paths = data.get("documentPaths", [])

    try:
        decoded = fb_auth.verify_id_token(id_token)
        uid = decoded['uid']
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Authentication failed."})

    if not limiter.check_extract_claim(uid):
        return JSONResponse(
            status_code=429,
            content={"error": "Claim generation limit reached. Please wait a few minutes."}
        )

    if not document_paths:
        return JSONResponse(content={"claim": ""})

    try:
        participant_id = validate_participant_id(uid)
        document_paths = validate_document_paths(document_paths, participant_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid uploaded document reference."})

    try:
        doc_texts, _ = await asyncio.get_event_loop().run_in_executor(
            None, download_and_extract, document_paths
        )
    except Exception as e:
        print(f"[extract_claim] download error: {e}")
        return JSONResponse(content={"claim": ""})

    if not doc_texts:
        return JSONResponse(content={"claim": ""})

    # Limit input to ~3000 words
    combined = " ".join(doc_texts)
    word_limit = 3000
    words = combined.split()
    if len(words) > word_limit:
        combined = " ".join(words[:word_limit])

    prompt = (
        "Summarize the following startup or business document into 2-3 sentences "
        "describing the core idea, the problem being solved, and the target market. "
        "Write it as a first-person pitch position (e.g. 'We are building ...'). "
        "Return only the summary, no preamble.\n\nDocument:\n\n" + combined
    )

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _genai.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
            )
        )
        claim_text = response.text.strip()
    except Exception as e:
        print(f"[extract_claim] Gemini error: {e}")
        return JSONResponse(content={"claim": ""})

    return JSONResponse(content={"claim": claim_text})

@app.get("/health")
async def health():
    return {"ok": True}

@app.on_event("startup")
async def startup():
    asyncio.create_task(limiter.periodic_cleanup())

# ── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)
