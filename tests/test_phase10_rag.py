import pytest

from apps.ai.providers.base import AIProvider
from apps.chat.services import SYSTEM_PROMPT, RAGResult, RAGService
from apps.retrieval.services import RetrievalResult, RetrievalService


class FakeAIProvider(AIProvider):

    def __init__(self, response: str = "Fake answer"):
        self.response = response
        self.last_prompt = None
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        self.call_count += 1
        return self.response


class FakeRetrievalService(RetrievalService):

    def __init__(self, results: list[RetrievalResult] | None = None):
        self._results = results or []

    def search(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        return self._results


SAMPLE_RESULTS = [
    RetrievalResult(
        content="Each player starts with $1,500.",
        source="monopoly.pdf",
        page=4,
        score=0.95,
    ),
    RetrievalResult(
        content="Players take turns rolling two dice.",
        source="monopoly.pdf",
        page=5,
        score=0.88,
    ),
]


@pytest.mark.django_db
class TestRAGServiceAsk:

    def test_returns_rag_result(self):
        provider = FakeAIProvider(response="Each player starts with $1,500.")
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        result = service.ask("How much money do players start with?")
        assert isinstance(result, RAGResult)
        assert result.answer == "Each player starts with $1,500."

    def test_includes_retrieval_results(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        result = service.ask("question")
        assert result.retrieval_results == SAMPLE_RESULTS

    def test_ai_provider_called_once(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("question")
        assert provider.call_count == 1

    def test_prompt_contains_system_instruction(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("How much money?")
        assert SYSTEM_PROMPT in provider.last_prompt

    def test_prompt_contains_question(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("How much money?")
        assert "How much money?" in provider.last_prompt

    def test_prompt_contains_context_from_chunks(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("question")
        assert "Each player starts with $1,500." in provider.last_prompt
        assert "Players take turns rolling two dice." in provider.last_prompt

    def test_prompt_contains_source_metadata(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("question")
        assert "[Source: monopoly.pdf, Page: 4]" in provider.last_prompt
        assert "[Source: monopoly.pdf, Page: 5]" in provider.last_prompt

    def test_prompt_instructs_not_to_invent(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("question")
        assert "Do not invent facts" in provider.last_prompt

    def test_prompt_instructs_only_use_context(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(SAMPLE_RESULTS),
            ai_provider=provider,
        )
        service.ask("question")
        assert "using only the provided context" in provider.last_prompt


@pytest.mark.django_db
class TestRAGServiceEmptyResults:

    def test_empty_retrieval_still_calls_provider(self):
        provider = FakeAIProvider(
            response="The information is not available in the provided documents."
        )
        service = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider,
        )
        result = service.ask("What is the meaning of life?")
        assert provider.call_count == 1
        assert result.answer == "The information is not available in the provided documents."

    def test_empty_retrieval_returns_empty_results_list(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider,
        )
        result = service.ask("question")
        assert result.retrieval_results == []

    def test_empty_context_in_prompt(self):
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider,
        )
        service.ask("question")
        assert "Context:\n\n" in provider.last_prompt


@pytest.mark.django_db
class TestRAGServiceContextBuilding:

    def test_single_result_context(self):
        results = [
            RetrievalResult(
                content="Go directly to jail.",
                source="rules.pdf",
                page=10,
                score=0.92,
            ),
        ]
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=provider,
        )
        service.ask("question")
        assert "[Source: rules.pdf, Page: 10]\nGo directly to jail." in provider.last_prompt

    def test_multiple_sources_context(self):
        results = [
            RetrievalResult(content="Chunk A", source="doc1.pdf", page=1, score=0.9),
            RetrievalResult(content="Chunk B", source="doc2.pdf", page=3, score=0.8),
        ]
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=provider,
        )
        service.ask("question")
        assert "[Source: doc1.pdf, Page: 1]\nChunk A" in provider.last_prompt
        assert "[Source: doc2.pdf, Page: 3]\nChunk B" in provider.last_prompt

    def test_context_blocks_separated_by_double_newline(self):
        results = [
            RetrievalResult(content="A", source="a.pdf", page=1, score=0.9),
            RetrievalResult(content="B", source="b.pdf", page=2, score=0.8),
        ]
        provider = FakeAIProvider()
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=provider,
        )
        service.ask("question")
        context_section = provider.last_prompt.split("Context:\n")[1].split("\n\nQuestion:\n")[0]
        assert "\n\n" in context_section


@pytest.mark.django_db
class TestRAGServiceAbstraction:

    def test_uses_ai_provider_interface(self):
        provider = FakeAIProvider()
        assert isinstance(provider, AIProvider)
        service = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider,
        )
        service.ask("question")
        assert provider.call_count == 1

    def test_provider_is_injectable(self):
        provider_a = FakeAIProvider(response="Answer A")
        provider_b = FakeAIProvider(response="Answer B")
        service_a = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider_a,
        )
        service_b = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=provider_b,
        )
        assert service_a.ask("q").answer == "Answer A"
        assert service_b.ask("q").answer == "Answer B"
