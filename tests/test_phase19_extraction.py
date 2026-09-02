import json
import uuid

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.ai.providers.base import AIProvider
from apps.documents.models import Document, DocumentPage
from apps.intelligence.models import (
    Conflict,
    Dependency,
    Feature,
    ProjectAnalysis,
    Requirement,
    Risk,
    SourceReference,
    UserFlow,
    UserFlowStep,
)
from apps.intelligence.services import ExtractionService


SAMPLE_EXTRACTION_RESPONSE = {
    "features": [
        {
            "name": "User Authentication",
            "description": "Login and registration system",
            "source_references": [
                {
                    "document_name": "requirements.pdf",
                    "page_number": 1,
                    "excerpt": "Users must be able to log in",
                }
            ],
            "requirements": [
                {
                    "description": "Users must authenticate with email and password",
                    "status": "COVERED",
                    "source_references": [
                        {
                            "document_name": "requirements.pdf",
                            "page_number": 1,
                            "excerpt": "email and password authentication",
                        }
                    ],
                },
                {
                    "description": "Two-factor authentication support",
                    "status": "MISSING",
                    "source_references": [
                        {
                            "document_name": "requirements.pdf",
                            "page_number": 2,
                            "excerpt": "2FA should be supported",
                        }
                    ],
                },
            ],
            "user_flows": [
                {
                    "name": "Login Flow",
                    "description": "Standard login process",
                    "source_references": [
                        {
                            "document_name": "requirements.pdf",
                            "page_number": 3,
                            "excerpt": "login process",
                        }
                    ],
                    "steps": [
                        {
                            "order": 1,
                            "description": "User enters email and password",
                            "actor": "User",
                            "source_references": [
                                {
                                    "document_name": "requirements.pdf",
                                    "page_number": 3,
                                    "excerpt": "enter credentials",
                                }
                            ],
                        },
                        {
                            "order": 2,
                            "description": "System validates credentials",
                            "actor": "System",
                            "source_references": [
                                {
                                    "document_name": "requirements.pdf",
                                    "page_number": 3,
                                    "excerpt": "validate credentials",
                                }
                            ],
                        },
                    ],
                }
            ],
            "risks": [
                {
                    "severity": "HIGH",
                    "description": "No 2FA increases account takeover risk",
                    "source_references": [
                        {
                            "document_name": "requirements.pdf",
                            "page_number": 2,
                            "excerpt": "2FA should be supported",
                        }
                    ],
                }
            ],
        },
        {
            "name": "Document Upload",
            "description": "File upload and processing",
            "source_references": [
                {
                    "document_name": "design.pdf",
                    "page_number": 1,
                    "excerpt": "upload documents",
                }
            ],
            "requirements": [
                {
                    "description": "Support PDF file uploads",
                    "status": "COVERED",
                    "source_references": [
                        {
                            "document_name": "design.pdf",
                            "page_number": 1,
                            "excerpt": "PDF uploads",
                        }
                    ],
                }
            ],
            "user_flows": [],
            "risks": [],
        },
    ],
    "dependencies": [
        {
            "from_feature": "Document Upload",
            "to_feature": "User Authentication",
            "dependency_type": "requires",
            "inference_type": "EXPLICIT",
            "description": "Uploading requires authentication",
            "source_references": [
                {
                    "document_name": "requirements.pdf",
                    "page_number": 4,
                    "excerpt": "authenticated users can upload",
                }
            ],
        }
    ],
    "conflicts": [],
}


class FakeAIProvider(AIProvider):

    def __init__(self, response: str = ""):
        self.response = response
        self.last_prompt = None
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        self.call_count += 1
        return self.response


def _create_test_documents():
    doc1 = Document.objects.create(
        name="requirements.pdf",
        file="documents/requirements.pdf",
        status=Document.Status.COMPLETED,
    )
    for i in range(1, 5):
        DocumentPage.objects.create(
            document=doc1,
            page_number=i,
            content=f"Page {i} content of requirements document.",
        )

    doc2 = Document.objects.create(
        name="design.pdf",
        file="documents/design.pdf",
        status=Document.Status.COMPLETED,
    )
    DocumentPage.objects.create(
        document=doc2,
        page_number=1,
        content="Page 1 content of design document.",
    )

    return doc1, doc2


@pytest.mark.django_db
class TestExtractionServiceRun:

    def test_creates_features(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert Feature.objects.filter(analysis=analysis).count() == 2
        assert Feature.objects.filter(analysis=analysis, name="User Authentication").exists()
        assert Feature.objects.filter(analysis=analysis, name="Document Upload").exists()

    def test_creates_requirements(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        auth_feature = Feature.objects.get(analysis=analysis, name="User Authentication")
        reqs = Requirement.objects.filter(feature=auth_feature)
        assert reqs.count() == 2
        assert reqs.filter(status=Requirement.Status.COVERED).count() == 1
        assert reqs.filter(status=Requirement.Status.MISSING).count() == 1

    def test_creates_user_flows_with_steps(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        auth_feature = Feature.objects.get(analysis=analysis, name="User Authentication")
        flows = UserFlow.objects.filter(feature=auth_feature)
        assert flows.count() == 1
        assert flows.first().name == "Login Flow"

        steps = UserFlowStep.objects.filter(user_flow=flows.first()).order_by("order")
        assert steps.count() == 2
        assert steps[0].actor == "User"
        assert steps[1].actor == "System"

    def test_creates_dependencies(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        deps = Dependency.objects.filter(analysis=analysis)
        assert deps.count() == 1
        dep = deps.first()
        assert dep.from_feature.name == "Document Upload"
        assert dep.to_feature.name == "User Authentication"
        assert dep.dependency_type == "requires"
        assert dep.inference_type == Dependency.InferenceType.EXPLICIT

    def test_creates_risks(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        risks = Risk.objects.filter(analysis=analysis)
        assert risks.count() == 1
        assert risks.first().severity == Risk.Severity.HIGH
        assert risks.first().feature.name == "User Authentication"

    def test_creates_source_references(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        refs = SourceReference.objects.filter(analysis=analysis)
        assert refs.count() > 0

        auth_feature = Feature.objects.get(analysis=analysis, name="User Authentication")
        feature_refs = auth_feature.source_references.all()
        assert feature_refs.count() == 1
        assert feature_refs.first().document.name == "requirements.pdf"
        assert feature_refs.first().page_number == 1
        assert feature_refs.first().excerpt == "Users must be able to log in"

    def test_source_reference_document_mapping(self):
        doc1, doc2 = _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        upload_feature = Feature.objects.get(analysis=analysis, name="Document Upload")
        feature_refs = upload_feature.source_references.all()
        assert feature_refs.first().document.pk == doc2.pk

    def test_ai_provider_called_once(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert provider.call_count == 1

    def test_prompt_contains_document_content(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider(json.dumps(SAMPLE_EXTRACTION_RESPONSE))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert "requirements.pdf" in provider.last_prompt
        assert "design.pdf" in provider.last_prompt
        assert "Page 1 content of requirements document." in provider.last_prompt
        assert "Page 1 content of design document." in provider.last_prompt


@pytest.mark.django_db
class TestExtractionServiceEdgeCases:

    def test_no_completed_documents_raises(self):
        Document.objects.create(
            name="pending.pdf",
            file="documents/pending.pdf",
            status=Document.Status.PENDING,
        )
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider("{}")
        service = ExtractionService(ai_provider=provider)

        with pytest.raises(ValueError, match="No completed documents"):
            service.run(analysis)

    def test_invalid_json_raises(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider("not valid json {{{")
        service = ExtractionService(ai_provider=provider)

        with pytest.raises(ValueError, match="invalid JSON"):
            service.run(analysis)

    def test_content_exceeds_max_length(self, settings):
        settings.EXTRACTION_MAX_CONTENT_LENGTH = 10
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        provider = FakeAIProvider("{}")
        service = ExtractionService(ai_provider=provider)

        with pytest.raises(ValueError, match="exceeds maximum"):
            service.run(analysis)

    def test_empty_features_array(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        response = {"features": [], "dependencies": [], "conflicts": []}
        provider = FakeAIProvider(json.dumps(response))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert Feature.objects.filter(analysis=analysis).count() == 0

    def test_skips_dependency_with_unknown_feature(self):
        _create_test_documents()
        analysis = ProjectAnalysis.objects.create()
        response = {
            "features": [
                {
                    "name": "Feature A",
                    "description": "desc",
                    "source_references": [],
                    "requirements": [],
                    "user_flows": [],
                    "risks": [],
                }
            ],
            "dependencies": [
                {
                    "from_feature": "Feature A",
                    "to_feature": "Nonexistent Feature",
                    "dependency_type": "requires",
                    "inference_type": "EXPLICIT",
                    "description": "bad dep",
                    "source_references": [],
                }
            ],
            "conflicts": [],
        }
        provider = FakeAIProvider(json.dumps(response))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert Dependency.objects.filter(analysis=analysis).count() == 0

    def test_pending_documents_excluded(self):
        _create_test_documents()
        Document.objects.create(
            name="pending.pdf",
            file="documents/pending.pdf",
            status=Document.Status.PENDING,
        )
        analysis = ProjectAnalysis.objects.create()
        response = {"features": [], "dependencies": [], "conflicts": []}
        provider = FakeAIProvider(json.dumps(response))
        service = ExtractionService(ai_provider=provider)
        service.run(analysis)

        assert "pending.pdf" not in provider.last_prompt


@pytest.mark.django_db
class TestTriggerAnalysisAPI:

    def setup_method(self):
        self.client = APIClient()

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_returns_202(self, mock_task):
        response = self.client.post("/api/project/analyze/")
        assert response.status_code == 202
        assert "id" in response.data
        assert response.data["status"] == "PENDING"

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_creates_analysis(self, mock_task):
        self.client.post("/api/project/analyze/")
        assert ProjectAnalysis.objects.count() == 1

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_dispatches_celery_task(self, mock_task):
        self.client.post("/api/project/analyze/")
        analysis = ProjectAnalysis.objects.first()
        mock_task.delay.assert_called_once_with(str(analysis.pk))

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_rejects_when_in_progress(self, mock_task):
        ProjectAnalysis.objects.create(status=ProjectAnalysis.Status.PROCESSING)
        response = self.client.post("/api/project/analyze/")
        assert response.status_code == 409

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_rejects_when_pending(self, mock_task):
        ProjectAnalysis.objects.create(status=ProjectAnalysis.Status.PENDING)
        response = self.client.post("/api/project/analyze/")
        assert response.status_code == 409

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_allows_after_completed(self, mock_task):
        ProjectAnalysis.objects.create(status=ProjectAnalysis.Status.COMPLETED)
        response = self.client.post("/api/project/analyze/")
        assert response.status_code == 202

    @patch("apps.intelligence.views.run_project_analysis")
    def test_trigger_allows_after_failed(self, mock_task):
        ProjectAnalysis.objects.create(status=ProjectAnalysis.Status.FAILED)
        response = self.client.post("/api/project/analyze/")
        assert response.status_code == 202


@pytest.mark.django_db
class TestAnalysisStatusAPI:

    def setup_method(self):
        self.client = APIClient()

    def test_latest_returns_404_when_empty(self):
        response = self.client.get("/api/project/analysis/latest/")
        assert response.status_code == 404

    def test_latest_returns_analysis(self):
        analysis = ProjectAnalysis.objects.create(
            status=ProjectAnalysis.Status.COMPLETED,
        )
        response = self.client.get("/api/project/analysis/latest/")
        assert response.status_code == 200
        assert response.data["id"] == str(analysis.pk)
        assert response.data["status"] == "COMPLETED"

    def test_detail_returns_analysis(self):
        analysis = ProjectAnalysis.objects.create(
            status=ProjectAnalysis.Status.COMPLETED,
        )
        response = self.client.get(f"/api/project/analysis/{analysis.pk}/")
        assert response.status_code == 200
        assert response.data["id"] == str(analysis.pk)

    def test_detail_returns_404_for_nonexistent(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/project/analysis/{fake_id}/")
        assert response.status_code == 404

    def test_latest_includes_nested_features(self):
        analysis = ProjectAnalysis.objects.create(
            status=ProjectAnalysis.Status.COMPLETED,
        )
        Feature.objects.create(
            analysis=analysis,
            name="Test Feature",
            description="A test",
        )
        response = self.client.get("/api/project/analysis/latest/")
        assert len(response.data["features"]) == 1
        assert response.data["features"][0]["name"] == "Test Feature"


@pytest.mark.django_db
class TestCeleryTask:

    def test_task_sets_completed_on_success(self):
        doc = Document.objects.create(
            name="test.pdf",
            file="documents/test.pdf",
            status=Document.Status.COMPLETED,
        )
        DocumentPage.objects.create(
            document=doc, page_number=1, content="Test content."
        )
        analysis = ProjectAnalysis.objects.create()

        response = {"features": [], "dependencies": [], "conflicts": []}
        provider = FakeAIProvider(json.dumps(response))

        with patch(
            "apps.intelligence.services.get_extraction_provider",
            return_value=provider,
        ):
            from apps.intelligence.tasks import run_project_analysis
            run_project_analysis(str(analysis.pk))

        analysis.refresh_from_db()
        assert analysis.status == ProjectAnalysis.Status.COMPLETED
        assert analysis.completed_at is not None

    def test_task_sets_failed_on_error(self):
        doc = Document.objects.create(
            name="test.pdf",
            file="documents/test.pdf",
            status=Document.Status.COMPLETED,
        )
        DocumentPage.objects.create(
            document=doc, page_number=1, content="Test content."
        )
        analysis = ProjectAnalysis.objects.create()

        class FailingProvider(AIProvider):
            def generate(self, prompt: str) -> str:
                raise RuntimeError("LLM unavailable")

        with patch(
            "apps.intelligence.services.get_extraction_provider",
            return_value=FailingProvider(),
        ):
            from apps.intelligence.tasks import run_project_analysis
            run_project_analysis(str(analysis.pk))

        analysis.refresh_from_db()
        assert analysis.status == ProjectAnalysis.Status.FAILED
        assert "LLM unavailable" in analysis.error_message

    def test_task_deletes_previous_completed_analysis(self):
        doc = Document.objects.create(
            name="test.pdf",
            file="documents/test.pdf",
            status=Document.Status.COMPLETED,
        )
        DocumentPage.objects.create(
            document=doc, page_number=1, content="Test content."
        )
        old_analysis = ProjectAnalysis.objects.create(
            status=ProjectAnalysis.Status.COMPLETED,
        )
        new_analysis = ProjectAnalysis.objects.create()

        response = {"features": [], "dependencies": [], "conflicts": []}
        provider = FakeAIProvider(json.dumps(response))

        with patch(
            "apps.intelligence.services.get_extraction_provider",
            return_value=provider,
        ):
            from apps.intelligence.tasks import run_project_analysis
            run_project_analysis(str(new_analysis.pk))

        assert not ProjectAnalysis.objects.filter(pk=old_analysis.pk).exists()
        new_analysis.refresh_from_db()
        assert new_analysis.status == ProjectAnalysis.Status.COMPLETED

    def test_task_ignores_nonexistent_analysis(self):
        from apps.intelligence.tasks import run_project_analysis
        run_project_analysis(str(uuid.uuid4()))
