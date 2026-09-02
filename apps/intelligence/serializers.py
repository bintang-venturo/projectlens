from rest_framework import serializers

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


class SourceReferenceSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source="document.name", default=None)

    class Meta:
        model = SourceReference
        fields = ["id", "document_name", "page_number", "excerpt"]


class UserFlowStepSerializer(serializers.ModelSerializer):
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = UserFlowStep
        fields = ["id", "order", "description", "actor", "source_references"]


class UserFlowSerializer(serializers.ModelSerializer):
    steps = UserFlowStepSerializer(many=True, read_only=True)
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = UserFlow
        fields = ["id", "name", "description", "steps", "source_references"]


class RequirementSerializer(serializers.ModelSerializer):
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Requirement
        fields = ["id", "description", "status", "source_references"]


class RiskSerializer(serializers.ModelSerializer):
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Risk
        fields = ["id", "severity", "description", "feature", "requirement", "source_references"]


class FeatureSerializer(serializers.ModelSerializer):
    requirements = RequirementSerializer(many=True, read_only=True)
    user_flows = UserFlowSerializer(many=True, read_only=True)
    risks = RiskSerializer(many=True, read_only=True)
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Feature
        fields = [
            "id", "name", "description",
            "requirements", "user_flows", "risks", "source_references",
        ]


class DependencySerializer(serializers.ModelSerializer):
    from_feature_name = serializers.CharField(source="from_feature.name", read_only=True)
    to_feature_name = serializers.CharField(source="to_feature.name", read_only=True)
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Dependency
        fields = [
            "id", "from_feature", "from_feature_name",
            "to_feature", "to_feature_name",
            "dependency_type", "inference_type", "description",
            "source_references",
        ]


class ConflictSerializer(serializers.ModelSerializer):
    source_references = SourceReferenceSerializer(many=True, read_only=True)

    class Meta:
        model = Conflict
        fields = [
            "id", "requirement_a", "requirement_b",
            "description", "source_references",
        ]


class AnalysisStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAnalysis
        fields = ["id", "status", "triggered_at", "completed_at", "error_message"]


class AnalysisDetailSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)
    dependencies = DependencySerializer(many=True, read_only=True)
    conflicts = ConflictSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectAnalysis
        fields = [
            "id", "status", "triggered_at", "completed_at", "error_message",
            "features", "dependencies", "conflicts",
        ]
