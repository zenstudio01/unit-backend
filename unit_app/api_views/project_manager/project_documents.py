from unit_app.api_views.common_imports import *

from .serializers import (
    ProjectDocumentSerializer,
    ProjectDocumentVersionSerializer,
)
from .cloudinary_documents import (
    validate_document_file,
    upload_project_document,
    generate_document_download_url,
    delete_cloudinary_document,
)
from .helper import *


def document_queryset(user):
    return ProjectDocument.objects.filter(
        project__in=allowed_projects(user)
    ).select_related("project", "uploaded_by")


def deny_write():
    return Response(
        {"message": "Permission denied."},
        status=403,
    )


def upload_error(error):
    return Response(
        {"file": [str(error)]},
        status=400,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def project_documents(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")

        if not project_id:
            return Response(
                {"message": "project_id is required."},
                status=400,
            )

        project = get_accessible_project(
            request.user, project_id
        )

        documents = document_queryset(
            request.user
        ).filter(project=project).prefetch_related(
            "versions"
        )

        category = request.query_params.get("category")
        status_value = request.query_params.get("status")
        search = request.query_params.get("search", "").strip()

        if category:
            documents = documents.filter(category=category)

        if status_value:
            documents = documents.filter(status=status_value)

        if search:
            documents = documents.filter(
                Q(title__icontains=search)
                | Q(document_number__icontains=search)
                | Q(description__icontains=search)
            )

        return Response({
            "results": ProjectDocumentSerializer(
                documents, many=True
            ).data
        })

    project_id = request.data.get("project")

    if not project_id:
        return Response(
            {"project": ["This field is required."]},
            status=400,
        )

    project = get_accessible_project(
        request.user, project_id
    )

    if not can_manage_project(request.user, project):
        return deny_write()

    file = request.FILES.get("file")

    try:
        validate_document_file(file)
    except ValidationError as error:
        return upload_error(error)

    serializer = ProjectDocumentSerializer(
        data=request.data
    )
    serializer.is_valid(raise_exception=True)

    # Create metadata first to obtain a document ID.
    # If Cloudinary fails, the database transaction
    # rolls back.
    uploaded = None

    try:
        with transaction.atomic():
            document = serializer.save(
                project=project,
                uploaded_by=request.user,
                status="draft",
            )

            uploaded = upload_project_document(
                file,
                project.id,
                document.id,
            )

            ProjectDocumentVersion.objects.create(
                document=document,
                version_number=1,
                cloudinary_public_id=uploaded["public_id"],
                cloudinary_resource_type=uploaded["resource_type"],
                cloudinary_delivery_type=uploaded["delivery_type"],
                original_filename=file.name[:255],
                file_size=uploaded["file_size"],
                file_format=uploaded["file_format"],
                uploaded_by=request.user,
                change_notes="Initial upload",
            )

    except Exception:
        # Cloudinary is outside the database transaction.
        # Attempt cleanup if the database operation failed.
        if uploaded:
            try:
                from cloudinary import uploader
                uploader.destroy(
                    uploaded["public_id"],
                    resource_type=uploaded["resource_type"],
                    type=uploaded["delivery_type"],
                )
            except Exception:
                pass
        return Response(
            {"message": "Document upload failed."},
            status=500,
        )

    return Response(
        ProjectDocumentSerializer(document).data,
        status=201,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_document_detail(request, document_id):
    document = get_object_or_404(
        document_queryset(request.user),
        pk=document_id,
    )

    if request.method == "GET":
        return Response(
            ProjectDocumentSerializer(document).data
        )

    if not can_manage_project(
        request.user, document.project
    ):
        return deny_write()

    if request.method == "DELETE":
        if document.status == "approved":
            return Response({
                "message":
                    "Approved documents cannot be deleted."
            }, status=400)

        versions = list(document.versions.all())

        with transaction.atomic():
            document.delete()

            # Delete files only after the database commit.
            def cleanup():
                for version in versions:
                    try:
                        delete_cloudinary_document(version)
                    except Exception:
                        # Log this failure in production and
                        # retry using a background job.
                        pass

            transaction.on_commit(cleanup)

        return Response(status=204)

    if document.status == "approved":
        return Response({
            "message":
                "Upload a revision before editing this document."
        }, status=400)

    serializer = ProjectDocumentSerializer(
        document,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def project_document_versions(request, document_id):
    document = get_object_or_404(
        document_queryset(request.user),
        pk=document_id,
    )

    if request.method == "GET":
        return Response({
            "results": ProjectDocumentVersionSerializer(
                document.versions.all(),
                many=True,
            ).data
        })

    if not can_manage_project(
        request.user, document.project
    ):
        return deny_write()

    file = request.FILES.get("file")

    try:
        validate_document_file(file)
    except ValidationError as error:
        return upload_error(error)

    uploaded = None

    try:
        with transaction.atomic():
            locked = ProjectDocument.objects.select_for_update().get(
                pk=document.id
            )

            latest = locked.versions.first()
            next_version = (
                latest.version_number + 1
                if latest else 1
            )

            uploaded = upload_project_document(
                file,
                locked.project_id,
                locked.id,
            )

            version = ProjectDocumentVersion.objects.create(
                document=locked,
                version_number=next_version,
                cloudinary_public_id=uploaded["public_id"],
                cloudinary_resource_type=uploaded["resource_type"],
                cloudinary_delivery_type=uploaded["delivery_type"],
                original_filename=file.name[:255],
                file_size=uploaded["file_size"],
                file_format=uploaded["file_format"],
                change_notes=request.data.get(
                    "change_notes", ""
                ),
                uploaded_by=request.user,
            )

            locked.status = "draft"
            locked.reviewed_by = None
            locked.reviewed_at = None
            locked.review_notes = ""
            locked.save()

    except Exception:
        if uploaded:
            try:
                from cloudinary import uploader
                uploader.destroy(
                    uploaded["public_id"],
                    resource_type=uploaded["resource_type"],
                    type=uploaded["delivery_type"],
                )
            except Exception:
                pass

        return Response(
            {"message": "Revision upload failed."},
            status=500,
        )

    return Response(
        ProjectDocumentVersionSerializer(version).data,
        status=201,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def project_document_review(request, document_id):
    document = get_object_or_404(
        document_queryset(request.user),
        pk=document_id,
    )

    if not can_manage_project(
        request.user, document.project
    ):
        return deny_write()

    target = request.data.get("status")

    transitions = {
        "draft": ["under_review"],
        "under_review": ["approved", "rejected"],
        "rejected": ["draft"],
        "approved": [],
    }

    if target not in transitions.get(document.status, []):
        return Response({
            "message": "Invalid status transition."
        }, status=400)

    document.status = target

    if target in ("approved", "rejected"):
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()
        document.review_notes = request.data.get(
            "review_notes", ""
        )
    else:
        document.reviewed_by = None
        document.reviewed_at = None
        document.review_notes = ""

    document.save()

    return Response(
        ProjectDocumentSerializer(document).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_document_download(
    request,
    document_id,
    version_id,
):
    document = get_object_or_404(
        document_queryset(request.user),
        pk=document_id,
    )

    version = get_object_or_404(
        ProjectDocumentVersion,
        pk=version_id,
        document=document,
    )

    try:
        url = generate_document_download_url(version)
    except Exception:
        return Response({
            "message": "Could not generate download link."
        }, status=502)

    return Response({
        "download_url": url,
        "filename": version.original_filename,
        "expires_in": 300,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_document_summary(request):
    project_id = request.query_params.get("project_id")

    if not project_id:
        return Response(
            {"message": "project_id is required."},
            status=400,
        )

    project = get_accessible_project(
        request.user, project_id
    )

    documents = ProjectDocument.objects.filter(
        project=project
    )

    return Response({
        "total_documents": documents.count(),
        "approved": documents.filter(
            status="approved"
        ).count(),
        "under_review": documents.filter(
            status="under_review"
        ).count(),
        "draft": documents.filter(
            status="draft"
        ).count(),
        "rejected": documents.filter(
            status="rejected"
        ).count(),
    })
