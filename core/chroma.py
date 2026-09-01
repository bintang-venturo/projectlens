import chromadb
from django.conf import settings

COLLECTION_NAME = "projectlens_documents"


class ChromaService:

    def __init__(self, client: chromadb.ClientAPI | None = None):
        self._client = client

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
        return self._client

    def get_collection(self):
        return self.client.get_or_create_collection(name=COLLECTION_NAME)

    def get_existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        collection = self.get_collection()
        result = collection.get(ids=ids, include=[])
        return set(result["ids"])

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        collection = self.get_collection()
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def delete_by_document(self, document_id: str) -> None:
        collection = self.get_collection()
        collection.delete(where={"document_id": document_id})
