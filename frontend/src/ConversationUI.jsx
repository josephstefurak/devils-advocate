import { useState, useEffect } from 'react'
import { colors, font, spacing, radius } from './theme'

// ── 1. Mic Volume Visualizer ────────────────────────────────────
export function MicVisualizer({ volume, isPaused }) {
    const bars = 5
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 3, height: 20 }}>
            {Array.from({ length: bars }).map((_, i) => {
                const threshold = (i + 1) / bars
                const active = !isPaused && volume > threshold * 0.15
                return (
                    <div key={i} style={{
                        width: 3,
                        borderRadius: 2,
                        background: active ? colors.success : colors.borderSubtle,
                        height: active ? `${8 + i * 4}px` : '4px',
                        transition: 'height 0.08s ease, background 0.08s ease',
                    }} />
                )
            })}
        </div>
    )
}

// ── 2. Turn Indicator + Interrupt hint ─────────────────────────
export function TurnIndicator({ isAgentSpeaking, isPaused, agentHasSpoken }) {
    const waiting = !agentHasSpoken && !isAgentSpeaking

    return (
        <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: `${spacing.sm}px ${spacing.md}px`,
            borderRadius: radius.md,
            border: `1px solid ${waiting ? colors.border : isAgentSpeaking ? colors.accent : colors.success}`,
            background: waiting ? colors.bgSurfaceAlt
                : isAgentSpeaking ? `${colors.accent}10`
                    : `${colors.success}10`,
            transition: 'all 0.3s ease',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                <PulsingDot
                    active={!waiting && !isAgentSpeaking && !isPaused}
                    color={colors.success}
                />
                <span style={{
                    fontSize: font.sm, fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: 1,
                    color: waiting ? colors.textFaint
                        : isAgentSpeaking ? colors.accent
                            : colors.success,
                }}>
                    {isPaused ? 'Paused'
                        : waiting ? 'Waiting for agent...'
                            : isAgentSpeaking ? 'Agent is responding...'
                                : 'Your turn — speak now'}
                </span>
            </div>
            {isAgentSpeaking && (
                <span style={{ fontSize: font.xs, color: colors.textFaint, fontStyle: 'italic' }}>
                    You can interrupt by speaking
                </span>
            )}
        </div>
    )
}

// ── 3. Mic Status Bar ───────────────────────────────────────────
export function MicStatusBar({ volume, isPaused }) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: spacing.sm,
            padding: `6px ${spacing.md}px`,
            background: colors.bgSurfaceAlt,
            borderRadius: radius.sm,
            border: `1px solid ${colors.border}`,
        }}>
            <PulsingDot active={!isPaused} color={colors.accent} size={8} />
            <span style={{ fontSize: font.xs, color: colors.textFaint, textTransform: 'uppercase', letterSpacing: 1 }}>
                {isPaused ? 'Mic paused' : 'Mic live'}
            </span>
            <MicVisualizer volume={volume} isPaused={isPaused} />
        </div>
    )
}

// ── 4. First-time onboarding banner ────────────────────────────
export function OnboardingBanner({ onDismiss }) {
    return (
        <div style={{
            padding: spacing.md,
            background: `${colors.info}15`,
            border: `1px solid ${colors.info}40`,
            borderRadius: radius.md,
            display: 'flex', alignItems: 'flex-start',
            justifyContent: 'space-between', gap: spacing.md,
        }}>
            <div style={{ display: 'flex', gap: spacing.md, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 20 }}>🎤</span>
                <div>
                    <p style={{ margin: 0, fontSize: font.md, color: colors.textSecondary, fontWeight: 600 }}>
                        This is a live voice conversation
                    </p>
                    <p style={{ margin: '4px 0 0', fontSize: font.sm, color: colors.textMuted, lineHeight: 1.5 }}>
                        Speak naturally to respond. Your mic is always active — no buttons needed.
                        You can interrupt the agent at any time by speaking over it.
                    </p>
                </div>
            </div>
            <button onClick={onDismiss} style={{
                background: 'none', border: 'none', color: colors.textFaint,
                cursor: 'pointer', fontSize: font.base, flexShrink: 0, padding: 0,
            }}>✕</button>
        </div>
    )
}

// ── 5. Agent speaking indicator (enhanced) ─────────────────────
export function AgentSpeakingBadge({ isAgentSpeaking }) {
    if (!isAgentSpeaking) return null
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: spacing.sm,
        }}>
            <AgentWaveform />
            <span style={{ color: colors.accent, fontSize: font.sm, fontStyle: 'italic' }}>
                Agent is speaking — interrupt anytime
            </span>
        </div>
    )
}

// ── Internal helpers ────────────────────────────────────────────
function PulsingDot({ active, color, size = 8 }) {
    return (
        <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
            <div style={{
                width: size, height: size, borderRadius: '50%',
                background: active ? color : colors.borderSubtle,
            }} />
            {active && (
                <div style={{
                    position: 'absolute', inset: 0, borderRadius: '50%',
                    background: color, opacity: 0.4,
                    animation: 'pulse 1.5s ease-out infinite',
                }} />
            )}
        </div>
    )
}

function AgentWaveform() {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {[1, 2, 3, 2, 1].map((h, i) => (
                <div key={i} style={{
                    width: 3, borderRadius: 2,
                    background: colors.accent,
                    height: `${h * 5}px`,
                    animation: `wave 0.8s ease-in-out ${i * 0.1}s infinite alternate`,
                }} />
            ))}
        </div>
    )
}

// Export keyframes as a string so App.jsx can add them to its <style> tag
export const conversationKeyframes = `
  @keyframes pulse {
    0% { transform: scale(1); opacity: 0.4; }
    100% { transform: scale(2.2); opacity: 0; }
  }
  @keyframes wave {
    from { transform: scaleY(1); }
    to { transform: scaleY(2); }
  }
`