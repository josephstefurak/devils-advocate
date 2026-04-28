# tests/backend/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
os.environ.setdefault("GEMINI_API_KEY", "test-fake-key-12345")
os.environ.setdefault("OPENAI_API_KEY", "test-fake-key-12345")
os.environ.setdefault("FIREBASE_KEY_PATH", "/tmp/fake_firebase_key.json")

# ── Gemini mock ────────────────────────────────────────────────────
@pytest.fixture
def mock_gemini_response():
    """A fake GenerateContent response with a .text attribute."""
    def _make(text: str):
        response = MagicMock()
        response.text = text
        return response
    return _make

@pytest.fixture(autouse=False)
def mock_genai_client(mock_gemini_response):
    """Patches google.genai.Client so no real API calls are made."""
    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        # Make aio.models.generate_content an async mock
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=mock_gemini_response('{"classification": "DEFENDED", "summary": "test", "strength": 7, "reason": "test reason"}')
        )
        yield mock_client

# ── Firestore mock ─────────────────────────────────────────────────
@pytest.fixture
def mock_firestore_db():
    """In-memory fake Firestore — stores data in a plain dict."""
    store = {}

    class FakeDocRef:
        def __init__(self, doc_id):
            self.doc_id = doc_id
            store.setdefault(doc_id, {})

        def set(self, data):
            store[self.doc_id] = dict(data)

        def update(self, data):
            # Flatten dot-notation keys like "metrics.total_turns"
            for key, value in data.items():
                if "." in key:
                    parts = key.split(".", 1)
                    store[self.doc_id].setdefault(parts[0], {})
                    store[self.doc_id][parts[0]][parts[1]] = value
                else:
                    store[self.doc_id][key] = value

        def get(self):
            doc = MagicMock()
            doc.to_dict.return_value = dict(store.get(self.doc_id, {}))
            return doc

        def delete(self):
            store.pop(self.doc_id, None)

    class FakeCollection:
        def document(self, doc_id):
            return FakeDocRef(doc_id)

    class FakeDB:
        def collection(self, name):
            return FakeCollection()

    return FakeDB(), store

@pytest.fixture
def mock_firebase(mock_firestore_db):
    """Patches firebase_admin so SessionLogger can be instantiated without credentials."""
    fake_db, store = mock_firestore_db
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=fake_db), \
         patch("firebase_admin.firestore.ArrayUnion", side_effect=lambda x: x), \
         patch("firebase_admin.firestore.Increment", side_effect=lambda x: x):
        yield fake_db, store

# ── Socket.IO test client ──────────────────────────────────────────
@pytest.fixture
async def socket_client(mock_firebase, mock_genai_client):
    """
    Spins up the full Socket.IO + FastAPI app in-process.
    Patches all external services before import so nothing real is called.
    """
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client"):
        import socketio
        # Import app after patches are in place
        from main import socket_app
        client = socketio.AsyncSimpleClient()
        await client.connect(
            "http://localhost:8000",
            transports=["websocket"],
            socketio_path="/socket.io",
            headers={},
            # Use ASGI mode — no real server needed
            **{"asgi_app": socket_app}
        )
        yield client
        await client.disconnect()
