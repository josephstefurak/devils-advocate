from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


FEEDBACK_VERSION = "research_feedback_v1"

ScaleResponse = Annotated[int, Field(ge=1, le=5)]

AgeRange = Literal[
    "under_18",
    "18_24",
    "25_34",
    "35_44",
    "45_54",
    "55_plus",
    "prefer_not_to_say",
]

FounderExperience = Literal[
    "first_time_founder",
    "repeat_founder",
    "startup_team_not_founder",
    "student_explorer",
    "not_startup_related",
    "prefer_not_to_say",
]

IndustryDomain = Literal[
    "saas_ai_tooling",
    "consumer",
    "marketplace",
    "healthcare_biotech",
    "fintech",
    "climate_energy",
    "education",
    "enterprise_it",
    "hardware_robotics",
    "services_agency",
    "other",
    "prefer_not_to_say",
]

MostValuablePart = Literal[
    "live_pushback",
    "defending_out_loud",
    "weaknesses_exposed",
    "judge_scorecard",
    "written_report_next_steps",
    "transcript_claim_tracker",
    "other",
]

VoiceAiFamiliarity = Literal[
    "never",
    "a_few_times",
    "monthly",
    "weekly_or_more",
    "prefer_not_to_say",
]

VoiceHurdle = Literal[
    "nothing_major",
    "speech_recognition",
    "turn_taking",
    "pace_too_fast",
    "needed_more_time",
    "audio_quality_lag",
    "awkward_speaking_out_loud",
    "noisy_environment",
    "accessibility",
    "other",
]

VoicePreference = Literal[
    "voice",
    "text_chat",
    "both_depends",
    "no_preference",
]


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _average(*values: int | None) -> float | None:
    answered = [value for value in values if value is not None]
    if not answered:
        return None
    return round(sum(answered) / len(answered), 2)


class IdeaImpactFeedback(BaseModel):
    refined_idea: ScaleResponse
    constructive_challenge: ScaleResponse
    clearer_next_steps: ScaleResponse


class VoiceExperienceFeedback(BaseModel):
    naturalness: ScaleResponse
    turn_taking_ease: ScaleResponse
    expression_ease: ScaleResponse
    next_time_preference: VoicePreference
    hurdles: list[VoiceHurdle] = Field(min_length=1)
    hurdles_other: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_hurdles(self):
        selected = set(self.hurdles)
        if "nothing_major" in selected and len(selected) > 1:
            raise ValueError("nothing_major cannot be combined with other hurdles")
        if "other" in selected and not _clean_optional_text(self.hurdles_other):
            raise ValueError("hurdles_other is required when other is selected")
        if "other" not in selected:
            self.hurdles_other = None
        else:
            self.hurdles_other = _clean_optional_text(self.hurdles_other)
        return self


class ReportUtilityFeedback(BaseModel):
    organization: ScaleResponse
    digestibility: ScaleResponse
    actionability: ScaleResponse


class ValueSignalFeedback(BaseModel):
    most_valuable_part: MostValuablePart


class OpenFeedback(BaseModel):
    most_valuable_insight: str | None = Field(default=None, max_length=1000)
    one_thing_to_change: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def clean_text(self):
        self.most_valuable_insight = _clean_optional_text(self.most_valuable_insight)
        self.one_thing_to_change = _clean_optional_text(self.one_thing_to_change)
        return self


class ParticipantProfile(BaseModel):
    industry_domain: IndustryDomain | None = None
    founder_experience: FounderExperience | None = None
    prior_voice_ai_familiarity: VoiceAiFamiliarity | None = None
    age_range: AgeRange | None = None


class ClientContext(BaseModel):
    report_available: bool


class StudyFeedback(BaseModel):
    idea_impact: IdeaImpactFeedback
    voice_experience: VoiceExperienceFeedback
    report_utility: ReportUtilityFeedback | None = None
    value_signal: ValueSignalFeedback
    open_feedback: OpenFeedback = Field(default_factory=OpenFeedback)
    participant_profile: ParticipantProfile = Field(default_factory=ParticipantProfile)
    client_context: ClientContext

    @model_validator(mode="after")
    def validate_report_alignment(self):
        if self.client_context.report_available and self.report_utility is None:
            raise ValueError("report_utility is required when a report is available")
        if not self.client_context.report_available:
            self.report_utility = None
        return self


class FeedbackSubmissionRequest(BaseModel):
    idToken: str = Field(min_length=1)
    sessionId: str = Field(min_length=1)
    feedback: StudyFeedback


def build_feedback_record(feedback: StudyFeedback) -> dict:
    summary_scores = {
        "idea_impact_index": _average(
            feedback.idea_impact.refined_idea,
            feedback.idea_impact.constructive_challenge,
            feedback.idea_impact.clearer_next_steps,
        ),
        "voice_ux_index": _average(
            feedback.voice_experience.naturalness,
            feedback.voice_experience.turn_taking_ease,
            feedback.voice_experience.expression_ease,
        ),
        "report_utility_index": _average(
            feedback.report_utility.organization if feedback.report_utility else None,
            feedback.report_utility.digestibility if feedback.report_utility else None,
            feedback.report_utility.actionability if feedback.report_utility else None,
        ),
    }

    return {
        **feedback.model_dump(exclude_none=True),
        "feedback_version": FEEDBACK_VERSION,
        "summary_scores": summary_scores,
    }
