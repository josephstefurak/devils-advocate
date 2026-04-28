#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


FEEDBACK_VERSION = "research_feedback_v1"
DEFAULT_COLLECTION = "sessions"
TESTISH_EXACT_CLAIMS = {
    "test",
    "testing",
    "hello",
    "asdf",
    "demo",
    "sample",
    "fake",
    "ai hr tool",
    "b2b saas for hr teams",
    "i want to build an ai hr tool",
    "i want to build a b2b saas for hr teams",
}
TESTISH_PATTERNS = [
    re.compile(r"\btest(ing)?\b"),
    re.compile(r"\basdf\b"),
    re.compile(r"\bhello\b"),
    re.compile(r"\bfake\b"),
    re.compile(r"\bsample\b"),
]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def short_hash(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "path"):
        return value.path
    return value


def duration_seconds(session: dict[str, Any]) -> float | None:
    start = session.get("created_at") or session.get("started_at")
    end = session.get("ended_at")
    if isinstance(start, datetime) and isinstance(end, datetime):
        return round(max(0.0, (end - start).total_seconds()), 2)
    return None


def metric_value(session: dict[str, Any], key: str) -> int | None:
    metrics = session.get("metrics") or {}
    value = metrics.get(key)
    if isinstance(value, int):
        return value
    return None


def total_turns(session: dict[str, Any]) -> int:
    return metric_value(session, "total_turns") or len(session.get("turns") or [])


def user_uid(session: dict[str, Any]) -> str:
    return ((session.get("user") or {}).get("uid") or "unknown").strip()


def is_testish_claim(claim: Any) -> bool:
    normalized = normalize_text(claim)
    if not normalized or normalized in TESTISH_EXACT_CLAIMS:
        return True
    if len(normalized) < 15:
        return True
    return any(pattern.search(normalized) for pattern in TESTISH_PATTERNS)


def duplicate_counters(sessions: list[dict[str, Any]]) -> tuple[Counter, Counter]:
    claim_counts = Counter(normalize_text(session.get("user_claim")) for session in sessions)
    uid_counts = Counter(user_uid(session) for session in sessions)
    return claim_counts, uid_counts


def quality_flags(
    session: dict[str, Any],
    claim_counts: Counter,
    uid_counts: Counter,
) -> list[str]:
    flags = []
    feedback = session.get("post_debate_feedback")
    report = session.get("report")
    feedback_context = (feedback or {}).get("client_context") or {}
    duration = duration_seconds(session)
    turns = total_turns(session)
    user_turns = metric_value(session, "user_turns")
    agent_turns = metric_value(session, "agent_turns")
    claim_key = normalize_text(session.get("user_claim"))
    uid = user_uid(session)

    if session.get("consent_given") is not True:
        flags.append("no_consent")
    if session.get("ended_at") is None:
        flags.append("not_finalized")
    if not feedback:
        flags.append("missing_post_debate_feedback")
    elif feedback.get("feedback_version") != FEEDBACK_VERSION:
        flags.append("unexpected_feedback_version")
    if not report:
        flags.append("missing_report")
    if feedback and feedback_context.get("report_available") is not True:
        flags.append("feedback_says_no_report")
    if turns < 4:
        flags.append("too_few_turns")
    if user_turns is not None and user_turns < 2:
        flags.append("too_few_user_turns")
    if agent_turns is not None and agent_turns < 2:
        flags.append("too_few_agent_turns")
    if duration is not None and duration < 45:
        flags.append("duration_lt45s")
    if duration is not None and duration > 600:
        flags.append("duration_gt10m")
    if claim_counts[claim_key] > 1:
        flags.append("duplicate_claim")
    if uid_counts[uid] > 1:
        flags.append("duplicate_user")
    if is_testish_claim(session.get("user_claim")):
        flags.append("testish_claim")
    return flags


def analysis_group(session: dict[str, Any]) -> str:
    if not session.get("post_debate_feedback"):
        return "no_feedback"
    if session.get("report"):
        return "report_backed_feedback"
    return "no_report_feedback"


def feedback_row(session: dict[str, Any], flags: list[str]) -> dict[str, Any]:
    feedback = session.get("post_debate_feedback") or {}
    report = session.get("report") or {}
    summary_scores = feedback.get("summary_scores") or {}
    idea = feedback.get("idea_impact") or {}
    voice = feedback.get("voice_experience") or {}
    report_utility = feedback.get("report_utility") or {}
    value_signal = feedback.get("value_signal") or {}
    profile = feedback.get("participant_profile") or {}
    client_context = feedback.get("client_context") or {}

    return {
        "session_id": session.get("session_id") or session.get("_id"),
        "created_at": to_jsonable(session.get("created_at")),
        "ended_at": to_jsonable(session.get("ended_at")),
        "duration_seconds": duration_seconds(session),
        "analysis_group": analysis_group(session),
        "quality_flags": "|".join(flags),
        "has_report": bool(session.get("report")),
        "feedback_report_available": client_context.get("report_available"),
        "consent_given": session.get("consent_given"),
        "uid_hash": short_hash(user_uid(session)),
        "claim_hash": short_hash(normalize_text(session.get("user_claim"))),
        "stage": session.get("stage"),
        "voice": session.get("voice"),
        "total_turns": total_turns(session),
        "user_turns": metric_value(session, "user_turns"),
        "agent_turns": metric_value(session, "agent_turns"),
        "report_overall_score": report.get("overall_score"),
        "report_verdict": report.get("verdict"),
        "idea_impact_index": summary_scores.get("idea_impact_index"),
        "voice_ux_index": summary_scores.get("voice_ux_index"),
        "report_utility_index": summary_scores.get("report_utility_index"),
        "refined_idea": idea.get("refined_idea"),
        "constructive_challenge": idea.get("constructive_challenge"),
        "clearer_next_steps": idea.get("clearer_next_steps"),
        "voice_naturalness": voice.get("naturalness"),
        "turn_taking_ease": voice.get("turn_taking_ease"),
        "expression_ease": voice.get("expression_ease"),
        "next_time_preference": voice.get("next_time_preference"),
        "voice_hurdles": "|".join(voice.get("hurdles") or []),
        "report_organization": report_utility.get("organization"),
        "report_digestibility": report_utility.get("digestibility"),
        "report_actionability": report_utility.get("actionability"),
        "most_valuable_part": value_signal.get("most_valuable_part"),
        "industry_domain": profile.get("industry_domain"),
        "founder_experience": profile.get("founder_experience"),
        "prior_voice_ai_familiarity": profile.get("prior_voice_ai_familiarity"),
        "age_range": profile.get("age_range"),
    }


def quality_row(session: dict[str, Any], flags: list[str]) -> dict[str, Any]:
    return {
        "session_id": session.get("session_id") or session.get("_id"),
        "analysis_group": analysis_group(session),
        "quality_flags": "|".join(flags),
        "has_feedback": bool(session.get("post_debate_feedback")),
        "has_report": bool(session.get("report")),
        "consent_given": session.get("consent_given"),
        "ended": session.get("ended_at") is not None,
        "duration_seconds": duration_seconds(session),
        "total_turns": total_turns(session),
        "uid_hash": short_hash(user_uid(session)),
        "claim_hash": short_hash(normalize_text(session.get("user_claim"))),
    }


def average_present(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return None
    return round(mean(values), 2)


def counter_for(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    values = Counter(str(row.get(key)) for row in rows if row.get(key) not in (None, ""))
    return dict(values.most_common())


def build_summary(
    sessions: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    flag_counts = Counter()
    for row in quality_rows:
        for flag in row["quality_flags"].split("|"):
            if flag:
                flag_counts[flag] += 1

    groups = Counter(row["analysis_group"] for row in quality_rows)
    feedback_groups = Counter(row["analysis_group"] for row in feedback_rows)
    report_backed = [row for row in feedback_rows if row["analysis_group"] == "report_backed_feedback"]
    no_report = [row for row in feedback_rows if row["analysis_group"] == "no_report_feedback"]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": {
            "total_sessions": len(sessions),
            "sessions_with_feedback": len(feedback_rows),
            "report_backed_feedback_sessions": len(report_backed),
            "no_report_feedback_sessions": len(no_report),
            "consent_true_sessions": sum(1 for s in sessions if s.get("consent_given") is True),
            "finalized_sessions": sum(1 for s in sessions if s.get("ended_at") is not None),
            "sessions_over_180s": sum(
                1 for s in sessions if duration_seconds(s) is not None and duration_seconds(s) > 180
            ),
            "sessions_over_600s": sum(
                1 for s in sessions if duration_seconds(s) is not None and duration_seconds(s) > 600
            ),
        },
        "analysis_groups_all_sessions": dict(groups.most_common()),
        "analysis_groups_feedback_sessions": dict(feedback_groups.most_common()),
        "quality_flag_counts": dict(flag_counts.most_common()),
        "feedback_averages_all": {
            "idea_impact_index": average_present(feedback_rows, "idea_impact_index"),
            "voice_ux_index": average_present(feedback_rows, "voice_ux_index"),
            "report_utility_index": average_present(feedback_rows, "report_utility_index"),
            "report_overall_score": average_present(feedback_rows, "report_overall_score"),
        },
        "feedback_averages_report_backed": {
            "idea_impact_index": average_present(report_backed, "idea_impact_index"),
            "voice_ux_index": average_present(report_backed, "voice_ux_index"),
            "report_utility_index": average_present(report_backed, "report_utility_index"),
            "report_overall_score": average_present(report_backed, "report_overall_score"),
        },
        "feedback_averages_no_report": {
            "idea_impact_index": average_present(no_report, "idea_impact_index"),
            "voice_ux_index": average_present(no_report, "voice_ux_index"),
            "report_utility_index": average_present(no_report, "report_utility_index"),
        },
        "categorical_counts": {
            "most_valuable_part": counter_for(feedback_rows, "most_valuable_part"),
            "next_time_preference": counter_for(feedback_rows, "next_time_preference"),
            "industry_domain": counter_for(feedback_rows, "industry_domain"),
            "founder_experience": counter_for(feedback_rows, "founder_experience"),
            "prior_voice_ai_familiarity": counter_for(feedback_rows, "prior_voice_ai_familiarity"),
            "age_range": counter_for(feedback_rows, "age_range"),
        },
    }


def build_export(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    claim_counts, uid_counts = duplicate_counters(sessions)
    quality_rows = []
    feedback_rows = []

    for session in sessions:
        flags = quality_flags(session, claim_counts, uid_counts)
        quality_rows.append(quality_row(session, flags))
        if session.get("post_debate_feedback"):
            feedback_rows.append(feedback_row(session, flags))

    return {
        "raw_sessions": [to_jsonable(session) for session in sessions],
        "feedback_rows": feedback_rows,
        "quality_rows": quality_rows,
        "summary": build_summary(sessions, feedback_rows, quality_rows),
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(path: Path, summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    lines = [
        "# Firestore Session Export Summary",
        "",
        f"Generated at: `{summary['generated_at']}`",
        "",
        "## Counts",
        "",
        f"- Total sessions: {counts['total_sessions']}",
        f"- Sessions with feedback: {counts['sessions_with_feedback']}",
        f"- Report-backed feedback sessions: {counts['report_backed_feedback_sessions']}",
        f"- No-report feedback sessions: {counts['no_report_feedback_sessions']}",
        f"- Finalized sessions: {counts['finalized_sessions']}",
        f"- Sessions over 180s: {counts['sessions_over_180s']}",
        f"- Sessions over 600s: {counts['sessions_over_600s']}",
        "",
        "## Feedback Averages",
        "",
    ]
    for key, value in summary["feedback_averages_all"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Quality Flags", ""])
    for key, value in summary["quality_flag_counts"].items():
        lines.append(f"- {key}: {value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_sessions(collection: str) -> list[dict[str, Any]]:
    sessions = []
    for snapshot in firestore.client().collection(collection).stream():
        session = snapshot.to_dict() or {}
        session["_id"] = snapshot.id
        sessions.append(session)
    sessions.sort(
        key=lambda item: item["created_at"].timestamp()
        if isinstance(item.get("created_at"), datetime)
        else 0
    )
    return sessions


def initialize_firebase(key_path: str | None) -> None:
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    if key_path:
        firebase_admin.initialize_app(credentials.Certificate(key_path))
    else:
        firebase_admin.initialize_app(credentials.ApplicationDefault())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export and aggregate Firestore debate sessions.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--key-path", default=os.getenv("FIREBASE_KEY_PATH"))
    parser.add_argument(
        "--output",
        default=f"exports/firestore_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
    )
    parser.add_argument(
        "--include-raw",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write raw session JSON in addition to aggregate files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_firebase(args.key_path)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    sessions = fetch_sessions(args.collection)
    export = build_export(sessions)

    if args.include_raw:
        write_json(output_dir / "sessions_raw.json", export["raw_sessions"])
    write_json(output_dir / "sessions_feedback.json", export["feedback_rows"])
    write_csv(output_dir / "sessions_feedback.csv", export["feedback_rows"])
    write_csv(output_dir / "sessions_quality_flags.csv", export["quality_rows"])
    write_json(output_dir / "aggregate_summary.json", export["summary"])
    write_markdown_summary(output_dir / "aggregate_summary.md", export["summary"])

    counts = export["summary"]["counts"]
    print(f"Exported {counts['total_sessions']} sessions to {output_dir}")
    print(
        "Feedback sessions: "
        f"{counts['sessions_with_feedback']} total, "
        f"{counts['report_backed_feedback_sessions']} report-backed, "
        f"{counts['no_report_feedback_sessions']} without reports"
    )


if __name__ == "__main__":
    main()
