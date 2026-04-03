import asyncio
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from openai_client import OpenAIClient
from prompts import JUDGE_PROMPTS, JUDGE_SYNTHESIS_LABELS, VERDICT_PANEL_SYNTHESIS_PROMPT


# ── Per-turn model (replaces ClaimClassificationResult) ──────────────

class JudgeTurnScore(BaseModel):
    classification: Literal["DEFENDED", "CONCEDED", "NEW_CLAIM", "DEFLECTED"] = Field(
        description="Exactly one of: DEFENDED, CONCEDED, NEW_CLAIM, DEFLECTED"
    )
    strength: int = Field(description="1-10 score for how compelling the turn was")
    classification_rationale: str = Field(
        description=(
            "1-3 sentences: why this classification fits the user's latest turn and why it is not "
            "the next-best alternative (e.g. why DEFLECTED rather than DEFENDED). Cite the turn or agent attack."
        )
    )
    strength_rationale: str = Field(
        description=(
            "1-3 sentences: why this strength number for this classification, using the rubric "
            "(e.g. partial vs full rebuttal, evidence vs assertion)."
        )
    )
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


class VerdictPanelSynthesis(BaseModel):
    summary: str = Field(
        description=(
            "Consensus paragraphs on what judges agreed on, then Note: paragraphs for material "
            "disagreements between personality lenses, using the judge labels from the prompt."
        )
    )


_verdict_synthesis_client = OpenAIClient(system_prompt=VERDICT_PANEL_SYNTHESIS_PROMPT)


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
    """Merge per-turn judge scores: plurality classification; strength = mean of judges in that class only."""
    classifications = [s.classification for _, s in scores]
    counts = Counter(classifications)
    max_votes = max(counts.values())
    tied_labels = [c for c, n in counts.items() if n == max_votes]
    if len(tied_labels) == 1:
        consensus_classification = tied_labels[0]
    else:
        # Plurality tie: pick the label whose judges have the higher mean strength.
        consensus_classification = max(
            tied_labels,
            key=lambda c: sum(s.strength for _, s in scores if s.classification == c)
            / counts[c],
        )

    in_consensus = [(name, s) for name, s in scores if s.classification == consensus_classification]
    strengths_in = [s.strength for _, s in in_consensus]
    avg_strength = round(sum(strengths_in) / len(strengths_in)) if strengths_in else 0

    # Representative judge only from consensus-aligned votes (closest to that average).
    diffs = [(abs(s.strength - avg_strength), name, s) for name, s in in_consensus]
    diffs.sort(key=lambda x: x[0])
    representative = diffs[0][2] if diffs else scores[0][1]

    judge_scores = [
        {
            "judge_name": name,
            "classification": s.classification,
            "strength": s.strength,
            "classification_rationale": s.classification_rationale,
            "strength_rationale": s.strength_rationale,
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
        result = await client.generate(prompt, JudgeTurnScore, temperature=0.3, max_completion_tokens=2048)
        return (name, result)

    try:
        results = await asyncio.gather(
            *[_score_one(name, client) for name, client in judges.items()],
            return_exceptions=True,
        )
        valid: list[tuple[str, JudgeTurnScore]] = []
        for item in results:
            if isinstance(item, BaseException):
                continue
            name, score = item
            if isinstance(score, JudgeTurnScore):
                valid.append((name, score))
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

Your written summary MUST reflect your distinct MBTI VC persona from your system instructions—not a generic investor voice. Let your type's priorities shift emphasis across dimensions (e.g. ESTP weighs execution_risk and market-facing proof; INTJ weighs competitive_awareness and thesis depth; INFJ weighs whether mission and model align for the people affected).
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


def _fallback_panel_summary(verdicts: list[dict], consensus_overall: float) -> str:
    """If synthesis fails, use the single judge whose overall is closest to the panel average."""
    with_summary = [v for v in verdicts if (v.get("summary") or "").strip()]
    if not with_summary:
        return ""
    with_overall = [v for v in with_summary if v.get("overall") is not None]
    if with_overall:
        rep = min(
            with_overall,
            key=lambda v: abs(float(v["overall"]) - consensus_overall),
        )
        return str(rep["summary"]).strip()
    return str(with_summary[0]["summary"]).strip()


def _format_verdict_block(v: dict) -> str:
    name = v.get("judge_name", "unknown")
    label = JUDGE_SYNTHESIS_LABELS.get(name, name)
    overall = v.get("overall", "?")
    winner = v.get("winner", "?")
    summary = (v.get("summary") or "").strip()
    lines = [
        f"--- Judge key: {name} | Roster label: {label} ---",
        f"Overall: {overall}/10 | winner: {winner}",
    ]
    if v.get("scores"):
        s = v["scores"]
        lines.append(
            "Scores: "
            f"problem_clarity={s.get('problem_clarity')}, market_logic={s.get('market_logic')}, "
            f"execution_risk={s.get('execution_risk')}, competitive_awareness={s.get('competitive_awareness')}, "
            f"internal_coherence={s.get('internal_coherence')}"
        )
    lines.append(f"Summary: {summary}")
    return "\n".join(lines)


def _build_verdict_synthesis_prompt(verdicts: list[dict]) -> str:
    roster = "\n".join(
        f"- {k}: {label}" for k, label in sorted(JUDGE_SYNTHESIS_LABELS.items())
    )
    blocks = "\n\n".join(_format_verdict_block(v) for v in verdicts)
    return f"""ROSTER (use these exact labels when contrasting judges in Note: paragraphs):
{roster}

VERDICTS:
{blocks}
"""


async def synthesize_verdict_panel_summary(verdicts: list[dict]) -> str | None:
    """LLM synthesis of consensus + personality-based divergences across the panel."""
    if not verdicts:
        return None
    prompt = _build_verdict_synthesis_prompt(verdicts)
    out = await _verdict_synthesis_client.generate(
        prompt,
        VerdictPanelSynthesis,
        temperature=0.35,
        max_completion_tokens=2500,
    )
    text = (out.summary or "").strip()
    return text or None


async def merge_verdicts(verdicts: list[dict]) -> dict:
    """Average numeric scores; narrative summary via LLM (consensus + divergent Notes)."""
    if not verdicts:
        return {}

    all_scores = {}
    for key in ["problem_clarity", "market_logic", "execution_risk", "competitive_awareness", "internal_coherence"]:
        vals = [v["scores"][key] for v in verdicts if v.get("scores")]
        all_scores[key] = round(sum(vals) / len(vals), 1) if vals else 0

    overalls = [v["overall"] for v in verdicts if v.get("overall") is not None]
    consensus_overall = round(sum(overalls) / len(overalls), 1) if overalls else 0
    winner = "founder" if consensus_overall >= 6 else "agent"

    consensus_summary = ""
    try:
        synthesized = await synthesize_verdict_panel_summary(verdicts)
        if synthesized:
            consensus_summary = synthesized
    except Exception as e:
        print(f"Verdict panel synthesis failed: {e}")
    if not consensus_summary:
        consensus_summary = _fallback_panel_summary(verdicts, consensus_overall)

    return {
        "verdicts": verdicts,
        "consensus": {
            "scores": all_scores,
            "overall": consensus_overall,
            "winner": winner,
            "summary": consensus_summary,
        },
    }
