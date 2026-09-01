from dataclasses import dataclass

from apps.ai.generation import get_generation_provider
from apps.ai.providers.base import AIProvider
from apps.retrieval.services import RetrievalResult, RetrievalService

SYSTEM_PROMPT = (
    "You are a document question-answering assistant.\n\n"
    "Answer the user's question using only the provided context.\n\n"
    "If the context does not contain enough information to answer the question, "
    "say that the information is not available in the provided documents.\n\n"
    "Do not invent facts."
)


@dataclass
class RAGResult:
    answer: str
    retrieval_results: list[RetrievalResult]


class RAGService:

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        ai_provider: AIProvider | None = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.ai_provider = ai_provider or get_generation_provider()

    def ask(self, question: str) -> RAGResult:
        results = self.retrieval_service.search(question)
        context = self._build_context(results)
        prompt = self._build_prompt(context, question)
        answer = self.ai_provider.generate(prompt)
        return RAGResult(answer=answer, retrieval_results=results)

    def _build_context(self, results: list[RetrievalResult]) -> str:
        if not results:
            return ""
        blocks = []
        for r in results:
            blocks.append(
                f"[Source: {r.source}, Page: {r.page}]\n{r.content}"
            )
        return "\n\n".join(blocks)

    def _build_prompt(self, context: str, question: str) -> str:
        return f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion:\n{question}"
