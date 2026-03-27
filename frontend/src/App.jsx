import { useRef, useEffect, useState } from 'react'
import { useAuth } from './hooks/useAuth'
import { useDebateSession } from './hooks/useDebateSession'
import { useDocumentUpload } from './useDocumentUpload'
import {
  TurnIndicator, MicStatusBar, OnboardingBanner,
  AgentSpeakingBadge, conversationKeyframes,
} from './ConversationUI'
import LandingPage from './LandingPage'
import {
  colors, radius, font, spacing,
  scoreColor, classificationColor,
} from './theme'
import { copyShareText } from './ShareCard.jsx'
import { FeedbackWidget } from './feedback'

// ── Shared style objects ───────────────────────────────────────
const mono = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: font.xs,
  textTransform: 'uppercase',
  letterSpacing: 2,
}

const serif = {
  fontFamily: "'Georgia', 'Times New Roman', serif",
}

const displayFont = {
  fontFamily: "'Bebas Neue', 'Georgia', serif",
}

const card = {
  background: colors.bgSurface,
  border: `1px solid ${colors.border}`,
  borderRadius: radius.lg,
  padding: spacing.xl,
}

const CLAIM_CHARACTER_LIMIT = 500

// ── Small reusable components ──────────────────────────────────
function Spinner() {
  return (
    <div style={{
      width: 16, height: 16, borderRadius: '50%',
      border: `2px solid ${colors.borderSubtle}`,
      borderTopColor: colors.accent,
      animation: 'spin 0.8s linear infinite',
      flexShrink: 0,
    }} />
  )
}

function SectionLabel({ children, color = colors.textFaint }) {
  return (
    <div style={{ ...mono, color, marginBottom: spacing.sm }}>
      {children}
    </div>
  )
}

function ScoreRing({ score, size = 56 }) {
  const col = scoreColor(score)
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: col.bg, border: `2px solid ${col.border}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size > 50 ? font.xxl : font.xl,
      fontWeight: 700, color: col.text,
      ...displayFont,
    }}>
      {score}
    </div>
  )
}

function PrimaryBtn({ onClick, children, style = {} }) {
  return (
    <button
      className="da-btn"
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: spacing.sm,
        padding: `13px 30px`,
        background: colors.accent, color: 'white', border: '1px solid transparent',
        borderRadius: radius.md,
        ...displayFont, fontSize: font.xl, letterSpacing: 2,
        cursor: 'pointer',
        boxShadow: '0 4px 20px rgba(230,57,70,0.2)',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

function GhostBtn({ onClick, children, color = colors.textFaint, borderColor, style = {} }) {
  return (
    <button
      className="da-btn"
      onClick={onClick}
      style={{
        padding: `8px 18px`,
        background: 'transparent', color,
        border: `1px solid ${borderColor || color}`,
        borderRadius: radius.sm,
        ...mono, cursor: 'pointer',
        ...style,
      }}
    >
      {children}
    </button>
  )
}
function HoldToEndButton({ onConfirm }) {
  const [holding, setHolding] = useState(false)
  const [progress, setProgress] = useState(0)
  const animFrameRef = useRef(null)
  const startTimeRef = useRef(null)
  const HOLD_DURATION = 1500

  function startHold() {
    setHolding(true)
    startTimeRef.current = Date.now()

    function tick() {
      const elapsed = Date.now() - startTimeRef.current
      const pct = Math.min(elapsed / HOLD_DURATION, 1)
      setProgress(pct)
      if (pct < 1) {
        animFrameRef.current = requestAnimationFrame(tick)
      } else {
        onConfirm()
        setHolding(false)
        setProgress(0)
      }
    }
    animFrameRef.current = requestAnimationFrame(tick)
  }

  function cancelHold() {
    setHolding(false)
    setProgress(0)
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
  }

  const bars = 12
  return (
    <button
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={startHold}
      onTouchEnd={cancelHold}
      style={{
        display: 'flex', alignItems: 'center', gap: spacing.sm,
        padding: `13px 30px`,
        background: holding ? `${colors.accent}22` : colors.accent,
        color: 'white', border: holding ? `1px solid ${colors.accent}` : 'none',
        borderRadius: radius.md,
        ...displayFont, fontSize: font.xl, letterSpacing: 2,
        cursor: 'pointer',
        boxShadow: holding ? 'none' : '0 4px 20px rgba(230,57,70,0.2)',
        transition: 'background 0.1s ease, box-shadow 0.1s ease',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        minWidth: 200,
      }}
    >
      {holding ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            {Array.from({ length: bars }).map((_, i) => {
              const threshold = i / bars
              const active = progress > threshold
              const height = active ? 8 + Math.sin((i / bars) * Math.PI) * 12 : 3
              return (
                <div key={i} style={{
                  width: 3, borderRadius: 2,
                  height: `${height}px`,
                  background: active ? 'white' : 'rgba(255,255,255,0.3)',
                  transition: 'height 0.05s ease',
                }} />
              )
            })}
          </div>
          <span>ENDING...</span>
        </>
      ) : (
        <>
          <span>⏹</span>
          <span>END & EVALUATE (Hold)</span>
        </>
      )}
    </button>
  )
}

function MicDictation({ onTranscript, onInterim }) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)

  function toggleMic() {
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      onInterim('')
      return
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Try Chrome.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          onTranscript(e.results[i][0].transcript)
          onInterim('')
        } else {
          interim += e.results[i][0].transcript
        }
      }
      if (interim) onInterim(interim)
    }

    recognition.onend = () => { setListening(false); onInterim('') }
    recognition.onerror = () => { setListening(false); onInterim('') }

    recognition.start()
    recognitionRef.current = recognition
    setListening(true)
  }

  return (
    <button
      onClick={toggleMic}
      className="da-btn"
      title={listening ? 'Stop dictation' : 'Dictate your claim'}
      style={{
        background: listening ? `${colors.accent}20` : 'transparent',
        border: `1px solid ${listening ? colors.accent : colors.borderSubtle}`,
        borderRadius: radius.sm,
        color: listening ? colors.accent : colors.textFaint,
        cursor: 'pointer',
        padding: `6px 10px`,
        ...mono,
        fontSize: 10,
        display: 'flex', alignItems: 'center', gap: 6,
        transition: 'all 0.2s ease',
        flexShrink: 0,
      }}
    >
      {listening ? (
        <>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: colors.accent,
            animation: 'pulse 1s ease-out infinite',
          }} />
          Stop
        </>
      ) : (
        <>🎤 Dictate</>
      )}
    </button>
  )
}

// ── Main App ───────────────────────────────────────────────────
export default function App() {
  const { user, authReady, signInWithGoogle, signInWithGitHub, handleSignOut } = useAuth()

  const {
    status, transcript, partials, claims, report, judgeResult,
    isAgentSpeaking, isPaused, consentGiven, sessionStatus, micVolume, reportReady, sessionId,
    startDebate, endDebate, resetSession, togglePause,
    handleConsentToggle, exportToPDF,
  } = useDebateSession()

  const { uploadedFiles, uploading, loadingFiles, uploadFile, removeFile } =
    useDocumentUpload(user, status === 'debating')

  const [claim, setClaim] = useState('')
  const [stage, setStage] = useState('late')
  const [extracting, setExtracting] = useState(false)
  const [cachedExtractedClaim, setCachedExtractedClaim] = useState('')
  const [lastGeneratedPaths, setLastGeneratedPaths] = useState(null)
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [showLanding, setShowLanding] = useState(true)
  const [shareStatus, setShareStatus] = useState(null)
  const [interimText, setInterimText] = useState('')
  const [hoveredStage, setHoveredStage] = useState(null)
  const [pressedStage, setPressedStage] = useState(null)

  const fileInputRef = useRef(null)
  const reportRef = useRef(null)
  const transcriptEndRef = useRef(null)
  const agentHasSpokenRef = useRef(false)

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, partials])

  useEffect(() => {
    if (transcript.some(t => t.speaker === 'agent')) {
      setShowOnboarding(false)
      agentHasSpokenRef.current = true
    }
  }, [transcript])

  async function handleStartDebate() {
    if (!authReady || !user) return alert('Auth not ready yet, try again')
    if (!claim.trim() && uploadedFiles.length === 0) return alert('Enter your position or upload documents to get started.')
    agentHasSpokenRef.current = false
    await startDebate(claim.trim() || '', user, uploadedFiles, stage)
  }

  async function handleFillFromDocument() {
    if (!user || uploadedFiles.length === 0) return

    const currentKey = JSON.stringify([...uploadedFiles.map(f => f.path)].sort())

    // Cache hit — same document set, no backend call needed
    if (currentKey === lastGeneratedPaths && cachedExtractedClaim) {
      setClaim(prev => prev ? `${prev}\n\n${cachedExtractedClaim}` : cachedExtractedClaim)
      return
    }

    setExtracting(true)
    try {
      const idToken = await user.getIdToken()
      const url = `${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/extract_claim`

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idToken, documentPaths: uploadedFiles.map(f => f.path) }),
      })

      const text = await res.text()
      let data = {}
      try {
        data = text ? JSON.parse(text) : {}
      } catch {
        throw new Error(`Backend returned non-JSON response: ${text}`)
      }

      if (res.status === 429) {
        alert(data.error || 'Claim generation limit reached. Please wait a few minutes.')
        return
      }
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)

      if (data.claim) {
        setCachedExtractedClaim(data.claim)
        setLastGeneratedPaths(currentKey)
        setClaim(prev => prev ? `${prev}\n\n${data.claim}` : data.claim)
      }
    } catch (err) {
      console.error('Extract claim error:', err)
      alert(`Extract claim failed: ${err.message}`)
    } finally {
      setExtracting(false)
    }
  }
  async function handleShare() {
    try {
      await copyShareText({ claim, judgeResult })
      setShareStatus('copied')
      setTimeout(() => setShareStatus(null), 3000)
    } catch {
      setShareStatus('failed')
    }
  }

  // ── Knowledge base panel ───────────────────────────────────────
  const knowledgeBasePanel = authReady && user && (
    <div style={{ marginTop: spacing.lg }}>
      <div style={{ ...mono, color: colors.textPrimary, fontSize: font.sm, letterSpacing: 2, textTransform: 'uppercase', marginBottom: spacing.sm }}>
        Your Knowledge Base
      </div>
      <p style={{ ...serif, color: colors.textMuted, fontSize: font.xs, lineHeight: 1.5, margin: `0 0 ${spacing.md}px` }}>
        Upload your deck, one-pager, or data — the agent will use it to challenge you with specifics from your own materials.
      </p>
      {status !== 'debating' && (
        <div
          className="file-drop"
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `1px dashed ${colors.borderSubtle}`,
            borderRadius: radius.md,
            padding: spacing.lg,
            textAlign: 'center',
            marginBottom: spacing.sm,
            cursor: 'pointer',
            background: colors.bgDark,
            transition: 'border-color 0.2s',
          }}
        >
          <input
            ref={fileInputRef} type="file" accept=".pdf,.txt" multiple
            style={{ display: 'none' }}
            onChange={e => {
              Array.from(e.target.files).forEach(uploadFile)
              e.target.value = ''
            }}
          />
          <p style={{ margin: 0, ...mono, color: colors.textFaint }}>
            {uploading ? 'Uploading...' : '+ Pitch deck, business plan, or notes (PDF / .txt)'}
          </p>
        </div>
      )}

      {loadingFiles ? (
        <p style={{ ...mono, color: colors.textGhost }}>Loading...</p>
      ) : uploadedFiles.length === 0 ? (
        <p style={{ ...mono, color: colors.textGhost }}>No documents uploaded yet.</p>
      ) : (
        uploadedFiles.map((f, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: `6px ${spacing.md}px`, marginBottom: spacing.xs,
            background: colors.bgSurfaceAlt, borderRadius: radius.sm,
            border: `1px solid ${colors.border}`,
          }}>
            <span style={{ ...mono, color: colors.textMuted, letterSpacing: 1 }}>
              📄 {f.name}
              <span style={{ color: colors.textGhost, marginLeft: spacing.sm }}>
                ({(f.size / 1024).toFixed(0)}KB)
              </span>
            </span>
            {status !== 'debating' && (
              <button onClick={() => removeFile(f.path)} style={{
                background: 'none', border: 'none',
                color: colors.textFaint, cursor: 'pointer', fontSize: font.base,
              }}>✕</button>
            )}
          </div>
        ))
      )}

      {uploadedFiles.length > 0 && status !== 'debating' && (
        <div style={{ marginTop: spacing.sm }}>
          <GhostBtn
            onClick={handleFillFromDocument}
            color={extracting ? colors.textGhost : colors.info}
            style={{ opacity: extracting ? 0.6 : 1, cursor: extracting ? 'default' : 'pointer' }}
          >
            {extracting ? '⏳ Extracting...' : '📄 Fill from document'}
          </GhostBtn>
        </div>
      )}

      {user?.isAnonymous && status !== 'debating' && uploadedFiles.length > 0 && (
        <p style={{ ...mono, color: colors.textGhost, marginTop: spacing.sm }}>
          Guest uploads deleted at session end.
        </p>
      )}
    </div>
  )

  // ── Landing gate ───────────────────────────────────────────────
  if (showLanding) {
    return <LandingPage onEnter={() => setShowLanding(false)} />
  }

  // ── App shell ──────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh',
      background: colors.bgBase,
      color: colors.textPrimary,
      ...serif,
    }}>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;700&display=swap');
        @keyframes blink  { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes spin   { to { transform: rotate(360deg) } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) } }
        @keyframes pulse  { 0% { transform:scale(1); opacity:0.8; } 100% { transform:scale(2.5); opacity:0; } }
        ${conversationKeyframes}
        .da-btn { transition: all 0.15s ease; cursor: pointer; }
        .da-btn:hover { opacity: 0.82; transform: translateY(-1px); border-color: ${colors.accent} !important; }
        .file-drop:hover { border-color: ${colors.accent} !important; }
        textarea:focus { border-color: ${colors.accent} !important; outline: none; }
      `}</style>

      {/* ── Top bar ─────────────────────────────────────────────── */}
      <div style={{
        borderBottom: `1px solid ${colors.border}`,
        padding: `${spacing.md}px ${spacing.xxl}px`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 10,
        background: colors.bgBase,
      }}>
        <button
          onClick={() => setShowLanding(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: spacing.md,
            background: 'none', border: 'none', cursor: 'pointer',
            padding: 0,
          }}
        >
          <span style={{ fontSize: 24 }}>👹</span>
          <span style={{ ...displayFont, fontSize: font.xl, letterSpacing: 3, color: colors.textPrimary }}>
            DEVIL'S ADVOCATE
          </span>
        </button>

        {authReady && (
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
            {user?.isAnonymous ? (
              <>
                <span style={{ ...mono, color: colors.textFaint }}>Guest</span>
                <GhostBtn onClick={signInWithGoogle} color={colors.info}>Google</GhostBtn>
                <GhostBtn
                  onClick={signInWithGitHub}
                  color={colors.textMuted}
                  borderColor={colors.githubBorder}
                  style={{ background: colors.githubBtnBg }}
                >GitHub</GhostBtn>
              </>
            ) : (
              <>
                <span style={{ ...mono, color: colors.textMuted }}>
                  {user?.displayName || user?.email}
                </span>
                <GhostBtn onClick={handleSignOut}>Sign out</GhostBtn>
              </>
            )}
          </div>
        )}
      </div>

      {/* ── Body layout ─────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: spacing.xl,
        maxWidth: 1200, margin: '0 auto',
        padding: `${spacing.xxl}px`,
        alignItems: 'flex-start',
      }}>

        {/* ── Left: main content ────────────────────────────────── */}
        <div style={{ flex: 1, minWidth: 0 }}>

          {/* ══════════ IDLE ══════════ */}
          {status === 'idle' && (
            <div style={{ animation: 'fadeIn 0.4s ease forwards' }}>
              <h1 style={{
                ...displayFont, fontSize: 68, lineHeight: 0.92,
                letterSpacing: 2, margin: `0 0 ${spacing.md}px`,
              }}>
                WHAT'S YOUR<br />
                <span style={{
                  color: colors.accent,
                  fontFamily: "'DM Serif Display', Georgia, serif",
                  fontStyle: 'italic',
                }}>
                  big idea?
                </span>
              </h1>
              <p style={{ ...mono, color: colors.textPrimary, lineHeight: 1.6, marginBottom: spacing.lg }}>
                State your position or upload documents below — the Devil's Advocate will do the rest.
              </p>

              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.sm }}>
                <span style={{ ...mono, color: colors.textFaint, fontSize: font.xs }}>
                  Prefer to speak it out?
                </span>
                <MicDictation
                  onTranscript={(chunk) => setClaim(prev => {
                    const joined = prev ? `${prev.trim()} ${chunk.trim()}` : chunk.trim()
                    return joined.slice(0, CLAIM_CHARACTER_LIMIT)
                  })}
                  onInterim={setInterimText}
                />
              </div>

              <textarea
                value={interimText ? `${claim} ${interimText}` : claim}
                onChange={e => {
                  if (!interimText) setClaim(e.target.value)
                }}
                placeholder="e.g. We're building an app that helps independent restaurants manage reservations and reduce no-shows - without the high commission fees of existing booking platforms"
                maxLength={CLAIM_CHARACTER_LIMIT}
                rows={5}
                style={{
                  width: '100%', padding: spacing.md,
                  borderRadius: radius.md,
                  background: colors.bgSurface,
                  color: colors.textPrimary,
                  border: `1px solid ${colors.borderSubtle}`,
                  fontSize: font.lg,
                  ...serif,
                  resize: 'vertical',
                  boxSizing: 'border-box',
                  lineHeight: 1.6,
                  transition: 'border-color 0.2s',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: spacing.sm }}>
                <span style={{ ...mono, fontSize: font.xs, color: claim.length >= CLAIM_CHARACTER_LIMIT ? colors.accent : colors.textGhost }}>
                  {CLAIM_CHARACTER_LIMIT - claim.length} remaining
                </span>
              </div>

              {/* ── Stage toggle ───────────────────────────────── */}
              <div style={{ marginTop: spacing.md }}>
                <div style={{ ...mono, color: colors.textPrimary, fontSize: font.sm, letterSpacing: 2, marginBottom: 4 }}>
                  WHAT STAGE IS YOUR IDEA?
                </div>
                <p style={{ ...serif, color: colors.textFaint, fontSize: font.xs, margin: `0 0 ${spacing.sm}px` }}>
                  This shapes how your opponent debates you.
                </p>
                {/* Segmented control container */}
                <div style={{
                  position: 'relative',
                  display: 'flex',
                  background: colors.bgSurfaceAlt,
                  border: `1px solid ${hoveredStage !== null ? colors.accent : colors.border}`,
                  borderRadius: 10,
                  padding: 3,
                  transition: 'border-color 0.15s ease',
                }}>
                  {/* Sliding pill */}
                  <div style={{
                    position: 'absolute',
                    top: 3,
                    left: 3,
                    width: 'calc(50% - 3px)',
                    height: 'calc(100% - 6px)',
                    borderRadius: 8,
                    background: colors.accent,
                    boxShadow: '0 0 14px rgba(230,57,70,0.35)',
                    transition: 'transform 0.1s ease',
                    transform: stage === 'late' ? 'translateX(100%)' : 'translateX(0)',
                    pointerEvents: 'none',
                  }} />
                  {[
                    { value: 'early', label: "I'm exploring an idea" },
                    { value: 'late',  label: "I have traction & data" },
                  ].map(({ value, label }) => {
                    const active = stage === value
                    const hovered = hoveredStage === value
                    const pressed = pressedStage === value
                    return (
                      <button
                        key={value}
                        onClick={() => setStage(value)}
                        onMouseEnter={() => setHoveredStage(value)}
                        onMouseLeave={() => { setHoveredStage(null); setPressedStage(null) }}
                        onMouseDown={() => setPressedStage(value)}
                        onMouseUp={() => setPressedStage(null)}
                        style={{
                          flex: 1,
                          position: 'relative',
                          zIndex: 1,
                          padding: '10px 16px',
                          background: (!active && hovered) ? 'rgba(255,255,255,0.04)' : 'transparent',
                          border: 'none',
                          borderRadius: 7,
                          color: active ? '#fff' : 'rgba(167,167,167,0.65)',
                          cursor: 'pointer',
                          textAlign: 'center',
                          transition: 'color 0.2s ease, background 0.15s ease, transform 0.1s ease',
                          transform: (!active && pressed) ? 'scale(0.97)' : 'scale(1)',
                          ...mono,
                          fontSize: '0.72rem',
                          letterSpacing: 1,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {label}
                      </button>
                    )
                  })}
                </div>
                {/* Dynamic helper text */}
                <div style={{
                  ...mono,
                  fontSize: '0.6rem',
                  color: colors.textGhost,
                  marginTop: spacing.sm,
                  transition: 'opacity 0.2s ease',
                  opacity: 0.8,
                }}>
                  {stage === 'early'
                    ? "Challenge assumptions and uncover blind spots."
                    : "Stress-test metrics, scalability, and risks."}
                </div>
              </div>

              {knowledgeBasePanel}

              <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg, alignItems: 'center', justifyContent: 'center' }}>
                <PrimaryBtn onClick={handleStartDebate}>
                  <span>🎤</span> START DEBATE
                </PrimaryBtn>
                {(judgeResult || report) && (
                  <GhostBtn
                    onClick={() => exportToPDF(reportRef, { report, claim })}
                    color={colors.info}
                  >Export PDF</GhostBtn>
                )}
              </div>
            </div>
          )}

          {/* ══════════ CONNECTING ══════════ */}
          {status === 'connecting' && (
            <div style={{ animation: 'fadeIn 0.4s ease forwards' }}>
              <h1 style={{
                ...displayFont, fontSize: 56, lineHeight: 0.92,
                letterSpacing: 2, margin: `0 0 ${spacing.xl}px`,
                color: colors.textFaint,
              }}>
                SUMMONING<br />
                <span style={{
                  color: colors.accent,
                  fontFamily: "'DM Serif Display', Georgia, serif",
                  fontStyle: 'italic',
                }}>
                  your opponent
                </span>
              </h1>

              <div style={{ ...card }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, marginBottom: spacing.md }}>
                  <Spinner />
                  <span style={{ ...mono, color: colors.textMuted }}>
                    {sessionStatus || 'Starting...'}
                  </span>
                </div>
                <div style={{ height: 1, background: colors.border, marginBottom: spacing.md }} />
                <p style={{ ...mono, color: colors.textFaint, margin: 0 }}>
                  First load may take 10–15 s while the server wakes up.
                </p>
              </div>
            </div>
          )}

          {/* ══════════ DEBATING ══════════ */}
          {status === 'debating' && (
            <div style={{ animation: 'fadeIn 0.4s ease forwards' }}>

              {/* Position card */}
              <div style={{
                ...card,
                borderLeft: `3px solid ${colors.accent}`,
                marginBottom: spacing.lg,
              }}>
                <SectionLabel color={colors.accent}>Your Position</SectionLabel>
                <p style={{
                  ...serif, color: colors.textSecondary,
                  fontSize: font.lg, lineHeight: 1.6, margin: 0,
                }}>
                  {claim}
                </p>
              </div>

              {showOnboarding && (
                <div style={{ marginBottom: spacing.md }}>
                  <OnboardingBanner onDismiss={() => setShowOnboarding(false)} />
                </div>
              )}

              <div style={{ marginBottom: spacing.sm }}>
                <TurnIndicator
                  isAgentSpeaking={isAgentSpeaking}
                  isPaused={isPaused}
                  agentHasSpoken={agentHasSpokenRef.current}
                />
              </div>
              <div style={{ marginBottom: spacing.lg }}>
                <MicStatusBar volume={micVolume} isPaused={isPaused} />
              </div>
              <AgentSpeakingBadge isAgentSpeaking={isAgentSpeaking} />

              {knowledgeBasePanel}

              {/* Argument tracker */}
              {claims.length > 0 && (
                <div style={{ marginTop: spacing.xl }}>
                  <SectionLabel>Argument Tracker</SectionLabel>
                  {claims.slice(-5).map((c, i) => {
                    const col = classificationColor(c.classification)
                    return (
                      <div key={i} style={{
                        padding: `${spacing.sm}px ${spacing.md}px`,
                        marginBottom: spacing.sm,
                        borderRadius: radius.sm,
                        background: col.bg,
                        borderLeft: `3px solid ${col.border}`,
                      }}>
                        <div style={{
                          display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center', marginBottom: 2,
                        }}>
                          <span style={{ ...mono, fontWeight: 700, color: col.text }}>
                            {c.classification}
                          </span>
                          <span style={{ ...mono, color: colors.textDim }}>
                            Strength {c.strength}/10
                          </span>
                        </div>
                        <p style={{
                          margin: 0, fontSize: font.sm, ...serif,
                          color: colors.textMuted, lineHeight: 1.4,
                        }}>
                          {c.summary}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Consent toggle */}
              <button onClick={() => {
                const label = document.getElementById('consent-label')
                const scan = document.getElementById('consent-scan')
                label?.classList.add('glitching')
                scan?.classList.add('glitching')
                setTimeout(() => {
                  label?.classList.remove('glitching')
                  scan?.classList.remove('glitching')
                }, 300)
                handleConsentToggle()
              }} style={{
                marginTop: spacing.xl,
                padding: `${spacing.md}px ${spacing.lg}px`,
                display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', gap: spacing.lg,
                borderRadius: radius.md,
                border: `1px solid ${consentGiven ? colors.success + '40' : colors.borderSubtle}`,
                background: consentGiven ? `${colors.success}08` : 'transparent',
                transition: 'background 0.3s ease, border-color 0.3s ease',
                width: '100%', cursor: 'pointer', textAlign: 'left',
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: spacing.sm }}>
                  <span style={{ fontSize: 14, marginTop: 1, flexShrink: 0 }}>
                    {consentGiven ? '🔬' : '🔒'}
                  </span>
                  <div>
                    <p style={{ margin: 0, ...mono, color: consentGiven ? colors.success : colors.textMuted }}>
                      Share session data for research
                    </p>
                    <p style={{
                      margin: '3px 0 0', fontSize: font.xs,
                      color: colors.textGhost, ...serif, lineHeight: 1.4,
                    }}>
                      Your transcript, claim data, and audio may be stored and used for academic research. Toggle off to discard all data at session end.
                    </p>
                  </div>
                </div>

                <div style={{
                  flexShrink: 0,
                  border: `1px solid ${consentGiven ? colors.success : colors.accent}`,
                  borderRadius: radius.sm,
                  padding: `4px 10px`,
                  position: 'relative',
                  overflow: 'hidden',
                  minWidth: 110,
                  textAlign: 'center',
                }}>
                  <style>{`
                          @keyframes glitch-scan {
                              0%   { transform: translateY(-100%); opacity: 0.6; }
                              100% { transform: translateY(200%);  opacity: 0; }
                          }
                          @keyframes glitch-flicker {
                              0%,100% { opacity: 1; }
                              20%     { opacity: 0.2; }
                              40%     { opacity: 1; }
                              60%     { opacity: 0.4; }
                              80%     { opacity: 1; }
                          }
                          .glitch-label { animation: none; }
                          .glitch-label.glitching { animation: glitch-flicker 0.25s ease forwards; }
                          .glitch-scan-line {
                              position: absolute;
                              left: 0; right: 0;
                              height: 3px;
                              background: ${consentGiven ? colors.success : colors.accent};
                              opacity: 0;
                              pointer-events: none;
                          }
                          .glitch-scan-line.glitching { animation: glitch-scan 0.25s ease forwards; }
                      `}</style>

                  <div className="glitch-scan-line" id="consent-scan" />
                  <span
                    id="consent-label"
                    className="glitch-label"
                    style={{
                      ...mono,
                      fontSize: 10,
                      letterSpacing: 3,
                      color: consentGiven ? colors.success : colors.accent,
                      textDecoration: consentGiven ? 'none' : 'line-through',
                      textDecorationColor: colors.accent,
                      textDecorationThickness: 2,
                      display: 'block',
                      position: 'relative',
                      zIndex: 1,
                    }}
                  >
                    {consentGiven ? '[DECLASSIFIED]' : '[REDACTED]'}
                  </span>
                  {consentGiven && (
                    <span style={{
                      position: 'absolute',
                      top: 0, left: 0, right: 0, bottom: 0,
                      background: `${colors.success}10`,
                      pointerEvents: 'none',
                    }} />
                  )}
                </div>
              </button>

              {/* Controls */}
              <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
                <GhostBtn
                  onClick={togglePause}
                  color={isPaused ? colors.success : colors.textMuted}
                  borderColor={isPaused ? colors.success : colors.borderSubtle}
                >
                  {isPaused ? '▶ Resume' : '⏸ Pause'}
                </GhostBtn>
                <HoldToEndButton onConfirm={endDebate} />
              </div>
            </div>
          )}

          {/* ══════════ ENDED ══════════ */}
          {status === 'ended' && (
            <div style={{ animation: 'fadeIn 0.4s ease forwards' }}>
              <h1 style={{
                ...displayFont, fontSize: 60, lineHeight: 0.92,
                letterSpacing: 2, margin: `0 0 ${spacing.xl}px`,
              }}>
                DEBATE<br />
                <span style={{
                  color: colors.success,
                  fontFamily: "'DM Serif Display', Georgia, serif",
                  fontStyle: 'italic',
                }}>complete</span>
              </h1>

              <div ref={reportRef}>

                {/* Judge scorecard */}
                {judgeResult && (
                  <div style={{ ...card, marginBottom: spacing.lg }}>
                    <div style={{
                      display: 'flex', justifyContent: 'space-between',
                      alignItems: 'center', marginBottom: spacing.lg,
                    }}>
                      <SectionLabel>Judge Scorecard</SectionLabel>
                      <span style={{
                        padding: `4px ${spacing.md}px`,
                        borderRadius: radius.pill, ...mono,
                        background: judgeResult.winner === 'founder' ? colors.defendedBg : colors.concededBg,
                        color: judgeResult.winner === 'founder' ? colors.success : colors.accent,
                      }}>
                        {judgeResult.winner === 'founder' ? '🏆 Founder Wins' : '🤖 Agent Wins'}
                      </span>
                    </div>

                    <div style={{
                      display: 'grid', gridTemplateColumns: '1fr 1fr',
                      gap: spacing.sm, marginBottom: spacing.lg,
                    }}>
                      {Object.entries(judgeResult.scores).map(([dim, score]) => {
                        const col = scoreColor(score)
                        return (
                          <div key={dim} style={{
                            background: colors.bgSurfaceAlt,
                            borderRadius: radius.sm,
                            padding: `${spacing.sm}px ${spacing.md}px`,
                          }}>
                            <div style={{ ...mono, color: colors.textFaint, marginBottom: spacing.xs }}>
                              {dim.replace(/_/g, ' ')}
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                              <div style={{
                                flex: 1, height: 3, background: colors.borderSubtle,
                                borderRadius: 2, overflow: 'hidden',
                              }}>
                                <div style={{
                                  width: `${score * 10}%`, height: '100%',
                                  borderRadius: 2, background: col.text,
                                  transition: 'width 0.8s ease',
                                }} />
                              </div>
                              <span style={{ ...mono, color: col.text, width: 16, textAlign: 'right' }}>
                                {score}
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: spacing.md }}>
                      <ScoreRing score={judgeResult.overall} size={48} />
                      <p style={{
                        ...serif, color: colors.textDim,
                        fontSize: font.md, lineHeight: 1.6, margin: 0,
                      }}>
                        {judgeResult.summary}
                      </p>
                    </div>
                    <div data-pdf-hide style={{ marginTop: spacing.lg, borderTop: `1px solid ${colors.border}`, paddingTop: spacing.lg }}>
                      <button onClick={handleShare} style={{
                        padding: `8px 20px`,
                        background: 'transparent',
                        color: shareStatus === 'copied' ? colors.success : colors.textFaint,
                        border: `1px solid ${shareStatus === 'copied' ? colors.success : colors.borderSubtle}`,
                        borderRadius: radius.md,
                        fontSize: font.sm,
                        cursor: 'pointer',
                        fontFamily: "'JetBrains Mono', monospace",
                        letterSpacing: 1,
                        transition: 'color 0.2s, border-color 0.2s',
                      }}>
                        {shareStatus === 'copied' ? '✓ COPIED TO CLIPBOARD' : shareStatus === 'failed' ? 'COPY FAILED' : '📋 SHARE SCORE'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Debate report */}
                {!reportReady ? (
                  <div style={{ ...card }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, marginBottom: spacing.sm }}>
                      <Spinner />
                      <span style={{ ...mono, color: colors.textFaint }}>Generating report...</span>
                    </div>
                    <p style={{ ...serif, color: colors.textGhost, fontSize: font.sm, lineHeight: 1.5, margin: 0 }}>
                      Analyzing your debate transcript — this usually takes about 30 seconds.
                    </p>
                  </div>
                ) : report ? (
                  <>
                    {/* Page 1: Scorecard context, idea, verdict, strengths, weaknesses */}
                    <div style={{ ...card, marginBottom: spacing.lg }}>

                      {report.idea_summary && (
                        <div style={{
                          background: colors.bgDeep,
                          border: `1px solid ${colors.border}`,
                          borderRadius: radius.md,
                          padding: spacing.md, marginBottom: spacing.xl,
                        }}>
                          <SectionLabel>Idea (as debated)</SectionLabel>
                          <p style={{
                            ...serif, color: colors.textMuted,
                            fontSize: font.md, lineHeight: 1.6, margin: 0,
                          }}>
                            {report.idea_summary}
                          </p>
                        </div>
                      )}

                      <p style={{
                        color: colors.textSecondary, fontSize: font.lg,
                        lineHeight: 1.5, marginBottom: spacing.xl
                      }}>
                        {report.verdict}
                      </p>

                      <div style={{ marginBottom: spacing.lg }}>
                        <SectionLabel color={colors.success}>Strengths</SectionLabel>
                        {report.strengths.map((s, i) => (
                          <div key={i} style={{
                            display: 'flex', gap: spacing.sm,
                            alignItems: 'flex-start', marginBottom: spacing.sm,
                          }}>
                            <span style={{ color: colors.success, marginTop: 2, flexShrink: 0 }}>✓</span>
                            <p style={{ ...serif, margin: 0, fontSize: font.md, lineHeight: 1.5, color: colors.textMuted }}>
                              {s}
                            </p>
                          </div>
                        ))}
                      </div>

                      <div>
                        <SectionLabel color={colors.accent}>Weaknesses</SectionLabel>
                        {report.weaknesses.map((w, i) => (
                          <div key={i} style={{
                            display: 'flex', gap: spacing.sm,
                            alignItems: 'flex-start', marginBottom: spacing.sm,
                          }}>
                            <span style={{ color: colors.accent, marginTop: 2, flexShrink: 0 }}>✗</span>
                            <p style={{ ...serif, margin: 0, fontSize: font.md, lineHeight: 1.5, color: colors.textMuted }}>
                              {w}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Page 2: Debate breakdown, best moment, biggest gap, next steps */}
                    <div style={{ ...card }} data-pdf-page-break>

                      {report.claim_events?.length > 0 && (
                        <div style={{ marginBottom: spacing.lg }}>
                          <SectionLabel>Debate Breakdown</SectionLabel>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                            {report.claim_events.map((c, i) => {
                              const col = classificationColor(c.classification)
                              return (
                                <div key={i} style={{
                                  borderLeft: `3px solid ${col.border}`,
                                  padding: `${spacing.md}px ${spacing.md}px`,
                                  borderBottom: i < report.claim_events.length - 1 ? `1px solid ${colors.border}` : 'none',
                                }}>
                                  <div style={{
                                    display: 'flex', alignItems: 'center', gap: spacing.sm,
                                    marginBottom: spacing.xs,
                                  }}>
                                    <span style={{ ...mono, fontSize: font.xs, fontWeight: 700, color: col.text }}>
                                      {c.classification}
                                    </span>
                                    <span style={{ ...mono, fontSize: font.xs, color: colors.textDim }}>
                                      {c.strength}/10
                                    </span>
                                  </div>
                                  <p style={{
                                    ...serif, margin: 0, fontSize: font.sm,
                                    lineHeight: 1.5, color: colors.textMuted,
                                  }}>
                                    {c.summary}
                                  </p>
                                  {c.suggested_argument && (
                                    <p style={{
                                      ...serif, margin: `${spacing.xs}px 0 0`,
                                      fontSize: font.sm, lineHeight: 1.5,
                                      color: colors.textDim, fontStyle: 'italic',
                                    }}>
                                      {c.suggested_argument}
                                    </p>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      <div style={{
                        display: 'grid', gridTemplateColumns: '1fr 1fr',
                        gap: spacing.md, marginBottom: spacing.lg,
                      }}>
                        {[
                          { label: 'Best Moment', color: colors.info, content: report.sharpest_moment },
                          { label: 'Biggest Gap', color: colors.warning, content: report.biggest_gap },
                        ].map(({ label, color, content }) => (
                          <div key={label} style={{
                            background: colors.bgSurfaceAlt,
                            borderRadius: radius.md, padding: spacing.md,
                            borderTop: `2px solid ${color}`,
                          }}>
                            <SectionLabel color={color}>{label}</SectionLabel>
                            <p style={{
                              ...serif, color: colors.textMuted,
                              fontSize: font.sm, lineHeight: 1.5, margin: 0,
                            }}>
                              {content}
                            </p>
                          </div>
                        ))}
                      </div>

                      <div style={{
                        background: '#0a1a0a',
                        border: `1px solid #1a3a1a`,
                        borderLeft: `3px solid ${colors.success}`,
                        borderRadius: radius.md, padding: spacing.md,
                      }}>
                        <SectionLabel color={colors.success}>Next Steps</SectionLabel>
                        <p style={{
                          ...serif, color: colors.textMuted,
                          fontSize: font.md, lineHeight: 1.5, margin: 0,
                        }}>
                          {report.recommendation}
                        </p>
                      </div>
                    </div>
                  </>
                ) : (
                  <div style={{ ...card }}>
                    <span style={{ ...mono, color: colors.textFaint }}>
                      Session too short — no report generated.
                    </span>
                  </div>
                )}

              </div>

              <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
                {(judgeResult || report) && (
                  <GhostBtn onClick={() => exportToPDF(reportRef, { report, claim })} color={colors.info}>
                    Export PDF
                  </GhostBtn>
                )}
                <PrimaryBtn
                  onClick={resetSession}
                  style={{ opacity: !reportReady ? 0.4 : 1, pointerEvents: !reportReady ? 'none' : 'auto' }}
                >
                  {!reportReady ? 'GENERATING...' : 'NEW DEBATE'}
                </PrimaryBtn>
              </div>
              <FeedbackWidget sessionId={sessionId} uid={user?.uid} claim={claim} />
            </div>
          )}
        </div>

        {/* ── Right: transcript panel ──────────────────────────── */}
        <div style={{
          width: 360, flexShrink: 0,
          position: 'sticky', top: 65,
          height: 'calc(100vh - 90px)',
          display: 'flex', flexDirection: 'column',
          background: colors.bgSurface,
          border: `1px solid ${colors.border}`,
          borderRadius: radius.lg,
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: `${spacing.md}px ${spacing.lg}px`,
            borderBottom: `1px solid ${colors.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <span style={{ ...mono, color: colors.textFaint }}>Transcript</span>
            {status === 'debating' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: colors.accent,
                  animation: 'pulse 1.5s ease-out infinite',
                }} />
                <span style={{ ...mono, color: colors.accent }}>LIVE</span>
              </div>
            )}
          </div>

          {/* Body */}
          <div style={{ flex: 1, overflowY: 'auto', padding: spacing.lg }}>
            {transcript.length === 0 && Object.values(partials).every(v => !v) ? (
              <p style={{ ...mono, color: colors.textGhost }}>
                Transcript will appear here...
              </p>
            ) : null}

            {status === 'debating' && transcript.length > 0 && !transcript.some(t => t.speaker === 'agent') && Object.values(partials).every(v => !v) && (
              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.lg }}>
                <div style={{ display: 'flex', gap: 4 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: colors.accent,
                      animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
                <span style={{ ...mono, color: colors.textFaint }}>Preparing argument...</span>
              </div>
            )}

            {(transcript.length > 0 || Object.values(partials).some(v => v)) && (
              <>
                {transcript.map((t, i) => (
                  <div key={i} style={{ marginBottom: spacing.lg }}>
                    <div style={{
                      ...mono, marginBottom: 4,
                      color: t.speaker === 'agent' ? colors.accent
                        : t.speaker === 'user' ? colors.success
                          : colors.textFaint,
                    }}>
                      {t.speaker === 'agent' ? "Devil's Advocate"
                        : t.speaker === 'user' ? 'You'
                          : '🧠 Reasoning'}
                    </div>
                    <p style={{
                      margin: 0, lineHeight: 1.6, fontSize: font.base,
                      fontFamily: t.speaker === 'reasoning'
                        ? "'JetBrains Mono', monospace"
                        : "'Georgia', serif",
                      color: t.speaker === 'reasoning' ? colors.textFaint : colors.textSecondary,
                      fontStyle: t.speaker === 'reasoning' ? 'italic' : 'normal',
                    }}>
                      {t.text}
                    </p>
                  </div>
                ))}

                {Object.entries(partials).map(([speaker, text]) =>
                  text ? (
                    <div key={`partial-${speaker}`} style={{ marginBottom: spacing.lg, opacity: 0.5 }}>
                      <div style={{
                        ...mono, marginBottom: 4,
                        color: speaker === 'agent' ? colors.accent : colors.success,
                      }}>
                        {speaker === 'agent' ? "Devil's Advocate" : 'You'}
                      </div>
                      <p style={{
                        margin: 0, lineHeight: 1.6, fontSize: font.base,
                        ...serif, color: colors.textSecondary,
                      }}>
                        {text}
                        <span style={{ animation: 'blink 1s step-end infinite' }}>▍</span>
                      </p>
                    </div>
                  ) : null
                )}
              </>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>

      </div>
    </div>
  )
}
