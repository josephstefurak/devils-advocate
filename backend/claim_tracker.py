# backend/claim_tracker.py
import asyncio
import json
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
- DEFLECTED: User changed subject or gave a non-answer

Respond with ONLY a JSON object in this exact format:
{{
    "classification": "DEFENDED",
    "summary": "One sentence summary of what the user argued",
    "strength": 7
}}

strength is 1-10 (10 = very compelling argument, 1 = very weak).
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
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=200,
            )
        )
        result = json.loads(response.text)
        await on_result(result)
    except Exception as e:
        print(f"Claim tracker error: {e}")