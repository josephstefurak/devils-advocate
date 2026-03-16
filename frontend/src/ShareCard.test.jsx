import { describe, expect, it } from 'vitest'
import { buildShareText } from './ShareCard'

describe('buildShareText', () => {
    it('uses the canonical public deployment URL', () => {
        const text = buildShareText({
            claim: 'A startup idea',
            report: { overall_score: 7 },
            judgeResult: {
                winner: 'founder',
                summary: 'Strong defense overall.',
                scores: {
                    problem_clarity: 7,
                    market_logic: 6,
                    execution_risk: 6,
                    competitive_awareness: 7,
                    internal_coherence: 7,
                },
            },
        })

        expect(text).toContain('https://devils-advocate-488918.web.app/')
    })
})
