import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Judge structured output ──────────────────────────────────────────────
class JudgeScores(BaseModel):
    problem_clarity: float = Field(description="1-10: Problem Detail/Unmet Need, Solution Detail, Customer Segment — clarity of the problem, solution, and who has it")
    market_logic: float = Field(description="1-10: Market, Go to Market — market size, beachhead, TAM, distribution, sales model, CAC/LTV")
    execution_risk: float = Field(description="1-10: Product Readiness, Traction, Commercialization Pathway, Team, AI (if applicable) — can they execute?")
    competitive_awareness: float = Field(description="1-10: Competition, Competitive Advantage — knowledge of competitors and ability to differentiate")
    internal_coherence: float = Field(description="1-10: Were their arguments consistent and logically sound across all themes throughout?")


class JudgeResult(BaseModel):
    scores: JudgeScores = Field(description="Scores for each dimension (1-10)")
    overall: float | None = Field(
        default=None,
        description="Average of the five scores, rounded to 1 decimal. May be omitted and computed from scores.",
    )
    winner: str = Field(description='"founder" if overall >= 6, "agent" if < 6')
    summary: str = Field(description="2-3 sentence plain-English verdict on how the founder performed")


# ── Report structured output ─────────────────────────────────────────────
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


JUDGE_PROMPT = """
You are an impartial debate judge evaluating a founder's pitch defense against an adversarial AI.

You will receive a full transcript of the debate. Score the FOUNDER (not the AI) across the five dimensions.

If the transcript contains fewer than 2 substantive exchanges, return all scores as 0
and set summary to "Insufficient debate content to evaluate."

Determine: overall (average of five scores, 1 decimal), winner ("founder" if overall >= 6, "agent" if < 6),
and summary (2-3 sentence plain-English verdict on how the founder performed).
"""


async def generate_report(state) -> dict | None:
    if state.turn_count < 2:
        return None
    transcript = state.get_recent_context(n=100)
    claim_summary = "\n".join([
        f"- [{e.classification}] {e.summary} (strength: {e.strength}/10)"
        for e in state.claim_events
    ])

    prompt = f"""
You are a rigorous evaluator of startup pitch performance. A founder just defended their business
idea in a live adversarial debate against an AI challenger.

ORIGINAL IDEA (as stated at the start):
{state.user_claim}

FULL TRANSCRIPT:
{transcript}

ARGUMENT EVENTS (classified in real time):
{claim_summary}

Generate a structured debrief. You MUST follow these rules:
- Every strength and weakness must cite a specific moment, quote, or exchange from the transcript.
  Do NOT write generic observations — cite specific evidence.
- Be transparent about your reasoning. If you give a low overall_score, explain why in the verdict.
- The idea_summary should reflect what the idea EVOLVED into during the debate, not just the opening claim.
- sharpest_moment and biggest_gap must be grounded in something actually said, not inferred.

If the transcript contains fewer than 2 substantive exchanges, return all scores as 0.

overall_score is 1-10 (10 = exceptionally well-defended, investor-ready).
strengths and weaknesses must each have at least 2 items and no more than 4.
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=ReportResult.model_json_schema(),
                max_output_tokens=1500,
            )
        )
        report = ReportResult.model_validate_json(response.text)
        return report.model_dump()
    except Exception as e:
        print(f"Report generation error: {e}")
        return None


async def run_judge(state) -> dict | None:
    response = None
    transcript_text = "\n".join(
        f"{t.speaker.upper()}: {t.text}" for t in state.turns
    )

    prompt = f"""
ORIGINAL CLAIM: {state.user_claim}

TRANSCRIPT:
{transcript_text}
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JUDGE_PROMPT,
                response_mime_type="application/json",
                response_json_schema=JudgeResult.model_json_schema(),
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )

        raw_text = (response.text or "").strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if len(lines) >= 3 and lines[-1].strip().startswith("```"):
                inner = "\n".join(lines[1:-1]).strip()
                raw_text = inner or raw_text

        judge = JudgeResult.model_validate_json(raw_text)
        result = judge.model_dump()
        # Ensure overall is computed if missing
        if result.get("overall") is None and result.get("scores"):
            s = result["scores"]
            result["overall"] = round(
                (s["problem_clarity"] + s["market_logic"] + s["execution_risk"]
                 + s["competitive_awareness"] + s["internal_coherence"]) / 5, 1
            )
        return result
    except Exception as e:
        print(f"Judge error: {e}")
        print(f"[Judge] Full response text: {response.text if response else 'no response'}")
        return None