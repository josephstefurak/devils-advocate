import { initializeApp } from 'firebase/app'
import { getAuth, signInAnonymously, signInWithPopup, GoogleAuthProvider, GithubAuthProvider, onAuthStateChanged, signOut } from 'firebase/auth'
import { getStorage, ref, uploadBytesResumable, deleteObject, listAll, getMetadata } from 'firebase/storage'
import { getAnalytics } from 'firebase/analytics'


const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
    measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
}

const app = initializeApp(firebaseConfig)

export const auth = getAuth(app)
export const storage = getStorage(app)
export const analytics = getAnalytics(app)
export const googleProvider = new GoogleAuthProvider()
export const githubProvider = new GithubAuthProvider()
export { ref, uploadBytesResumable, deleteObject, listAll, getMetadata }

export { signInAnonymously, signInWithPopup, onAuthStateChanged, signOut }