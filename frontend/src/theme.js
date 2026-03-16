// ── Devil's Advocate — Design Tokens ──────────────────────────────
// Change visuals here without touching component logic.

export const colors = {
    // Backgrounds
    bgBase: '#0f0f0f',
    bgSurface: '#111',
    bgSurfaceAlt: '#1a1a1a',
    bgDeep: '#0a0a0a',
    bgDark: '#0d0d0d',

    // Borders
    border: '#222',
    borderSubtle: '#333',

    // Accent / status
    accent: '#e63946',   // devil red — primary CTA, agent label
    success: '#4ade80',   // defended, positive
    info: '#60a5fa',   // neutral info, new claim
    warning: '#f59e0b',   // biggest gap, caution

    // Text
    textPrimary: '#f0f0f0',
    textSecondary: '#eee',
    textMuted: '#ccc',
    textDim: '#AAA',
    textFaint: '#777',
    textGhost: '#555',

    // Semantic surfaces (classification backgrounds)
    defendedBg: '#052e16',
    defendedBorder: '#4ade80',
    concededBg: '#2d1010',
    concededBorder: '#e63946',
    newClaimBg: '#1a1a2e',
    newClaimBorder: '#60a5fa',

    // Score surfaces
    scoreHighBg: '#052e16',
    scoreMidBg: '#1a1a2e',
    scoreLowBg: '#2d1010',

    // Auth
    googleBtnBg: '#1a1a2e',
    githubBtnBg: '#161b22',
    githubBorder: '#30363d',
}

export const radius = {
    xs: 4,
    sm: 6,
    md: 8,
    lg: 10,
    pill: 20,
    circle: '50%',
}

export const font = {
    xs: 11,
    sm: 12,
    md: 13,
    base: 14,
    lg: 15,
    xl: 16,
    xxl: 22,
    h2: 28,
}

export const spacing = {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
}

export const letterSpacing = {
    label: 1,
    tight: 0.5,
}

// ── Helpers ────────────────────────────────────────────────────────
// Returns the right color set for a 1-10 score value
export function scoreColor(score) {
    if (score >= 7) return { text: colors.success, bg: colors.scoreHighBg, border: colors.success }
    if (score >= 4) return { text: colors.info, bg: colors.scoreMidBg, border: colors.info }
    return { text: colors.accent, bg: colors.scoreLowBg, border: colors.accent }
}

// Returns the right color set for a claim classification string
export function classificationColor(classification) {
    switch (classification) {
        case 'DEFENDED': return { bg: colors.defendedBg, border: colors.defendedBorder, text: colors.success }
        case 'CONCEDED': return { bg: colors.concededBg, border: colors.concededBorder, text: colors.accent }
        default: return { bg: colors.newClaimBg, border: colors.newClaimBorder, text: colors.info }
    }
}