from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class Turn:
    speaker: Literal['user', 'agent']
    text: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    argument_type: str = ""  # evidence | analogy | assertion | question


@dataclass
class ClaimEvent:
    user_turn: str
    classification: str  # DEFENDED | CONCEDED | NEW_CLAIM | DEFLECTED
    summary: str
    strength: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class SessionState:
    user_claim: str
    turns: list[Turn] = field(default_factory=list)
    committed_position: str = ""
    claim_events: list = field(default_factory=list)
    turn_count: int = 0
    session_id: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    )
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_turn(self, speaker: str, text: str):
        self.turns.append(Turn(speaker=speaker, text=text))
        self.turn_count += 1

    def get_user_claims(self) -> list[str]:
        return [t.text for t in self.turns if t.speaker == 'user']

    def get_recent_context(self, n: int = 6) -> str:
        recent = self.turns[-n:] if len(self.turns) >= n else self.turns
        return "\n".join([f"{t.speaker.upper()}: {t.text}" for t in recent])
    
    def add_claim_event(self, user_turn: str, result: dict):  
        self.claim_events.append(ClaimEvent(
            user_turn=user_turn,
            classification=result.get("classification", ""),
            summary=result.get("summary", ""),
            strength=result.get("strength", 0),
        ))

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_claim": self.user_claim,
            "turn_count": self.turn_count,
            "started_at": self.started_at,
            "turns": [
                {
                    "speaker": t.speaker,
                    "text": t.text,
                    "timestamp": t.timestamp
                }
                for t in self.turns
            ],
            "claim_events": [ 
                {
                    "user_turn": c.user_turn,
                    "classification": c.classification,
                    "summary": c.summary,
                    "strength": c.strength,
                    "timestamp": c.timestamp,
                }
                for c in self.claim_events
            ],
        }