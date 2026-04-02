import { useState, useEffect } from 'react'
import { ref, uploadBytesResumable, deleteObject, listAll, getMetadata } from 'firebase/storage'
import { storage } from './firebase'

export function useDocumentUpload(user, isDebating) {
    const [uploadedFiles, setUploadedFiles] = useState([])
    const [uploading, setUploading] = useState(false)
    const [loadingFiles, setLoadingFiles] = useState(false)

    // Load existing files whenever user changes
    useEffect(() => {
        if (!user) return
        async function loadExistingFiles() {
            setLoadingFiles(true)
            try {
                const folderRef = ref(storage, `users/${user.uid}/documents/`)
                const list = await listAll(folderRef)

                const files = await Promise.all(
                    list.items
                        // Filter out general knowledge base docs
                        .filter(item => !item.name.includes('GENERALDOCAUTO_'))
                        .map(async (item) => {
                            const meta = await getMetadata(item)
                            const filename = item.name.split('_').slice(1).join('_') || item.name
                            return { name: filename, path: item.fullPath, size: meta.size }
                        })
                )
                setUploadedFiles(files)
            } catch {
                // Folder doesn't exist yet — fine
            } finally {
                setLoadingFiles(false)
            }
        }

        loadExistingFiles()
    }, [user])

    async function uploadFile(file) {
        if (!user || isDebating) return
        if (!['application/pdf', 'text/plain'].includes(file.type)) {
            alert('Only PDF and .txt files are supported')
            return
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('File must be under 10MB')
            return
        }

        setUploading(true)
        const path = `users/${user.uid}/documents/${Date.now()}_${file.name}`
        const storageRef = ref(storage, path)

        try {
            await uploadBytesResumable(storageRef, file)
            setUploadedFiles(prev => [...prev, { name: file.name, path, size: file.size }])
        } catch (err) {
            console.error('Upload error:', err)
            alert('Upload failed')
        } finally {
            setUploading(false)
        }
    }

    async function removeFile(filePath) {
        if (isDebating) return
        try {
            await deleteObject(ref(storage, filePath))
            setUploadedFiles(prev => prev.filter(f => f.path !== filePath))
        } catch (error) {
            console.error('Delete error:', error)
        }
    }

    async function clearAllFiles() {
        if (!user || isDebating) return
        try {
            const folderRef = ref(storage, `users/${user.uid}/documents/`)
            const list = await listAll(folderRef)
            await Promise.all(list.items.map(item => deleteObject(item)))
            setUploadedFiles([])
        } catch {
            // Fine
        }
    }

    return { uploadedFiles, uploading, loadingFiles, uploadFile, removeFile, clearAllFiles }
}
