// ── buildShareText() ──────────────────────────────────────────────
// Generates a Wordle-style plain text card for clipboard sharing.
//
// Example output:
//
//   😈 DEVIL'S ADVOCATE
//   ─────────────────────
//   "I want to build a B2B SaaS for HR teams"
//
//   🟥🟥🟥🟨🟨🟨🟨🟩🟩🟩  7/10
//   🤖 Agent wins
//
//   Problem clarity    ████████░░  8
//   Market logic       █████░░░░░  5
//   Execution risk     ███████░░░  7
//   Competition        ████████░░  8
//   Coherence          ███████░░░  7
//
//   "The founder cited real data but never closed
//    the distribution gap."
//
//   Stress-test your idea → devils-advocate-488918.web.app

export function buildShareText({ claim, report, judgeResult }) {
    const lines = []

    // ── Header ──
    lines.push(`👹 DEVIL'S ADVOCATE`)
    lines.push(`─────────────────────────────`)

    // ── Claim ──
    const truncated = claim.length > 80 ? claim.slice(0, 77) + '...' : claim
    lines.push(`"${truncated}"`)
    lines.push(``)

    // ── Score bar (Wordle-style emoji blocks) ──
    if (report) {
        const score = report.overall_score  // 1–10
        const filled = Math.round(score)
        const empty = 10 - filled

        // Color the blocks by score bracket
        let block
        if (score >= 7) block = '🟩'       // green = strong
        else if (score >= 4) block = '🟨'  // yellow = mid
        else block = '🟥'                  // red = weak

        const bar = block.repeat(filled) + '⬛'.repeat(empty)
        lines.push(`${bar}  ${score}/10`)
    }

    // ── Winner ──
    if (judgeResult) {
        const won = judgeResult.winner === 'founder'
        lines.push(won ? `🏆 Founder wins` : `🤖 Agent wins`)
    }

    lines.push(``)

    // ── Per-dimension score bars ──
    if (judgeResult?.scores) {
        const dims = {
            problem_clarity: 'Problem clarity   ',
            market_logic: 'Market logic      ',
            execution_risk: 'Execution risk    ',
            competitive_awareness: 'Competition       ',
            internal_coherence: 'Coherence         ',
        }

        for (const [key, label] of Object.entries(dims)) {
            const val = judgeResult.scores[key]
            if (val == null) continue
            const bar = scoreBar(val)
            lines.push(`${label} ${bar}  ${val}`)
        }

        lines.push(``)
    }

    // ── Verdict quote ──
    if (judgeResult?.summary) {
        const summary = judgeResult.summary
        // Wrap at ~48 chars so it looks good in iMessage / Twitter
        const wrapped = wordWrap(summary, 48)
        wrapped.forEach((l, i) => {
            lines.push(i === 0 ? `"${l}` : ` ${l}`)
        })
        // Close the quote on the last line
        lines[lines.length - 1] += `"`
        lines.push(``)
    }

    // ── CTA ──
    lines.push(`Stress-test your idea →`)
    lines.push(`https://devils-advocate-488918.web.app/`)

    return lines.join('\n')
}


// ── copyShareText() ───────────────────────────────────────────────
// Builds the text and copies it to clipboard.
// Returns 'copied' on success, throws on failure.

export async function copyShareText({ claim, report, judgeResult }) {
    const text = buildShareText({ claim, report, judgeResult })
    await navigator.clipboard.writeText(text)
    return 'copied'
}


// ── Helpers ───────────────────────────────────────────────────────

// Renders a 10-char block bar using Unicode box chars
// e.g. score 7 → ███████░░░
function scoreBar(score) {
    const filled = Math.round(score)
    const empty = 10 - filled
    return '█'.repeat(filled) + '░'.repeat(empty)
}

// Wraps a string at maxWidth, breaking on spaces
function wordWrap(str, maxWidth) {
    const words = str.split(' ')
    const lines = []
    let current = ''

    for (const word of words) {
        if ((current + ' ' + word).trim().length > maxWidth) {
            if (current) lines.push(current)
            current = word
        } else {
            current = current ? current + ' ' + word : word
        }
    }
    if (current) lines.push(current)
    return lines
}
