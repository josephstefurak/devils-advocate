import os
import json
from google import genai
from google.genai import types


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

JUDGE_PROMPT = """
You are an impartial debate judge evaluating a founder's pitch defense against an adversarial AI.

You will receive a full transcript of the debate. Score the FOUNDER (not the AI) across these dimensions:

1. problem_clarity (1-10): How clearly did they articulate the problem they're solving?
2. market_logic (1-10): How well did they defend market size, TAM, and timing?
3. execution_risk (1-10): How convincingly did they address execution and operational challenges?
4. competitive_awareness (1-10): How well did they handle questions about competition and differentiation?
5. internal_coherence (1-10): Were their arguments consistent and logically sound throughout?

If the transcript contains fewer than 2 substantive exchanges, return all scores as 0
and set summary to "Insufficient debate content to evaluate."

Also determine:
- overall: average of the five scores, rounded to 1 decimal
- winner: "founder" if overall >= 6, "agent" if < 6
- summary: 2-3 sentence plain-English verdict on how the founder performed

Return ONLY valid JSON, no markdown, no preamble:
{
  "scores": {
    "problem_clarity": 0,
    "market_logic": 0,
    "execution_risk": 0,
    "competitive_awareness": 0,
    "internal_coherence": 0
  },
  "overall": 0,
  "winner": "founder",
  "summary": ""
}
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
  Do NOT write generic observations like "the founder showed market awareness" — instead write
  "the founder cited a 40% YoY growth rate in the SMB HR software category when challenged on
  timing, which directly addressed the agent's concern."
- Be transparent about your reasoning. If you give a low overall_score, explain why in the verdict.
- The idea_summary should reflect what the idea EVOLVED into during the debate, not just the
  opening claim — founders often refine or pivot their framing mid-session.
- sharpest_moment and biggest_gap must be grounded in something actually said, not inferred.

If the transcript contains fewer than 2 substantive exchanges, return all scores as 0
and set summary to "Insufficient debate content to evaluate."

Respond ONLY with a JSON object in this exact format (no markdown, no extra keys):
{{
    "idea_summary": "2-3 sentence description of the business idea as it stood by the END of the debate, including any refinements made during the session",
    "overall_score": 7,
    "verdict": "One sentence verdict that transparently explains the score — what earned it and what held it back",
    "strengths": [
        "Specific strength with direct reference to what was said or argued",
        "Another strength with transcript evidence"
    ],
    "weaknesses": [
        "Most critical weakness, citing the specific challenge that went unanswered or was poorly handled",
        "Another weakness with specific reference"
    ],
    "sharpest_moment": "The single best argument the founder made — quote or closely paraphrase what they said",
    "biggest_gap": "The most important question raised by the agent that the founder never adequately answered — be specific about what was asked and why the answer fell short",
    "recommendation": "2-3 sentences of actionable next steps tied directly to the gaps exposed in this debate"
}}

overall_score is 1-10 (10 = exceptionally well-defended, investor-ready).
strengths and weaknesses must each have at least 2 items and no more than 4.
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=1500,
            )
        )
        result = json.loads(response.text)

        # Defensive defaults — ensures frontend and future PDF renderer never get null fields
        result.setdefault("idea_summary", "")
        result.setdefault("overall_score", 0)
        result.setdefault("verdict", "")
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("sharpest_moment", "")
        result.setdefault("biggest_gap", "")
        result.setdefault("recommendation", "")

        return result
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
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JUDGE_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1024,
            )
        )
        
        raw = response.text.strip()
        print(f"[Judge] Raw response: {raw[:200]}")  # log first 200 chars
        
        # Strip markdown fences if model ignored response_mime_type
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        if not result.get("overall"):
            scores = result.get("scores", {})
            if scores:
                result["overall"] = round(sum(scores.values()) / len(scores), 1)

        return result
    except Exception as e:
        print(f"Judge error: {e}")
        print(f"[Judge] Full response text: {response.text if response else 'no response'}")
        return None