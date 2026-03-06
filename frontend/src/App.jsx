import { useState, useRef, useEffect } from 'react'
import { io } from 'socket.io-client'
import { auth, googleProvider, githubProvider, signInAnonymously, signInWithPopup, onAuthStateChanged, signOut } from './firebase'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState('idle')       // idle | connecting | debating | ended
  const [transcript, setTranscript] = useState([])   // { speaker, text }[]
  const [claim, setClaim] = useState('')
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
  const [partials, setPartials] = useState({})        // { speaker: accumulated_text }
  const [claims, setClaims] = useState([]) // { classification, summary, strength }[]
  const [report, setReport] = useState(null)
  const [consentGiven, setConsentGiven] = useState(true)
  const [isPaused, setIsPaused] = useState(false)
  const [judgeResult, setJudgeResult] = useState(null)
  const [user, setUser] = useState(null)       // null = not yet resolved
  const [authReady, setAuthReady] = useState(false)



  const reportRef = useRef(null)


  const socketRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioContextRef = useRef(null)
  const streamRef = useRef(null)
  const nextAudioTimeRef = useRef(0)
  const isAgentSpeakingRef = useRef(false)
  const micStartedRef = useRef(false)
  const speakingTimerRef = useRef(null)
  const isPausedRef = useRef(false)

  const audioQueueRef = useRef([])
  const isProcessingAudioRef = useRef(false)

  const transcriptEndRef = useRef(null)
  const activeSourcesRef = useRef([])

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (firebaseUser) {
        setUser(firebaseUser)
      } else {
        // Auto sign-in anonymously if no user at all
        signInAnonymously(auth)
      }
      setAuthReady(true)
    })
    return () => unsubscribe()
  }, [])

  async function signInWithGoogle() {
    try {
      await signInWithPopup(auth, googleProvider)
      // onAuthStateChanged fires automatically and updates user state
    } catch (err) {
      console.error('Sign-in error:', err)
    }
  }

  async function signInWithGitHub() {
    try {
      await signInWithPopup(auth, githubProvider)
    } catch (err) {
      console.error('GitHub sign-in error:', err)
    }
  }

  async function handleSignOut() {
    await signOut(auth)
    // onAuthStateChanged will fire → triggers signInAnonymously again
  }

  // ── Connect to backend ──────────────────────────────────────────
  function connectSocket() {
    socketRef.current = io(BACKEND_URL)

    socketRef.current.on('transcript', ({ speaker, text }) => {
      setTranscript(prev => [...prev, { speaker, text }])
      setPartials(prev => ({ ...prev, [speaker]: '' }))
    })

    socketRef.current.on('transcript_partial', ({ speaker, text }) => {
      setPartials(prev => ({ ...prev, [speaker]: (prev[speaker] || '') + text }))
    })

    socketRef.current.on('agent_audio', (audioData) => {
      playAudioChunk(audioData)
    })

    socketRef.current.on('agent_speaking', (val) => {
      setIsAgentSpeaking(val)
      isAgentSpeakingRef.current = val
      if (!val) {
        nextAudioTimeRef.current = 0
      }
    })

    socketRef.current.on('judge_result', (data) => {
      setJudgeResult(data)
    })

    socketRef.current.on('claim_update', (result) => {
      setClaims(prev => [...prev, result])
    })


    socketRef.current.on('session_ready', () => {
      setStatus('debating')
      if (!micStartedRef.current) {
        micStartedRef.current = true
        startMicCapture()
      }
    })

    socketRef.current.on('disconnect', () => {
      setStatus('ended')
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
    })

    socketRef.current.on('debate_report', (data) => {
      setReport(data)
    })

    socketRef.current.on('agent_interrupted', () => {
      console.log('interrupted fired')
      interruptAgent()
    })

    socketRef.current.on('error', ({ message }) => {
      console.error('Server error:', message)
      alert(message)  // or render inline — up to you
    })
  }

  // ── Start a debate session ──────────────────────────────────────
  async function startDebate() {
    if (!authReady || !user) return alert('Auth not ready yet, try again')
    if (!claim.trim()) return alert('Enter your position first')
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: 24000 })
    }
    await audioContextRef.current.resume()
    setStatus('connecting')
    setReport(null)
    setTranscript([])
    setPartials({})
    setClaims([])
    setConsentGiven(true)
    setJudgeResult(null)
    micStartedRef.current = false    // add this
    audioQueueRef.current = []       // add this — clear any leftover audio
    isProcessingAudioRef.current = false  // add this
    connectSocket()
    socketRef.current.emit('start_session', { claim, uid: user.uid, isAnonymous: user.isAnonymous })
  }

  // ── Mic capture and streaming ───────────────────────────────────
  async function startMicCapture() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      streamRef.current = stream

      const micContext = new AudioContext({ sampleRate: 16000 })

      const workletCode = `
        class PCMProcessor extends AudioWorkletProcessor {
          process(inputs) {
            const input = inputs[0]?.[0]
            if (input) {
              const pcm = new Int16Array(input.length)
              for (let i = 0; i < input.length; i++) {
                const s = Math.max(-1, Math.min(1, input[i]))
                pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
              }
              this.port.postMessage(pcm.buffer, [pcm.buffer])
            }
            return true
          }
        }
        registerProcessor('pcm-processor', PCMProcessor)
      `

      const blob = new Blob([workletCode], { type: 'application/javascript' })
      const url = URL.createObjectURL(blob)
      await micContext.audioWorklet.addModule(url)
      URL.revokeObjectURL(url)

      const source = micContext.createMediaStreamSource(stream)
      const workletNode = new AudioWorkletNode(micContext, 'pcm-processor')

      workletNode.port.onmessage = (e) => {

        if (!isPausedRef.current) {
          socketRef.current?.emit('audio_chunk', e.data)
        }

      }

      source.connect(workletNode)
      workletNode.connect(micContext.destination)
    } catch (err) {
      console.error('Mic error:', err)
      alert('Microphone access denied')
    }
  }

  function togglePause() {
    const newVal = !isPausedRef.current
    isPausedRef.current = newVal
    setIsPaused(newVal)
    if (newVal) {
      // Also stop any agent audio currently playing
      interruptAgent()
    }
  }

  // ── Play audio response from agent ─────────────────────────────
  function playAudioChunk(base64Audio) {
    const ctx = audioContextRef.current
    if (!ctx) return

    // Decode immediately — don't queue, schedule directly on the audio timeline
    const bytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0))
    const samples = bytes.length / 2
    const float32 = new Float32Array(samples)
    const view = new DataView(bytes.buffer)
    for (let i = 0; i < samples; i++) {
      float32[i] = view.getInt16(i * 2, true) / 32768.0
    }

    const buffer = ctx.createBuffer(1, samples, 24000)
    buffer.copyToChannel(float32, 0)
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)

    // Schedule back-to-back with no gap — this is the key fix
    const startTime = Math.max(ctx.currentTime, nextAudioTimeRef.current)
    source.start(startTime)
    nextAudioTimeRef.current = startTime + buffer.duration

    // Track active sources so we can kill them on interruption
    activeSourcesRef.current.push(source)
    source.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source)
    }

    // Mark speaking
    isAgentSpeakingRef.current = true
    setIsAgentSpeaking(true)

    // Reset the "done speaking" timer on every new chunk
    if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
    const endDelay = (nextAudioTimeRef.current - ctx.currentTime + 0.3) * 1000
    speakingTimerRef.current = setTimeout(() => {
      isAgentSpeakingRef.current = false
      setIsAgentSpeaking(false)
      nextAudioTimeRef.current = 0
    }, endDelay)
  }
  async function exportToPDF() {
    if (!reportRef.current) return

    const { default: jsPDF } = await import('jspdf')
    const { default: html2canvas } = await import('html2canvas')

    const canvas = await html2canvas(reportRef.current, {
      backgroundColor: '#0d0d0d',
      scale: 2,                    // retina quality
      useCORS: true,
      logging: false,
    })

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'px',
      format: 'a4',
    })

    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const imgWidth = pageWidth
    const imgHeight = (canvas.height * pageWidth) / canvas.width

    // Handle multi-page if content is tall
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= pageHeight

    while (heightLeft > 0) {
      position -= pageHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight
    }

    const filename = `devils-advocate-${new Date().toISOString().slice(0, 10)}.pdf`
    pdf.save(filename)
  }

  // ── End session ─────────────────────────────────────────────────
  function endDebate() {
    setStatus('ended')
    micStartedRef.current = false
    if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    socketRef.current?.emit('end_session')
    //socketRef.current?.disconnect()
  }

  function interruptAgent() {
    // Stop all scheduled audio immediately
    activeSourcesRef.current.forEach(source => {
      try { source.stop() } catch { }
    })
    activeSourcesRef.current = []
    nextAudioTimeRef.current = 0

    if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
    isAgentSpeakingRef.current = false
    setIsAgentSpeaking(false)
  }

  // ── Utility: convert float32 audio to 16-bit PCM ───────────────
  function floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2)
    const view = new DataView(buffer)
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return buffer
  }

  function handleConsentToggle() {
    const newVal = !consentGiven
    setConsentGiven(newVal)
    socketRef.current?.emit('set_consent', { consent: newVal })
  }

  return (
    <div style={{ display: 'flex', gap: 24, maxWidth: 1100, margin: '40px auto', padding: '0 20px' }}>

      {/* ── Left: main UI ── */}
      <div style={{ flex: 1 }}>
        <h1 style={{ fontSize: 28, marginBottom: 8 }}>Devil's Advocate</h1>
        <p style={{ color: '#888', marginBottom: 32 }}>
          State your business idea. The agent will argue against it.
        </p>
        {/* ── Auth header ── */}
        {authReady && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 24, padding: '10px 14px',
            background: '#111', border: '1px solid #222', borderRadius: 8
          }}>
            {user?.isAnonymous ? (
              <span style={{ fontSize: 13, color: '#555' }}>
                Signed in as guest
              </span>
            ) : (
              <span style={{ fontSize: 13, color: '#aaa' }}>
                {user?.displayName || user?.email}
              </span>
            )}

            {user?.isAnonymous ? (
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={signInWithGoogle}
                  style={{
                    padding: '6px 14px', background: '#1a1a2e',
                    color: '#60a5fa', border: '1px solid #60a5fa',
                    borderRadius: 6, fontSize: 13, cursor: 'pointer'
                  }}
                >
                  Sign in with Google
                </button>
                <button
                  onClick={signInWithGitHub}
                  style={{
                    padding: '6px 14px', background: '#161b22',
                    color: '#aaa', border: '1px solid #30363d',
                    borderRadius: 6, fontSize: 13, cursor: 'pointer'
                  }}
                >
                  Sign in with GitHub
                </button>
              </div>
            ) : (
              <button
                onClick={handleSignOut}
                style={{
                  padding: '6px 14px', background: 'transparent',
                  color: '#555', border: '1px solid #333',
                  borderRadius: 6, fontSize: 13, cursor: 'pointer'
                }}
              >
                Sign out
              </button>
            )}
          </div>
        )}

        {status === 'idle' && (
          <div>
            <textarea
              value={claim}
              onChange={e => setClaim(e.target.value)}
              placeholder="Describe your business idea..."
              rows={4}
              style={{
                width: '100%', padding: 12, borderRadius: 8,
                background: '#1a1a1a', color: '#f0f0f0',
                border: '1px solid #333', fontSize: 15,
                resize: 'vertical', boxSizing: 'border-box'
              }}
            />
            <button
              onClick={startDebate}
              style={{
                marginTop: 12, padding: '12px 28px',
                background: '#e63946', color: 'white',
                border: 'none', borderRadius: 8,
                fontSize: 16, cursor: 'pointer'
              }}
            >
              Start Debate
            </button>
          </div>
        )}

        {status === 'connecting' && <p style={{ color: '#888' }}>Connecting...</p>}

        {status === 'debating' && (
          <div>
            {isAgentSpeaking && (
              <p style={{ color: '#e63946', fontStyle: 'italic' }}>Agent is speaking...</p>
            )}
            {/* ── Argument Tracker ── */}
            {claims.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h3 style={{
                  fontSize: 12, color: '#555', textTransform: 'uppercase',
                  letterSpacing: 1, marginBottom: 8
                }}>
                  Argument Tracker
                </h3>
                {claims.slice(-5).map((c, i) => (
                  <div key={i} style={{
                    padding: '8px 12px', marginBottom: 6, borderRadius: 6,
                    background: c.classification === 'DEFENDED' ? '#052e16'
                      : c.classification === 'CONCEDED' ? '#2d1010'
                        : '#1a1a2e',
                    borderLeft: `3px solid ${c.classification === 'DEFENDED' ? '#4ade80'
                      : c.classification === 'CONCEDED' ? '#e63946'
                        : '#60a5fa'}`
                  }}>
                    <div style={{
                      display: 'flex', justifyContent: 'space-between',
                      alignItems: 'center', marginBottom: 2
                    }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                        color: c.classification === 'DEFENDED' ? '#4ade80'
                          : c.classification === 'CONCEDED' ? '#e63946'
                            : '#60a5fa'
                      }}>
                        {c.classification}
                      </span>
                      <span style={{ fontSize: 10, color: '#888' }}>
                        Strength: {c.strength}/10
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: '#aaa', lineHeight: 1.4 }}>
                      {c.summary}
                    </p>
                  </div>
                ))}
              </div>
            )}
            {/* ── Consent toggle ── */}
            <div style={{
              marginTop: 24, padding: '12px 16px',
              background: '#111', border: '1px solid #222',
              borderRadius: 8, display: 'flex',
              alignItems: 'center', justifyContent: 'space-between', gap: 16
            }}>
              <div>
                <p style={{ margin: 0, fontSize: 13, color: '#ccc', fontWeight: 600 }}>
                  Share session data for research
                </p>
                <p style={{ margin: '2px 0 0', fontSize: 11, color: '#555', lineHeight: 1.4 }}>
                  Anonymized transcript and scores used for academic study only.
                  Off by default. You can change this any time before ending.
                </p>
              </div>
              <button
                onClick={handleConsentToggle}
                style={{
                  flexShrink: 0,
                  width: 44, height: 24, borderRadius: 12,
                  border: 'none', cursor: 'pointer',
                  background: consentGiven ? '#4ade80' : '#333',
                  position: 'relative', transition: 'background 0.2s'
                }}
              >
                <span style={{
                  position: 'absolute', top: 3,
                  left: consentGiven ? 22 : 3,
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'white', transition: 'left 0.2s'
                }} />
              </button>
            </div>
            <button onClick={togglePause} style={{
              marginTop: 16, marginRight: 8, padding: '10px 24px',
              background: isPaused ? '#4ade80' : '#555',
              color: isPaused ? '#000' : 'white',
              border: 'none', borderRadius: 8, fontSize: 15, cursor: 'pointer'
            }}>
              {isPaused ? 'Resume' : 'Pause'}
            </button>
            <button
              onClick={endDebate}
              style={{
                marginTop: 16, padding: '10px 24px', background: '#333',
                color: 'white', border: 'none', borderRadius: 8,
                fontSize: 15, cursor: 'pointer'
              }}
            >
              End Debate & Generate Evaluation
            </button>
          </div>
        )}

        {status === 'ended' && (
          <div>
            <p style={{ color: '#4ade80', marginBottom: 16 }}>Debate ended.</p>
            <div ref={reportRef}>

              {/* ── Judge Scorecard ── */}
              {judgeResult && (
                <div style={{ background: '#111', borderRadius: 10, border: '1px solid #222', padding: 24, marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <h3 style={{ fontSize: 12, color: '#555', textTransform: 'uppercase', letterSpacing: 1, margin: 0 }}>
                      Judge Scorecard
                    </h3>
                    <span style={{
                      padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 700,
                      background: judgeResult.winner === 'founder' ? '#052e16' : '#2d1010',
                      color: judgeResult.winner === 'founder' ? '#4ade80' : '#e63946'
                    }}>
                      {judgeResult.winner === 'founder' ? '🏆 Founder Wins' : '🤖 Agent Wins'}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
                    {Object.entries(judgeResult.scores).map(([dim, score]) => (
                      <div key={dim} style={{ background: '#1a1a1a', borderRadius: 6, padding: '8px 12px' }}>
                        <div style={{ fontSize: 10, color: '#555', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                          {dim.replace(/_/g, ' ')}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ flex: 1, height: 4, background: '#333', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{
                              width: `${score * 10}%`, height: '100%', borderRadius: 2,
                              background: score >= 7 ? '#4ade80' : score >= 4 ? '#f59e0b' : '#e63946',
                              transition: 'width 0.6s ease'
                            }} />
                          </div>
                          <span style={{ fontSize: 12, color: '#ccc', width: 20, textAlign: 'right' }}>{score}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{
                      width: 48, height: 48, borderRadius: '50%', flexShrink: 0,
                      background: judgeResult.overall >= 7 ? '#052e16' : judgeResult.overall >= 4 ? '#1a1a2e' : '#2d1010',
                      border: `2px solid ${judgeResult.overall >= 7 ? '#4ade80' : judgeResult.overall >= 4 ? '#60a5fa' : '#e63946'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 16, fontWeight: 700,
                      color: judgeResult.overall >= 7 ? '#4ade80' : judgeResult.overall >= 4 ? '#60a5fa' : '#e63946'
                    }}>
                      {judgeResult.overall}
                    </div>
                    <p style={{ color: '#888', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                      {judgeResult.summary}
                    </p>
                  </div>
                </div>
              )}

              {/* ── Debate Report ── */}
              {report ? (
                <div style={{ background: '#111', borderRadius: 10, border: '1px solid #222', padding: 24 }}>

                  {/* Idea summary */}
                  {report.idea_summary && (
                    <div style={{ background: '#0a0a0a', border: '1px solid #222', borderRadius: 8, padding: 12, marginBottom: 20 }}>
                      <h3 style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                        Idea (as debated)
                      </h3>
                      <p style={{ color: '#bbb', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                        {report.idea_summary}
                      </p>
                    </div>
                  )}

                  {/* Score + verdict */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
                    <div style={{
                      width: 64, height: 64, borderRadius: '50%', flexShrink: 0,
                      background: report.overall_score >= 7 ? '#052e16' : report.overall_score >= 4 ? '#1a1a2e' : '#2d1010',
                      border: `2px solid ${report.overall_score >= 7 ? '#4ade80' : report.overall_score >= 4 ? '#60a5fa' : '#e63946'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 22, fontWeight: 700,
                      color: report.overall_score >= 7 ? '#4ade80' : report.overall_score >= 4 ? '#60a5fa' : '#e63946'
                    }}>
                      {report.overall_score}
                    </div>
                    <p style={{ color: '#ccc', fontSize: 15, lineHeight: 1.5, margin: 0 }}>
                      {report.verdict}
                    </p>
                  </div>

                  {/* Strengths */}
                  <div style={{ marginBottom: 16 }}>
                    <h3 style={{ fontSize: 11, color: '#4ade80', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
                      Strengths
                    </h3>
                    {report.strengths.map((s, i) => (
                      <p key={i} style={{ color: '#aaa', fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>
                        ✓ {s}
                      </p>
                    ))}
                  </div>

                  {/* Weaknesses */}
                  <div style={{ marginBottom: 16 }}>
                    <h3 style={{ fontSize: 11, color: '#e63946', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
                      Weaknesses
                    </h3>
                    {report.weaknesses.map((w, i) => (
                      <p key={i} style={{ color: '#aaa', fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>
                        ✗ {w}
                      </p>
                    ))}
                  </div>

                  {/* Sharpest moment + biggest gap */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                    <div style={{ background: '#1a1a1a', borderRadius: 8, padding: 12 }}>
                      <h3 style={{ fontSize: 10, color: '#60a5fa', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                        Best Moment
                      </h3>
                      <p style={{ color: '#aaa', fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                        {report.sharpest_moment}
                      </p>
                    </div>
                    <div style={{ background: '#1a1a1a', borderRadius: 8, padding: 12 }}>
                      <h3 style={{ fontSize: 10, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                        Biggest Gap
                      </h3>
                      <p style={{ color: '#aaa', fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                        {report.biggest_gap}
                      </p>
                    </div>
                  </div>

                  {/* Recommendation */}
                  <div style={{ background: '#0f1f0f', border: '1px solid #1a3a1a', borderRadius: 8, padding: 12 }}>
                    <h3 style={{ fontSize: 10, color: '#4ade80', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                      Next Steps
                    </h3>
                    <p style={{ color: '#aaa', fontSize: 13, lineHeight: 1.5, margin: 0 }}>
                      {report.recommendation}
                    </p>
                  </div>
                </div>
              ) : (
                <p style={{ color: '#555', fontSize: 13 }}>Generating report...</p>
              )}
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
              {(judgeResult || report) && (
                <button
                  onClick={exportToPDF}
                  style={{
                    padding: '10px 24px', background: '#1a1a2e',
                    color: '#60a5fa', border: '1px solid #60a5fa',
                    borderRadius: 8, fontSize: 15, cursor: 'pointer'
                  }}
                >
                  Export PDF
                </button>
              )}
              <button
                onClick={() => { setStatus('idle'); setClaim(''); setReport(null); setJudgeResult(null) }}
                style={{
                  padding: '10px 24px', background: '#4d4d4dc2',
                  color: 'white', border: 'none', borderRadius: 8,
                  fontSize: 15, cursor: 'pointer'
                }}
              >
                Start New Debate
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Right: transcript panel ── */}
      <div style={{
        width: 340, flexShrink: 0,
        background: '#111', borderRadius: 10,
        border: '1px solid #222', padding: 16,
        height: 'calc(100vh - 80px)',
        display: 'flex', flexDirection: 'column'
      }}>
        <h2 style={{ fontSize: 14, color: '#555', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          Transcript
        </h2>
        <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {transcript.length === 0 && Object.values(partials).every(v => !v) ? (
            <p style={{ color: '#444', fontSize: 14 }}>Transcript will appear here...</p>
          ) : (
            <>
              {transcript.map((t, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <span style={{
                    color: t.speaker === 'agent' ? '#e63946'
                      : t.speaker === 'user' ? '#4ade80'
                        : '#555',
                    fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5
                  }}>
                    {t.speaker === 'agent' ? "Devil's Advocate"
                      : t.speaker === 'user' ? 'You'
                        : '🧠 Reasoning'}
                  </span>
                  <p style={{
                    margin: '4px 0 0', lineHeight: 1.6, fontSize: 14,
                    color: t.speaker === 'reasoning' ? '#555' : '#ccc',
                    fontStyle: t.speaker === 'reasoning' ? 'italic' : 'normal'
                  }}>
                    {t.text}
                  </p>
                </div>
              ))}
              {/* Live partials — dimmed with cursor */}
              {Object.entries(partials).map(([speaker, text]) =>
                text ? (
                  <div key={`partial-${speaker}`} style={{ marginBottom: 16, opacity: 0.55 }}>
                    <span style={{
                      color: speaker === 'agent' ? '#e63946' : '#4ade80',
                      fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5
                    }}>
                      {speaker === 'agent' ? "Devil's Advocate" : 'You'}
                    </span>
                    <p style={{ margin: '4px 0 0', lineHeight: 1.6, fontSize: 14, color: '#ccc' }}>
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