import { useState } from 'react'
import { getFirestore, collection, addDoc, serverTimestamp } from 'firebase/firestore'
import { colors, font, spacing, radius } from '../theme'

const mono = {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: 2,
}

const serif = {
    fontFamily: "'Georgia', 'Times New Roman', serif",
}

const card = {
    background: colors.bgSurface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    padding: spacing.xl,
}
export function FeedbackWidget({ sessionId, uid, claim }) {
    const [isOpen, setIsOpen] = useState(false)
    const [rating, setRating] = useState(null)
    const [text, setText] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(false)

    async function handleSubmit() {
        if (!rating) return
        setSubmitting(true)
        setError(false)
        try {
            const db = getFirestore()
            await addDoc(collection(db, 'feedback'), {
                rating,
                text: text.trim() || null,
                sessionId: sessionId || null,
                uid: uid || null,
                claim: claim || null,
                timestamp: serverTimestamp(),
            })
            setSubmitted(true)
        } catch (err) {
            console.error('Feedback error:', err)
            setError(true)
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div style={{ ...card, marginTop: spacing.lg }}>
            <button
                onClick={() => setIsOpen(prev => !prev)}
                style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    width: '100%', padding: 0,
                }}
            >
                <span style={{ ...mono, color: submitted ? colors.success : colors.textFaint }}>
                    {submitted ? '✓ Feedback submitted' : 'Leave feedback'}
                </span>
                {!submitted && (
                    <span style={{ ...mono, color: colors.textFaint }}>
                        {isOpen ? '▲' : '▼'}
                    </span>
                )}
            </button>

            {isOpen && !submitted && (
                <div style={{ marginTop: spacing.md }}>
                    <div style={{ ...mono, color: colors.textFaint, marginBottom: spacing.sm }}>
                        Rate your experience
                    </div>

                    <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md }}>
                        {[1, 2, 3, 4, 5].map(n => (
                            <button key={n} onClick={() => setRating(n)} style={{
                                width: 36, height: 36,
                                borderRadius: radius.sm,
                                border: `1px solid ${rating === n ? colors.accent : colors.borderSubtle}`,
                                background: rating === n ? `${colors.accent}20` : colors.bgSurfaceAlt,
                                color: rating === n ? colors.accent : colors.textFaint,
                                cursor: 'pointer',
                                ...mono,
                            }}>
                                {n}
                            </button>
                        ))}
                    </div>

                    <textarea
                        value={text}
                        onChange={e => setText(e.target.value)}
                        placeholder="Anything we should know? (optional)"
                        rows={3}
                        style={{
                            width: '100%',
                            padding: spacing.sm,
                            background: colors.bgSurfaceAlt,
                            border: `1px solid ${colors.borderSubtle}`,
                            borderRadius: radius.sm,
                            color: colors.textPrimary,
                            ...serif,
                            fontSize: font.sm,
                            resize: 'none',
                            boxSizing: 'border-box',
                            marginBottom: spacing.md,
                        }}
                    />

                    {error && (
                        <p style={{ ...mono, color: colors.accent, marginBottom: spacing.sm }}>
                            Submission failed — try again
                        </p>
                    )}

                    <button
                        onClick={handleSubmit}
                        disabled={!rating || submitting}
                        style={{
                            padding: `8px 18px`,
                            background: 'transparent',
                            color: !rating || submitting ? colors.textGhost : colors.info,
                            border: `1px solid ${!rating || submitting ? colors.borderSubtle : colors.info}`,
                            borderRadius: radius.sm,
                            ...mono,
                            cursor: !rating || submitting ? 'default' : 'pointer',
                            opacity: !rating || submitting ? 0.5 : 1,
                        }}
                    >
                        {submitting ? 'Submitting...' : 'Submit Feedback'}
                    </button>
                </div>
            )}
        </div>
    )
}