# tests/backend/test_claim_tracker.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

VALID_RESULT = {
    "classification": "DEFENDED",
    "summary": "User cited specific CAC payback data to counter the agent's challenge",
    "strength": 7,
    "reason": "User provided concrete data that directly addressed the agent's challenge",
    "suggested_argument": "Our pilots show 8 month payback"
}

CONCEDED_RESULT = {
    "classification": "CONCEDED",
    "summary": "User admitted they hadn't validated the market size assumption",
    "strength": 2,
    "reason": "User acknowledged a gap without providing counter-evidence",
    "suggested_argument": "We're still validating the market size assumption"
}


@pytest.fixture
def mock_client():
    with patch("claim_tracker.client") as mock:
        yield mock


class TestClassifyTurn:
    async def test_returns_defended_classification(self, mock_client):
        mock_response = MagicMock()
        mock_response.text = json.dumps(VALID_RESULT)
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from claim_tracker import classify_turn

        results = []
        async def capture(result):
            results.append(result)

        await classify_turn(
            original_claim="I want to build a B2B SaaS for HR teams",
            context="AGENT: What's your CAC?\nUSER: Under 12 months",
            user_turn="Our pilots show 8 month payback",
            on_result=capture
        )

        assert len(results) == 1
        assert results[0]["classification"] == "DEFENDED"
        assert results[0]["strength"] == 7

    async def test_returns_conceded_classification(self, mock_client):
        mock_response = MagicMock()
        mock_response.text = json.dumps(CONCEDED_RESULT)
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from claim_tracker import classify_turn

        results = []
        async def capture(result):
            results.append(result)

        await classify_turn(
            original_claim="I want to build a B2B SaaS for HR teams",
            context="AGENT: What's your TAM?\nUSER: It's huge",
            user_turn="Yeah I haven't really validated that yet",
            on_result=capture
        )

        assert results[0]["classification"] == "CONCEDED"
        assert results[0]["strength"] == 2

    async def test_on_result_not_called_on_api_failure(self, mock_client):
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("API down")
        )

        from claim_tracker import classify_turn

        results = []
        async def capture(result):
            results.append(result)

        # Should not raise — silently swallows the error
        await classify_turn(
            original_claim="my idea",
            context="some context",
            user_turn="my turn",
            on_result=capture
        )

        assert len(results) == 0

    async def test_on_result_not_called_on_invalid_json(self, mock_client):
        mock_response = MagicMock()
        mock_response.text = "not valid json at all"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from claim_tracker import classify_turn

        results = []
        async def capture(result):
            results.append(result)

        await classify_turn(
            original_claim="my idea",
            context="context",
            user_turn="turn",
            on_result=capture
        )

        assert len(results) == 0

    async def test_prompt_contains_original_claim(self, mock_client):
        mock_response = MagicMock()
        mock_response.text = json.dumps(VALID_RESULT)
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        from claim_tracker import classify_turn

        await classify_turn(
            original_claim="unique claim string XYZ123",
            context="context",
            user_turn="turn",
            on_result=AsyncMock()
        )

        call_args = mock_client.aio.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents") or call_args.args[1]
        assert "unique claim string XYZ123" in prompt

    async def test_all_classifications_accepted(self, mock_client):
        for classification in ["DEFENDED", "CONCEDED", "NEW_CLAIM", "DEFLECTED"]:
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "classification": classification,
                "summary": "test summary",
                "strength": 5,
                "reason": "test reason",
                "suggested_argument": "test suggested argument"
            })
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            from claim_tracker import classify_turn

            results = []
            async def capture(result):
                results.append(result)

            await classify_turn("claim", "context", "turn", capture)
            assert results[-1]["classification"] == classification