/**
 * uploadAudio.js
 *
 * Uploads a debate audio Blob to Firebase Storage under:
 *   sessions/{sessionId}/audio.{ext}
 *
 * Features:
 *   - Automatic MIME→extension mapping
 *   - Progress callback
 *   - Retry with exponential backoff (3 attempts)
 *   - Returns the Firebase Storage download URL on success
 *   - All errors propagate so callers can decide whether they're fatal
 *
 * The caller is responsible for consent gating — do not call this
 * unless consentGiven is true.
 */

import { ref, uploadBytesResumable, getDownloadURL } from 'firebase/storage'
import { storage } from '../firebase'  // adjust path if your firebase.js is elsewhere

// ── Config ────────────────────────────────────────────────────────

const MAX_RETRIES    = 3
const BASE_DELAY_MS  = 1_500  // doubles on each retry: 1.5s, 3s, 6s

// ── Public API ────────────────────────────────────────────────────

/**
 * uploadAudioToStorage(sessionId, blob, options?)
 *
 * @param {string}   sessionId          Firestore session document ID
 * @param {Blob}     blob               Audio blob from useAudioRecorder.stopRecording()
 * @param {object}   [options]
 * @param {function} [options.onProgress]  (0–100: number) → void  — upload progress
 *
 * @returns {Promise<string>}  Firebase Storage download URL
 * @throws  {Error}            After MAX_RETRIES failed attempts
 */
export async function uploadAudioToStorage(sessionId, blob, { onProgress } = {}) {
    if (!sessionId) {
        throw new Error('[uploadAudio] sessionId is required')
    }
    if (!blob || blob.size === 0) {
        throw new Error('[uploadAudio] Blob is empty — nothing to upload')
    }

    const ext        = mimeToExt(blob.type)
    const storagePath = `sessions/${sessionId}/audio.${ext}`
    const storageRef = ref(storage, storagePath)

    console.log(`[uploadAudio] Starting upload → ${storagePath} (${(blob.size / 1024).toFixed(1)} KB)`)

    let lastError

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        try {
            const downloadURL = await attemptUpload(storageRef, blob, onProgress)
            console.log(`[uploadAudio] Upload complete on attempt ${attempt}. URL: ${downloadURL}`)
            return downloadURL
        } catch (err) {
            lastError = err
            const isRetryable = isRetryableError(err)
            console.warn(
                `[uploadAudio] Attempt ${attempt}/${MAX_RETRIES} failed` +
                ` (${isRetryable ? 'retrying' : 'non-retryable'}):`,
                err.message
            )
            if (!isRetryable || attempt === MAX_RETRIES) break
            await sleep(BASE_DELAY_MS * attempt)
        }
    }

    throw new Error(
        `[uploadAudio] Upload failed after ${MAX_RETRIES} attempts: ${lastError?.message}`
    )
}

// ── Internal helpers ──────────────────────────────────────────────

/**
 * Single upload attempt. Returns download URL on success, throws on failure.
 */
function attemptUpload(storageRef, blob, onProgress) {
    println(`[uploadAudio] Uploading to Firebase Storage...`)
    return new Promise((resolve, reject) => {
        const uploadTask = uploadBytesResumable(storageRef, blob, {
            contentType: blob.type || 'audio/webm',
        })

        uploadTask.on(
            'state_changed',
            (snapshot) => {
                if (onProgress && snapshot.totalBytes > 0) {
                    const pct = Math.round(
                        (snapshot.bytesTransferred / snapshot.totalBytes) * 100
                    )
                    try { onProgress(pct) } catch { /* callback errors must not break upload */ }
                }
            },
            (err) => {
                // Firebase Storage error object
                reject(err)
            },
            async () => {
                try {
                    const url = await getDownloadURL(uploadTask.snapshot.ref)
                    resolve(url)
                } catch (err) {
                    reject(new Error(`getDownloadURL failed: ${err.message}`))
                }
            }
        )
    })
}

/**
 * Determine whether a Firebase Storage error is worth retrying.
 * Non-retryable: auth errors, quota exceeded, object not found.
 * Retryable: network errors, unknown/server errors.
 */
function isRetryableError(err) {
    // Firebase Storage error codes: https://firebase.google.com/docs/storage/web/handle-errors
    const nonRetryableCodes = new Set([
        'storage/unauthorized',
        'storage/unauthenticated',
        'storage/quota-exceeded',
        'storage/invalid-argument',
        'storage/invalid-url',
        'storage/invalid-event-name',
        'storage/no-default-bucket',
        'storage/cannot-slice-blob',
    ])
    if (err?.code && nonRetryableCodes.has(err.code)) return false
    return true
}

function mimeToExt(mimeType) {
    if (!mimeType)                      return 'webm'
    if (mimeType.includes('ogg'))       return 'ogg'
    if (mimeType.includes('mp4'))       return 'mp4'
    if (mimeType.includes('wav'))       return 'wav'
    return 'webm'
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}
