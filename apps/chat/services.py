from dataclasses import dataclass, field

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
class Citation:
    source: str
    page: int


@dataclass
class RAGResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieval_results: list[RetrievalResult] = field(default_factory=list)


def build_citations(results: list[RetrievalResult]) -> list[Citation]:
    seen: set[tuple[str, int]] = set()
    citations: list[Citation] = []
    for r in results:
        key = (r.source, r.page)
        if key not in seen:
            seen.add(key)
            citations.append(Citation(source=r.source, page=r.page))
    return citations


class RAGService:

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        ai_provider: AIProvider | None = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.ai_provider = ai_provider or get_generation_provider()

    def ask(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> RAGResult:
        results = self.retrieval_service.search(question)
        context = self._build_context(results)
        prompt = self._build_prompt(context, question, history)
        answer = self.ai_provider.generate(prompt)
        citations = build_citations(results)
        return RAGResult(answer=answer, citations=citations, retrieval_results=results)

    def _build_context(self, results: list[RetrievalResult]) -> str:
        if not results:
            return ""
        blocks = []
        for r in results:
            blocks.append(
                f"[Source: {r.source}, Page: {r.page}]\n{r.content}"
            )
        return "\n\n".join(blocks)

    def _build_history_block(self, history: list[dict]) -> str:
        lines = []
        for msg in history:
            role = msg["role"].capitalize()
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _build_prompt(
        self,
        context: str,
        question: str,
        history: list[dict] | None = None,
    ) -> str:
        parts = [SYSTEM_PROMPT]
        if history:
            parts.append(f"Conversation history:\n{self._build_history_block(history)}")
        parts.append(f"Context:\n{context}")
        parts.append(f"Question:\n{question}")
        return "\n\n".join(parts)
