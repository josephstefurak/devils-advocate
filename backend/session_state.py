from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import uuid

@dataclass
class Turn:
    speaker: Literal['user', 'agent']
    text: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    argument_type: str = ""  # evidence | analogy | assertion | question


@dataclass
class JudgeUpdate:
    user_turn: str
    classification: str  # consensus: DEFENDED | CONCEDED | NEW_CLAIM | DEFLECTED
    summary: str
    strength: int  # consensus: average of judges (rounded)
    suggested_argument: str = ""  # from representative judge
    judge_scores: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SessionState:
    user_claim: str
    turns: list[Turn] = field(default_factory=list)
    committed_position: str = ""
    judge_updates: list[JudgeUpdate] = field(default_factory=list)
    turn_count: int = 0
    stage: str = "late"
    session_id: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + str(uuid.uuid4())[:8]
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

    def add_judge_update(self, user_turn: str, result: dict):
        self.judge_updates.append(JudgeUpdate(
            user_turn=user_turn,
            classification=result.get("classification", ""),
            summary=result.get("summary", ""),
            strength=result.get("strength", 0),
            suggested_argument=result.get("suggested_argument", ""),
            judge_scores=result.get("judge_scores", []),
        ))

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_claim": self.user_claim,
            "stage": self.stage,
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
            "judge_updates": [
                {
                    "user_turn": u.user_turn,
                    "classification": u.classification,
                    "summary": u.summary,
                    "strength": u.strength,
                    "suggested_argument": u.suggested_argument,
                    "judge_scores": u.judge_scores,
                    "timestamp": u.timestamp,
                }
                for u in self.judge_updates
            ],
        }
