import { useState, useEffect } from 'react'
import {
    auth,
    googleProvider,
    githubProvider,
    signInAnonymously,
    signInWithPopup,
    onAuthStateChanged,
    signOut,
} from '../firebase'

/**
 * useAuth
 *
 * Handles Firebase auth lifecycle:
 * - Auto signs in anonymously if no user is present
 * - Exposes user, authReady, and sign-in/out actions
 *
 * Returns:
 *   user        — Firebase user object or null
 *   authReady   — true once the initial auth state has resolved
 *   signInWithGoogle
 *   signInWithGitHub
 *   handleSignOut
 */
export function useAuth() {
    const [user, setUser] = useState(null)
    const [authReady, setAuthReady] = useState(false)

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
            if (firebaseUser) {
                setUser(firebaseUser)
            } else {
                signInAnonymously(auth)
            }
            setAuthReady(true)
        })
        return () => unsubscribe()
    }, [])

    async function signInWithGoogle() {
        try {
            await signInWithPopup(auth, googleProvider)
        } catch (err) {
            console.error('Google sign-in error:', err)
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
        // onAuthStateChanged fires → triggers signInAnonymously again
    }

    return { user, authReady, signInWithGoogle, signInWithGitHub, handleSignOut }
}