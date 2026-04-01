import asyncio

from pydantic import BaseModel, Field

from openai_client import OpenAIClient
from prompts import REPORT_AGGREGATOR_PROMPT


# ── Report structured output (unchanged shape for frontend compat) ───

class ReportResult(BaseModel):
    idea_summary: str = Field(
        default="",
        description="2-3 sentence description of the business idea as it stood by the END of the debate",
    )
    overall_score: float = Field(description="1-10 score (10 = exceptionally well-defended)")
    verdict: str = Field(
        default="",
        description="One sentence verdict explaining the score",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="2-4 specific strengths with transcript evidence",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="2-4 specific weaknesses with transcript evidence",
    )
    sharpest_moment: str = Field(
        default="",
        description="The single best argument the founder made",
    )
    biggest_gap: str = Field(
        default="",
        description="The most important question raised that the founder never adequately answered",
    )
    recommendation: str = Field(
        default="",
        description="2-3 sentences of actionable next steps",
    )


_report_client = OpenAIClient(system_prompt=REPORT_AGGREGATOR_PROMPT)


async def generate_report(state, verdicts: list[dict] | None = None) -> dict | None:
    if state.turn_count < 2:
        return None

    transcript = state.get_recent_context(n=100)

    judge_update_summary = ""
    if hasattr(state, "judge_updates") and state.judge_updates:
        lines = []
        for upd in state.judge_updates:
            lines.append(f"- [{upd.classification}] {upd.summary} (consensus strength: {upd.strength}/10)")
            for js in (upd.judge_scores if isinstance(upd.judge_scores, list) else []):
                name = js.get("judge_name", "unknown")
                lines.append(f"    {name} ({js.get('strength', '?')}/10): {js.get('reaction', '')}")
        judge_update_summary = "\n".join(lines)

    verdict_summary = ""
    if verdicts:
        lines = []
        for v in verdicts:
            name = v.get("judge_name", "unknown")
            overall = v.get("overall", "?")
            winner = v.get("winner", "?")
            summary = v.get("summary", "")
            lines.append(f"- {name} (overall: {overall}/10, winner: {winner}): {summary}")
            if v.get("scores"):
                s = v["scores"]
                lines.append(f"    Scores: problem_clarity={s.get('problem_clarity')}, market_logic={s.get('market_logic')}, execution_risk={s.get('execution_risk')}, competitive_awareness={s.get('competitive_awareness')}, internal_coherence={s.get('internal_coherence')}")
        verdict_summary = "\n".join(lines)

    prompt = f"""ORIGINAL IDEA (as stated at the start):
{state.user_claim}

FULL TRANSCRIPT:
{transcript}

PER-TURN JUDGE UPDATES:
{judge_update_summary or "(none)"}

FINAL JUDGE VERDICTS:
{verdict_summary or "(none)"}

Generate a structured debrief report.
"""

    try:
        report = await asyncio.wait_for(
            _report_client.generate(prompt, ReportResult, temperature=0.3, max_tokens=4000),
            timeout=30.0,
        )
        return report.model_dump()
    except (Exception, asyncio.CancelledError) as e:
        print(f"Report generation error: {e}")
        return None
