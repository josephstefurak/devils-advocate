import { useState, useRef } from 'react'
import { io } from 'socket.io-client'
import { colors, font } from '../theme'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const LETTER_PX = { w: 612, h: 792 }
const PDF_TITLE_PAGE_LINK = 'https://devils-advocate-488918.web.app/'

/**
 * useDebateSession
 *
 * Owns all socket, audio, and session state.
 * App.jsx should call this once and destructure what it needs.
 *
 * Returns:
 *   -- State --
 *   status          'idle' | 'connecting' | 'debating' | 'ended'
 *   transcript      { speaker, text }[]
 *   partials        { [speaker]: string }  (live streaming text)
 *   claims          { classification, summary, strength }[]
 *   report          post-debate report object or null
 *   judgeResult     judge scorecard object or null
 *   isAgentSpeaking boolean
 *   isPaused        boolean
 *   consentGiven    boolean
 *
 *   -- Actions --
 *   startDebate(claim, user, uploadedFiles)
 *   endDebate()
 *   togglePause()
 *   handleConsentToggle()
 *   resetSession()
 *   exportToPDF(reportRef)
 */
export function useDebateSession() {
    // ── State ──────────────────────────────────────────────────────
    const [status, setStatus] = useState('idle')
    const [transcript, setTranscript] = useState([])
    const [partials, setPartials] = useState({})
    const [claims, setClaims] = useState([])
    const [report, setReport] = useState(null)
    const [judgeResult, setJudgeResult] = useState(null)
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
    const [isPaused, setIsPaused] = useState(false)
    const [consentGiven, setConsentGiven] = useState(true)
    const [sessionStatus, setSessionStatus] = useState('')
    const [micVolume, setMicVolume] = useState(0)  // 0-1 float
    const [reportReady, setReportReady] = useState(false)

    // ── Refs ───────────────────────────────────────────────────────
    const socketRef = useRef(null)
    const audioContextRef = useRef(null)
    const micContextRef = useRef(null)
    const streamRef = useRef(null)
    const nextAudioTimeRef = useRef(0)
    const isAgentSpeakingRef = useRef(false)
    const micStartedRef = useRef(false)
    const speakingTimerRef = useRef(null)
    const isPausedRef = useRef(false)
    const activeSourcesRef = useRef([])
    const micVolumeRef = useRef(0)
    const preserveIdleOnDisconnectRef = useRef(false)

    function resetLiveState() {
        micStartedRef.current = false
        isPausedRef.current = false
        setIsPaused(false)
        setMicVolume(0)
        micVolumeRef.current = 0
        interruptAgent()

        if (speakingTimerRef.current) {
            clearTimeout(speakingTimerRef.current)
            speakingTimerRef.current = null
        }

        streamRef.current?.getTracks().forEach(t => t.stop())
        streamRef.current = null

        if (audioContextRef.current) {
            audioContextRef.current.close()
            audioContextRef.current = null
        }

        if (micContextRef.current) {
            micContextRef.current.close()
            micContextRef.current = null
        }
    }

    function disconnectSocket({ preserveIdle = false } = {}) {
        if (!socketRef.current) return
        preserveIdleOnDisconnectRef.current = preserveIdle
        socketRef.current.disconnect()
        socketRef.current = null
    }

    // ── Socket setup ───────────────────────────────────────────────
    function connectSocket() {
        socketRef.current = io(BACKEND_URL, {
            transports: ['websocket'],
        })

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
            if (!val) nextAudioTimeRef.current = 0
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
            resetLiveState()
            if (preserveIdleOnDisconnectRef.current) {
                preserveIdleOnDisconnectRef.current = false
                return
            }
            setStatus('ended')
        })

        socketRef.current.on('debate_report', (data) => {
            setReport(data)  // null is fine, UI handles it
            setReportReady(true)
            setStatus('ended')
            resetLiveState()
        })

        socketRef.current.on('agent_interrupted', () => {
            interruptAgent()
        })

        socketRef.current.on('error', ({ message }) => {
            console.error('Server error:', message)
            alert(message)
        })

        socketRef.current.on('session_status', ({ step }) => {
            setSessionStatus(step)
        })

    }

    // ── Start / End ────────────────────────────────────────────────
    async function startDebate(claim, user, uploadedFiles) {
        if (!audioContextRef.current) {
            audioContextRef.current = new AudioContext({ sampleRate: 24000 })
        }
        await audioContextRef.current.resume()

        setStatus('connecting')
        setReport(null)
        setTranscript([])
        setPartials({})
        setClaims([])
        setReportReady(false)
        setConsentGiven(true)
        setJudgeResult(null)
        micStartedRef.current = false
        activeSourcesRef.current = []

        connectSocket()

        const idToken = await user.getIdToken()
        socketRef.current.emit('start_session', {
            claim,
            idToken,
            isAnonymous: user.isAnonymous,
            documentPaths: uploadedFiles.map(f => f.path),
        })
    }

    function endDebate() {
        setStatus('ended')
        resetLiveState()
        socketRef.current?.emit('end_session')
    }

    function resetSession() {
        resetLiveState()
        disconnectSocket({ preserveIdle: true })
        setStatus('idle')
        setReport(null)
        setReportReady(false)
        setJudgeResult(null)
        setTranscript([])
        setPartials({})
        setClaims([])
        setSessionStatus('')
        setConsentGiven(true)
    }

    // ── Pause / Consent ────────────────────────────────────────────
    function togglePause() {
        const newVal = !isPausedRef.current
        isPausedRef.current = newVal
        setIsPaused(newVal)
        if (newVal) interruptAgent()
    }

    function handleConsentToggle() {
        const newVal = !consentGiven
        setConsentGiven(newVal)
        socketRef.current?.emit('set_consent', { consent: newVal })
    }

    // ── Mic capture ────────────────────────────────────────────────
    async function startMicCapture() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
            })
            streamRef.current = stream

            micContextRef.current = new AudioContext({ sampleRate: 16000 })
            const micContext = micContextRef.current

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
                    // Compute RMS volume for visualizer
                    const pcm = new Int16Array(e.data)
                    let sum = 0
                    for (let i = 0; i < pcm.length; i++) sum += (pcm[i] / 32768) ** 2
                    const rms = Math.sqrt(sum / pcm.length)
                    micVolumeRef.current = rms
                    setMicVolume(rms)
                }
            }

            source.connect(workletNode)
            workletNode.connect(micContext.destination)
        } catch (err) {
            console.error('Mic error:', err)
            alert('Microphone access denied')
        }
    }

    // ── Audio playback ─────────────────────────────────────────────
    function playAudioChunk(base64Audio) {
        const ctx = audioContextRef.current
        if (!ctx) return

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

        const startTime = Math.max(ctx.currentTime, nextAudioTimeRef.current)
        source.start(startTime)
        nextAudioTimeRef.current = startTime + buffer.duration

        activeSourcesRef.current.push(source)
        source.onended = () => {
            activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source)
        }

        isAgentSpeakingRef.current = true
        setIsAgentSpeaking(true)

        if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
        const endDelay = (nextAudioTimeRef.current - ctx.currentTime + 0.3) * 1000
        speakingTimerRef.current = setTimeout(() => {
            isAgentSpeakingRef.current = false
            setIsAgentSpeaking(false)
            nextAudioTimeRef.current = 0
        }, endDelay)
    }

    function interruptAgent() {
        activeSourcesRef.current.forEach(source => {
            try { source.stop() } catch { }
        })
        activeSourcesRef.current = []
        nextAudioTimeRef.current = 0
        if (speakingTimerRef.current) clearTimeout(speakingTimerRef.current)
        isAgentSpeakingRef.current = false
        setIsAgentSpeaking(false)
    }

    // ── PDF export ─────────────────────────────────────────────────
    async function exportToPDF(reportRef, { report, claim } = {}) {
        if (!reportRef?.current) return
        const { default: jsPDF } = await import('jspdf')
        const { default: html2canvas } = await import('html2canvas')

        const pdf = new jsPDF({ orientation: 'portrait', unit: 'px', format: 'letter' })
        const pageWidth = pdf.internal.pageSize.getWidth()
        const pageHeight = pdf.internal.pageSize.getHeight()

        // Title page (page 1) when report is available — render as HTML so it uses site fonts
        if (report) {
            const dateStr = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
            const titleEl = document.createElement('div')
            titleEl.setAttribute('data-pdf-title-page', '')
            Object.assign(titleEl.style, {
                position: 'fixed',
                left: '-9999px',
                top: '0',
                width: `${LETTER_PX.w}px`,
                height: `${LETTER_PX.h}px`,
                background: colors.bgDark,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '80px 48px',
                boxSizing: 'border-box',
                fontFamily: "'Georgia', 'Times New Roman', serif",
            })
            titleEl.innerHTML = `
                <div style="
                    font-family: 'Bebas Neue', Georgia, serif;
                    font-size: 42px;
                    letter-spacing: 2px;
                    color: ${colors.accent};
                    margin-bottom: 16px;
                    text-align: center;
                ">DEVIL'S ADVOCATE</div>
                <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 12px;
                    letter-spacing: 2px;
                    color: ${colors.textFaint};
                    text-transform: uppercase;
                    margin-bottom: 72px;
                ">Pitch Defense Report</div>
                <div style="
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 11px;
                    color: ${colors.textDim};
                    margin-bottom: 48px;
                ">${dateStr}</div>
                <div style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 10px;
                        letter-spacing: 1px;
                        color: ${colors.textFaint};
                    ">For more info:</span>
                    <a href="${PDF_TITLE_PAGE_LINK}" style="
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 11px;
                        color: ${colors.accent};
                        text-decoration: none;
                        letter-spacing: 1px;
                    ">${PDF_TITLE_PAGE_LINK}</a>
                </div>
            `
            document.body.appendChild(titleEl)
            const titleCanvas = await html2canvas(titleEl, {
                backgroundColor: colors.bgDark,
                scale: 2,
                useCORS: true,
                logging: false,
            })
            document.body.removeChild(titleEl)
            const titleImg = titleCanvas.toDataURL('image/png')
            const titlePdfH = titleCanvas.height * (pageWidth / titleCanvas.width)
            pdf.addImage(titleImg, 'PNG', 0, 0, pageWidth, titlePdfH)
            pdf.addPage()
        }

        const container = reportRef.current

        // Hide elements not meant for PDF first, so layout reflects the exported state
        const hiddenEls = Array.from(container.querySelectorAll('[data-pdf-hide]'))
        hiddenEls.forEach(el => el.style.display = 'none')

        // Measure forced break positions after hiding, so they match the canvas
        const containerRect = container.getBoundingClientRect()
        const forcedBreaksDom = Array.from(container.querySelectorAll('[data-pdf-page-break]'))
            .map(el => el.getBoundingClientRect().top - containerRect.top)
            .filter(pos => pos > 0)
            .sort((a, b) => a - b)

        const canvas = await html2canvas(container, {
            backgroundColor: '#0d0d0d',
            scale: 2,
            useCORS: true,
            logging: false,
        })

        hiddenEls.forEach(el => el.style.display = '')

        const domToCanvas = canvas.width / container.offsetWidth
        const scaledPageH = pageHeight * (canvas.width / pageWidth)

        const forcedBreaks = forcedBreaksDom
            .map(pos => pos * domToCanvas)
            .filter(pos => pos < canvas.height)

        const breakPoints = []
        let cursor = 0
        let forcedIdx = 0

        while (cursor + scaledPageH < canvas.height) {
            if (forcedIdx < forcedBreaks.length && forcedBreaks[forcedIdx] <= cursor + scaledPageH) {
                breakPoints.push(forcedBreaks[forcedIdx])
                cursor = forcedBreaks[forcedIdx]
                forcedIdx++
            } else {
                breakPoints.push(cursor + scaledPageH)
                cursor += scaledPageH
            }
        }

        // Render each page slice onto a temporary canvas and add to PDF
        const slices = [0, ...breakPoints, canvas.height]
        for (let i = 0; i < slices.length - 1; i++) {
            const sliceTop = slices[i]
            const sliceH = slices[i + 1] - sliceTop

            const tmpCanvas = document.createElement('canvas')
            tmpCanvas.width = canvas.width
            tmpCanvas.height = sliceH
            tmpCanvas.getContext('2d').drawImage(
                canvas, 0, sliceTop, canvas.width, sliceH, 0, 0, canvas.width, sliceH
            )

            const sliceImg = tmpCanvas.toDataURL('image/png')
            const slicePdfH = sliceH * (pageWidth / canvas.width)

            if (i > 0) pdf.addPage()
            pdf.setFillColor(13, 13, 13)
            pdf.rect(0, 0, pageWidth, pageHeight, 'F')
            pdf.addImage(sliceImg, 'PNG', 0, 0, pageWidth, slicePdfH)
        }

        pdf.save(`devils-advocate-${new Date().toISOString().slice(0, 10)}.pdf`)
    }

    return {
        // state
        status,
        transcript,
        partials,
        claims,
        report,
        judgeResult,
        isAgentSpeaking,
        isPaused,
        consentGiven,
        sessionStatus,
        micVolume,
        reportReady,
        // actions
        startDebate,
        endDebate,
        resetSession,
        togglePause,
        handleConsentToggle,
        exportToPDF,

    }
}
