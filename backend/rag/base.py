from abc import ABC, abstractmethod

class RAGBackend(ABC):

    @abstractmethod
    def ingest_documents(self, participant_id: str, texts: list[str], metadatas: list[dict]) -> None:
        """Index documents for a participant."""
        pass

    @abstractmethod
    def retrieve(self, participant_id: str, query: str, n_results: int = 3) -> str:
        """Return top-n relevant chunks as a single string."""
        pass

    @abstractmethod
    def delete_participant(self, participant_id: str) -> None:
        """Clean up a participant's corpus — call at session end."""
        pass