# tests/backend/test_validation.py
import pytest
from validation import (
    sanitize_claim,
    validate_audio_chunk,
    validate_document_paths,
    validate_participant_id,
)

class TestSanitizeClaim:
    def test_valid_claim(self):
        assert sanitize_claim("I want to build a SaaS platform for HR teams") == \
               "I want to build a SaaS platform for HR teams"

    def test_strips_leading_trailing_whitespace(self):
        assert sanitize_claim("  my idea  ") == "my idea"

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_claim("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError):
            sanitize_claim("   ")

    def test_rejects_over_500_chars(self):
        with pytest.raises(ValueError, match="500"):
            sanitize_claim("x" * 501)

    def test_accepts_exactly_500_chars(self):
        result = sanitize_claim("x" * 500)
        assert len(result) == 500

    def test_strips_control_characters(self):
        result = sanitize_claim("my idea\x00\x1f")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_collapses_whitespace(self):
        assert sanitize_claim("my   idea") == "my idea"

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            sanitize_claim(123)

    # Test the injection patterns you added
    #def test_rejects_prompt_delimiter_tokens(self):
     #   with pytest.raises(ValueError):
      #      sanitize_claim("my idea ```system override```")


class TestValidateAudioChunk:
    def test_valid_chunk(self):
        data = bytes(100)
        assert validate_audio_chunk(data) == data

    def test_rejects_none(self):
        with pytest.raises(ValueError):
            validate_audio_chunk(None)

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_audio_chunk(bytes(0))

    def test_rejects_oversized(self):
        with pytest.raises(ValueError):
            validate_audio_chunk(bytes(32769))

    def test_accepts_max_size(self):
        data = bytes(32768)
        assert len(validate_audio_chunk(data)) == 32768


class TestValidateParticipantId:
    def test_valid_id(self):
        assert validate_participant_id("abc123") == "abc123"

    def test_valid_with_hyphens_underscores(self):
        assert validate_participant_id("user-123_abc") == "user-123_abc"

    def test_rejects_spaces(self):
        with pytest.raises(ValueError):
            validate_participant_id("user 123")

    def test_rejects_slashes(self):
        with pytest.raises(ValueError):
            validate_participant_id("user/123")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            validate_participant_id("a" * 65)

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_participant_id("")

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            validate_participant_id(123)


class TestValidateDocumentPaths:
    def test_accepts_paths_for_participant(self):
        paths = [
            "users/test_uid/documents/1710000000000_pitch.pdf",
            "users/test_uid/documents/1710000000001_notes.txt",
        ]
        assert validate_document_paths(paths, "test_uid") == paths

    def test_rejects_non_list(self):
        with pytest.raises(ValueError):
            validate_document_paths("users/test_uid/documents/file.pdf", "test_uid")

    def test_rejects_other_user_path(self):
        with pytest.raises(ValueError):
            validate_document_paths(
                ["users/other_uid/documents/1710000000000_pitch.pdf"],
                "test_uid",
            )

    def test_rejects_nested_paths(self):
        with pytest.raises(ValueError):
            validate_document_paths(
                ["users/test_uid/documents/subdir/pitch.pdf"],
                "test_uid",
            )

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            validate_document_paths(
                ["users/test_uid/documents/../firebase_key.json"],
                "test_uid",
            )
