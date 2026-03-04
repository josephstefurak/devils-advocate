import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def generate_report(state) -> dict:
    transcript = state.get_recent_context(n=100)  # full transcript
    claim_summary = "\n".join([
        f"- [{e.classification}] {e.summary} (strength: {e.strength}/10)"
        for e in state.claim_events
    ])

    prompt = f"""
You are evaluating a business idea stress-test session.

ORIGINAL IDEA: {state.user_claim}

FULL TRANSCRIPT:
{transcript}

ARGUMENT EVENTS:
{claim_summary}

Generate a structured debrief report. Respond ONLY with a JSON object in this exact format:
{{
    "overall_score": 7,
    "verdict": "One sentence verdict on the viability of this idea",
    "strengths": [
        "Specific strength identified during the debate",
        "Another strength"
    ],
    "weaknesses": [
        "Most critical weakness exposed",
        "Another weakness"
    ],
    "sharpest_moment": "The single best argument or insight the user made",
    "biggest_gap": "The most important question that was never adequately answered",
    "recommendation": "2-3 sentence actionable next step for this founder"
}}

Be specific — reference actual things said in the debate. No generic advice.
overall_score is 1-10 (10 = very strong idea well defended).
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=1000,
            )
        )
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"Report generation error: {e}")
        return None