# tests/backend/test_session_lifecycle.py
import pytest
import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch
import socketio
import uvicorn

SERVER_PORT = 8765  # use a non-standard port to avoid conflicts


@pytest.fixture(scope="module")
def patched_server():
    mock_gemini = MagicMock()
    mock_gemini.connect = AsyncMock()
    mock_gemini.send_audio = AsyncMock()
    mock_gemini.send_context = AsyncMock()
    mock_gemini.close = AsyncMock()
    mock_gemini.running = True
    mock_gemini.session = MagicMock()
    mock_gemini.session.send_client_content = AsyncMock()

    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()), \
         patch("firebase_admin.auth.verify_id_token", return_value={
             "uid": "test_uid_123",
             "firebase": {"sign_in_provider": "anonymous"}
         }), \
         patch("gemini_client.GeminiLiveClient", return_value=mock_gemini), \
         patch("rag.chroma_backend.ChromaBackend.ingest_documents"), \
         patch("rag.chroma_backend.ChromaBackend.retrieve", return_value=""), \
         patch("rag.chroma_backend.ChromaBackend.delete_participant"), \
         patch("main.download_and_extract", return_value=([], [])), \
         patch("main.delete_user_files"):

        import importlib
        import main
        importlib.reload(main)

        config = uvicorn.Config(
            main.socket_app,
            host="127.0.0.1",
            port=SERVER_PORT,
            log_level="error"
        )
        server = uvicorn.Server(config)

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        # Wait for server to be ready
        time.sleep(1.5)

        yield mock_gemini

        server.should_exit = True
        thread.join(timeout=3)


class TestSessionLifecycle:
    async def test_full_session_flow(self, patched_server):
        mock_gemini = patched_server
        client = socketio.AsyncSimpleClient()

        await client.connect(f"http://127.0.0.1:{SERVER_PORT}")

        await client.emit("start_session", {
            "claim": "I want to build a B2B SaaS for HR teams",
            "idToken": "fake_token",
            "isAnonymous": True,
            "documentPaths": []
        })

        # Drain events until we get session_ready — other events may arrive first
        session_ready = False
        for _ in range(10):
            event = await client.receive(timeout=3)
            if event[0] == "session_ready":
                session_ready = True
                break

        assert session_ready, "Never received session_ready event"

        await client.emit("audio_chunk", bytes(1024))
        await asyncio.sleep(0.1)

        await client.emit("end_session")
        await asyncio.sleep(0.3)

        mock_gemini.close.assert_called_once()
        await client.disconnect()

    async def test_rejects_empty_claim(self, patched_server):
        client = socketio.AsyncSimpleClient()
        await client.connect(f"http://127.0.0.1:{SERVER_PORT}")

        await client.emit("start_session", {
            "claim": "",
            "idToken": "fake_token",
            "isAnonymous": True,
            "documentPaths": [],
            "stage": "early"
        })

        event = await client.receive(timeout=3)
        assert event[0] == "error"
        assert "enter your position or upload documents" in event[1]["message"].lower()

        await client.disconnect()

    async def test_rejects_document_paths_for_other_users(self, patched_server):
        client = socketio.AsyncSimpleClient()
        await client.connect(f"http://127.0.0.1:{SERVER_PORT}")

        await client.emit("start_session", {
            "claim": "I want to build a B2B SaaS for HR teams",
            "idToken": "fake_token",
            "isAnonymous": True,
            "documentPaths": ["users/other-user/documents/pitch.pdf"],
            "stage": "early"
        })

        error_event = None
        for _ in range(5):
            event = await client.receive(timeout=3)
            if event[0] == "error":
                error_event = event
                break

        assert error_event is not None, "Never received error event"
        assert "invalid uploaded document reference" in error_event[1]["message"].lower()

        await client.disconnect()

    async def test_invalid_stage_falls_back_gracefully(self, patched_server):
        """An unrecognised stage value must not crash the session."""
        client = socketio.AsyncSimpleClient()
        await client.connect(f"http://127.0.0.1:{SERVER_PORT}")

        await client.emit("start_session", {
            "claim": "I want to build an AI HR tool",
            "idToken": "fake_token",
            "isAnonymous": True,
            "documentPaths": [],
            "stage": "seed"  # invalid value — should fall back to 'late'
        })

        session_ready = False
        for _ in range(10):
            event = await client.receive(timeout=3)
            if event[0] == "session_ready":
                session_ready = True
                break
            if event[0] == "error":
                break

        assert session_ready, "Invalid stage value caused an error instead of falling back to late"
        await client.disconnect()

    async def test_missing_stage_key_starts_session(self, patched_server):
        """Missing stage should behave identically to stage='late'."""
        client = socketio.AsyncSimpleClient()
        await client.connect(f"http://127.0.0.1:{SERVER_PORT}")

        await client.emit("start_session", {
            "claim": "I want to build an AI HR tool",
            "idToken": "fake_token",
            "isAnonymous": True,
            "documentPaths": []
            # no 'stage'
        })

        session_ready = False
        for _ in range(10):
            event = await client.receive(timeout=3)
            if event[0] == "session_ready":
                session_ready = True
                break

        assert session_ready, "Missing stage key broke session start"
        await client.disconnect()

    async def test_rate_limit_enforced(self, patched_server):
        clients = []
        blocked = False

        for _ in range(12):
            c = socketio.AsyncSimpleClient()
            try:
                await c.connect(
                    f"http://127.0.0.1:{SERVER_PORT}",
                    headers={"X-Forwarded-For": "9.9.9.9"}
                )
                clients.append(c)
            except Exception:
                blocked = True
                break

        assert blocked or len(clients) <= 10

        for c in clients:
            await c.disconnect()
