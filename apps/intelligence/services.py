import json
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.ai.generation import get_extraction_provider
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
from apps.intelligence.prompts import build_extraction_prompt

logger = logging.getLogger(__name__)


class ExtractionService:

    def __init__(self, ai_provider: AIProvider | None = None):
        self.ai_provider = ai_provider or get_extraction_provider()

    def run(self, analysis: ProjectAnalysis) -> None:
        documents_content = self._gather_documents()
        if not documents_content:
            raise ValueError("No completed documents available for analysis.")

        total_length = sum(
            len(page["content"])
            for doc in documents_content
            for page in doc["pages"]
        )
        max_length = settings.EXTRACTION_MAX_CONTENT_LENGTH
        if total_length > max_length:
            raise ValueError(
                f"Total document content ({total_length} chars) exceeds "
                f"maximum ({max_length} chars). Reduce document count or size."
            )

        prompt = build_extraction_prompt(documents_content)
        raw_response = self.ai_provider.generate(prompt)

        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        doc_name_map = {doc["name"]: doc["document_id"] for doc in documents_content}
        self._save_extraction(analysis, data, doc_name_map)

    def _gather_documents(self) -> list[dict]:
        docs = Document.objects.filter(status=Document.Status.COMPLETED).order_by("name")
        result = []
        for doc in docs:
            pages = DocumentPage.objects.filter(document=doc).order_by("page_number")
            page_list = [
                {"page_number": p.page_number, "content": p.content}
                for p in pages
            ]
            if page_list:
                result.append({
                    "document_id": str(doc.pk),
                    "name": doc.name,
                    "pages": page_list,
                })
        return result

    def _save_extraction(
        self,
        analysis: ProjectAnalysis,
        data: dict,
        doc_name_map: dict[str, str],
    ) -> None:
        feature_map: dict[str, Feature] = {}

        for feat_data in data.get("features", []):
            feature = Feature.objects.create(
                analysis=analysis,
                name=feat_data["name"],
                description=feat_data.get("description", ""),
            )
            feature_map[feature.name] = feature
            self._create_source_references(
                analysis, feature, feat_data.get("source_references", []), doc_name_map
            )

            for req_data in feat_data.get("requirements", []):
                req = Requirement.objects.create(
                    analysis=analysis,
                    feature=feature,
                    description=req_data["description"],
                    status=req_data.get("status", Requirement.Status.COVERED),
                )
                self._create_source_references(
                    analysis, req, req_data.get("source_references", []), doc_name_map
                )

            for flow_data in feat_data.get("user_flows", []):
                flow = UserFlow.objects.create(
                    analysis=analysis,
                    feature=feature,
                    name=flow_data["name"],
                    description=flow_data.get("description", ""),
                )
                self._create_source_references(
                    analysis, flow, flow_data.get("source_references", []), doc_name_map
                )

                for step_data in flow_data.get("steps", []):
                    step = UserFlowStep.objects.create(
                        user_flow=flow,
                        order=step_data["order"],
                        description=step_data["description"],
                        actor=step_data.get("actor", ""),
                    )
                    self._create_source_references(
                        analysis, step, step_data.get("source_references", []), doc_name_map
                    )

            for risk_data in feat_data.get("risks", []):
                risk = Risk.objects.create(
                    analysis=analysis,
                    feature=feature,
                    severity=risk_data.get("severity", Risk.Severity.MEDIUM),
                    description=risk_data["description"],
                )
                self._create_source_references(
                    analysis, risk, risk_data.get("source_references", []), doc_name_map
                )

        for dep_data in data.get("dependencies", []):
            from_feat = feature_map.get(dep_data.get("from_feature"))
            to_feat = feature_map.get(dep_data.get("to_feature"))
            if not from_feat or not to_feat:
                logger.warning(
                    "Skipping dependency: unknown feature reference %s -> %s",
                    dep_data.get("from_feature"),
                    dep_data.get("to_feature"),
                )
                continue
            dep = Dependency.objects.create(
                analysis=analysis,
                from_feature=from_feat,
                to_feature=to_feat,
                dependency_type=dep_data.get("dependency_type", ""),
                inference_type=dep_data.get("inference_type", Dependency.InferenceType.EXPLICIT),
                description=dep_data.get("description", ""),
            )
            self._create_source_references(
                analysis, dep, dep_data.get("source_references", []), doc_name_map
            )

        for conflict_data in data.get("conflicts", []):
            feat_a = feature_map.get(conflict_data.get("feature_a"))
            feat_b = feature_map.get(conflict_data.get("feature_b"))
            if not feat_a or not feat_b:
                logger.warning(
                    "Skipping conflict: unknown feature reference %s / %s",
                    conflict_data.get("feature_a"),
                    conflict_data.get("feature_b"),
                )
                continue

            req_a_desc = conflict_data.get("requirement_a_description", "")
            req_b_desc = conflict_data.get("requirement_b_description", "")
            req_a = feat_a.requirements.filter(description=req_a_desc).first()
            req_b = feat_b.requirements.filter(description=req_b_desc).first()
            if not req_a or not req_b:
                logger.warning(
                    "Skipping conflict: could not match requirements for %s / %s",
                    conflict_data.get("feature_a"),
                    conflict_data.get("feature_b"),
                )
                continue

            conflict = Conflict.objects.create(
                analysis=analysis,
                requirement_a=req_a,
                requirement_b=req_b,
                description=conflict_data.get("description", ""),
            )
            self._create_source_references(
                analysis, conflict, conflict_data.get("source_references", []), doc_name_map
            )

    def _create_source_references(
        self,
        analysis: ProjectAnalysis,
        entity,
        refs: list[dict],
        doc_name_map: dict[str, str],
    ) -> None:
        if not refs:
            return

        content_type = ContentType.objects.get_for_model(entity)
        source_refs = []
        for ref in refs:
            doc_id = doc_name_map.get(ref.get("document_name"))
            source_refs.append(
                SourceReference(
                    analysis=analysis,
                    content_type=content_type,
                    object_id=entity.pk,
                    document_id=doc_id,
                    page_number=ref.get("page_number"),
                    excerpt=ref.get("excerpt", ""),
                )
            )
        SourceReference.objects.bulk_create(source_refs)
