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
        with open(filepath, encoding='utf-8', errors='ignore') as f:
            text = f.read()
        words = text.split()
        chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 250)]
        for chunk in chunks:
            clean = chunk.encode('utf-8', errors='ignore').decode('utf-8').replace('\x00', '').strip()
            if clean:
                _BASE_CHUNKS.append(clean)
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

        all_texts = _BASE_CHUNKS + texts
        all_metas = _BASE_METAS + metadatas
        all_ids = [f"base_{i}" for i in range(len(_BASE_CHUNKS))] + \
                [f"user_{i}" for i in range(len(texts))]

        clean = []
        clean_metas = []
        clean_ids = []

        for t, m, i in zip(all_texts, all_metas, all_ids):
            try:
                # Force a clean native Python str through encode/decode
                # This strips null bytes and fixes any str subclass issues
                clean_t = t.encode('utf-8', errors='ignore').decode('utf-8').replace('\x00', '').strip()
                if clean_t:
                    clean.append(clean_t)
                    clean_metas.append(m)
                    clean_ids.append(i)
            except Exception as e:
                print(f"[Chroma] Skipping bad doc id={i}: {e}")
                continue

        if not clean:
            print("[Chroma] No valid documents after cleaning — skipping upsert")
            return

        print(f"[Chroma] Upserting {len(clean)} docs")
        collection.upsert(
            documents=clean,
            ids=clean_ids,
            metadatas=clean_metas
        )

    def retrieve(self, participant_id: str, query: str, n_results: int = 3) -> str:
        collection = self._get_collection(participant_id)
        results = collection.query(query_texts=[query], n_results=n_results)
        chunks = results.get("documents", [[]])[0]
        return "\n\n".join(chunks) if chunks else ""

    def delete_participant(self, participant_id: str) -> None:
        try:
            _client.delete_collection(f"participant_{participant_id}")
        except Exception as e:
            print(f"RAG delete_participant error: {e}")
            # Force-create a fresh empty collection to prevent stale data leaking
            try:
                _client.get_or_create_collection(f"participant_{participant_id}")
                _client.delete_collection(f"participant_{participant_id}")
            except Exception as e2:
                print(f"RAG delete_participant error (fallback): {e2}")
                pass 
