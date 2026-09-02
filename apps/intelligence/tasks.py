import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_project_analysis(self, analysis_id: str) -> None:
    from apps.intelligence.models import ProjectAnalysis
    from apps.intelligence.services import ExtractionService

    try:
        analysis = ProjectAnalysis.objects.get(pk=analysis_id)
    except ProjectAnalysis.DoesNotExist:
        logger.error("ProjectAnalysis %s not found", analysis_id)
        return

    analysis.status = ProjectAnalysis.Status.PROCESSING
    analysis.save(update_fields=["status", "updated_at"])

    try:
        service = ExtractionService()
        service.run(analysis)

        ProjectAnalysis.objects.filter(
            status=ProjectAnalysis.Status.COMPLETED,
        ).exclude(pk=analysis.pk).delete()

        analysis.status = ProjectAnalysis.Status.COMPLETED
        analysis.completed_at = timezone.now()
        analysis.save(update_fields=["status", "completed_at", "updated_at"])
    except Exception as exc:
        logger.exception("Project analysis %s failed", analysis_id)
        analysis.status = ProjectAnalysis.Status.FAILED
        analysis.error_message = str(exc)
        analysis.completed_at = timezone.now()
        analysis.save(
            update_fields=["status", "error_message", "completed_at", "updated_at"]
        )
