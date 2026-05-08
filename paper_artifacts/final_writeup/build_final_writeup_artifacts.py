#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw_export" / "sessions_raw.json"
OUT = ROOT
FIGURES = OUT / "figures"
TABLES = OUT / "tables"

NAVY = "#15264B"
ORANGE = "#E84B36"
GRAY = "#687385"

FEEDBACK_VERSION = "research_feedback_v1"
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


def is_testish_claim(claim: Any) -> bool:
    normalized = normalize_text(claim)
    if not normalized or normalized in TESTISH_EXACT_CLAIMS:
        return True
    if len(normalized) < 15:
        return True
    return any(pattern.search(normalized) for pattern in TESTISH_PATTERNS)


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_seconds(session: dict[str, Any]) -> float | None:
    start = parse_dt(session.get("created_at"))
    end = parse_dt(session.get("ended_at"))
    if start and end:
        return max(0.0, (end - start).total_seconds())
    return None


def feedback(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("post_debate_feedback") or {}


def metrics(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("metrics") or {}


def consensus(session: dict[str, Any]) -> dict[str, Any]:
    result = session.get("judge_result") or {}
    return result.get("consensus") or result


def user_uid(session: dict[str, Any]) -> str:
    return ((session.get("user") or {}).get("uid") or "unknown").strip()


def developer_test_feedback(session: dict[str, Any]) -> bool:
    open_feedback = feedback(session).get("open_feedback") or {}
    text = " ".join(str(value) for value in open_feedback.values() if value)
    return bool(re.search(r"\btest\b|sean\s+kraemer", text, flags=re.IGNORECASE))


def duplicate_keepers(sessions: list[dict[str, Any]]) -> set[int]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        groups[(user_uid(session), normalize_text(session.get("user_claim")))].append(session)
    keepers = set()
    for group in groups.values():
        keepers.add(
            id(
                max(
                    group,
                    key=lambda session: (
                        bool(feedback(session)),
                        bool(session.get("report")),
                        metrics(session).get("user_turns") or 0,
                        parse_dt(session.get("created_at")) or datetime.min,
                    ),
                )
            )
        )
    return keepers


def feedback_reasons(session: dict[str, Any]) -> list[str]:
    reasons = []
    if session.get("consent_given") is not True:
        reasons.append("no_consent")
    if not feedback(session):
        reasons.append("missing_feedback")
    elif feedback(session).get("feedback_version") != FEEDBACK_VERSION:
        reasons.append("unexpected_feedback_version")
    if is_testish_claim(session.get("user_claim")):
        reasons.append("testish_claim")
    if developer_test_feedback(session):
        reasons.append("researcher_or_test_feedback")
    return reasons


def report_backed_reasons(session: dict[str, Any], keepers: set[int]) -> list[str]:
    reasons = feedback_reasons(session)
    client_context = feedback(session).get("client_context") or {}
    if not session.get("ended_at"):
        reasons.append("missing_ended_at")
    if not session.get("report"):
        reasons.append("missing_report")
    if client_context.get("report_available") is not True:
        reasons.append("report_not_available_to_participant")
    if (metrics(session).get("user_turns") or 0) < 2:
        reasons.append("too_few_user_turns")
    if (metrics(session).get("agent_turns") or 0) < 2:
        reasons.append("too_few_agent_turns")
    if id(session) not in keepers:
        reasons.append("non_keeper_duplicate")
    return list(dict.fromkeys(reasons))


def hinges(values: list[float]) -> tuple[float | None, float | None, float | None]:
    values = sorted(values)
    if not values:
        return None, None, None
    if len(values) == 1:
        return values[0], values[0], values[0]
    middle = median(values)
    if len(values) % 2:
        lower = values[: len(values) // 2]
        upper = values[len(values) // 2 + 1 :]
    else:
        lower = values[: len(values) // 2]
        upper = values[len(values) // 2 :]
    return median(lower), middle, median(upper)


def fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def nested(data: dict[str, Any], *keys: str) -> Any:
    cur = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def anonymize(sessions: list[dict[str, Any]]) -> dict[str, str]:
    ordered = sorted(sessions, key=lambda session: session.get("created_at") or "")
    return {session.get("session_id"): f"P{i + 1}" for i, session in enumerate(ordered)}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_chart(fig: plt.Figure, basename: str) -> None:
    fig.savefig(FIGURES / f"{basename}.png", dpi=200, facecolor="white")
    fig.savefig(FIGURES / f"{basename}.svg", facecolor="white")
    plt.close(fig)


def manual_transcript_coding(primary: list[dict[str, Any]], pid: dict[str, str]) -> list[dict[str, Any]]:
    # Single-author, lightweight coding from redacted transcripts. Challenge paraphrases are intentionally generic.
    coded = {
        "20260402_201133_57275ef9": [
            (2, "Pressed two-sided marketplace liquidity/critical-mass assumptions.", "yes", "strong", "Google Search claim", "possible issue", "deflected", "yes", "Evidence was plausible but not externally verified here."),
            (4, "Challenged supplier participation and behavior-change assumptions.", "yes", "acceptable", "general startup knowledge", "no obvious issue", "deflected", "yes", "Moved the user toward adoption incentives."),
            (6, "Questioned analogy to more stable marketplace categories and free-adoption logic.", "yes", "acceptable", "user-provided material", "possible issue", "deflected", "yes", "Some challenge text was truncated in the transcript."),
            (9, "Pressed localized demand generation and acquisition-cost feasibility.", "yes", "strong", "Google Search claim", "possible issue", "new claim", "yes", "User responded with a partnership/distribution move."),
        ],
        "20260422_161931_21a1e6a4": [
            (2, "Challenged incumbent/platform absorption risk for an AI workflow concept.", "yes", "strong", "general startup knowledge", "no obvious issue", "deflected", "yes", "Strong relevance to defensibility."),
            (4, "Continued incumbent-risk challenge after a non-substantive response.", "yes", "acceptable", "session transcript", "no obvious issue", "no substantive response", "no", "Agent turn was partially truncated."),
            (6, "Questioned whether the target customer pain was must-have versus nice-to-have.", "yes", "strong", "general startup knowledge", "no obvious issue", "deflected", "yes", "Directly addressed adoption and pain intensity."),
            (9, "Reframed the answer as insufficient against platform/incumbent risk.", "yes", "acceptable", "session transcript", "no obvious issue", "no substantive response", "yes", "Repeated a prior critique, but still relevant."),
        ],
        "20260422_165031_1f7420c6": [
            (2, "Questioned retention for a low-frequency consumer utility.", "yes", "strong", "Google Search claim", "possible issue", "deflected", "yes", "Evidence claim not externally verified in this audit."),
            (4, "Argued one-time setup undermines recurring business-model strength.", "yes", "acceptable", "session transcript", "no obvious issue", "defended", "yes", "User responded with a subscription model."),
            (7, "Pressed whether a passive subscription can sustain value and avoid cancellation.", "yes", "strong", "Google Search claim", "possible issue", "no substantive response", "yes", "Good challenge, but no later response captured."),
        ],
    }
    rows = []
    for session in sorted(primary, key=lambda s: s.get("created_at") or ""):
        sid = session.get("session_id")
        for item in coded.get(sid, []):
            rows.append(
                {
                    "participant_id": pid[sid],
                    "turn_number": item[0],
                    "challenge_paraphrase_redacted": item[1],
                    "relevant_to_pitch": item[2],
                    "logical_soundness": item[3],
                    "evidence_type": item[4],
                    "factual_risk": item[5],
                    "user_response_type": item[6],
                    "productive_moment": item[7],
                    "notes_redacted": item[8],
                }
            )
    return rows


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    sessions = json.loads(RAW.read_text(encoding="utf-8"))
    keepers = duplicate_keepers(sessions)
    feedback_all = [s for s in sessions if feedback(s)]
    feedback_valid = [s for s in feedback_all if not feedback_reasons(s)]
    primary = [s for s in sessions if not report_backed_reasons(s, keepers)]
    pid = anonymize(feedback_valid)

    # Inclusion rows.
    inclusion = [
        {"metric": "sessions_started_exported", "count": len(sessions), "notes": "Fresh shared Firestore export."},
        {"metric": "consented_sessions", "count": sum(1 for s in sessions if s.get("consent_given") is True), "notes": "No-consent sessions may be deleted at finalization."},
        {"metric": "sessions_ending_cleanly", "count": sum(1 for s in sessions if s.get("ended_at")), "notes": "Any finalized session in export."},
        {"metric": "sessions_with_generated_report", "count": sum(1 for s in sessions if s.get("report")), "notes": "Any session with report object, regardless of feedback."},
        {"metric": "feedback_submissions_raw", "count": len(feedback_all), "notes": "Before removing researcher/test response."},
        {"metric": "valid_research_feedback_submissions", "count": len(feedback_valid), "notes": "N for survey analysis."},
        {"metric": "excluded_researcher_test_feedback", "count": sum(1 for s in feedback_all if developer_test_feedback(s)), "notes": "Open text contained test marker."},
        {"metric": "valid_report_backed_sessions", "count": len(primary), "notes": "n for report-backed analysis."},
        {"metric": "report_backed_with_five_judge_verdicts", "count": sum(1 for s in primary if len((s.get("judge_result") or {}).get("verdicts") or []) == 5), "notes": "One older report-backed record only has consensus-style result."},
        {"metric": "non_test_claim_sessions", "count": sum(1 for s in sessions if not is_testish_claim(s.get("user_claim"))), "notes": "Claim heuristic only."},
    ]
    write_csv(TABLES / "inclusion_counts.csv", inclusion)

    excluded = []
    for session in sorted(feedback_all, key=lambda s: s.get("created_at") or ""):
        sid = session.get("session_id")
        excluded.append(
            {
                "participant_or_row": pid.get(sid, "excluded"),
                "session_id_redacted": f"session_{len(excluded) + 1}",
                "created_at": session.get("created_at"),
                "feedback_tier_reasons": "; ".join(feedback_reasons(session)) or "included",
                "report_backed_reasons": "; ".join(report_backed_reasons(session, keepers)) or "included",
            }
        )
    write_csv(TABLES / "inclusion_exclusion_audit.csv", excluded)

    # Survey stats.
    construct_defs = [
        ("Idea impact", "idea_impact_index"),
        ("Voice UX", "voice_ux_index"),
        ("Report utility", "report_utility_index"),
    ]
    construct_rows = []
    for label, key in construct_defs:
        vals = [nested(feedback(s), "summary_scores", key) for s in feedback_valid]
        vals = [float(v) for v in vals if isinstance(v, (int, float))]
        q1, med, q3 = hinges(vals)
        construct_rows.append(
            {"construct": label, "n": len(vals), "median": fmt(med), "iqr": fmt(None if q1 is None or q3 is None else q3 - q1), "min": fmt(min(vals) if vals else None), "max": fmt(max(vals) if vals else None)}
        )
    write_csv(TABLES / "survey_constructs.csv", construct_rows)

    likert_defs = [
        ("Refined idea", ("idea_impact", "refined_idea")),
        ("Constructive challenge", ("idea_impact", "constructive_challenge")),
        ("Clearer next steps", ("idea_impact", "clearer_next_steps")),
        ("Voice naturalness", ("voice_experience", "naturalness")),
        ("Turn-taking ease", ("voice_experience", "turn_taking_ease")),
        ("Expression ease", ("voice_experience", "expression_ease")),
        ("Report organization", ("report_utility", "organization")),
        ("Report digestibility", ("report_utility", "digestibility")),
        ("Report actionability", ("report_utility", "actionability")),
    ]
    likert_rows = []
    for label, path in likert_defs:
        vals = [nested(feedback(s), *path) for s in feedback_valid]
        vals = [float(v) for v in vals if isinstance(v, (int, float))]
        q1, med, q3 = hinges(vals)
        top2 = sum(1 for v in vals if v >= 4)
        likert_rows.append(
            {"item": label, "top2": top2, "n": len(vals), "median": fmt(med), "iqr": fmt(None if q1 is None or q3 is None else q3 - q1)}
        )
    write_csv(TABLES / "likert_top2_counts.csv", likert_rows)

    mv = Counter(nested(feedback(s), "value_signal", "most_valuable_part") for s in feedback_valid)
    value_rows = [{"most_valuable_part": k, "count": v} for k, v in mv.most_common()]
    write_csv(TABLES / "most_valuable_counts.csv", value_rows)

    hurdles = Counter()
    for s in feedback_valid:
        hurdles.update(nested(feedback(s), "voice_experience", "hurdles") or [])
    hurdle_rows = [{"hurdle": k, "count": v} for k, v in hurdles.most_common()]
    write_csv(TABLES / "ux_hurdle_counts.csv", hurdle_rows)

    theme_rows = [
        {"theme": "Need more response control/time", "count": 3, "evidence": "Requests for more time, pause, manual start, or larger response allowance."},
        {"theme": "Speech recognition / microphone reliability", "count": 3, "evidence": "Mentions of filler noise, microphone sensitivity, or cut-off transcription."},
        {"theme": "Sharper weakness exposure was valuable", "count": 4, "evidence": "Open text credited the system with exposing holes, weaknesses, or business-model assumptions."},
        {"theme": "Mobile / modality fit issues", "count": 2, "evidence": "Mentions of mobile compatibility or multimodal inputs."},
    ]
    write_csv(TABLES / "open_text_themes.csv", theme_rows)

    # Report-backed stats.
    rubric_keys = ["problem_clarity", "market_logic", "execution_risk", "competitive_awareness", "internal_coherence"]
    rubric_rows = []
    overall_vals = []
    for s in primary:
        c = consensus(s)
        if isinstance(c.get("overall"), (int, float)):
            overall_vals.append(float(c["overall"]))
    q1, overall_median, q3 = hinges(overall_vals)
    rubric_rows.append({"dimension": "consensus_overall", "n": len(overall_vals), "median": fmt(overall_median), "iqr": fmt(None if q1 is None or q3 is None else q3 - q1), "min": fmt(min(overall_vals) if overall_vals else None), "max": fmt(max(overall_vals) if overall_vals else None)})
    for key in rubric_keys:
        vals = []
        for s in primary:
            v = nested(consensus(s), "scores", key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        q1, med, q3 = hinges(vals)
        rubric_rows.append({"dimension": key, "n": len(vals), "median": fmt(med), "iqr": fmt(None if q1 is None or q3 is None else q3 - q1), "min": fmt(min(vals) if vals else None), "max": fmt(max(vals) if vals else None)})
    write_csv(TABLES / "judge_rubric_summary.csv", rubric_rows)

    judge_means = defaultdict(list)
    for s in primary:
        for verdict in (s.get("judge_result") or {}).get("verdicts") or []:
            if isinstance(verdict.get("overall"), (int, float)):
                judge_means[verdict.get("judge_name", "unknown")].append(float(verdict["overall"]))
    judge_mean_rows = [{"judge": k, "mean_overall": fmt(sum(v) / len(v)), "n": len(v)} for k, v in sorted(judge_means.items())]
    write_csv(TABLES / "per_judge_mean_overall.csv", judge_mean_rows)

    class_counts = Counter()
    user_turns_analyzed = 0
    for s in primary:
        updates = s.get("judge_updates") or []
        user_turns_analyzed += len(updates)
        for update in updates:
            class_counts[update.get("classification", "unknown")] += 1
    class_rows = [{"classification": k, "count": class_counts.get(k, 0)} for k in ["DEFENDED", "CONCEDED", "NEW_CLAIM", "DEFLECTED"]]
    write_csv(TABLES / "turn_classification_counts.csv", class_rows)

    # Transcript coding.
    transcript_rows = manual_transcript_coding(primary, pid)
    write_csv(TABLES / "transcript_challenge_coding.csv", transcript_rows)
    coding_summary = [
        {"metric": "adversary_challenges_coded", "count": len(transcript_rows)},
        {"metric": "relevant_to_pitch_yes", "count": sum(1 for r in transcript_rows if r["relevant_to_pitch"] == "yes")},
        {"metric": "acceptable_or_strong_logic", "count": sum(1 for r in transcript_rows if r["logical_soundness"] in {"acceptable", "strong"})},
        {"metric": "supported_by_evidence_or_context", "count": sum(1 for r in transcript_rows if r["evidence_type"] in {"user-provided material", "session transcript", "Google Search claim", "general startup knowledge"})},
        {"metric": "possible_or_high_factual_risk", "count": sum(1 for r in transcript_rows if r["factual_risk"] in {"possible issue", "high risk"})},
        {"metric": "productive_moments_yes", "count": sum(1 for r in transcript_rows if r["productive_moment"] == "yes")},
    ]
    write_csv(TABLES / "transcript_coding_summary.csv", coding_summary)

    # Charts.
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    labels = [r["construct"] + f"\\n(n={r['n']})" for r in construct_rows]
    values = [float(r["median"]) if r["median"] != "n/a" else 0 for r in construct_rows]
    ax.bar(labels, values, color=[NAVY, NAVY, ORANGE])
    ax.set_ylim(0, 5)
    ax.set_ylabel("Median index (1-5)")
    ax.set_title("Pilot survey construct medians", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#D8DDE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    for i, v in enumerate(values):
        ax.text(i, v + 0.08, f"{v:.1f}", ha="center", fontweight="bold")
    save_chart(fig, "pilot_survey_constructs")

    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    mv_labels = [r["most_valuable_part"].replace("_", " ") for r in value_rows]
    mv_values = [r["count"] for r in value_rows]
    ax.barh(mv_labels[::-1], mv_values[::-1], color=NAVY)
    ax.set_xlabel("Count")
    ax.set_title("Most valuable interaction component (N=9)", loc="left", fontweight="bold")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    for y, v in enumerate(mv_values[::-1]):
        ax.text(v + 0.05, y, str(v), va="center", fontweight="bold")
    save_chart(fig, "most_valuable_counts")

    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    jr_plot = rubric_rows
    labels = [r["dimension"].replace("_", " ") for r in jr_plot][::-1]
    values = [float(r["median"]) if r["median"] != "n/a" else 0 for r in jr_plot][::-1]
    colors = ([ORANGE] + [NAVY] * (len(jr_plot) - 1))[::-1]
    ax.barh(labels, values, color=colors)
    ax.axvline(6.0, linestyle="--", color=GRAY, linewidth=1)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Median consensus score")
    ax.set_title("Judge scores, report-backed subset (n=3)", loc="left", fontweight="bold")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#D8DDE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    for y, v in enumerate(values):
        ax.text(v + 0.1, y, f"{v:.1f}", va="center", fontweight="bold")
    save_chart(fig, "judge_scores_report_subset")

    fig, ax = plt.subplots(figsize=(7.2, 4.05))
    labels = [r["classification"] for r in class_rows]
    values = [r["count"] for r in class_rows]
    ax.bar(labels, values, color=NAVY)
    ax.set_ylabel("Count")
    ax.set_title("Per-turn judge classifications (available report-backed turns)", loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#D8DDE8", linewidth=0.7)
    ax.set_axisbelow(True)
    for i, v in enumerate(values):
        ax.text(i, v + 0.05, str(v), ha="center", fontweight="bold")
    save_chart(fig, "turn_classification_counts")

    # LaTeX snippets.
    latex = r"""\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/pilot_survey_constructs.png}
\caption{Descriptive pilot survey construct medians. Idea impact and voice UX use all valid research feedback submissions (N=9); report utility is available only when a post-debate report was shown (n=3).}
\label{fig:pilot-survey-constructs}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/most_valuable_counts.png}
\caption{Participants most often selected weakness exposure as the most valuable component of the interaction. Counts are descriptive because the formative pilot sample is small (N=9).}
\label{fig:most-valuable-counts}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figures/judge_scores_report_subset.png}
\caption{Consensus judge scores for the report-backed subset (n=3). The dashed threshold at 6.0 indicates the founder-win cutoff used by the system; all report-backed sessions were scored below this threshold.}
\label{fig:judge-scores}
\end{figure}

\begin{table}[t]
\centering
\small
\begin{tabular}{lccc}
\toprule
Measure & n & Median & IQR \\
\midrule
Idea impact index & 9 & 4.0 & 1.8 \\
Voice UX index & 9 & 4.0 & 1.3 \\
Report utility index & 3 & 3.7 & 1.7 \\
Consensus overall score & 3 & 3.2 & 1.2 \\
\bottomrule
\end{tabular}
\caption{Descriptive outcomes from the formative pilot. Report utility and judge scores are limited to the report-backed subset.}
\label{tab:pilot-results}
\end{table}
"""
    (OUT / "latex_snippets.tex").write_text(latex, encoding="utf-8")

    summary = {
        "total_sessions": len(sessions),
        "valid_feedback_N": len(feedback_valid),
        "report_backed_n": len(primary),
        "report_backed_with_five_judges": sum(1 for s in primary if len((s.get("judge_result") or {}).get("verdicts") or []) == 5),
        "turn_classification_updates_available": user_turns_analyzed,
        "figures": sorted(p.name for p in FIGURES.glob("*")),
        "tables": sorted(p.name for p in TABLES.glob("*")),
    }
    (OUT / "artifact_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
