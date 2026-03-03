import { useState, useRef, useEffect } from 'react'
import { io } from 'socket.io-client'

const BACKEND_URL = 'http://localhost:8000'

export default function App() {
  const [status, setStatus] = useState('idle')       // idle | connecting | debating | ended
  const [transcript, setTranscript] = useState([])   // { speaker, text }[]
  const [claim, setClaim] = useState('')
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
  const [partials, setPartials] = useState({})        // { speaker: accumulated_text }
  const [claims, setClaims] = useState([]) // { classification, summary, strength }[]

  const socketRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioContextRef = useRef(null)
  const streamRef = useRef(null)
  const nextAudioTimeRef = useRef(0)
  const isAgentSpeakingRef = useRef(false)
  const micStartedRef = useRef(false)
  const speakingTimerRef = useRef(null)

  const audioQueueRef = useRef([])
  const isProcessingAudioRef = useRef(false)

  const transcriptEndRef = useRef(null)

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

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
  }

  // ── Start a debate session ──────────────────────────────────────
  async function startDebate() {
    if (!claim.trim()) return alert('Enter your position first')
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext({ sampleRate: 24000 })
    }
    await audioContextRef.current.resume()
    setStatus('connecting')
    setTranscript([])
    setPartials({})
    connectSocket()
    socketRef.current.emit('start_session', { claim })
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
        if (!isAgentSpeakingRef.current) {  // don't send while agent speaks
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

  // ── Play audio response from agent ─────────────────────────────
  /*
  async function playAudioChunk(base64Audio) {
    const ctx = audioContextRef.current
    if (!ctx) return

    isAgentSpeakingRef.current = true
    setIsAgentSpeaking(true)

    // Clear any pending "speaking done" timer
    if (speakingTimerRef.current) {
      clearTimeout(speakingTimerRef.current)
    }

    const response = await fetch(`data:application/octet-stream;base64,${base64Audio}`)
    const arrayBuffer = await response.arrayBuffer()

    const samples = arrayBuffer.byteLength / 2
    const float32 = new Float32Array(samples)
    const view = new DataView(arrayBuffer)
    for (let i = 0; i < samples; i++) {
      float32[i] = view.getInt16(i * 2, true) / 32768.0
    }

    const buffer = ctx.createBuffer(1, samples, 24000)
    buffer.copyToChannel(float32, 0)
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)

    const startTime = Math.max(ctx.currentTime, nextAudioTimeRef.current)
    source.start(startTime)
    nextAudioTimeRef.current = startTime + buffer.duration

    // After 500ms of no new chunks arriving, mark speaking as done
    const endDelay = (nextAudioTimeRef.current - ctx.currentTime + 0.5) * 1000
    speakingTimerRef.current = setTimeout(() => {
      isAgentSpeakingRef.current = false
      setIsAgentSpeaking(false)
      nextAudioTimeRef.current = 0
    }, endDelay)
  }
  */


  function playAudioChunk(base64Audio) {
    audioQueueRef.current.push(base64Audio)
    if (!isProcessingAudioRef.current) processAudioQueue()
  }


  async function processAudioQueue() {
    isProcessingAudioRef.current = true
    while (audioQueueRef.current.length > 0) {
      const base64Audio = audioQueueRef.current.shift()
      await processAndPlayChunk(base64Audio)
    }
    isProcessingAudioRef.current = false
    // All chunks done — open mic
    if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
    isAgentSpeakingRef.current = false
    setIsAgentSpeaking(false)
    nextAudioTimeRef.current = 0
  }

  async function processAndPlayChunk(base64Audio) {
    const ctx = audioContextRef.current
    if (!ctx) return

    isAgentSpeakingRef.current = true
    setIsAgentSpeaking(true)

    // Direct decode — avoids fetch/blob corruption
    const binary = atob(base64Audio)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)

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

    const startTime = Math.max(ctx.currentTime, nextAudioTimeRef.current)
    source.start(startTime)
    nextAudioTimeRef.current = startTime + buffer.duration

    await new Promise(resolve => {
      source.onended = resolve
      setTimeout(resolve, (buffer.duration + 0.1) * 1000)
    })
  }

  // ── End session ─────────────────────────────────────────────────
  function endDebate() {
    setStatus('ended')
    micStartedRef.current = false
    if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    socketRef.current?.emit('end_session')
    socketRef.current?.disconnect()
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
  return (
    <div style={{ display: 'flex', gap: 24, maxWidth: 1100, margin: '40px auto', padding: '0 20px' }}>

      {/* ── Left: main UI ── */}
      <div style={{ flex: 1 }}>
        <h1 style={{ fontSize: 28, marginBottom: 8 }}>Devil's Advocate</h1>
        <p style={{ color: '#888', marginBottom: 32 }}>
          State your business idea. The agent will argue against it.
        </p>

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
            <button
              onClick={endDebate}
              style={{
                marginTop: 16, padding: '10px 24px', background: '#333',
                color: 'white', border: 'none', borderRadius: 8,
                fontSize: 15, cursor: 'pointer'
              }}
            >
              End Debate
            </button>
          </div>
        )}

        {status === 'ended' && (
          <div>
            <p style={{ color: '#4ade80' }}>Debate ended.</p>
            <button
              onClick={() => { setStatus('idle'); setClaim('') }}
              style={{
                padding: '10px 24px', background: '#333',
                color: 'white', border: 'none',
                borderRadius: 8, fontSize: 15, cursor: 'pointer'
              }}
            >
              Start New Debate
            </button>
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