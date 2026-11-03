from unit_app.api_views.common_imports import *

from .serializers import (
    QualityInspectionSerializer as InspectionSerializer,
    QualityChecklistSerializer as ChecklistSerializer,
    QualityDefectSerializer as DefectSerializer,
    QualityEvidenceSerializer as EvidenceSerializer,
)

from .helper import *


def fail(message, status=400):
    return Response({"message": message}, status=status)


def inspection_for(request, inspection_id):
    inspection = get_object_or_404(
        Inspection.objects.select_related("project"),
        pk=inspection_id,
    )
    get_accessible_project(
        request.user, inspection.project_id
    )
    return inspection


def can_edit(request, inspection):
    return can_manage_project(
        request.user, inspection.project
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quality_inspections(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return fail("project_id is required.")

        project = get_accessible_project(
            request.user, project_id
        )

        qs = Inspection.objects.filter(
            project=project
        ).prefetch_related(
            "checklist_items", "defects", "evidence"
        )

        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        return Response({
            "results": InspectionSerializer(
                qs, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return fail("project is required.")

    project = get_accessible_project(
        request.user, project_id
    )
    if not can_manage_project(request.user, project):
        return fail("Permission denied.", 403)

    serializer = InspectionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phase = serializer.validated_data.get("phase")
    if phase and phase.project_id != project.pk:
        return fail("Phase belongs to another project.")

    inspection = serializer.save(
        project=project,
        inspection_number=(
            f"INS-{uuid.uuid4().hex[:12].upper()}"
        ),
        created_by=request.user,
    )

    return Response(
        InspectionSerializer(inspection).data,
        status=201,
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def quality_inspection_detail(request, inspection_id):
    inspection = inspection_for(
        request, inspection_id
    )

    if request.method == "GET":
        return Response(
            InspectionSerializer(inspection).data
        )

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    if inspection.status not in ("draft", "in_progress"):
        return fail("Inspection cannot be edited now.")

    serializer = InspectionSerializer(
        inspection,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)

    phase = serializer.validated_data.get("phase")
    if phase and phase.project_id != inspection.project_id:
        return fail("Phase belongs to another project.")

    # Prevent moving inspections between projects.
    if (
        "project" in serializer.validated_data
        and serializer.validated_data["project"].pk
        != inspection.project_id
    ):
        return fail("Cannot change inspection project.")

    serializer.save(project=inspection.project)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quality_inspection_status(request, inspection_id):
    inspection = inspection_for(
        request, inspection_id
    )

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    target = request.data.get("status")

    transitions = {
        "draft": {"in_progress"},
        "in_progress": {"submitted"},
        "submitted": {"approved", "rejected"},
        "rejected": {"in_progress"},
    }

    with transaction.atomic():
        inspection = Inspection.objects.select_for_update().get(
            pk=inspection.pk
        )

        if target not in transitions.get(
            inspection.status, set()
        ):
            return fail("Invalid inspection status transition.")

        if target == "submitted":
            checks = inspection.checklist_items.all()
            if not checks.exists():
                return fail("Add checklist items first.")
            if checks.filter(result="pending").exists():
                return fail("Complete all checklist items.")

        if target == "approved":
            if inspection.checklist_items.filter(
                result="fail"
            ).exists():
                return fail(
                    "Failed checklist items must be resolved "
                    "and re-inspected before approval."
                )
            if inspection.defects.exclude(
                status="verified"
            ).exists():
                return fail(
                    "All defects must be verified first."
                )

        inspection.status = target

        if target in ("approved", "rejected"):
            inspection.reviewed_by = request.user
            inspection.reviewed_at = timezone.now()
            inspection.review_notes = request.data.get(
                "review_notes", ""
            )

        if target == "submitted":
            inspection.inspected_date = (
                inspection.inspected_date
                or timezone.localdate()
            )

        inspection.save()

    return Response(
        InspectionSerializer(inspection).data
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quality_checklists(request, inspection_id):
    inspection = inspection_for(
        request, inspection_id
    )

    if request.method == "GET":
        return Response({
            "results": ChecklistSerializer(
                inspection.checklist_items.all(),
                many=True,
            ).data
        })

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    if inspection.status not in ("draft", "in_progress"):
        return fail("Inspection is locked.")

    serializer = ChecklistSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    item = serializer.save(inspection=inspection)

    return Response(
        ChecklistSerializer(item).data,
        status=201,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def quality_checklist_detail(request, checklist_id):
    item = get_object_or_404(
        Checklist.objects.select_related(
            "inspection__project"
        ),
        pk=checklist_id,
    )
    inspection = inspection_for(
        request, item.inspection_id
    )

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    if inspection.status not in ("draft", "in_progress"):
        return fail("Inspection is locked.")

    serializer = ChecklistSerializer(
        item, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quality_defects(request, inspection_id):
    inspection = inspection_for(
        request, inspection_id
    )

    if request.method == "GET":
        return Response({
            "results": DefectSerializer(
                inspection.defects.all(),
                many=True,
            ).data
        })

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    if inspection.status not in (
        "draft", "in_progress", "rejected"
    ):
        return fail("Cannot add defects now.")

    serializer = DefectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    checklist_item = serializer.validated_data.get(
        "checklist_item"
    )
    if checklist_item and (
        checklist_item.inspection_id != inspection.pk
    ):
        return fail("Checklist item belongs to another inspection.")

    defect = serializer.save(inspection=inspection)

    return Response(
        DefectSerializer(defect).data,
        status=201,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quality_defect_status(request, defect_id):
    defect = get_object_or_404(
        Defect.objects.select_related(
            "inspection__project"
        ),
        pk=defect_id,
    )
    inspection = inspection_for(
        request, defect.inspection_id
    )

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    target = request.data.get("status")
    transitions = {
        "open": {"in_progress"},
        "in_progress": {"resolved"},
        "resolved": {"verified", "in_progress"},
        "verified": {"in_progress"},
    }

    if target not in transitions.get(
        defect.status, set()
    ):
        return fail("Invalid defect status transition.")

    if target == "resolved":
        corrective_action = request.data.get(
            "corrective_action", ""
        ).strip()
        if not corrective_action:
            return fail("Corrective action is required.")
        defect.corrective_action = corrective_action

    if target == "verified":
        defect.verified_by = request.user
        defect.verification_notes = request.data.get(
            "verification_notes", ""
        )

    if target == "in_progress":
        defect.verified_by = None
        defect.verification_notes = ""

    defect.status = target
    defect.save()

    return Response(DefectSerializer(defect).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def quality_upload_evidence(request, inspection_id):
    inspection = inspection_for(
        request, inspection_id
    )

    if not can_edit(request, inspection):
        return fail("Permission denied.", 403)

    file = request.FILES.get("file")
    if not file:
        return fail("Image file is required.")

    if file.size > 10 * 1024 * 1024:
        return fail("Maximum image size is 10 MB.")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        return fail("Only JPEG, PNG and WebP are supported.")

    defect = None
    defect_id = request.data.get("defect")
    if defect_id:
        defect = get_object_or_404(
            Defect,
            pk=defect_id,
            inspection=inspection,
        )

    # The Cloudinary SDK uses your existing cloudinary.config.
    result = cloudinary.uploader.upload(
        file,
        folder=(
            f"unit/quality/project_{inspection.project_id}"
            f"/inspection_{inspection.id}"
        ),
        resource_type="image",
        overwrite=False,
    )

    evidence = Evidence.objects.create(
        inspection=inspection,
        defect=defect,
        cloudinary_public_id=result["public_id"],
        resource_type="image",
        file_url=result["secure_url"],
        caption=request.data.get("caption", ""),
        uploaded_by=request.user,
    )

    return Response(
        EvidenceSerializer(evidence).data,
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quality_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return fail("project_id is required.")

    project = get_accessible_project(
        request.user, project_id
    )

    inspections = Inspection.objects.filter(
        project=project
    )
    defects = Defect.objects.filter(
        inspection__project=project
    )
    checks = Checklist.objects.filter(
        inspection__project=project
    )

    return Response({
        "total_inspections": inspections.count(),
        "draft_inspections": inspections.filter(
            status="draft"
        ).count(),
        "in_progress_inspections": inspections.filter(
            status="in_progress"
        ).count(),
        "submitted_inspections": inspections.filter(
            status="submitted"
        ).count(),
        "approved_inspections": inspections.filter(
            status="approved"
        ).count(),
        "rejected_inspections": inspections.filter(
            status="rejected"
        ).count(),
        "failed_checks": checks.filter(
            result="fail"
        ).count(),
        "open_defects": defects.exclude(
            status="verified"
        ).count(),
        "critical_defects": defects.filter(
            severity="critical"
        ).exclude(status="verified").count(),
    })
