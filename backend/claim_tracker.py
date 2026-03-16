# backend/claim_tracker.py
import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Structured output ─────────────────────────────────────────────────────
class ClaimClassificationResult(BaseModel):
    classification: Literal["DEFENDED", "CONCEDED", "NEW_CLAIM", "DEFLECTED"] = Field(
        description="Exactly one of: DEFENDED, CONCEDED, NEW_CLAIM, DEFLECTED"
    )
    summary: str = Field(description="One sentence summary of what the user argued")
    strength: int = Field(description="1-10 (10 = very compelling argument, 1 = very weak)")
    reason: str = Field(
        description="One sentence explaining why the turn was classified as such and the score was assigned. Maximum 25 words."
    )
    suggested_argument: str = Field(
        default="",
        description=(
            "1-3 sentences on the strongest argument the user could have made to "
            "better defend their position in this turn. Maximum 85 words. "
            "Optional — default empty string if not provided."
        ),
    )


CLASSIFY_PROMPT = """
You are analyzing a live debate transcript. The user is defending a business idea against
an adversarial AI agent.

USER'S ORIGINAL CLAIM: {original_claim}

RECENT DEBATE CONTEXT:
{context}

USER'S LATEST TURN: "{user_turn}"

Classify the user's latest turn as exactly ONE of:
- DEFENDED: User made a substantive counter-argument that addressed the agent's attack
- CONCEDED: User admitted a weakness, agreed with the agent, or gave ground
- NEW_CLAIM: User introduced a new aspect of their idea not previously discussed
- DEFLECTED: User changed the subject to something else that was a part of the original claim or gave a non-answer

STRENGTH SCORE (1–10):
Rate how compelling the turn is *given its classification*:

- DEFENDED (1–10): Did the counter-argument actually neutralize the attack?
  - 9–10: Directly refutes the attack with specific evidence, data, or airtight logic
  - 6–8: Addresses the core concern but leaves minor gaps or relies on assertion/assumptions
  - 3–5: Partially relevant but misses the main thrust of the attack
  - 1–2: Superficial or circular — restates the original claim without new information or evidence

- CONCEDED (1–10): How damaging is the concession?
  - 9–10: Minor concession — user acknowledged a small weakness while their core argument remains fully intact
  - 6–8: Moderate concession — gives some ground but the idea is still defensible
  - 3–5: Significant concession — weakens a meaningful part of the argument
  - 1–2: Devastating concession — concedes a core pillar; the original claim is largely undermined

- NEW_CLAIM (1–10): How strong is the new claim on its own merits?
  - 9–10: Compelling new angle with clear, concrete reasoning or evidence
  - 6–8: Interesting and somewhat compelling but slightly underdeveloped. Some evidence or reasoning is provided but it is not very strong.
  - 3–5: Vaguely described; not very compelling and lacks evidence or reasoning
  - 1–2: Not compelling at all; no evidence or reasoning is provided

- DEFLECTED (1–10): How much does the deflection still support the core argument?
  - 9–10: Seamless pivot to a genuinely strong topic, backed by clear and convincing reasoning
  - 6–8: Reasonably smooth pivot to a decent topic, but reasoning is underdeveloped or partially convincing
  - 3–5: Awkward pivot or weak topic choice, with thin or unconvincing reasoning
  - 1–2: Jarring or transparent subject change, lands on a weak point with little to no supporting reasoning

- SUGGESTED ARGUMENT: Your suggested argument to the user to better defend their position in this turn should be 1-3 sentences. It should be a strong argument that improves teh users argument by providing additional evidence derived from the context or reasoning.
"""


async def classify_turn(
    original_claim: str,
    context: str,
    user_turn: str,
    on_result: callable
):
    """
    Runs in background. Calls Gemini Flash to classify a user turn.
    Calls on_result(dict) when done.
    """
    try:
        prompt = CLASSIFY_PROMPT.format(
            original_claim=original_claim,
            context=context,
            user_turn=user_turn
        )
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=ClaimClassificationResult.model_json_schema(),
                max_output_tokens=1024,
            )
        )
        text = response.text.strip()
        if not text:
            print("Claim tracker: empty response, skipping")
            return
        result = ClaimClassificationResult.model_validate_json(text)
        await on_result(result.model_dump())
    except Exception as e:
        print(f"Claim tracker error: {e}")