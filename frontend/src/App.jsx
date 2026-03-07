import { useRef, useEffect, useState } from 'react'
import { useAuth } from './hooks/useAuth'
import { useDebateSession } from './hooks/useDebateSession'
import { useDocumentUpload } from './useDocumentUpload'
import {
  TurnIndicator, MicStatusBar, OnboardingBanner,
  AgentSpeakingBadge, conversationKeyframes,
} from './ConversationUI'
import LandingPage from './LandingPage'

// ── UI imports (will become components in the next refactor pass) ──
// All inline styles below should be migrated to use theme.js tokens
// once you start splitting into components.
import {
  colors, radius, font, spacing, letterSpacing,
  scoreColor, classificationColor,
} from './theme'


function Spinner() {
  return (
    <div style={{
      width: 18, height: 18, borderRadius: '50%',
      border: `2px solid ${colors.borderSubtle}`,
      borderTopColor: colors.accent,
      animation: 'spin 0.8s linear infinite',
      flexShrink: 0,
    }} />
  )
}

export default function App() {
  const { user, authReady, signInWithGoogle, signInWithGitHub, handleSignOut } = useAuth()

  const {
    status, transcript, partials, claims, report, judgeResult,
    isAgentSpeaking, isPaused, consentGiven, sessionStatus, micVolume,
    startDebate, endDebate, resetSession, togglePause,
    handleConsentToggle, exportToPDF,
  } = useDebateSession()

  const { uploadedFiles, uploading, loadingFiles, uploadFile, removeFile } =
    useDocumentUpload(user, status === 'debating')

  const [claim, setClaim] = useState('')
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [showLanding, setShowLanding] = useState(true)

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
    }
  }, [transcript])

  useEffect(() => {
    if (transcript.some(t => t.speaker === 'agent')) {
      agentHasSpokenRef.current = true
    }
  }, [transcript])


  // ── Handlers ────────────────────────────────────────────────────
  async function handleStartDebate() {
    if (!authReady || !user) return alert('Auth not ready yet, try again')
    if (!claim.trim()) return alert('Enter your position first')
    await startDebate(claim, user, uploadedFiles)
  }

  // ── Knowledge base panel (shared between idle + debating) ───────
  const knowledgeBasePanel = authReady && user && (
    <div style={{ marginTop: spacing.lg }}>
      <h3 style={{
        fontSize: font.xs, color: colors.textFaint,
        textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm
      }}>
        Your Knowledge Base
      </h3>

      {status !== 'debating' && (
        <div
          style={{
            border: `1px dashed ${colors.borderSubtle}`, borderRadius: radius.md,
            padding: spacing.lg, textAlign: 'center', marginBottom: spacing.sm,
            cursor: 'pointer', background: colors.bgDark,
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef} type="file" accept=".pdf,.txt" multiple
            style={{ display: 'none' }}
            onChange={e => {
              Array.from(e.target.files).forEach(uploadFile)
              e.target.value = ''
            }}
          />
          <p style={{ margin: 0, color: colors.textFaint, fontSize: font.md }}>
            {uploading ? 'Uploading...' : '+ Add pitch deck, business plan, or notes (PDF or .txt)'}
          </p>
        </div>
      )}

      {loadingFiles ? (
        <p style={{ color: colors.textGhost, fontSize: font.sm }}>Loading documents...</p>
      ) : uploadedFiles.length === 0 ? (
        <p style={{ color: colors.textGhost, fontSize: font.sm }}>No documents uploaded yet.</p>
      ) : (
        uploadedFiles.map((f, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: `6px ${spacing.md}px`, marginBottom: spacing.xs,
            background: colors.bgSurfaceAlt, borderRadius: radius.sm,
          }}>
            <span style={{ fontSize: font.sm, color: colors.textMuted }}>
              📄 {f.name}
              <span style={{ color: colors.textGhost, marginLeft: spacing.sm }}>
                ({(f.size / 1024).toFixed(0)}KB)
              </span>
            </span>
            {status !== 'debating' && (
              <button
                onClick={() => removeFile(f.path)}
                style={{
                  background: 'none', border: 'none',
                  color: colors.textFaint, cursor: 'pointer',
                  fontSize: font.base, padding: `0 ${spacing.xs}px`,
                }}
              >✕</button>
            )}
          </div>
        ))
      )}

      {user?.isAnonymous && status !== 'debating' && uploadedFiles.length > 0 && (
        <p style={{ fontSize: font.xs, color: colors.textGhost, marginTop: spacing.sm }}>
          Guest uploads are deleted when your session ends.
        </p>
      )}
    </div>
  )

  // ── Render ──────────────────────────────────────────────────────
  if (showLanding) {
    return <LandingPage onEnter={() => setShowLanding(false)} />
  }
  return (
    <div style={{
      display: 'flex', gap: 24,
      maxWidth: 1100, margin: '40px auto', padding: `0 ${spacing.xl}px`,
    }}>

      {/* ── Left: main UI ── */}
      <div style={{ flex: 1 }}>
        <h1 style={{ fontSize: font.h2, marginBottom: spacing.sm }}>Devil's Advocate</h1>
        <p style={{ color: colors.textDim, marginBottom: spacing.xxl }}>
          State your business idea. The agent will argue against it.
        </p>

        {/* ── Auth header ── */}
        {authReady && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: spacing.xl, padding: `10px ${spacing.md}px`,
            background: colors.bgSurface, border: `1px solid ${colors.border}`,
            borderRadius: radius.md,
          }}>
            {user?.isAnonymous ? (
              <span style={{ fontSize: font.md, color: colors.textFaint }}>Signed in as guest</span>
            ) : (
              <span style={{ fontSize: font.md, color: colors.textMuted }}>
                {user?.displayName || user?.email}
              </span>
            )}
            {user?.isAnonymous ? (
              <div style={{ display: 'flex', gap: spacing.sm }}>
                <button onClick={signInWithGoogle} style={{
                  padding: `6px ${spacing.md}px`, background: colors.googleBtnBg,
                  color: colors.info, border: `1px solid ${colors.info}`,
                  borderRadius: radius.sm, fontSize: font.md, cursor: 'pointer',
                }}>Sign in with Google</button>
                <button onClick={signInWithGitHub} style={{
                  padding: `6px ${spacing.md}px`, background: colors.githubBtnBg,
                  color: colors.textMuted, border: `1px solid ${colors.githubBorder}`,
                  borderRadius: radius.sm, fontSize: font.md, cursor: 'pointer',
                }}>Sign in with GitHub</button>
              </div>
            ) : (
              <button onClick={handleSignOut} style={{
                padding: `6px ${spacing.md}px`, background: 'transparent',
                color: colors.textFaint, border: `1px solid ${colors.borderSubtle}`,
                borderRadius: radius.sm, fontSize: font.md, cursor: 'pointer',
              }}>Sign out</button>
            )}
          </div>
        )}

        {/* ── IDLE ── */}
        {status === 'idle' && (
          <div>
            <textarea
              value={claim}
              onChange={e => setClaim(e.target.value)}
              placeholder="Describe your business idea..."
              rows={4}
              style={{
                width: '100%', padding: spacing.md, borderRadius: radius.md,
                background: colors.bgSurfaceAlt, color: colors.textPrimary,
                border: `1px solid ${colors.borderSubtle}`, fontSize: font.lg,
                resize: 'vertical', boxSizing: 'border-box',
              }}
            />
            {knowledgeBasePanel}
            <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.md }}>
              <button onClick={handleStartDebate} style={{
                padding: `12px 28px`, background: colors.accent,
                color: 'white', border: 'none', borderRadius: radius.md,
                fontSize: font.xl, cursor: 'pointer',
              }}>Start Debate</button>
              {(judgeResult || report) && (
                <button onClick={() => exportToPDF(reportRef)} style={{
                  padding: `10px 24px`, background: colors.googleBtnBg,
                  color: colors.info, border: `1px solid ${colors.info}`,
                  borderRadius: radius.md, fontSize: font.lg, cursor: 'pointer',
                }}>Export PDF</button>
              )}
            </div>
          </div>
        )}

        {/* ── CONNECTING ── */}
        {status === 'connecting' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Spinner />
              <p style={{ color: colors.textMuted }}>{sessionStatus || 'Starting...'}</p>
            </div>
            <p style={{ color: colors.textFaint, fontSize: font.sm, marginTop: 8 }}>
              First load may take 10–15 seconds while the server wakes up.
            </p>
          </div>
        )}

        {/* ── DEBATING ── */}
        {status === 'debating' && (
          <div>
            <div style={{
              background: colors.bgDeep, border: `1px solid ${colors.border}`,
              borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.lg,
            }}>
              <h3 style={{
                fontSize: font.xs, color: colors.textFaint,
                textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
              }}>Your Position</h3>
              <p style={{ color: colors.textSecondary, fontSize: font.base, lineHeight: 1.6, margin: 0 }}>
                {claim}
              </p>
            </div>

            {/* Onboarding banner — auto-dismiss after first agent turn */}
            {showOnboarding && (
              <OnboardingBanner onDismiss={() => setShowOnboarding(false)} />
            )}

            {/* Turn indicator */}
            <div style={{ marginTop: spacing.md }}>
              <TurnIndicator
                isAgentSpeaking={isAgentSpeaking}
                isPaused={isPaused}
                agentHasSpoken={agentHasSpokenRef.current}
              />
            </div>

            {/* Mic status + visualizer */}
            <div style={{ marginTop: spacing.sm }}>
              <MicStatusBar volume={micVolume} isPaused={isPaused} />
            </div>

            {/* Enhanced agent speaking badge */}
            <AgentSpeakingBadge isAgentSpeaking={isAgentSpeaking} />

            {knowledgeBasePanel}

            {/* Argument tracker */}
            {claims.length > 0 && (
              <div style={{ marginTop: spacing.xl }}>
                <h3 style={{
                  fontSize: font.sm, color: colors.textFaint,
                  textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                }}>Argument Tracker</h3>
                {claims.slice(-5).map((c, i) => {
                  const col = classificationColor(c.classification)
                  return (
                    <div key={i} style={{
                      padding: `8px ${spacing.md}px`, marginBottom: spacing.sm,
                      borderRadius: radius.sm, background: col.bg,
                      borderLeft: `3px solid ${col.border}`,
                    }}>
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 2,
                      }}>
                        <span style={{
                          fontSize: font.xs, fontWeight: 700,
                          textTransform: 'uppercase', color: col.text,
                        }}>{c.classification}</span>
                        <span style={{ fontSize: font.xs, color: colors.textDim }}>
                          Strength: {c.strength}/10
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: font.sm, color: colors.textMuted, lineHeight: 1.4 }}>
                        {c.summary}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Consent toggle */}
            <div style={{
              marginTop: spacing.xl, padding: `${spacing.md}px ${spacing.lg}px`,
              background: colors.bgSurface, border: `1px solid ${colors.border}`,
              borderRadius: radius.md, display: 'flex',
              alignItems: 'center', justifyContent: 'space-between', gap: spacing.lg,
            }}>
              <div>
                <p style={{ margin: 0, fontSize: font.md, color: colors.textSecondary, fontWeight: 600 }}>
                  Share session data for research
                </p>
                <p style={{ margin: '2px 0 0', fontSize: font.xs, color: colors.textFaint, lineHeight: 1.4 }}>
                  Transcript and report used for academic study only.
                  On by default. You can change this any time before ending the debate.
                </p>
              </div>
              <button
                onClick={handleConsentToggle}
                style={{
                  flexShrink: 0, width: 44, height: 24, borderRadius: radius.pill,
                  border: 'none', cursor: 'pointer',
                  background: consentGiven ? colors.success : colors.borderSubtle,
                  position: 'relative', transition: 'background 0.2s',
                }}
              >
                <span style={{
                  position: 'absolute', top: 3,
                  left: consentGiven ? 22 : 3,
                  width: 18, height: 18, borderRadius: radius.circle,
                  background: 'white', transition: 'left 0.2s',
                }} />
              </button>
            </div>

            <button onClick={togglePause} style={{
              marginTop: spacing.lg, marginRight: spacing.sm,
              padding: `10px 24px`,
              background: isPaused ? colors.success : colors.borderSubtle,
              color: isPaused ? '#000' : 'white',
              border: 'none', borderRadius: radius.md, fontSize: font.lg, cursor: 'pointer',
            }}>
              {isPaused ? 'Resume' : 'Pause'}
            </button>
            <button onClick={endDebate} style={{
              marginTop: spacing.lg, padding: `10px 24px`,
              background: colors.borderSubtle, color: 'white',
              border: 'none', borderRadius: radius.md, fontSize: font.lg, cursor: 'pointer',
            }}>
              End Debate & Generate Evaluation
            </button>
          </div>
        )}

        {/* ── ENDED ── */}
        {status === 'ended' && (
          <div>
            <p style={{ color: colors.success, marginBottom: spacing.lg }}>Debate ended.</p>
            <div ref={reportRef}>

              {/* Judge scorecard */}
              {judgeResult && (
                <div style={{
                  background: colors.bgSurface, borderRadius: radius.lg,
                  border: `1px solid ${colors.border}`, padding: spacing.xl, marginBottom: spacing.lg,
                }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: spacing.lg,
                  }}>
                    <h3 style={{
                      fontSize: font.sm, color: colors.textFaint,
                      textTransform: 'uppercase', letterSpacing: letterSpacing.label, margin: 0,
                    }}>Judge Scorecard</h3>
                    <span style={{
                      padding: `4px ${spacing.md}px`, borderRadius: radius.pill,
                      fontSize: font.sm, fontWeight: 700,
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
                          background: colors.bgSurfaceAlt, borderRadius: radius.sm,
                          padding: `8px ${spacing.md}px`,
                        }}>
                          <div style={{
                            fontSize: font.xs, color: colors.textFaint,
                            textTransform: 'uppercase', letterSpacing: letterSpacing.tight, marginBottom: spacing.xs,
                          }}>
                            {dim.replace(/_/g, ' ')}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                            <div style={{
                              flex: 1, height: 4, background: colors.borderSubtle,
                              borderRadius: 2, overflow: 'hidden',
                            }}>
                              <div style={{
                                width: `${score * 10}%`, height: '100%',
                                borderRadius: 2, background: col.text,
                                transition: 'width 0.6s ease',
                              }} />
                            </div>
                            <span style={{ fontSize: font.sm, color: colors.textSecondary, width: 20, textAlign: 'right' }}>
                              {score}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: spacing.md }}>
                    {(() => {
                      const col = scoreColor(judgeResult.overall)
                      return (
                        <div style={{
                          width: 48, height: 48, borderRadius: radius.circle, flexShrink: 0,
                          background: col.bg, border: `2px solid ${col.border}`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: font.xl, fontWeight: 700, color: col.text,
                        }}>
                          {judgeResult.overall}
                        </div>
                      )
                    })()}
                    <p style={{ color: colors.textDim, fontSize: font.md, lineHeight: 1.6, margin: 0 }}>
                      {judgeResult.summary}
                    </p>
                  </div>
                </div>
              )}

              {/* Debate report */}
              {report ? (
                <div style={{
                  background: colors.bgSurface, borderRadius: radius.lg,
                  border: `1px solid ${colors.border}`, padding: spacing.xl,
                }}>
                  {report.idea_summary && (
                    <div style={{
                      background: colors.bgDeep, border: `1px solid ${colors.border}`,
                      borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.xl,
                    }}>
                      <h3 style={{
                        fontSize: font.xs, color: colors.textDim,
                        textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                      }}>Idea (as debated)</h3>
                      <p style={{ color: colors.textMuted, fontSize: font.md, lineHeight: 1.6, margin: 0 }}>
                        {report.idea_summary}
                      </p>
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: spacing.lg, marginBottom: spacing.xl }}>
                    {(() => {
                      const col = scoreColor(report.overall_score)
                      return (
                        <div style={{
                          width: 64, height: 64, borderRadius: radius.circle, flexShrink: 0,
                          background: col.bg, border: `2px solid ${col.border}`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: font.xxl, fontWeight: 700, color: col.text,
                        }}>
                          {report.overall_score}
                        </div>
                      )
                    })()}
                    <p style={{ color: colors.textSecondary, fontSize: font.lg, lineHeight: 1.5, margin: 0 }}>
                      {report.verdict}
                    </p>
                  </div>

                  <div style={{ marginBottom: spacing.lg }}>
                    <h3 style={{
                      fontSize: font.xs, color: colors.success,
                      textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                    }}>Strengths</h3>
                    {report.strengths.map((s, i) => (
                      <p key={i} style={{ color: colors.textMuted, fontSize: font.md, lineHeight: 1.5, marginBottom: spacing.xs }}>
                        ✓ {s}
                      </p>
                    ))}
                  </div>

                  <div style={{ marginBottom: spacing.lg }}>
                    <h3 style={{
                      fontSize: font.xs, color: colors.accent,
                      textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                    }}>Weaknesses</h3>
                    {report.weaknesses.map((w, i) => (
                      <p key={i} style={{ color: colors.textMuted, fontSize: font.md, lineHeight: 1.5, marginBottom: spacing.xs }}>
                        ✗ {w}
                      </p>
                    ))}
                  </div>

                  <div style={{
                    display: 'grid', gridTemplateColumns: '1fr 1fr',
                    gap: spacing.md, marginBottom: spacing.lg,
                  }}>
                    {[
                      { label: 'Best Moment', color: colors.info, content: report.sharpest_moment },
                      { label: 'Biggest Gap', color: colors.warning, content: report.biggest_gap },
                    ].map(({ label, color, content }) => (
                      <div key={label} style={{
                        background: colors.bgSurfaceAlt, borderRadius: radius.md, padding: spacing.md,
                      }}>
                        <h3 style={{
                          fontSize: font.xs, color, textTransform: 'uppercase',
                          letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                        }}>{label}</h3>
                        <p style={{ color: colors.textMuted, fontSize: font.sm, lineHeight: 1.5, margin: 0 }}>
                          {content}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div style={{
                    background: '#0f1f0f', border: '1px solid #1a3a1a',
                    borderRadius: radius.md, padding: spacing.md,
                  }}>
                    <h3 style={{
                      fontSize: font.xs, color: colors.success,
                      textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.sm,
                    }}>Next Steps</h3>
                    <p style={{ color: colors.textMuted, fontSize: font.md, lineHeight: 1.5, margin: 0 }}>
                      {report.recommendation}
                    </p>
                  </div>
                </div>
              ) : (
                <p style={{ color: colors.textFaint, fontSize: font.md }}>Generating report...</p>
              )}
            </div>

            <div style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
              {(judgeResult || report) && (
                <button onClick={() => exportToPDF(reportRef)} style={{
                  padding: `10px 24px`, background: colors.googleBtnBg,
                  color: colors.info, border: `1px solid ${colors.info}`,
                  borderRadius: radius.md, fontSize: font.lg, cursor: 'pointer',
                }}>Export PDF</button>
              )}
              <button onClick={resetSession} style={{
                padding: `10px 24px`, background: '#4d4d4dc2',
                color: 'white', border: 'none', borderRadius: radius.md,
                fontSize: font.lg, cursor: 'pointer',
              }}>Clear (New Debate)</button>
            </div>
          </div>
        )}
      </div>

      {/* ── Right: transcript panel ── */}
      <div style={{
        width: 340, flexShrink: 0,
        background: colors.bgSurface, borderRadius: radius.lg,
        border: `1px solid ${colors.border}`, padding: spacing.lg,
        height: 'calc(100vh - 80px)',
        display: 'flex', flexDirection: 'column',
      }}>
        <h2 style={{
          fontSize: font.base, color: colors.textFaint,
          textTransform: 'uppercase', letterSpacing: letterSpacing.label, marginBottom: spacing.md,
        }}>Transcript</h2>
        <style>{`
          @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
          @keyframes spin { to { transform: rotate(360deg) } }
          ${conversationKeyframes}
        `}</style>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {transcript.length === 0 && Object.values(partials).every(v => !v) ? (
            <p style={{ color: colors.textGhost, fontSize: font.base }}>
              Transcript will appear here...
            </p>
          ) : (
            <>
              {transcript.map((t, i) => (
                <div key={i} style={{ marginBottom: spacing.lg }}>
                  <span style={{
                    color: t.speaker === 'agent' ? colors.accent
                      : t.speaker === 'user' ? colors.success
                        : colors.textFaint,
                    fontWeight: 600, fontSize: font.xs,
                    textTransform: 'uppercase', letterSpacing: letterSpacing.tight,
                  }}>
                    {t.speaker === 'agent' ? "Devil's Advocate"
                      : t.speaker === 'user' ? 'You'
                        : '🧠 Reasoning'}
                  </span>
                  <p style={{
                    margin: '4px 0 0', lineHeight: 1.6, fontSize: font.base,
                    color: t.speaker === 'reasoning' ? colors.textFaint : colors.textSecondary,
                    fontStyle: t.speaker === 'reasoning' ? 'italic' : 'normal',
                  }}>
                    {t.text}
                  </p>
                </div>
              ))}
              {Object.entries(partials).map(([speaker, text]) =>
                text ? (
                  <div key={`partial-${speaker}`} style={{ marginBottom: spacing.lg, opacity: 0.55 }}>
                    <span style={{
                      color: speaker === 'agent' ? colors.accent : colors.success,
                      fontWeight: 600, fontSize: font.xs,
                      textTransform: 'uppercase', letterSpacing: letterSpacing.tight,
                    }}>
                      {speaker === 'agent' ? "Devil's Advocate" : 'You'}
                    </span>
                    <p style={{ margin: '4px 0 0', lineHeight: 1.6, fontSize: font.base, color: colors.textSecondary }}>
                      {text}<span style={{ animation: 'blink 1s step-end infinite' }}>▍</span>
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
  )
}