import asyncio
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from openai_client import OpenAIClient
from prompts import JUDGE_PROMPTS


# ── Per-turn model (replaces ClaimClassificationResult) ──────────────

class JudgeTurnScore(BaseModel):
    classification: Literal["DEFENDED", "CONCEDED", "NEW_CLAIM", "DEFLECTED"] = Field(
        description="Exactly one of: DEFENDED, CONCEDED, NEW_CLAIM, DEFLECTED"
    )
    strength: int = Field(description="1-10 score for how compelling the turn was")
    summary: str = Field(description="One sentence summary of what the user argued")
    reaction: str = Field(description="One sentence reaction from this judge's perspective")
    suggested_argument: str = Field(
        default="",
        description="1-3 sentences on the strongest argument the user could have made, from this judge's perspective. Maximum 85 words.",
    )


# ── End-of-session model (replaces JudgeResult) ─────────────────────

class JudgeScores(BaseModel):
    problem_clarity: float = Field(description="1-10: Problem Detail/Unmet Need, Solution Detail, Customer Segment")
    market_logic: float = Field(description="1-10: Market, Go to Market — market size, beachhead, TAM, distribution")
    execution_risk: float = Field(description="1-10: Product Readiness, Traction, Commercialization, Team")
    competitive_awareness: float = Field(description="1-10: Competition, Competitive Advantage")
    internal_coherence: float = Field(description="1-10: Consistency and logical soundness of arguments throughout")


class JudgeVerdict(BaseModel):
    scores: JudgeScores = Field(description="Scores for each dimension (1-10)")
    overall: float | None = Field(
        default=None,
        description="Average of the five scores, rounded to 1 decimal.",
    )
    winner: str = Field(description='"founder" if overall >= 6, "agent" if < 6')
    summary: str = Field(description="2-3 sentence verdict on how the founder performed, from this judge's perspective")


# ── Panel construction ───────────────────────────────────────────────

def build_judge_panel(stage: str) -> dict[str, OpenAIClient]:
    """Build a dict of judge_name -> OpenAIClient, one per MBTI persona."""
    return {
        name: OpenAIClient(system_prompt=prompt_fn(stage))
        for name, prompt_fn in JUDGE_PROMPTS.items()
    }


# ── Per-turn live scoring ────────────────────────────────────────────

def _build_turn_prompt(original_claim: str, context: str, user_turn: str) -> str:
    return f"""USER'S ORIGINAL CLAIM: {original_claim}

RECENT DEBATE CONTEXT:
{context}

USER'S LATEST TURN: "{user_turn}"
"""


def _merge_turn_scores(scores: list[tuple[str, JudgeTurnScore]]) -> dict:
    """Merge individual judge turn scores into a consensus result."""
    classifications = [s.classification for _, s in scores]
    counts = Counter(classifications)
    consensus_classification = counts.most_common(1)[0][0]

    strengths = [s.strength for _, s in scores]
    avg_strength = round(sum(strengths) / len(strengths))

    # Pick the representative judge (closest to average strength)
    diffs = [(abs(s.strength - avg_strength), name, s) for name, s in scores]
    diffs.sort(key=lambda x: x[0])
    representative = diffs[0][2]

    judge_scores = [
        {
            "judge_name": name,
            "classification": s.classification,
            "strength": s.strength,
            "summary": s.summary,
            "reaction": s.reaction,
            "suggested_argument": s.suggested_argument,
        }
        for name, s in scores
    ]

    return {
        "classification": consensus_classification,
        "strength": avg_strength,
        "summary": representative.summary,
        "suggested_argument": representative.suggested_argument,
        "judge_scores": judge_scores,
    }


async def run_live_judge_update(
    judges: dict[str, OpenAIClient],
    state,
    user_turn: str,
) -> dict | None:
    """Fire all judges in parallel for a single user turn, return merged result."""
    prompt = _build_turn_prompt(
        original_claim=state.user_claim,
        context=state.get_recent_context(n=6),
        user_turn=user_turn,
    )

    async def _score_one(name: str, client: OpenAIClient):
        result = await client.generate(prompt, JudgeTurnScore, temperature=0.3, max_completion_tokens=1024)
        return (name, result)

    try:
        results = await asyncio.gather(
            *[_score_one(name, client) for name, client in judges.items()],
            return_exceptions=True,
        )
        valid = [(name, score) for name, score in results if not isinstance((name, score), BaseException) and isinstance(score, JudgeTurnScore)]
        if not valid:
            print("Judge live update: all judges failed")
            return None
        return _merge_turn_scores(valid)
    except Exception as e:
        print(f"Judge live update error: {e}")
        return None


# ── End-of-session full verdict ──────────────────────────────────────

_VERDICT_PROMPT_TEMPLATE = """You are delivering your FINAL VERDICT on this debate as a VC judge.

ORIGINAL CLAIM: {claim}

FULL TRANSCRIPT:
{transcript}

Score the FOUNDER (not the AI) across the five dimensions. If the transcript contains fewer than 2 substantive exchanges, return all scores as 0 and set summary to "Insufficient debate content to evaluate."

Compute overall as the average of the five scores (1 decimal). Set winner to "founder" if overall >= 6, "agent" if < 6.
"""


async def run_judge_panel(
    judges: dict[str, OpenAIClient],
    state,
) -> list[dict]:
    """Run all judges for final end-of-session verdicts. Returns list of verdict dicts."""
    transcript_text = "\n".join(
        f"{t.speaker.upper()}: {t.text}" for t in state.turns
    )
    prompt = _VERDICT_PROMPT_TEMPLATE.format(
        claim=state.user_claim,
        transcript=transcript_text,
    )

    async def _verdict_one(name: str, client: OpenAIClient):
        result = await client.generate(prompt, JudgeVerdict, temperature=0.2, max_completion_tokens=4000)
        verdict = result.model_dump()
        verdict["judge_name"] = name
        if verdict.get("overall") is None and verdict.get("scores"):
            s = verdict["scores"]
            verdict["overall"] = round(
                (s["problem_clarity"] + s["market_logic"] + s["execution_risk"]
                 + s["competitive_awareness"] + s["internal_coherence"]) / 5, 1
            )
        return verdict

    results = await asyncio.gather(
        *[_verdict_one(name, client) for name, client in judges.items()],
        return_exceptions=True,
    )
    valid = [r for r in results if isinstance(r, dict)]
    if not valid:
        print("Judge panel: all judges failed")
    return valid


def merge_verdicts(verdicts: list[dict]) -> dict:
    """Merge multiple judge verdicts into a consensus result compatible with the existing frontend."""
    if not verdicts:
        return {}

    all_scores = {}
    for key in ["problem_clarity", "market_logic", "execution_risk", "competitive_awareness", "internal_coherence"]:
        vals = [v["scores"][key] for v in verdicts if v.get("scores")]
        all_scores[key] = round(sum(vals) / len(vals), 1) if vals else 0

    overalls = [v["overall"] for v in verdicts if v.get("overall") is not None]
    consensus_overall = round(sum(overalls) / len(overalls), 1) if overalls else 0
    winner = "founder" if consensus_overall >= 6 else "agent"

    summaries = [v.get("summary", "") for v in verdicts if v.get("summary")]
    consensus_summary = " | ".join(summaries) if summaries else ""

    return {
        "verdicts": verdicts,
        "consensus": {
            "scores": all_scores,
            "overall": consensus_overall,
            "winner": winner,
            "summary": consensus_summary,
        },
    }
