
import os
import time
import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.utils

from django.core.exceptions import ValidationError


MAX_DOCUMENT_SIZE = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".jpg",
    ".jpeg", ".png", ".webp",
}


def validate_document_file(file):
    if not file:
        raise ValidationError("A document file is required.")

    if file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(
            "Maximum document size is 20 MB."
        )

    extension = os.path.splitext(file.name)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Unsupported file extension."
        )

    return extension


def upload_project_document(
    file,
    project_id,
    document_id,
):
    extension = validate_document_file(file)

    # Raw Cloudinary assets retain the extension in
    # their public_id.
    public_id = (
        f"unit/project_documents/"
        f"project_{project_id}/"
        f"document_{document_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )

    file.seek(0)

    result = cloudinary.uploader.upload(
        file,
        public_id=public_id,
        resource_type="raw",
        type="authenticated",
        overwrite=False,
        invalidate=False,
    )

    return {
        "public_id": result["public_id"],
        "resource_type": result.get(
            "resource_type", "raw"
        ),
        "delivery_type": result.get(
            "type", "authenticated"
        ),
        "file_size": result.get("bytes", file.size),
        "file_format": extension.lstrip("."),
    }


def generate_document_download_url(version):
    # The URL expires after 5 minutes.
    expires_at = int(time.time()) + 300

    return cloudinary.utils.private_download_url(
        version.cloudinary_public_id,
        format=None,
        resource_type=version.cloudinary_resource_type,
        type=version.cloudinary_delivery_type,
        expires_at=expires_at,
        attachment=True,
    )


def delete_cloudinary_document(version):
    return cloudinary.uploader.destroy(
        version.cloudinary_public_id,
        resource_type=version.cloudinary_resource_type,
        type=version.cloudinary_delivery_type,
        invalidate=True,
    )
