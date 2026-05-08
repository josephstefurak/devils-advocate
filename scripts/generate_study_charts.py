#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


FEEDBACK_VERSION = "research_feedback_v1"
NAVY = "#15264B"
ORANGE = "#E84B36"

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

LIKERT_ITEMS = [
    ("Voice naturalness", ("voice_experience", "naturalness")),
    ("Report digestibility", ("report_utility", "digestibility")),
    ("Refined idea", ("idea_impact", "refined_idea")),
    ("Report organization", ("report_utility", "organization")),
    ("Expression ease", ("voice_experience", "expression_ease")),
    ("Constructive challenge", ("idea_impact", "constructive_challenge")),
    ("Turn-taking ease", ("voice_experience", "turn_taking_ease")),
    ("Report actionability", ("report_utility", "actionability")),
    ("Clearer next steps", ("idea_impact", "clearer_next_steps")),
]

RUBRIC_ITEMS = [
    ("Consensus overall", ("overall",)),
    ("Problem clarity", ("scores", "problem_clarity")),
    ("Market logic", ("scores", "market_logic")),
    ("Execution risk", ("scores", "execution_risk")),
    ("Competitive awareness", ("scores", "competitive_awareness")),
    ("Internal coherence", ("scores", "internal_coherence")),
]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def short_hash(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def is_testish_claim(claim: Any) -> bool:
    normalized = normalize_text(claim)
    if not normalized or normalized in TESTISH_EXACT_CLAIMS:
        return True
    if len(normalized) < 15:
        return True
    return any(pattern.search(normalized) for pattern in TESTISH_PATTERNS)


def user_uid(session: dict[str, Any]) -> str:
    return ((session.get("user") or {}).get("uid") or "unknown").strip()


def uid_hash(session: dict[str, Any]) -> str:
    return short_hash(user_uid(session))


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def metric_value(session: dict[str, Any], key: str) -> int | float | None:
    value = (session.get("metrics") or {}).get(key)
    return value if isinstance(value, (int, float)) else None


def feedback(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("post_debate_feedback") or {}


def nested_value(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def consensus_block(session: dict[str, Any]) -> dict[str, Any]:
    result = session.get("judge_result") or {}
    return result.get("consensus") or result


def has_generated_report_legacy(session: dict[str, Any]) -> bool:
    return session.get("report_status") == "generated" or bool(session.get("report"))


def has_developer_test_feedback(session: dict[str, Any]) -> bool:
    open_feedback = feedback(session).get("open_feedback") or {}
    text = " ".join(str(value) for value in open_feedback.values() if value)
    return bool(re.search(r"\btest\b", text, flags=re.IGNORECASE))


def duplicate_keepers(sessions: list[dict[str, Any]]) -> set[int]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        groups[(uid_hash(session), normalize_text(session.get("user_claim")))].append(session)

    keepers = set()
    for group in groups.values():
        keeper = max(
            group,
            key=lambda session: (
                bool(session.get("post_debate_feedback")),
                has_generated_report_legacy(session),
                metric_value(session, "user_turns") or 0,
                parse_datetime(session.get("created_at")) or datetime.min,
            ),
        )
        keepers.add(id(keeper))
    return keepers


def primary_exclusion_reasons(session: dict[str, Any], keepers: set[int]) -> list[str]:
    reasons = []
    session_feedback = feedback(session)
    client_context = session_feedback.get("client_context") or {}

    if session.get("consent_given") is not True:
        reasons.append("no_consent")
    if not session_feedback:
        reasons.append("missing_post_debate_feedback")
    if session_feedback and session_feedback.get("feedback_version") != FEEDBACK_VERSION:
        reasons.append("unexpected_feedback_version")
    if not session.get("ended_at"):
        reasons.append("missing_ended_at")
    if not session.get("report"):
        reasons.append("missing_report")
    if client_context.get("report_available") is not True:
        reasons.append("report_not_available_to_client")
    if (metric_value(session, "user_turns") or 0) < 2:
        reasons.append("too_few_user_turns")
    if (metric_value(session, "agent_turns") or 0) < 2:
        reasons.append("too_few_agent_turns")
    if is_testish_claim(session.get("user_claim")):
        reasons.append("testish_claim")
    if id(session) not in keepers:
        reasons.append("non_keeper_duplicate")
    if has_developer_test_feedback(session):
        reasons.append("developer_test_feedback")
    return reasons


def feedback_tier_reasons(session: dict[str, Any]) -> list[str]:
    reasons = []
    if session.get("consent_given") is not True:
        reasons.append("no_consent")
    if not session.get("post_debate_feedback"):
        reasons.append("missing_post_debate_feedback")
    if has_developer_test_feedback(session):
        reasons.append("developer_test_feedback")
    return reasons


def hinges(values: list[float]) -> tuple[float | None, float | None, float | None]:
    sorted_values = sorted(values)
    count = len(sorted_values)
    if count == 0:
        return None, None, None
    if count == 1:
        return sorted_values[0], sorted_values[0], sorted_values[0]
    middle = median(sorted_values)
    if count % 2:
        lower = sorted_values[: count // 2]
        upper = sorted_values[count // 2 + 1 :]
    else:
        lower = sorted_values[: count // 2]
        upper = sorted_values[count // 2 :]
    return median(lower), middle, median(upper)


def format_number(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def likert_stats(primary_sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, (label, path) in enumerate(LIKERT_ITEMS):
        values = []
        for session in primary_sessions:
            value = nested_value(feedback(session), path)
            if isinstance(value, (int, float)):
                values.append(float(value))
        q1, item_median, q3 = hinges(values)
        top2 = sum(1 for value in values if value >= 4)
        denominator = len(values)
        percent = round((top2 / denominator) * 100) if denominator else 0
        rows.append(
            {
                "label": label,
                "source_order": index,
                "values": values,
                "top2": top2,
                "denominator": denominator,
                "percent": percent,
                "median": item_median,
                "iqr": None if q1 is None or q3 is None else q3 - q1,
            }
        )
    rows.sort(key=lambda row: (-row["percent"], -row["top2"], row["source_order"]))
    return rows


def rubric_stats(primary_sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for label, path in RUBRIC_ITEMS:
        values = []
        for session in primary_sessions:
            value = nested_value(consensus_block(session), path)
            if isinstance(value, (int, float)):
                values.append(float(value))
        q1, item_median, q3 = hinges(values)
        rows.append(
            {
                "label": label,
                "values": values,
                "median": item_median,
                "q1": q1,
                "q3": q3,
                "iqr": None if q1 is None or q3 is None else q3 - q1,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        )
    return rows


def verdict_counts(primary_sessions: list[dict[str, Any]]) -> Counter:
    counts = Counter()
    for session in primary_sessions:
        consensus = consensus_block(session)
        winner = consensus.get("winner")
        if not winner:
            overall = consensus.get("overall")
            winner = "founder" if isinstance(overall, (int, float)) and overall >= 6.0 else "agent"
        counts[str(winner).lower()] += 1
    return counts


def write_likert_chart(
    path: Path,
    rows: list[dict[str, Any]],
    feedback_count: int,
    agent_wins: int,
    consensus_median: float | None,
) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    labels = [
        f"{row['label']} - {row['top2']}/{row['denominator']} ({row['percent']}%)"
        for row in rows
    ]
    y_positions = list(range(len(rows)))
    ax.barh(y_positions, [row["percent"] for row in rows], color=NAVY, height=0.58)
    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 150)
    ax.set_xlabel("Agree + strongly agree")
    fig.text(
        0.04,
        0.93,
        f"Likert top-2-box rates (N={feedback_count} feedback tier)",
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="x", color="#D8DDE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    callout = (
        f"All {agent_wins} panels favored AGENT\n"
        f"median consensus {format_number(consensus_median)}/10"
    )
    ax.text(
        116,
        len(rows) - 1.6,
        callout,
        ha="center",
        va="center",
        color="white",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.55", "facecolor": ORANGE, "edgecolor": ORANGE},
    )

    fig.subplots_adjust(left=0.36, right=0.96, top=0.82, bottom=0.17)
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def write_rubric_chart(path: Path, rows: list[dict[str, Any]], primary_count: int) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    labels = [row["label"] for row in rows]
    medians = [row["median"] or 0 for row in rows]
    colors = [ORANGE] + [NAVY] * (len(rows) - 1)
    y_positions = list(range(len(rows)))
    ax.barh(
        y_positions,
        medians,
        color=colors,
        height=0.58,
        zorder=2,
    )
    for y, value, row in zip(y_positions, medians, rows, strict=True):
        q1 = row["q1"] if row["q1"] is not None else value
        q3 = row["q3"] if row["q3"] is not None else value
        whisker_color = NAVY if row["label"] == "Consensus overall" else ORANGE
        ax.errorbar(
            value,
            y,
            xerr=[[value - q1], [q3 - value]],
            fmt="none",
            ecolor=whisker_color,
            elinewidth=2.2,
            capsize=5,
            capthick=2.2,
            zorder=5,
        )
        label_x = max(value, row["q3"] if row["q3"] is not None else value) + 0.18
        ax.text(min(label_x, 9.8), y, format_number(value), va="center", fontsize=10)

    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 10)
    ax.set_xlabel("Consensus score")
    fig.text(
        0.04,
        0.93,
        f"Consensus rubric medians (N={primary_count} primary tier, all sessions)",
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.axvline(6, color="#777777", linewidth=1, linestyle="--")
    ax.grid(axis="x", color="#D8DDE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.text(0.12, 0.06, "Founder wins if consensus overall >= 6.0", color="#555555", fontsize=9)

    fig.subplots_adjust(left=0.25, right=0.94, top=0.82, bottom=0.18)
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def write_summary(
    path: Path,
    primary_sessions: list[dict[str, Any]],
    feedback_sessions: list[dict[str, Any]],
    likert_rows: list[dict[str, Any]],
    rubric_rows: list[dict[str, Any]],
    excluded_feedback: list[tuple[str, list[str]]],
    non_feedback_excluded_count: int,
) -> None:
    verdicts = verdict_counts(primary_sessions)
    overall_row = rubric_rows[0]
    lines = [
        "# Study Chart Numbers Summary",
        "",
        f"- Primary-tier N: {len(primary_sessions)}",
        f"- Feedback-tier N: {len(feedback_sessions)}",
        f"- Omitted non-feedback sessions: {non_feedback_excluded_count}",
        "",
        "## Likert Top-2-Box",
        "",
        "| Item | Top-2-Box | Percent | Median | IQR |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in likert_rows:
        lines.append(
            "| {label} | {top2}/{denominator} | {percent}% | {median} | {iqr} |".format(
                label=row["label"],
                top2=row["top2"],
                denominator=row["denominator"],
                percent=row["percent"],
                median=format_number(row["median"]),
                iqr=format_number(row["iqr"]),
            )
        )

    lines.extend(
        [
            "",
            "## Rubric Scores",
            "",
            "| Dimension | Median | IQR | Min | Max |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in rubric_rows:
        lines.append(
            "| {label} | {median} | {iqr} | {min} | {max} |".format(
                label=row["label"],
                median=format_number(row["median"]),
                iqr=format_number(row["iqr"]),
                min=format_number(row["min"]),
                max=format_number(row["max"]),
            )
        )

    lines.extend(
        [
            "",
            "## Consensus Overall",
            "",
            f"- Median: {format_number(overall_row['median'])}",
            f"- IQR: {format_number(overall_row['iqr'])}",
            f"- Agent wins: {verdicts.get('agent', 0)}",
            f"- Founder wins: {verdicts.get('founder', 0)}",
            "",
            "## Excluded Feedback Sessions",
            "",
        ]
    )
    if excluded_feedback:
        for session_id, reasons in excluded_feedback:
            lines.append(f"- `{session_id}`: {', '.join(reasons)}")
    else:
        lines.append("- None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate study chart PNGs from Firestore export JSON.")
    parser.add_argument("--export-dir", default="exports/firestore_for_charts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_dir = Path(args.export_dir)
    raw_path = export_dir / "sessions_raw.json"
    if not raw_path.exists():
        raise SystemExit(f"Missing export file: {raw_path}")

    sessions = json.loads(raw_path.read_text(encoding="utf-8"))
    chart_dir = export_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    keepers = duplicate_keepers(sessions)
    all_feedback_sessions = [session for session in sessions if session.get("post_debate_feedback")]
    feedback_sessions = [
        session for session in all_feedback_sessions if not feedback_tier_reasons(session)
    ]
    primary_sessions = [
        session for session in sessions if not primary_exclusion_reasons(session, keepers)
    ]

    excluded_feedback = []
    for session in all_feedback_sessions:
        reasons = primary_exclusion_reasons(session, keepers)
        feedback_reasons = feedback_tier_reasons(session)
        if reasons or feedback_reasons:
            merged_reasons = list(dict.fromkeys(feedback_reasons + reasons))
            excluded_feedback.append((session.get("session_id") or session.get("_id"), merged_reasons))

    non_feedback_excluded_count = len(
        [session for session in sessions if not session.get("post_debate_feedback")]
    )

    likert_rows = likert_stats(feedback_sessions)
    rubric_rows = rubric_stats(primary_sessions)
    verdicts = verdict_counts(primary_sessions)
    consensus_median = rubric_rows[0]["median"] if rubric_rows else None

    likert_png = chart_dir / "likert_top2box.png"
    rubric_png = chart_dir / "rubric_medians.png"
    summary_md = chart_dir / "numbers_summary.md"

    write_likert_chart(
        likert_png,
        likert_rows,
        len(feedback_sessions),
        verdicts.get("agent", 0),
        consensus_median,
    )
    write_rubric_chart(rubric_png, rubric_rows, len(primary_sessions))
    write_summary(
        summary_md,
        primary_sessions,
        feedback_sessions,
        likert_rows,
        rubric_rows,
        excluded_feedback,
        non_feedback_excluded_count,
    )

    print(f"Primary tier N: {len(primary_sessions)}")
    print(f"Feedback tier N: {len(feedback_sessions)}")
    print("Excluded feedback sessions:")
    if excluded_feedback:
        for session_id, reasons in excluded_feedback:
            print(f"- {session_id}: {', '.join(reasons)}")
    else:
        print("- none")
    print(f"Omitted non-feedback sessions: {non_feedback_excluded_count}")
    print()
    print("Sanity checks:")
    print(
        f"- Primary-tier N changed since last extraction at 4: "
        f"{'yes' if len(primary_sessions) != 4 else 'no'}"
    )
    print(
        f"- Feedback-tier N changed since last extraction at 10: "
        f"{'yes' if len(feedback_sessions) != 10 else 'no'}"
    )
    for path in [likert_png, rubric_png, summary_md]:
        print(f"- {path}: {'ok' if path.exists() and path.stat().st_size > 0 else 'missing/empty'}")


if __name__ == "__main__":
    main()
