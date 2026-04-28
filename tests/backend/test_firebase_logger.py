# tests/backend/test_firebase_logger.py
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def logger(mock_firebase):
    fake_db, store = mock_firebase
    import firebase_logger
    firebase_logger.db = fake_db  # ← this line is critical
    from firebase_logger import SessionLogger
    return SessionLogger("test_session_001", "my startup idea", uid="user123"), store

class TestInit:

    def test_stores_user_claim(self, logger):
        instance, store = logger
        assert store["test_session_001"]["user_claim"] == "my startup idea"

class TestLogTurn:
    def test_logs_user_turn(self, logger):
        instance, store = logger
        instance.log_turn("user", "my argument", 1)
        # The mock ArrayUnion just returns the list directly
        turns = store["test_session_001"]["turns"]
        assert any(t["speaker"] == "user" for t in turns)

class TestLogJudgeUpdate:
    def test_running_avg_no_read(self, logger):
        instance, store = logger
        instance.log_judge_update({"classification": "DEFENDED", "summary": "good", "strength": 8})
        instance.log_judge_update({"classification": "CONCEDED", "summary": "fair", "strength": 4})
        assert instance._strength_count == 2
        assert instance._strength_sum == 12

    def test_correct_metric_key_defended(self, logger):
        instance, store = logger
        instance.log_judge_update({"classification": "DEFENDED", "summary": "x", "strength": 5})
        metrics = store["test_session_001"].get("metrics", {})
        assert "defended_count" in str(store)  # updated via dot notation

    def test_correct_metric_key_new_claim(self, logger):
        instance, store = logger
        # Should not raise — new_claim maps correctly
        instance.log_judge_update({"classification": "NEW_CLAIM", "summary": "x", "strength": 5})

class TestLogReport:
    def test_log_report_marks_generated(self, logger):
        instance, store = logger
        instance.log_report({"overall_score": 7})
        session = store["test_session_001"]
        assert session["report"] == {"overall_score": 7}
        assert session["report_status"] == "generated"
        assert session["report_error"] is None

    def test_log_report_status_records_failure_reason(self, logger):
        instance, store = logger
        instance.log_report_status("missing", "generation_failed_or_timeout")
        session = store["test_session_001"]
        assert session["report_status"] == "missing"
        assert session["report_error"] == "generation_failed_or_timeout"

class TestFinalize:
    def test_deletes_doc_if_no_consent(self, logger):
        instance, store = logger
        instance.finalize(consent_given=False)
        assert "test_session_001" not in store

    def test_keeps_doc_if_consent(self, logger):
        instance, store = logger
        instance.finalize(consent_given=True)
        assert "test_session_001" in store
