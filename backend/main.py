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


load_dotenv()

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI()
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)
socket_app = socketio.ASGIApp(sio, app)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Active sessions store ──────────────────────────────────────────
# { socket_id: { gemini: GeminiLiveClient, state: SessionState } }
sessions = {}
last_retrieval = {}

# ── Socket events ──────────────────────────────────────────────────
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid, reason=None):
    print(f"Client disconnected: {sid}, reason: {reason}")
    session = sessions.pop(sid, None)
    if session:
        rag.delete_participant(session['participant_id'])  # add this
        await session['gemini'].close()

@sio.event
async def start_session(sid, data):
    claim = data.get('claim', '')
    print(f"Starting session for {sid}, claim: {claim}")
    participant_id = data.get("participant_id", sid)

    


    state = SessionState(user_claim=claim)
    system_prompt = build_system_prompt(claim)

    # Define callbacks that emit back to this socket
    async def on_audio(audio_b64):
        await sio.emit('agent_audio', audio_b64, to=sid)

    async def on_text(text, partial=False):
        if partial:
            await sio.emit('transcript_partial', {'speaker': 'agent', 'text': text}, to=sid)
        else:
            state.add_turn('agent', text)
            await sio.emit('transcript', {'speaker': 'agent', 'text': text}, to=sid)

    async def on_user_text(text, partial=False):
        if partial:
            await sio.emit('transcript_partial', {'speaker': 'user', 'text': text}, to=sid)
        else:
            state.add_turn('user', text)
            await sio.emit('transcript', {'speaker': 'user', 'text': text}, to=sid)
            # Fire claim classification in background (don't await — non-blocking)
            async def on_claim_result(result):
                state.add_claim_event(text, result)
                await sio.emit('claim_update', result, to=sid)
            asyncio.create_task(classify_turn(
                original_claim=state.user_claim,
                context=state.get_recent_context(n=6),
                user_turn=text,
                on_result=on_claim_result
            ))

    async def on_reasoning(text):
        await sio.emit('transcript', {'speaker': 'reasoning', 'text': text}, to=sid)   

    gemini = GeminiLiveClient(
        system_prompt=system_prompt,
        on_text=on_text,
        on_audio=on_audio,
        on_user_text=on_user_text,
        on_reasoning=on_reasoning
    )

    await gemini.connect()

    # Emit user's initial claim into transcript before session starts
    await sio.emit('transcript', {'speaker': 'user', 'text': claim}, to=sid)

    await gemini.session.send_client_content(
        turns=[{"role": "user", "parts": [{"text": claim}]}],
        turn_complete=True
    )

    rag.ingest_documents(participant_id, texts=[], metadatas=[])

    sessions[sid] = {'gemini': gemini, 'state': state, 'participant_id': participant_id}
    await sio.emit('session_ready', to=sid)

@sio.event
async def audio_chunk(sid, data):
    if sid not in sessions:
        return
    session = sessions[sid]
    gemini = session['gemini']
    if not gemini.running:
        print(f"Dropping chunk — gemini not running for {sid}")
        return

    # Inject RAG context once per new user turn
    current_turn = session['state'].turn_count
    if last_retrieval.get(sid) != current_turn and current_turn > 0:
        last_retrieval[sid] = current_turn
        recent = session['state'].get_recent_context(n=2)
        rag_context = rag.retrieve(session['participant_id'], recent, n_results=3)
        if rag_context:
            msg = build_rag_context(rag_context)
            await gemini.send_context(msg)

    await gemini.send_audio(bytes(data))

@sio.event
async def end_session(sid):
    session = sessions.pop(sid, None)
    if session is None:
        return
    rag.delete_participant(session['participant_id'])  # add this
    await session['gemini'].close()
    state = session['state']
    print(f"Session ended. Turns: {len(state.turns)}")

# ── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)