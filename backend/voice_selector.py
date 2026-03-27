"""
voice_selector.py

Randomly assigns a Gemini Live voice for a session and logs it to Firestore.

Usage in main.py:
    from voice_selector import assign_voice
    voice = assign_voice(session_id, logger)
    # then pass voice to GeminiLiveClient(voice_name=voice, ...)
"""

import random
from firebase_logger import SessionLogger

# ── Available Gemini Live voices ──────────────────────────────────
# Source: https://ai.google.dev/api/generate-content#v1beta.VoiceConfig
# Update this list as Google adds/removes voices.

AVAILABLE_VOICES = [
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Aoede",
    "Orbit",
    "Zephyr",
    "Leda",
    "Orus",
    "Schedar",
]


def assign_voice(session_id: str, logger: SessionLogger) -> str:
    """
    Randomly selects a voice, logs it to the Firestore session document,
    and returns the voice name for use in GeminiLiveClient.

    Args:
        session_id: Firestore session document ID (used only for logging context)
        logger:     Active SessionLogger instance for this session

    Returns:
        Voice name string, e.g. "Fenrir"

    Guarantees:
        - Always returns a valid voice name, even if Firestore write fails
        - Firestore failure is logged but never propagates
    """
    voice = random.choice(AVAILABLE_VOICES)

    try:
        logger.log_voice(voice)
    except Exception as e:
        # Non-fatal — session proceeds with the chosen voice regardless
        print(f"[VoiceSelector] Failed to log voice '{voice}' for session {session_id}: {e}")

    print(f"[VoiceSelector] Session {session_id} assigned voice: {voice}")
    return voice
