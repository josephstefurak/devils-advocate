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
    def __init__(self, session_id: str, user_claim: str, uid: str = None, is_anonymous: bool = True, stage: str = "late"):
        self.session_id = session_id
        self.ref = db.collection("sessions").document(session_id)
        self.ref.set({
            "session_id": session_id,
            "user_claim": user_claim,
            "stage": stage,
            "created_at": _now(),
            "ended_at": None,
            "consent_given": True,  # default to True until user explicitly updates it
            "user": {
                "uid": uid or "unknown",
                "is_anonymous": is_anonymous,
            },
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
                "new_claim_count": 0,
                "deflected_count": 0,
            }
        })
        self._strength_sum = 0
        self._strength_count = 0

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
    
    def log_judge(self, result: dict):
        self.ref.update({
            "judge_result": result
        })
    
    def log_voice(self, voice_name: str):
        self.ref.update({"voice": voice_name})

    def log_claim_event(self, event: dict):
        classification = event.get("classification", "").lower()
        strength = event.get("strength", 0)

        metric_key_map = {
            "defended": "defended_count",
            "conceded": "conceded_count",
            "new_claim": "new_claim_count",
            "deflected": "deflected_count",
        }
        metric_key = metric_key_map.get(classification)

        update = {
            "claim_events": firestore.ArrayUnion([{
                **event,
                "timestamp": _now(),
            }]),
        }

        if metric_key:
            update[f"metrics.{metric_key}"] = firestore.Increment(1)

        if strength:
            self._strength_sum += strength
            self._strength_count += 1
            update["metrics.avg_argument_strength"] = round(
                self._strength_sum / self._strength_count, 2
            )

        self.ref.update(update)

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