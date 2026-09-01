import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: str) -> None:
    from apps.documents.models import Document

    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error("Document %s not found", document_id)
        return

    doc.status = Document.Status.PROCESSING
    doc.save(update_fields=["status", "updated_at"])

    try:
        from apps.ingestion.services import ingest_document

        ingest_document(doc)
        # Phase 06+ will add: chunk, embed, store vectors
        doc.status = Document.Status.COMPLETED
        doc.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        doc.status = Document.Status.FAILED
        doc.error_message = str(exc)
        doc.save(update_fields=["status", "error_message", "updated_at"])
        raise self.retry(exc=exc)
