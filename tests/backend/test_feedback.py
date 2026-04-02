import importlib
from unittest.mock import patch

from fastapi.testclient import TestClient

from feedback import FEEDBACK_VERSION, StudyFeedback, build_feedback_record


def make_feedback_payload(report_available=True):
    payload = {
        "idea_impact": {
            "refined_idea": 5,
            "constructive_challenge": 4,
            "clearer_next_steps": 4,
        },
        "voice_experience": {
            "naturalness": 4,
            "turn_taking_ease": 3,
            "expression_ease": 4,
            "next_time_preference": "voice",
            "hurdles": ["turn_taking", "needed_more_time"],
        },
        "value_signal": {
            "most_valuable_part": "live_pushback",
        },
        "open_feedback": {
            "most_valuable_insight": "It pushed me to tighten my ICP.",
            "one_thing_to_change": "Give me a little more time before the next challenge.",
        },
        "participant_profile": {
            "industry_domain": "saas_ai_tooling",
            "founder_experience": "first_time_founder",
            "prior_voice_ai_familiarity": "a_few_times",
            "age_range": "25_34",
        },
        "client_context": {
            "report_available": report_available,
        },
    }
    if report_available:
        payload["report_utility"] = {
            "organization": 5,
            "digestibility": 4,
            "actionability": 5,
        }
    return payload


class TestFeedbackRecord:
    def test_build_feedback_record_adds_indices(self):
        record = build_feedback_record(StudyFeedback.model_validate(
            make_feedback_payload(report_available=True)
        ))

        assert record["feedback_version"] == FEEDBACK_VERSION
        assert record["summary_scores"]["idea_impact_index"] == 4.33
        assert record["summary_scores"]["voice_ux_index"] == 3.67
        assert record["summary_scores"]["report_utility_index"] == 4.67


class TestFeedbackApi:
    def test_session_feedback_updates_session_doc(self, mock_firestore_db):
        fake_db, store = mock_firestore_db
        store["session_001"] = {
            "session_id": "session_001",
            "consent_given": True,
            "user": {"uid": "user123", "is_anonymous": True},
        }

        with patch("firebase_admin.initialize_app"), \
             patch("firebase_admin.credentials.Certificate"), \
             patch("firebase_admin.firestore.client", return_value=fake_db), \
             patch("firebase_admin.firestore.ArrayUnion", side_effect=lambda x: x), \
             patch("firebase_admin.firestore.Increment", side_effect=lambda x: x), \
             patch("firebase_admin.auth.verify_id_token", return_value={"uid": "user123"}):
            import firebase_logger
            import main

            importlib.reload(firebase_logger)
            importlib.reload(main)

            client = TestClient(main.app)
            response = client.post("/session_feedback", json={
                "idToken": "fake-token",
                "sessionId": "session_001",
                "feedback": make_feedback_payload(report_available=True),
            })

        assert response.status_code == 200
        stored = store["session_001"]["post_debate_feedback"]
        assert stored["feedback_version"] == FEEDBACK_VERSION
        assert stored["value_signal"]["most_valuable_part"] == "live_pushback"
        assert stored["summary_scores"]["report_utility_index"] == 4.67
        assert "submitted_at" in stored

    def test_session_feedback_rejects_disabled_consent(self, mock_firestore_db):
        fake_db, store = mock_firestore_db
        store["session_002"] = {
            "session_id": "session_002",
            "consent_given": False,
            "user": {"uid": "user123", "is_anonymous": True},
        }

        with patch("firebase_admin.initialize_app"), \
             patch("firebase_admin.credentials.Certificate"), \
             patch("firebase_admin.firestore.client", return_value=fake_db), \
             patch("firebase_admin.firestore.ArrayUnion", side_effect=lambda x: x), \
             patch("firebase_admin.firestore.Increment", side_effect=lambda x: x), \
             patch("firebase_admin.auth.verify_id_token", return_value={"uid": "user123"}):
            import firebase_logger
            import main

            importlib.reload(firebase_logger)
            importlib.reload(main)

            client = TestClient(main.app)
            response = client.post("/session_feedback", json={
                "idToken": "fake-token",
                "sessionId": "session_002",
                "feedback": make_feedback_payload(report_available=False),
            })

        assert response.status_code == 403
        assert "consent" in response.json()["error"].lower()

    def test_session_feedback_rejects_invalid_hurdle_mix(self, mock_firestore_db):
        fake_db, store = mock_firestore_db
        store["session_003"] = {
            "session_id": "session_003",
            "consent_given": True,
            "user": {"uid": "user123", "is_anonymous": True},
        }
        payload = make_feedback_payload(report_available=False)
        payload["voice_experience"]["hurdles"] = ["nothing_major", "turn_taking"]

        with patch("firebase_admin.initialize_app"), \
             patch("firebase_admin.credentials.Certificate"), \
             patch("firebase_admin.firestore.client", return_value=fake_db), \
             patch("firebase_admin.firestore.ArrayUnion", side_effect=lambda x: x), \
             patch("firebase_admin.firestore.Increment", side_effect=lambda x: x), \
             patch("firebase_admin.auth.verify_id_token", return_value={"uid": "user123"}):
            import firebase_logger
            import main

            importlib.reload(firebase_logger)
            importlib.reload(main)

            client = TestClient(main.app)
            response = client.post("/session_feedback", json={
                "idToken": "fake-token",
                "sessionId": "session_003",
                "feedback": payload,
            })

        assert response.status_code == 400
