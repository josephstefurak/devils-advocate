from datetime import UTC, datetime, timedelta

from scripts.export_firestore_sessions import build_export, is_testish_claim


def make_feedback(report_available=True):
    feedback = {
        "feedback_version": "research_feedback_v1",
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
            "hurdles": ["turn_taking"],
        },
        "summary_scores": {
            "idea_impact_index": 4.33,
            "voice_ux_index": 3.67,
            "report_utility_index": 4.67 if report_available else None,
        },
        "value_signal": {"most_valuable_part": "live_pushback"},
        "participant_profile": {"founder_experience": "first_time_founder"},
        "client_context": {"report_available": report_available},
    }
    if report_available:
        feedback["report_utility"] = {
            "organization": 5,
            "digestibility": 4,
            "actionability": 5,
        }
    return feedback


def make_session(
    session_id,
    *,
    claim="We are building a logistics AI platform",
    uid="user-1",
    feedback=True,
    report=True,
    finalized=True,
    consent=True,
    report_available=True,
    total_turns=8,
):
    created_at = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
    session = {
        "_id": session_id,
        "session_id": session_id,
        "user_claim": claim,
        "created_at": created_at,
        "ended_at": created_at + timedelta(seconds=120) if finalized else None,
        "consent_given": consent,
        "user": {"uid": uid, "is_anonymous": True},
        "metrics": {
            "total_turns": total_turns,
            "user_turns": total_turns // 2,
            "agent_turns": total_turns - (total_turns // 2),
        },
        "turns": [],
    }
    if feedback:
        session["post_debate_feedback"] = make_feedback(report_available=report_available)
    if report:
        session["report"] = {"overall_score": 7, "verdict": "Solid defense"}
    return session


def test_build_export_includes_all_feedback_sessions_and_groups_missing_reports():
    sessions = [
        make_session("s1", report=True, report_available=True),
        make_session("s2", report=False, finalized=False, report_available=False),
        make_session("s3", feedback=False, report=False),
    ]

    export = build_export(sessions)

    assert len(export["feedback_rows"]) == 2
    assert export["summary"]["counts"]["sessions_with_feedback"] == 2
    assert export["summary"]["counts"]["report_backed_feedback_sessions"] == 1
    assert export["summary"]["counts"]["no_report_feedback_sessions"] == 1

    no_report = next(row for row in export["feedback_rows"] if row["session_id"] == "s2")
    assert no_report["analysis_group"] == "no_report_feedback"
    assert "missing_report" in no_report["quality_flags"]
    assert "feedback_says_no_report" in no_report["quality_flags"]
    assert "not_finalized" in no_report["quality_flags"]


def test_build_export_flags_duplicate_testish_and_no_consent_sessions():
    sessions = [
        make_session("s1", claim="test", uid="user-1", consent=False),
        make_session("s2", claim="test", uid="user-1", feedback=False, report=False),
    ]

    export = build_export(sessions)
    flags = next(row for row in export["quality_rows"] if row["session_id"] == "s1")["quality_flags"]

    assert "no_consent" in flags
    assert "duplicate_claim" in flags
    assert "duplicate_user" in flags
    assert "testish_claim" in flags


def test_testish_claim_heuristic_keeps_realistic_long_claims():
    assert is_testish_claim("test") is True
    assert is_testish_claim("We are building software for freight brokers to automate load matching") is False
