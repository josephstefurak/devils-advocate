import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class OpenAIClient:
    """Generic async OpenAI client for structured chat completions.

    Instantiate with a system prompt and call .generate() with a Pydantic
    response model to get validated structured output back.
    """

    def __init__(self, system_prompt: str, model: str = "gpt-5.4-mini-2026-03-17"):
        self.system_prompt = system_prompt
        self.model = model
        self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate(self, prompt: str, response_model, temperature: float = 0.3, max_tokens: int = 4000, timeout: float = 30.0):
        """Send a structured-output request and return a validated Pydantic instance."""
        response = await asyncio.wait_for(
            self._client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=timeout,
        )
        return response.choices[0].message.parsed
