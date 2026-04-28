import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_disconnect_finalizes_session_with_current_consent():
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()), \
         patch("google.genai.Client"), \
         patch("rag.chroma_backend.ChromaBackend.ingest_documents"), \
         patch("rag.chroma_backend.ChromaBackend.retrieve", return_value=""), \
         patch("rag.chroma_backend.ChromaBackend.delete_participant"):
        import main
        importlib.reload(main)

        logger = MagicMock()
        gemini = MagicMock()
        gemini.close = AsyncMock()

        main.sessions.clear()
        main.last_retrieval["sid-1"] = 3
        main.sessions["sid-1"] = {
            "participant_id": "user-123",
            "is_anonymous": False,
            "gemini": gemini,
            "logger": logger,
            "consent": False,
        }
        main.rag.delete_participant = MagicMock()

        await main.disconnect("sid-1", reason="transport close")

        main.rag.delete_participant.assert_called_once_with("user-123")
        gemini.close.assert_awaited_once()
        logger.finalize.assert_called_once_with(consent_given=False)
        assert "sid-1" not in main.sessions
        assert "sid-1" not in main.last_retrieval


@pytest.mark.asyncio
async def test_enforce_session_time_limit_ends_active_session(monkeypatch):
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()), \
         patch("google.genai.Client"), \
         patch("rag.chroma_backend.ChromaBackend.ingest_documents"), \
         patch("rag.chroma_backend.ChromaBackend.retrieve", return_value=""), \
         patch("rag.chroma_backend.ChromaBackend.delete_participant"):
        import main
        importlib.reload(main)

        main.sessions.clear()
        main.sessions["sid-timeout"] = {"logger": MagicMock()}
        monkeypatch.setattr(main, "MAX_SESSION_DURATION", 0.01)
        monkeypatch.setattr(main.sio, "emit", AsyncMock())
        monkeypatch.setattr(main, "end_session", AsyncMock())

        await main.enforce_session_time_limit("sid-timeout")

        main.sio.emit.assert_awaited_once_with(
            "error",
            {"message": "Session time limit reached."},
            to="sid-timeout",
        )
        main.end_session.assert_awaited_once_with("sid-timeout")


@pytest.mark.asyncio
async def test_enforce_session_time_limit_ignores_missing_session(monkeypatch):
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()), \
         patch("google.genai.Client"), \
         patch("rag.chroma_backend.ChromaBackend.ingest_documents"), \
         patch("rag.chroma_backend.ChromaBackend.retrieve", return_value=""), \
         patch("rag.chroma_backend.ChromaBackend.delete_participant"):
        import main
        importlib.reload(main)

        main.sessions.clear()
        monkeypatch.setattr(main, "MAX_SESSION_DURATION", 0.01)
        monkeypatch.setattr(main.sio, "emit", AsyncMock())
        monkeypatch.setattr(main, "end_session", AsyncMock())

        await main.enforce_session_time_limit("sid-missing")

        main.sio.emit.assert_not_awaited()
        main.end_session.assert_not_awaited()
