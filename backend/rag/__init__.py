import os
from .base import RAGBackend

def get_backend() -> RAGBackend:
    backend = os.getenv("RAG_BACKEND", "chroma")

    if backend == "chroma":
        from .chroma_backend import ChromaBackend
        return ChromaBackend()

    if backend == "vertex":
        from .vertex_backend import VertexBackend  # wire in later
        return VertexBackend()

    raise ValueError(f"Unknown RAG_BACKEND: {backend}")

# Singleton — one backend instance for the lifetime of the process
rag = get_backend()