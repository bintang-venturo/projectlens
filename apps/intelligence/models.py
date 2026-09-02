import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.documents.models import Document


class ProjectAnalysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-triggered_at"]
        verbose_name_plural = "project analyses"

    def __str__(self):
        return f"Analysis {self.id} ({self.status})"


class Feature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="features",
    )
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Requirement(models.Model):
    class Status(models.TextChoices):
        COVERED = "COVERED"
        MISSING = "MISSING"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COVERED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.status} requirement for {self.feature.name}"


class UserFlow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="user_flows",
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="user_flows",
    )
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserFlowStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_flow = models.ForeignKey(
        UserFlow,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField()
    description = models.TextField()
    actor = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_flow", "order"],
                name="unique_user_flow_step_order",
            ),
        ]

    def __str__(self):
        return f"Step {self.order} of {self.user_flow.name}"


class Dependency(models.Model):
    class InferenceType(models.TextChoices):
        EXPLICIT = "EXPLICIT"
        INFERRED = "INFERRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="dependencies",
    )
    from_feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="dependencies_out",
    )
    to_feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="dependencies_in",
    )
    dependency_type = models.CharField(max_length=100, blank=True, default="")
    inference_type = models.CharField(
        max_length=20,
        choices=InferenceType.choices,
        default=InferenceType.EXPLICIT,
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "dependencies"

    def __str__(self):
        return f"{self.from_feature.name} → {self.to_feature.name}"


class Conflict(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="conflicts",
    )
    requirement_a = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="conflicts_as_a",
    )
    requirement_b = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="conflicts_as_b",
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Conflict: {self.requirement_a_id} ↔ {self.requirement_b_id}"


class Risk(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="risks",
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risks",
    )
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risks",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    source_references = GenericRelation(
        "SourceReference",
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        ordering = ["-severity", "created_at"]

    def __str__(self):
        return f"{self.severity} risk: {self.description[:50]}"


class SourceReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        ProjectAnalysis,
        on_delete=models.CASCADE,
        related_name="source_references",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        related_name="source_references",
    )
    page_number = models.PositiveIntegerField(null=True, blank=True)
    excerpt = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["content_type", "object_id"],
                name="idx_source_ref_content_object",
            ),
        ]

    def __str__(self):
        doc_name = self.document.name if self.document else "unknown"
        return f"Source: {doc_name} (p.{self.page_number})"
