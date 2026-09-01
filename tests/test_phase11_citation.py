import pytest

from apps.ai.providers.base import AIProvider
from apps.chat.services import Citation, RAGResult, RAGService, build_citations
from apps.retrieval.services import RetrievalResult, RetrievalService


class FakeAIProvider(AIProvider):

    def __init__(self, response: str = "Fake answer"):
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


class FakeRetrievalService(RetrievalService):

    def __init__(self, results: list[RetrievalResult] | None = None):
        self._results = results or []

    def search(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        return self._results


class TestBuildCitations:

    def test_single_result(self):
        results = [
            RetrievalResult(content="text", source="doc.pdf", page=1, score=0.9),
        ]
        citations = build_citations(results)
        assert len(citations) == 1
        assert citations[0] == Citation(source="doc.pdf", page=1)

    def test_duplicate_source_page_removed(self):
        results = [
            RetrievalResult(content="chunk A", source="doc.pdf", page=4, score=0.95),
            RetrievalResult(content="chunk B", source="doc.pdf", page=4, score=0.90),
        ]
        citations = build_citations(results)
        assert len(citations) == 1
        assert citations[0] == Citation(source="doc.pdf", page=4)

    def test_different_pages_kept(self):
        results = [
            RetrievalResult(content="a", source="doc.pdf", page=1, score=0.9),
            RetrievalResult(content="b", source="doc.pdf", page=2, score=0.8),
        ]
        citations = build_citations(results)
        assert len(citations) == 2

    def test_different_sources_kept(self):
        results = [
            RetrievalResult(content="a", source="doc1.pdf", page=1, score=0.9),
            RetrievalResult(content="b", source="doc2.pdf", page=1, score=0.8),
        ]
        citations = build_citations(results)
        assert len(citations) == 2

    def test_empty_results(self):
        assert build_citations([]) == []

    def test_order_preserved(self):
        results = [
            RetrievalResult(content="a", source="b.pdf", page=3, score=0.9),
            RetrievalResult(content="b", source="a.pdf", page=1, score=0.8),
            RetrievalResult(content="c", source="c.pdf", page=2, score=0.7),
        ]
        citations = build_citations(results)
        assert citations[0] == Citation(source="b.pdf", page=3)
        assert citations[1] == Citation(source="a.pdf", page=1)
        assert citations[2] == Citation(source="c.pdf", page=2)

    def test_duplicate_removed_keeps_first_occurrence(self):
        results = [
            RetrievalResult(content="first", source="doc.pdf", page=5, score=0.95),
            RetrievalResult(content="other", source="other.pdf", page=1, score=0.90),
            RetrievalResult(content="dup", source="doc.pdf", page=5, score=0.80),
        ]
        citations = build_citations(results)
        assert len(citations) == 2
        assert citations[0] == Citation(source="doc.pdf", page=5)
        assert citations[1] == Citation(source="other.pdf", page=1)

    def test_returns_citation_dataclass(self):
        results = [
            RetrievalResult(content="text", source="doc.pdf", page=1, score=0.9),
        ]
        citations = build_citations(results)
        assert isinstance(citations[0], Citation)

    def test_citation_has_source_and_page(self):
        c = Citation(source="rules.pdf", page=7)
        assert c.source == "rules.pdf"
        assert c.page == 7

    def test_citations_from_metadata_not_invented(self):
        results = [
            RetrievalResult(content="text", source="real.pdf", page=42, score=0.9),
        ]
        citations = build_citations(results)
        assert citations[0].source == "real.pdf"
        assert citations[0].page == 42


@pytest.mark.django_db
class TestRAGServiceCitations:

    def test_ask_returns_citations(self):
        results = [
            RetrievalResult(content="Each player starts with $1,500.", source="monopoly.pdf", page=4, score=0.95),
        ]
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=FakeAIProvider(),
        )
        result = service.ask("How much money?")
        assert len(result.citations) == 1
        assert result.citations[0] == Citation(source="monopoly.pdf", page=4)

    def test_ask_deduplicates_citations(self):
        results = [
            RetrievalResult(content="chunk 1", source="doc.pdf", page=4, score=0.95),
            RetrievalResult(content="chunk 2", source="doc.pdf", page=4, score=0.90),
            RetrievalResult(content="chunk 3", source="doc.pdf", page=5, score=0.85),
        ]
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=FakeAIProvider(),
        )
        result = service.ask("question")
        assert len(result.citations) == 2

    def test_ask_empty_retrieval_no_citations(self):
        service = RAGService(
            retrieval_service=FakeRetrievalService([]),
            ai_provider=FakeAIProvider(),
        )
        result = service.ask("question")
        assert result.citations == []

    def test_rag_result_has_all_fields(self):
        results = [
            RetrievalResult(content="text", source="doc.pdf", page=1, score=0.9),
        ]
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=FakeAIProvider(response="The answer"),
        )
        result = service.ask("question")
        assert isinstance(result, RAGResult)
        assert result.answer == "The answer"
        assert len(result.citations) == 1
        assert result.retrieval_results == results

    def test_citations_are_structured_data(self):
        results = [
            RetrievalResult(content="text", source="doc.pdf", page=3, score=0.9),
        ]
        service = RAGService(
            retrieval_service=FakeRetrievalService(results),
            ai_provider=FakeAIProvider(),
        )
        result = service.ask("question")
        citation = result.citations[0]
        assert hasattr(citation, "source")
        assert hasattr(citation, "page")
        assert isinstance(citation.source, str)
        assert isinstance(citation.page, int)
