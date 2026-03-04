import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Init once
key_path = os.getenv("FIREBASE_KEY_PATH", "/secrets/firebase_key.json")
cred = credentials.Certificate(key_path)

firebase_admin.initialize_app(cred)
db = firestore.client()

def _now():
    return datetime.utcnow()

class SessionLogger:
    def __init__(self, session_id: str, user_claim: str):
        self.session_id = session_id
        self.ref = db.collection("sessions").document(session_id)
        self.ref.set({
            "session_id": session_id,
            "user_claim": user_claim,
            "created_at": _now(),
            "ended_at": None,
            "consent_given": False,
            "turns": [],
            "claim_events": [],
            "report": None,
            "metrics": {
                "total_turns": 0,
                "user_turns": 0,
                "agent_turns": 0,
                "interruption_count": 0,
                "defended_count": 0,
                "conceded_count": 0,
                "avg_argument_strength": 0,
            }
        })

    def log_turn(self, speaker: str, text: str, turn_index: int):
        self.ref.update({
            "turns": firestore.ArrayUnion([{
                "speaker": speaker,
                "text": text,
                "timestamp": _now(),
                "turn_index": turn_index,
            }]),
            f"metrics.total_turns": firestore.Increment(1),
            f"metrics.{'user' if speaker == 'user' else 'agent'}_turns": firestore.Increment(1),
        })

    def log_claim_event(self, event: dict):
        self.ref.update({
            "claim_events": firestore.ArrayUnion([{
                **event,
                "timestamp": _now(),
            }]),
            f"metrics.{event['classification'].lower()}_count": firestore.Increment(1),
        })
        # Recompute avg strength
        doc = self.ref.get().to_dict()
        events = doc.get("claim_events", [])
        strengths = [e.get("strength", 0) for e in events if e.get("strength")]
        if strengths:
            self.ref.update({
                "metrics.avg_argument_strength": round(sum(strengths) / len(strengths), 2)
            })

    def log_interruption(self):
        self.ref.update({
            "metrics.interruption_count": firestore.Increment(1)
        })

    def log_report(self, report: dict):
        self.ref.update({"report": report})

    def finalize(self, consent_given: bool):
        self.ref.update({
            "ended_at": _now(),
            "consent_given": consent_given,
        })
        # If no consent — delete the document entirely
        if not consent_given:
            self.ref.delete()
            print(f"[Firebase] Session {self.session_id} deleted — no consent")
        else:
            print(f"[Firebase] Session {self.session_id} logged")