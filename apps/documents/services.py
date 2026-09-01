from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import ValidationError

from apps.documents.models import Document
from apps.ingestion.tasks import process_document


def validate_pdf(file: UploadedFile) -> None:
    if file.size == 0:
        raise ValidationError({"file": "The uploaded file is empty."})

    if file.size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise ValidationError(
            {"file": f"File size exceeds the maximum allowed size ({max_mb} MB)."}
        )

    if file.content_type != "application/pdf":
        raise ValidationError({"file": "Only PDF files are accepted."})

    header = file.read(5)
    file.seek(0)
    if header != b"%PDF-":
        raise ValidationError({"file": "The file is not a valid PDF."})


def create_document(file: UploadedFile) -> Document:
    validate_pdf(file)

    doc = Document.objects.create(
        name=file.name,
        file=file,
        file_size=file.size,
    )

    process_document.delay(str(doc.pk))

    return doc
