import { useState } from 'react'
import { colors, font, spacing, radius } from '../theme'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const AGREEMENT_SCALE = [
    { value: 1, label: '1', aria: 'Strongly disagree' },
    { value: 2, label: '2', aria: 'Disagree' },
    { value: 3, label: '3', aria: 'Neutral' },
    { value: 4, label: '4', aria: 'Agree' },
    { value: 5, label: '5', aria: 'Strongly agree' },
]

const IDEA_IMPACT_QUESTIONS = [
    {
        key: 'refined_idea',
        prompt: 'The debate helped me refine or improve my business idea.',
    },
    {
        key: 'constructive_challenge',
        prompt: 'The debate felt constructive rather than simply tearing my idea down.',
    },
    {
        key: 'clearer_next_steps',
        prompt: 'I left the debate with clearer next steps for improving the idea.',
    },
]

const VOICE_EXPERIENCE_QUESTIONS = [
    {
        key: 'naturalness',
        prompt: 'Speaking with the system felt natural.',
    },
    {
        key: 'turn_taking_ease',
        prompt: 'It was easy to know when to speak or interrupt.',
    },
    {
        key: 'expression_ease',
        prompt: 'The voice format made it easy to express my thinking.',
    },
]

const REPORT_UTILITY_QUESTIONS = [
    {
        key: 'organization',
        prompt: 'The report sections felt well organized.',
    },
    {
        key: 'digestibility',
        prompt: 'The report was easy to digest.',
    },
    {
        key: 'actionability',
        prompt: 'The report gave me actionable insights.',
    },
]

const VOICE_PREFERENCE_OPTIONS = [
    { value: 'voice', label: 'Voice' },
    { value: 'text_chat', label: 'Text chat' },
    { value: 'both_depends', label: 'Both / depends' },
    { value: 'no_preference', label: 'No preference' },
]

const VOICE_HURDLE_OPTIONS = [
    { value: 'nothing_major', label: 'Nothing major' },
    { value: 'speech_recognition', label: 'Speech recognition misunderstood me' },
    { value: 'turn_taking', label: 'Hard to know when to jump in' },
    { value: 'pace_too_fast', label: 'Pace felt too fast' },
    { value: 'needed_more_time', label: 'Needed more time to think' },
    { value: 'audio_quality_lag', label: 'Audio quality / lag' },
    { value: 'awkward_speaking_out_loud', label: 'Felt awkward speaking out loud' },
    { value: 'noisy_environment', label: 'Noisy environment' },
    { value: 'accessibility', label: 'Accessibility / hearing / speech issue' },
    { value: 'other', label: 'Other' },
]

const MOST_VALUABLE_PART_OPTIONS = [
    { value: 'live_pushback', label: 'Live pushback' },
    { value: 'defending_out_loud', label: 'Defending it out loud' },
    { value: 'weaknesses_exposed', label: 'Seeing weaknesses exposed' },
    { value: 'judge_scorecard', label: 'Judge scorecard' },
    { value: 'written_report_next_steps', label: 'Written report / next steps' },
    { value: 'transcript_claim_tracker', label: 'Transcript / claim tracker' },
    { value: 'other', label: 'Other' },
]

const INDUSTRY_OPTIONS = [
    { value: 'saas_ai_tooling', label: 'SaaS / AI tooling' },
    { value: 'consumer', label: 'Consumer' },
    { value: 'marketplace', label: 'Marketplace' },
    { value: 'healthcare_biotech', label: 'Healthcare / biotech' },
    { value: 'fintech', label: 'Fintech' },
    { value: 'climate_energy', label: 'Climate / energy' },
    { value: 'education', label: 'Education' },
    { value: 'enterprise_it', label: 'Enterprise / IT' },
    { value: 'hardware_robotics', label: 'Hardware / robotics' },
    { value: 'services_agency', label: 'Services / agency' },
    { value: 'other', label: 'Other' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

const FOUNDER_EXPERIENCE_OPTIONS = [
    { value: 'first_time_founder', label: 'First-time founder' },
    { value: 'repeat_founder', label: 'Repeat founder' },
    { value: 'startup_team_not_founder', label: 'Startup team, not founder' },
    { value: 'student_explorer', label: 'Student exploring ideas' },
    { value: 'not_startup_related', label: 'Not startup-related' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

const VOICE_AI_FAMILIARITY_OPTIONS = [
    { value: 'never', label: 'Never' },
    { value: 'a_few_times', label: 'A few times' },
    { value: 'monthly', label: 'Monthly' },
    { value: 'weekly_or_more', label: 'Weekly or more' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

const AGE_RANGE_OPTIONS = [
    { value: 'under_18', label: 'Under 18' },
    { value: '18_24', label: '18-24' },
    { value: '25_34', label: '25-34' },
    { value: '35_44', label: '35-44' },
    { value: '45_54', label: '45-54' },
    { value: '55_plus', label: '55+' },
    { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

const mono = {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: 2,
}

const serif = {
    fontFamily: "'Georgia', 'Times New Roman', serif",
}

const sectionTitle = {
    ...mono,
    color: colors.textFaint,
    fontSize: 10,
    marginBottom: spacing.md,
}

const label = {
    ...mono,
    color: colors.textDim,
    marginBottom: spacing.sm,
    display: 'block',
    lineHeight: 1.5,
}

function Divider() {
    return <div style={{ height: 1, background: colors.border, margin: `${spacing.md} 0 ${spacing.lg} 0` }} />
}

function LikertQuestion({ prompt, value, onChange }) {
    return (
        <div style={{ marginBottom: spacing.md }}>
            <span style={label}>{prompt}</span>
            <div role="group" aria-label={prompt}>
                <div style={{ display: 'flex', gap: spacing.xs, marginBottom: 6 }}>
                    {AGREEMENT_SCALE.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            aria-label={`${prompt} ${option.aria}`}
                            aria-pressed={value === option.value}
                            onClick={() => onChange(option.value)}
                            style={{
                                flex: 1,
                                minHeight: 38,
                                borderRadius: radius.sm,
                                border: `1px solid ${value === option.value ? colors.info : colors.border}`,
                                background: value === option.value ? `${colors.info}18` : colors.bgSurface,
                                color: value === option.value ? colors.info : colors.textDim,
                                cursor: 'pointer',
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: font.md,
                                fontWeight: value === option.value ? 700 : 400,
                                transition: 'all 0.15s ease',
                            }}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    ...mono,
                    fontSize: 9,
                    color: colors.textFaint,
                    letterSpacing: 1,
                }}>
                    <span>Strongly disagree</span>
                    <span>Strongly agree</span>
                </div>
            </div>
        </div>
    )
}

function ChipSelect({ options, value, onChange, multi = false, exclusiveValue = null, prompt }) {
    function toggle(selected) {
        if (!multi) {
            onChange(value === selected ? null : selected)
            return
        }

        if (selected === exclusiveValue) {
            onChange(value.includes(selected) ? [] : [selected])
            return
        }

        const withoutExclusive = exclusiveValue ? value.filter((entry) => entry !== exclusiveValue) : value
        const next = withoutExclusive.includes(selected)
            ? withoutExclusive.filter((entry) => entry !== selected)
            : [...withoutExclusive, selected]
        onChange(next)
    }

    const isSelected = (selected) => multi ? value.includes(selected) : value === selected

    return (
        <div style={{ marginBottom: spacing.md }}>
            <span style={label}>{prompt}</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.xs }}>
                {options.map((option) => (
                    <button
                        key={option.value}
                        type="button"
                        aria-label={option.label}
                        aria-pressed={isSelected(option.value)}
                        onClick={() => toggle(option.value)}
                        style={{
                            padding: `7px 12px`,
                            borderRadius: radius.sm,
                            border: `1px solid ${isSelected(option.value) ? colors.info : colors.border}`,
                            background: isSelected(option.value) ? `${colors.info}18` : colors.bgSurface,
                            color: isSelected(option.value) ? colors.info : colors.textDim,
                            cursor: 'pointer',
                            ...mono,
                            fontSize: 10,
                            transition: 'all 0.15s ease',
                        }}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    )
}

function TextAreaField({ prompt, placeholder, value, onChange, rows = 3 }) {
    return (
        <div style={{ marginBottom: spacing.md }}>
            <label style={label}>
                {prompt}
                <textarea
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    placeholder={placeholder}
                    rows={rows}
                    style={textareaStyle}
                />
            </label>
        </div>
    )
}

function setGroupedValue(setter, key, nextValue) {
    setter((prev) => ({ ...prev, [key]: nextValue }))
}

export function FeedbackWidget({ sessionId, user, consentGiven, hasReport }) {
    const [isOpen, setIsOpen] = useState(false)
    const [showProfile, setShowProfile] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState('')

    const [ideaImpact, setIdeaImpact] = useState({
        refined_idea: null,
        constructive_challenge: null,
        clearer_next_steps: null,
    })
    const [voiceExperience, setVoiceExperience] = useState({
        naturalness: null,
        turn_taking_ease: null,
        expression_ease: null,
    })
    const [reportUtility, setReportUtility] = useState({
        organization: null,
        digestibility: null,
        actionability: null,
    })
    const [nextTimePreference, setNextTimePreference] = useState(null)
    const [voiceHurdles, setVoiceHurdles] = useState([])
    const [voiceHurdlesOther, setVoiceHurdlesOther] = useState('')
    const [mostValuablePart, setMostValuablePart] = useState(null)
    const [mostValuableInsight, setMostValuableInsight] = useState('')
    const [oneThingToChange, setOneThingToChange] = useState('')
    const [participantProfile, setParticipantProfile] = useState({
        industry_domain: null,
        founder_experience: null,
        prior_voice_ai_familiarity: null,
        age_range: null,
    })

    const hasUserContext = Boolean(sessionId && user)
    const needsOtherHurdleText = voiceHurdles.includes('other')
    const requiredAnswered =
        Object.values(ideaImpact).every(Boolean) &&
        Object.values(voiceExperience).every(Boolean) &&
        Boolean(nextTimePreference) &&
        voiceHurdles.length > 0 &&
        (!needsOtherHurdleText || voiceHurdlesOther.trim().length > 0) &&
        Boolean(mostValuablePart) &&
        (!hasReport || Object.values(reportUtility).every(Boolean))

    const canSubmit = consentGiven && hasUserContext && requiredAnswered && !submitting

    async function handleSubmit() {
        if (!canSubmit) {
            return
        }

        setSubmitting(true)
        setError('')

        try {
            const idToken = await user.getIdToken()
            const response = await fetch(`${BACKEND_URL}/session_feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    idToken,
                    sessionId,
                    feedback: {
                        idea_impact: ideaImpact,
                        voice_experience: {
                            ...voiceExperience,
                            next_time_preference: nextTimePreference,
                            hurdles: voiceHurdles,
                            hurdles_other: needsOtherHurdleText ? voiceHurdlesOther.trim() : null,
                        },
                        report_utility: hasReport ? reportUtility : null,
                        value_signal: {
                            most_valuable_part: mostValuablePart,
                        },
                        open_feedback: {
                            most_valuable_insight: mostValuableInsight.trim() || null,
                            one_thing_to_change: oneThingToChange.trim() || null,
                        },
                        participant_profile: participantProfile,
                        client_context: {
                            report_available: hasReport,
                        },
                    },
                }),
            })

            const data = await response.json().catch(() => ({}))
            if (!response.ok) {
                throw new Error(data.error || 'Submission failed.')
            }

            setSubmitted(true)
        } catch (err) {
            console.error('Feedback submission error:', err)
            setError(err.message || 'Submission failed.')
        } finally {
            setSubmitting(false)
        }
    }

    if (!consentGiven) {
        return (
            <div style={containerStyle}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: spacing.sm }}>
                    <span style={{ fontSize: 14 }}>🔒</span>
                    <div>
                        <div style={{ ...mono, color: colors.textMuted, marginBottom: spacing.xs }}>
                            Research feedback unavailable
                        </div>
                        <p style={{ ...serif, color: colors.textGhost, margin: 0, lineHeight: 1.5 }}>
                            Research sharing was turned off during this debate, so this session’s survey responses will not be stored either.
                        </p>
                    </div>
                </div>
            </div>
        )
    }

    if (!hasUserContext) {
        return (
            <div style={containerStyle}>
                <p style={{ ...serif, color: colors.textGhost, margin: 0, lineHeight: 1.5 }}>
                    Feedback is unavailable because this session does not have an active research record.
                </p>
            </div>
        )
    }

    if (submitted) {
        return (
            <div style={containerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                    <span style={{ fontSize: 14 }}>✓</span>
                    <span style={{ ...mono, color: colors.success }}>
                        Thanks — research feedback recorded
                    </span>
                </div>
            </div>
        )
    }

    if (!isOpen) {
        return (
            <div style={containerStyle}>
                <button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    style={headerButtonStyle}
                >
                    <div>
                        <div style={{ ...mono, color: colors.textMuted, marginBottom: 4 }}>
                            Study feedback
                        </div>
                        <p style={{ ...serif, color: colors.textGhost, margin: 0, lineHeight: 1.5 }}>
                            Help us evaluate idea impact, voice usability, and report quality. About 2-3 minutes.
                        </p>
                    </div>
                    <span style={{ ...mono, color: colors.textFaint, fontSize: 10 }}>OPEN</span>
                </button>
            </div>
        )
    }

    return (
        <div style={containerStyle}>
            <button
                type="button"
                onClick={() => setIsOpen(false)}
                style={headerButtonStyle}
            >
                <div>
                    <div style={{ ...mono, color: colors.textMuted, marginBottom: 4 }}>
                        Study feedback
                    </div>
                    <p style={{ ...serif, color: colors.textGhost, margin: 0, lineHeight: 1.5 }}>
                        Short post-debate survey focused on the debate experience, live voice flow, and report usefulness.
                    </p>
                </div>
                <span style={{ ...mono, color: colors.textFaint, fontSize: 10 }}>CLOSE</span>
            </button>

            <Divider />

            <div style={sectionTitle}>Debate outcomes</div>
            {IDEA_IMPACT_QUESTIONS.map((question) => (
                <LikertQuestion
                    key={question.key}
                    prompt={question.prompt}
                    value={ideaImpact[question.key]}
                    onChange={(nextValue) => setGroupedValue(setIdeaImpact, question.key, nextValue)}
                />
            ))}

            <Divider />

            <div style={sectionTitle}>Voice experience</div>
            {VOICE_EXPERIENCE_QUESTIONS.map((question) => (
                <LikertQuestion
                    key={question.key}
                    prompt={question.prompt}
                    value={voiceExperience[question.key]}
                    onChange={(nextValue) => setGroupedValue(setVoiceExperience, question.key, nextValue)}
                />
            ))}

            <ChipSelect
                prompt="If you did this again, which format would you prefer?"
                options={VOICE_PREFERENCE_OPTIONS}
                value={nextTimePreference}
                onChange={setNextTimePreference}
            />

            <ChipSelect
                prompt="What made the voice debate difficult, if anything? Select all that apply."
                options={VOICE_HURDLE_OPTIONS}
                value={voiceHurdles}
                onChange={setVoiceHurdles}
                multi
                exclusiveValue="nothing_major"
            />

            {needsOtherHurdleText && (
                <TextAreaField
                    prompt="What other hurdle mattered?"
                    placeholder="Describe the main issue."
                    value={voiceHurdlesOther}
                    onChange={setVoiceHurdlesOther}
                    rows={2}
                />
            )}

            <Divider />

            <div style={sectionTitle}>Report utility</div>
            {hasReport ? (
                REPORT_UTILITY_QUESTIONS.map((question) => (
                    <LikertQuestion
                        key={question.key}
                        prompt={question.prompt}
                        value={reportUtility[question.key]}
                        onChange={(nextValue) => setGroupedValue(setReportUtility, question.key, nextValue)}
                    />
                ))
            ) : (
                <p style={{ ...serif, color: colors.textGhost, marginTop: 0, lineHeight: 1.5 }}>
                    No post-debate report was generated for this session, so report-specific questions are skipped.
                </p>
            )}

            <Divider />

            <div style={sectionTitle}>Value signal</div>
            <ChipSelect
                prompt="What was the most valuable part of the experience?"
                options={MOST_VALUABLE_PART_OPTIONS}
                value={mostValuablePart}
                onChange={setMostValuablePart}
            />

            <TextAreaField
                prompt="What was the single most valuable insight or moment? Optional."
                placeholder="The most useful challenge, realization, or quote."
                value={mostValuableInsight}
                onChange={setMostValuableInsight}
            />

            <TextAreaField
                prompt="If one thing should change before the next study session, what should it be? Optional."
                placeholder="One concrete change that would improve the experience."
                value={oneThingToChange}
                onChange={setOneThingToChange}
            />

            <Divider />

            <button
                type="button"
                onClick={() => setShowProfile((prev) => !prev)}
                style={inlineToggleStyle}
            >
                <span>{showProfile ? '−' : '+'}</span>
                <span>About you (optional)</span>
            </button>

            {showProfile && (
                <div style={{ marginTop: spacing.md }}>
                    <p style={{ ...serif, color: colors.textGhost, marginTop: 0, lineHeight: 1.5 }}>
                        These are broad, anonymous ranges only. They help us interpret who the tool is working for.
                    </p>

                    <ChipSelect
                        prompt="What industry or domain best fits your idea?"
                        options={INDUSTRY_OPTIONS}
                        value={participantProfile.industry_domain}
                        onChange={(nextValue) => setGroupedValue(setParticipantProfile, 'industry_domain', nextValue)}
                    />

                    <ChipSelect
                        prompt="Which description best fits your startup experience?"
                        options={FOUNDER_EXPERIENCE_OPTIONS}
                        value={participantProfile.founder_experience}
                        onChange={(nextValue) => setGroupedValue(setParticipantProfile, 'founder_experience', nextValue)}
                    />

                    <ChipSelect
                        prompt="How familiar are you with voice AI tools?"
                        options={VOICE_AI_FAMILIARITY_OPTIONS}
                        value={participantProfile.prior_voice_ai_familiarity}
                        onChange={(nextValue) => setGroupedValue(setParticipantProfile, 'prior_voice_ai_familiarity', nextValue)}
                    />

                    <ChipSelect
                        prompt="What is your age range?"
                        options={AGE_RANGE_OPTIONS}
                        value={participantProfile.age_range}
                        onChange={(nextValue) => setGroupedValue(setParticipantProfile, 'age_range', nextValue)}
                    />
                </div>
            )}

            {error && (
                <>
                    <Divider />
                    <p style={{ ...mono, color: colors.accent, margin: `0 0 ${spacing.sm}px`, fontSize: 10 }}>
                        {error}
                    </p>
                </>
            )}

            <Divider />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md }}>
                <p style={{ ...serif, color: colors.textGhost, margin: 0, lineHeight: 1.5 }}>
                    Responses are stored with this session’s research record only.
                </p>
                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={!canSubmit}
                    style={{
                        padding: '9px 20px',
                        background: canSubmit ? `${colors.info}18` : 'transparent',
                        color: canSubmit ? colors.info : colors.textGhost,
                        border: `1px solid ${canSubmit ? colors.info : colors.border}`,
                        borderRadius: radius.sm,
                        ...mono,
                        cursor: canSubmit ? 'pointer' : 'default',
                        opacity: canSubmit ? 1 : 0.5,
                        transition: 'all 0.15s ease',
                        flexShrink: 0,
                    }}
                >
                    {submitting ? 'Submitting...' : 'Submit feedback'}
                </button>
            </div>
        </div>
    )
}

const containerStyle = {
    marginTop: spacing.lg,
    background: colors.bgSurfaceAlt,
    border: `1px solid ${colors.borderSubtle}`,
    borderTop: `2px solid ${colors.info}`,
    borderRadius: radius.lg,
    padding: spacing.lg,
}

const headerButtonStyle = {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    width: '100%',
    padding: 0,
    gap: spacing.md,
    textAlign: 'left',
}

const inlineToggleStyle = {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    ...mono,
    color: colors.textFaint,
    fontSize: 10,
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
}

const textareaStyle = {
    width: '100%',
    padding: spacing.sm,
    background: colors.bgSurface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.sm,
    color: colors.textMuted,
    fontFamily: "'Georgia', 'Times New Roman', serif",
    fontSize: font.sm,
    lineHeight: 1.5,
    resize: 'vertical',
    boxSizing: 'border-box',
    outline: 'none',
    marginTop: spacing.sm,
}
