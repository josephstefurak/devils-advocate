import { useState, useEffect } from 'react'
import { colors, font, radius, spacing } from './theme'

// ── Typewriter for the rotating challenger lines ───────────────
const CHALLENGES = [
    "Your TAM is a fantasy.",
    "Who actually pays for this?",
    "Why won't Google build this in six months?",
    "Your moat is a puddle.",
    "You haven't talked to a single customer.",
    "What happens when a competitor undercuts you by 80%?",
    "You're solving a problem nobody has.",
]

function Typewriter() {
    const [lineIndex, setLineIndex] = useState(0)
    const [displayed, setDisplayed] = useState('')
    const [typing, setTyping] = useState(true)

    useEffect(() => {
        const target = CHALLENGES[lineIndex]
        if (typing) {
            if (displayed.length < target.length) {
                const t = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 45)
                return () => clearTimeout(t)
            } else {
                const t = setTimeout(() => setTyping(false), 1800)
                return () => clearTimeout(t)
            }
        } else {
            if (displayed.length > 0) {
                const t = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 22)
                return () => clearTimeout(t)
            } else {
                const t = setTimeout(() => {
                    setLineIndex((prev) => (prev + 1) % CHALLENGES.length)
                    setTyping(true)
                }, 0)
                return () => clearTimeout(t)
            }
        }
    }, [displayed, typing, lineIndex])

    return (
        <span style={{ color: colors.accent }}>
            {displayed}
            <span style={{ animation: 'blink 1s step-end infinite', opacity: 1 }}>|</span>
        </span>
    )
}

// ── Simulated waveform bars ────────────────────────────────────
function VoiceWaveform({ active = true, color = colors.accent, barCount = 28 }) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 3,
            height: 40,
        }}>
            {Array.from({ length: barCount }).map((_, i) => {
                const base = Math.sin(i * 0.6) * 0.5 + 0.5
                const h = active ? 6 + base * 28 : 4
                return (
                    <div key={i} style={{
                        width: 3,
                        height: `${h}px`,
                        borderRadius: 2,
                        background: color,
                        opacity: active ? 0.7 + base * 0.3 : 0.2,
                        animation: active ? `wave ${0.6 + (i % 4) * 0.15}s ease-in-out ${i * 0.04}s infinite alternate` : 'none',
                    }} />
                )
            })}
        </div>
    )
}

// ── The three value pillars ────────────────────────────────────
const PILLARS = [
    {
        number: '01',
        headline: 'Stress-test your idea',
        body: 'Every weak assumption gets challenged. Every claim needs evidence. Walk out with a sharper idea or a clear reason to pivot.',
    },
    {
        number: '02',
        headline: 'No yes-men allowed',
        body: 'Your co-founder agrees with you. Your friends think it\'s cool. Devil\'s Advocate doesn\'t care — it asks what investors actually ask.',
    },
    {
        number: '03',
        headline: 'Think out loud',
        body: 'This is a voice debate, not a form. Speaking forces clarity. You\'ll discover what you actually believe about your idea.',
    },
]

// ── Mock conversation preview ──────────────────────────────────
const PREVIEW_TURNS = [
    { speaker: 'user', text: "We're building a B2B SaaS for restaurant inventory management." },
    { speaker: 'agent', text: "Toast already has inventory features. Why would a restaurant switch from an all-in-one platform to a point solution?" },
    { speaker: 'user', text: "Our AI predicts waste 40% more accurately than any existing tool." },
    { speaker: 'agent', text: "That's a feature, not a moat. Toast can hire two engineers and ship that in a quarter. What happens then?" },
]

function ConversationPreview() {
    const [visible, setVisible] = useState(0)

    useEffect(() => {
        if (visible >= PREVIEW_TURNS.length) return
        const delay = visible === 0 ? 800 : 1400
        const t = setTimeout(() => setVisible(v => v + 1), delay)
        return () => clearTimeout(t)
    }, [visible])

    return (
        <div style={{
            background: '#0a0a0a',
            border: `1px solid ${colors.border}`,
            borderRadius: radius.lg,
            padding: spacing.lg,
            fontFamily: 'monospace',
            fontSize: font.sm,
            lineHeight: 1.6,
        }}>
            {/* Mock browser chrome */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: spacing.sm,
                marginBottom: spacing.lg, paddingBottom: spacing.md,
                borderBottom: `1px solid ${colors.border}`,
            }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#e63946' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#444' }} />
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#444' }} />
                <span style={{ marginLeft: spacing.sm, fontSize: font.xs, color: colors.textFaint }}>
                    Live debate session
                </span>
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{
                        width: 6, height: 6, borderRadius: '50%', background: colors.accent,
                        animation: 'pulse 1.5s ease-out infinite',
                    }} />
                    <span style={{ fontSize: font.xs, color: colors.accent }}>LIVE</span>
                </div>
            </div>

            {PREVIEW_TURNS.slice(0, visible).map((turn, i) => (
                <div key={i} style={{
                    marginBottom: spacing.md,
                    animation: 'fadeSlideIn 0.3s ease forwards',
                }}>
                    <div style={{
                        fontSize: font.xs, fontWeight: 700,
                        textTransform: 'uppercase', letterSpacing: 1,
                        color: turn.speaker === 'agent' ? colors.accent : colors.success,
                        marginBottom: 4,
                        fontFamily: 'monospace',
                    }}>
                        {turn.speaker === 'agent' ? "Devil's Advocate" : "Founder"}
                    </div>
                    <p style={{
                        margin: 0,
                        color: turn.speaker === 'agent' ? '#e0e0e0' : colors.textMuted,
                        fontFamily: turn.speaker === 'agent'
                            ? "'Georgia', serif"
                            : 'monospace',
                        fontSize: turn.speaker === 'agent' ? font.md : font.sm,
                        fontStyle: turn.speaker === 'agent' ? 'normal' : 'normal',
                    }}>
                        {turn.text}
                    </p>
                </div>
            ))}

            {visible < PREVIEW_TURNS.length && (
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                    <VoiceWaveform active barCount={12} color={
                        visible % 2 === 0 ? colors.success : colors.accent
                    } />
                </div>
            )}
        </div>
    )
}

// ── Main LandingPage component ─────────────────────────────────
export default function LandingPage({ onEnter }) {
    return (
        <div style={{
            minHeight: '100vh',
            background: colors.bgBase,
            color: colors.textPrimary,
            fontFamily: "'Georgia', 'Times New Roman', serif",
            overflowX: 'hidden',
        }}>

            <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;700&display=swap');
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes wave {
          from { transform: scaleY(0.6); }
          to { transform: scaleY(1.4); }
        }
        @keyframes pulse {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(2.5); opacity: 0; }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .cta-btn:hover {
          background: #ff1a28 !important;
          transform: translateY(-1px);
          box-shadow: 0 8px 32px rgba(230,57,70,0.4) !important;
        }
        .pillar-card:hover {
          border-color: ${colors.accent} !important;
          background: #1a0a0a !important;
        }
      `}</style>

            {/* ── Thin top bar ── */}
            <div style={{
                borderBottom: `1px solid ${colors.border}`,
                padding: `${spacing.md}px ${spacing.xxl}px`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
                    <span style={{ fontSize: 24 }}>👹</span>
                    <span style={{
                        fontFamily: "'Bebas Neue', 'Georgia', serif",
                        fontSize: font.xl, letterSpacing: 3,
                        color: colors.textPrimary,
                    }}>
                        DEVIL'S ADVOCATE
                    </span>
                </div>
                <span style={{
                    fontSize: font.xs, color: colors.textFaint,
                    textTransform: 'uppercase', letterSpacing: 2,
                    fontFamily: "'JetBrains Mono', monospace",
                }}>
                    For founders who want the truth
                </span>
            </div>

            {/* ── Hero ── */}
            <div style={{
                maxWidth: 1100, margin: '0 auto',
                padding: `80px ${spacing.xxl}px 60px`,
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                gap: 60, alignItems: 'center',
            }}>

                {/* Left: copy */}
                <div style={{ animation: 'fadeIn 0.6s ease forwards' }}>

                    {/* Eyebrow */}
                    <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: spacing.sm,
                        marginBottom: spacing.xl,
                        padding: `4px ${spacing.md}px`,
                        border: `1px solid ${colors.accent}40`,
                        borderRadius: radius.pill,
                        background: `${colors.accent}10`,
                    }}>
                        <div style={{ position: 'relative', width: 8, height: 8 }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: colors.accent }} />
                            <div style={{
                                position: 'absolute', inset: 0, borderRadius: '50%',
                                background: colors.accent, animation: 'pulse 1.5s ease-out infinite',
                            }} />
                        </div>
                        <span style={{
                            fontSize: font.xs, color: colors.accent,
                            textTransform: 'uppercase', letterSpacing: 2,
                            fontFamily: "'JetBrains Mono', monospace",
                        }}>
                            Voice AI Debate Tool
                        </span>
                    </div>

                    {/* Main headline */}
                    <h1 style={{
                        fontFamily: "'Bebas Neue', 'Georgia', serif",
                        fontSize: 72, lineHeight: 0.95,
                        margin: `0 0 ${spacing.xl}px`,
                        letterSpacing: 2,
                    }}>
                        YOUR IDEA<br />
                        <span style={{
                            color: colors.accent,
                            fontStyle: 'italic',
                            fontFamily: "'DM Serif Display', 'Georgia', serif",
                        }}>
                            vs.
                        </span>
                        <br />REALITY
                    </h1>

                    {/* Typewriter subhead */}
                    <p style={{
                        fontSize: font.xl, lineHeight: 1.5,
                        color: colors.textMuted,
                        margin: `0 0 ${spacing.sm}px`,
                        fontFamily: "'JetBrains Mono', monospace",
                        minHeight: 28,
                    }}>
                        <Typewriter />
                    </p>

                    {/* Description */}
                    <p style={{
                        fontSize: font.lg, lineHeight: 1.7,
                        color: colors.textDim,
                        margin: `${spacing.lg}px 0 ${spacing.xl}px`,
                        fontFamily: "'Georgia', serif",
                        maxWidth: 440,
                    }}>
                        A voice AI that argues against your startup idea — the way a great investor would.
                        Speak your pitch. Get destroyed. Come out sharper.
                    </p>

                    {/* Voice indicator */}
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: spacing.md,
                        marginBottom: spacing.xl,
                        padding: `${spacing.sm}px ${spacing.md}px`,
                        background: colors.bgSurface,
                        border: `1px solid ${colors.border}`,
                        borderRadius: radius.md,
                        width: 'fit-content',
                    }}>
                        <VoiceWaveform active barCount={16} color={colors.success} />
                        <span style={{
                            fontSize: font.sm, color: colors.textMuted,
                            fontFamily: "'JetBrains Mono', monospace",
                        }}>
                            100% voice — no typing required
                        </span>
                    </div>

                    {/* CTA */}
                    <button
                        className="cta-btn"
                        onClick={onEnter}
                        style={{
                            display: 'flex', alignItems: 'center', gap: spacing.md,
                            padding: `16px 36px`,
                            background: colors.accent,
                            color: 'white',
                            border: 'none',
                            borderRadius: radius.md,
                            fontSize: font.xl,
                            fontWeight: 700,
                            cursor: 'pointer',
                            fontFamily: "'Bebas Neue', 'Georgia', serif",
                            letterSpacing: 2,
                            transition: 'all 0.2s ease',
                            boxShadow: '0 4px 20px rgba(230,57,70,0.25)',
                        }}
                    >
                        <span style={{ fontSize: 18 }}>🎤</span>
                        PITCH YOUR IDEA
                    </button>

                    <p style={{
                        marginTop: spacing.md,
                        fontSize: font.xs, color: colors.textFaint,
                        fontFamily: "'JetBrains Mono', monospace",
                    }}>
                        Free to start · No signup required · ~3 min session
                    </p>
                </div>

                {/* Right: conversation preview */}
                <div style={{
                    animation: 'fadeIn 0.6s ease 0.2s both',
                }}>
                    <div style={{
                        fontSize: font.xs, color: colors.textFaint,
                        textTransform: 'uppercase', letterSpacing: 2,
                        fontFamily: "'JetBrains Mono', monospace",
                        marginBottom: spacing.md,
                    }}>
                        ↓ Live debate preview
                    </div>
                    <ConversationPreview />
                </div>
            </div>

            {/* ── Divider ── */}
            <div style={{
                maxWidth: 1100, margin: '0 auto',
                padding: `0 ${spacing.xxl}px`,
                display: 'flex', alignItems: 'center', gap: spacing.xl,
            }}>
                <div style={{ flex: 1, height: 1, background: colors.border }} />
                <span style={{
                    fontSize: font.xs, color: colors.textFaint,
                    textTransform: 'uppercase', letterSpacing: 3,
                    fontFamily: "'JetBrains Mono', monospace",
                }}>Why it works</span>
                <div style={{ flex: 1, height: 1, background: colors.border }} />
            </div>

            {/* ── Three pillars ── */}
            <div style={{
                maxWidth: 1100, margin: '0 auto',
                padding: `${spacing.xxl * 2}px ${spacing.xxl}px`,
                display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
                gap: spacing.lg,
            }}>
                {PILLARS.map((p) => (
                    <div
                        key={p.number}
                        className="pillar-card"
                        style={{
                            padding: spacing.xl,
                            background: colors.bgSurface,
                            border: `1px solid ${colors.border}`,
                            borderRadius: radius.lg,
                            transition: 'all 0.2s ease',
                            cursor: 'default',
                        }}
                    >
                        <div style={{
                            fontFamily: "'Bebas Neue', 'Georgia', serif",
                            fontSize: 48, lineHeight: 1,
                            color: colors.accent, opacity: 0.25,
                            marginBottom: spacing.md,
                            letterSpacing: 2,
                        }}>
                            {p.number}
                        </div>
                        <h3 style={{
                            fontFamily: "'DM Serif Display', 'Georgia', serif",
                            fontSize: font.xl, lineHeight: 1.3,
                            margin: `0 0 ${spacing.sm}px`,
                            color: colors.textPrimary,
                        }}>
                            {p.headline}
                        </h3>
                        <p style={{
                            fontSize: font.md, lineHeight: 1.7,
                            color: colors.textDim, margin: 0,
                            fontFamily: "'Georgia', serif",
                        }}>
                            {p.body}
                        </p>
                    </div>
                ))}
            </div>

            {/* ── Bottom CTA strip ── */}
            <div style={{
                borderTop: `1px solid ${colors.border}`,
                padding: `${spacing.xxl * 2}px ${spacing.xxl}px`,
                textAlign: 'center',
            }}>
                <h2 style={{
                    fontFamily: "'Bebas Neue', 'Georgia', serif",
                    fontSize: 52, letterSpacing: 2,
                    margin: `0 0 ${spacing.md}px`,
                }}>
                    YOUR IDEA HAS NEVER BEEN CHALLENGED LIKE THIS
                </h2>
                <p style={{
                    fontSize: font.lg, color: colors.textDim,
                    margin: `0 0 ${spacing.xl}px`,
                    fontFamily: "'Georgia', serif",
                }}>
                    Stop getting validation from people who want you to succeed. Start getting the truth.
                </p>
                <button
                    className="cta-btn"
                    onClick={onEnter}
                    style={{
                        padding: `16px 48px`,
                        background: colors.accent,
                        color: 'white', border: 'none',
                        borderRadius: radius.md,
                        fontSize: font.xl, fontWeight: 700,
                        cursor: 'pointer',
                        fontFamily: "'Bebas Neue', 'Georgia', serif",
                        letterSpacing: 2,
                        transition: 'all 0.2s ease',
                        boxShadow: '0 4px 20px rgba(230,57,70,0.25)',
                    }}
                >
                    🎤 START YOUR DEBATE
                </button>
            </div>

        </div>
    )
}
