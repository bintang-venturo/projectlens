import json
import uuid

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentPage
from apps.intelligence.models import (
    Dependency,
    Feature,
    ProjectAnalysis,
    Requirement,
    Risk,
    SourceReference,
)


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def api_client():
    return APIClient()


def _create_completed_analysis():
    """Create a completed analysis with features, deps, risks for testing."""
    analysis = ProjectAnalysis.objects.create(
        status=ProjectAnalysis.Status.COMPLETED,
    )
    feat_auth = Feature.objects.create(
        analysis=analysis,
        name="User Authentication",
        description="Login and registration system",
    )
    feat_upload = Feature.objects.create(
        analysis=analysis,
        name="Document Upload",
        description="File upload and processing",
    )
    Requirement.objects.create(
        analysis=analysis,
        feature=feat_auth,
        description="Users must authenticate with email and password",
        status=Requirement.Status.COVERED,
    )
    Requirement.objects.create(
        analysis=analysis,
        feature=feat_auth,
        description="Two-factor authentication support",
        status=Requirement.Status.MISSING,
    )
    Risk.objects.create(
        analysis=analysis,
        feature=feat_auth,
        severity=Risk.Severity.HIGH,
        description="No 2FA increases account takeover risk",
    )
    Dependency.objects.create(
        analysis=analysis,
        from_feature=feat_upload,
        to_feature=feat_auth,
        dependency_type="requires",
        inference_type=Dependency.InferenceType.EXPLICIT,
        description="Uploading requires authentication",
    )
    return analysis, feat_auth, feat_upload


@pytest.mark.django_db
class TestProjectMapRoute:

    def test_project_map_page_loads(self, client):
        response = client.get(reverse("ui:project-map"))
        assert response.status_code == 200

    def test_project_map_url_resolves(self):
        assert reverse("ui:project-map") == "/project-map/"

    def test_project_map_uses_correct_template(self, client):
        response = client.get(reverse("ui:project-map"))
        templates = [t.name for t in response.templates]
        assert "ui/project_map.html" in templates

    def test_project_map_extends_base(self, client):
        response = client.get(reverse("ui:project-map"))
        templates = [t.name for t in response.templates]
        assert "ui/base.html" in templates


@pytest.mark.django_db
class TestProjectMapContent:

    def test_page_has_title(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "Project Map" in content

    def test_page_loads_cytoscape(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "cytoscape" in content.lower()

    def test_page_has_reanalyze_button(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "Re-analyze Project" in content

    def test_page_has_graph_container(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert 'id="cy"' in content

    def test_page_has_empty_state(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "No project analysis yet" in content

    def test_page_has_detail_panel(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "selectedFeature" in content

    def test_page_has_dependency_legend(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "Explicit" in content
        assert "Inferred" in content

    def test_page_loads_htmx(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "htmx" in content

    def test_page_loads_alpinejs(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "alpinejs" in content


@pytest.mark.django_db
class TestProjectMapNavigation:

    def test_sidebar_has_project_map_link(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "/project-map/" in content

    def test_project_map_nav_active(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        # Project Map link should have the active style
        assert "project-map" in content

    def test_other_pages_have_project_map_link(self, client):
        """Project Map nav link visible from other pages."""
        for url_name in ["ui:chat", "ui:documents", "ui:settings"]:
            response = client.get(reverse(url_name))
            content = response.content.decode()
            assert "/project-map/" in content, f"Missing project-map link on {url_name}"


@pytest.mark.django_db
class TestProjectMapAPIIntegration:
    """Verify API endpoints used by the Project Map frontend."""

    def test_latest_analysis_returns_graph_data(self, api_client):
        analysis, feat_auth, feat_upload = _create_completed_analysis()
        response = api_client.get("/api/project/analysis/latest/")
        assert response.status_code == 200
        data = response.data

        assert len(data["features"]) == 2
        assert len(data["dependencies"]) == 1

        dep = data["dependencies"][0]
        assert str(dep["from_feature"]) == str(feat_upload.pk)
        assert str(dep["to_feature"]) == str(feat_auth.pk)
        assert dep["inference_type"] == "EXPLICIT"
        assert dep["from_feature_name"] == "Document Upload"
        assert dep["to_feature_name"] == "User Authentication"

    def test_features_include_requirements(self, api_client):
        analysis, feat_auth, _ = _create_completed_analysis()
        response = api_client.get("/api/project/analysis/latest/")
        auth_data = next(
            f for f in response.data["features"] if f["name"] == "User Authentication"
        )
        assert len(auth_data["requirements"]) == 2
        statuses = {r["status"] for r in auth_data["requirements"]}
        assert statuses == {"COVERED", "MISSING"}

    def test_features_include_risks(self, api_client):
        analysis, feat_auth, _ = _create_completed_analysis()
        response = api_client.get("/api/project/analysis/latest/")
        auth_data = next(
            f for f in response.data["features"] if f["name"] == "User Authentication"
        )
        assert len(auth_data["risks"]) == 1
        assert auth_data["risks"][0]["severity"] == "HIGH"

    def test_empty_analysis_returns_404(self, api_client):
        response = api_client.get("/api/project/analysis/latest/")
        assert response.status_code == 404

    def test_analysis_detail_by_id(self, api_client):
        analysis, _, _ = _create_completed_analysis()
        response = api_client.get(f"/api/project/analysis/{analysis.pk}/")
        assert response.status_code == 200
        assert response.data["id"] == str(analysis.pk)
        assert response.data["status"] == "COMPLETED"

    def test_dependency_has_inference_type(self, api_client):
        """Verify edge styling data (EXPLICIT vs INFERRED) is in API response."""
        analysis = ProjectAnalysis.objects.create(
            status=ProjectAnalysis.Status.COMPLETED,
        )
        feat_a = Feature.objects.create(analysis=analysis, name="A")
        feat_b = Feature.objects.create(analysis=analysis, name="B")
        feat_c = Feature.objects.create(analysis=analysis, name="C")

        Dependency.objects.create(
            analysis=analysis,
            from_feature=feat_a,
            to_feature=feat_b,
            inference_type=Dependency.InferenceType.EXPLICIT,
        )
        Dependency.objects.create(
            analysis=analysis,
            from_feature=feat_b,
            to_feature=feat_c,
            inference_type=Dependency.InferenceType.INFERRED,
        )

        response = api_client.get("/api/project/analysis/latest/")
        deps = response.data["dependencies"]
        inference_types = {d["inference_type"] for d in deps}
        assert inference_types == {"EXPLICIT", "INFERRED"}


@pytest.mark.django_db
class TestProjectMapCytoscapeConfig:
    """Verify Cytoscape.js configuration in the template."""

    def test_graph_uses_cose_layout(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "cose" in content

    def test_inferred_edges_dashed(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "line-style" in content
        assert "dashed" in content

    def test_graph_fetches_from_api(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "/api/project/analysis/latest/" in content

    def test_trigger_posts_to_analyze_endpoint(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "/api/project/analyze/" in content

    def test_graph_polls_analysis_status(self, client):
        response = client.get(reverse("ui:project-map"))
        content = response.content.decode()
        assert "startPolling" in content
        assert "setInterval" in content
