from django.contrib import admin

from .models import (
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


@admin.register(ProjectAnalysis)
class ProjectAnalysisAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "triggered_at", "completed_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "triggered_at", "updated_at"]


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "analysis", "created_at"]
    list_filter = ["analysis"]
    readonly_fields = ["id", "created_at"]


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ["feature", "status", "short_description", "created_at"]
    list_filter = ["status", "analysis"]
    readonly_fields = ["id", "created_at"]

    @admin.display(description="Description")
    def short_description(self, obj):
        return obj.description[:80] + "…" if len(obj.description) > 80 else obj.description


@admin.register(UserFlow)
class UserFlowAdmin(admin.ModelAdmin):
    list_display = ["name", "feature", "created_at"]
    list_filter = ["analysis"]
    readonly_fields = ["id", "created_at"]


@admin.register(UserFlowStep)
class UserFlowStepAdmin(admin.ModelAdmin):
    list_display = ["user_flow", "order", "actor"]
    readonly_fields = ["id", "created_at"]


@admin.register(Dependency)
class DependencyAdmin(admin.ModelAdmin):
    list_display = ["from_feature", "to_feature", "dependency_type", "inference_type"]
    list_filter = ["inference_type", "analysis"]
    readonly_fields = ["id", "created_at"]


@admin.register(Conflict)
class ConflictAdmin(admin.ModelAdmin):
    list_display = ["requirement_a", "requirement_b", "created_at"]
    list_filter = ["analysis"]
    readonly_fields = ["id", "created_at"]


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ["feature", "requirement", "severity", "created_at"]
    list_filter = ["severity", "analysis"]
    readonly_fields = ["id", "created_at"]


@admin.register(SourceReference)
class SourceReferenceAdmin(admin.ModelAdmin):
    list_display = ["content_type", "object_id", "document", "page_number"]
    list_filter = ["content_type", "analysis"]
    readonly_fields = ["id", "created_at"]
