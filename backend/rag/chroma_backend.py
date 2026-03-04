import os
import glob
import chromadb
from chromadb.utils import embedding_functions
from .base import RAGBackend

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")

embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# In-memory client — no disk, safe for Cloud Run
# Swap to PersistentClient("./chroma_db") for local dev if you want persistence
_client = chromadb.EphemeralClient()

# Load static knowledge base chunks once at startup
_BASE_CHUNKS: list[str] = []
_BASE_METAS: list[dict] = []

def _load_base_knowledge():
    global _BASE_CHUNKS, _BASE_METAS
    for filepath in glob.glob(os.path.join(KNOWLEDGE_DIR, "*.txt")):
        with open(filepath) as f:
            text = f.read()
        words = text.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 250)]
        for j, chunk in enumerate(chunks):
            if chunk.strip():
                _BASE_CHUNKS.append(chunk)
                _BASE_METAS.append({"source": os.path.basename(filepath), "type": "base"})
    print(f"[RAG] Loaded {len(_BASE_CHUNKS)} base knowledge chunks")

_load_base_knowledge()  # runs once on import


class ChromaBackend(RAGBackend):

    def _get_collection(self, participant_id: str):
        """Each participant gets an isolated collection."""
        return _client.get_or_create_collection(
            name=f"participant_{participant_id}",
            embedding_function=embedding_fn
        )

    def ingest_documents(self, participant_id: str, texts: list[str], metadatas: list[dict]) -> None:
        collection = self._get_collection(participant_id)

        # Always seed with base knowledge + participant-specific docs
        all_texts = _BASE_CHUNKS + texts
        all_metas = _BASE_METAS + metadatas
        all_ids = [f"base_{i}" for i in range(len(_BASE_CHUNKS))] + \
                  [f"user_{i}" for i in range(len(texts))]

        collection.upsert(documents=all_texts, ids=all_ids, metadatas=all_metas)

    def retrieve(self, participant_id: str, query: str, n_results: int = 3) -> str:
        collection = self._get_collection(participant_id)
        results = collection.query(query_texts=[query], n_results=n_results)
        chunks = results.get("documents", [[]])[0]
        return "\n\n".join(chunks) if chunks else ""

    def delete_participant(self, participant_id: str) -> None:
        try:
            _client.delete_collection(f"participant_{participant_id}")
        except Exception:
            pass