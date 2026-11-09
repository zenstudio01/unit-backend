from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from unit_app.models import (
    ConstructionProject, OrganizationMembership, ProjectStakeholder,
    ProjectDocument, QualityInspection, QualityDefect,
    ProjectHandover, HandoverChecklistItem, HandoverDocument,
    HandoverInspection, HandoverAcceptance,
)
from unit_app.serializers.project_handover_serializers import (
    ProjectHandoverSerializer, HandoverChecklistItemSerializer,
    HandoverDocumentSerializer, HandoverInspectionSerializer,
    HandoverAcceptanceSerializer, HandoverDecisionInputSerializer,
    HandoverFinalizeSerializer,
)

# Roles allowed to administer a handover. Verify codes against your deployed Role rows.
MANAGER_ROLES = {"organization_owner", "organization_admin", "project_manager"}


def project_for_user(request, project_id):
    """Enforce tenant isolation before accessing any handover record."""
    project = get_object_or_404(
        ConstructionProject.objects.select_related("organization"), pk=project_id
    )
    user = request.user
    if user.is_superuser or project.organization.created_by_id == user.pk:
        return project
    is_member = OrganizationMembership.objects.filter(
        organization_id=project.organization_id, user=user, is_active=True
    ).exists()
    is_client = ProjectStakeholder.objects.filter(
        project=project, organization_id=project.organization_id, user=user,
        role="client", status="active"
    ).exists()
    if not (is_member or is_client):
        raise PermissionDenied("You do not have access to this project.")
    return project


def can_manage(user, project):
    if user.is_superuser or project.organization.created_by_id == user.pk:
        return True
    return OrganizationMembership.objects.filter(
        organization_id=project.organization_id,
        user=user, is_active=True,
    ).filter(
        Q(roles__code__in=MANAGER_ROLES) | Q(primary_role__code__in=MANAGER_ROLES)
    ).exists()


def require_manager(request, project):
    if not can_manage(request.user, project):
        raise PermissionDenied("Only an authorized project manager or organization administrator can do this.")


def get_handover(project):
    return get_object_or_404(
        ProjectHandover.objects.select_related("project", "client", "created_by"),
        project=project, organization_id=project.organization_id,
    )


def ensure_editable(handover):
    if handover.status == "handed_over":
        raise ValidationError({"detail": "A finalized handover cannot be edited."})
    if handover.status == "accepted":
        raise ValidationError({"detail": "An accepted handover must be finalized or formally reopened."})


def ensure_user_member(user_id, project):
    if user_id is None:
        return
    if not OrganizationMembership.objects.filter(
        organization_id=project.organization_id, user_id=user_id, is_active=True
    ).exists() and project.organization.created_by_id != user_id:
        raise ValidationError({"assigned_to": "User is not a member of this organization."})


def readiness(handover):
    items = handover.checklist_items.all()
    docs = handover.handover_documents.select_related("document")
    inspections = handover.handover_inspections.select_related("inspection")

    total = items.count()
    complete = items.filter(status__in=["completed", "not_applicable"]).count()
    pending = total - complete

    # An approved document must also have at least one stored version.
    missing_docs = [
        {"id": d.id, "document_id": d.document_id, "title": d.document.title}
        for d in docs.filter(is_required=True)
        if d.document.status != "approved" or not d.document.versions.exists()
    ]
    pending_inspections = [
        {"id": i.id, "inspection_id": i.inspection_id, "title": i.inspection.title}
        for i in inspections.filter(is_required=True)
        if i.inspection.status != "approved"
    ]

    # Include defects from ALL inspections in the project, not just linked inspections.
    unresolved = QualityDefect.objects.filter(
        inspection__project_id=handover.project_id,
        severity__in=["high", "critical"],
    ).exclude(status="verified")
    unresolved_count = unresolved.count()

    blockers = []
    if not handover.client_id:
        blockers.append("Assign a client stakeholder.")
    if total == 0:
        blockers.append("Add handover checklist items.")
    if pending:
        blockers.append(f"Complete {pending} remaining checklist item(s).")
    if not docs.filter(is_required=True).exists():
        blockers.append("Link at least one required handover document.")
    if missing_docs:
        blockers.append(f"Approve and upload versions for {len(missing_docs)} required document(s).")
    if not inspections.filter(is_required=True).exists():
        blockers.append("Link at least one required final inspection.")
    if pending_inspections:
        blockers.append(f"Approve {len(pending_inspections)} required inspection(s).")
    if unresolved_count:
        blockers.append(f"Verify {unresolved_count} unresolved high/critical defect(s).")

    return {
        "ready": not blockers,
        "checklist_total": total,
        "checklist_completed": complete,
        "checklist_pending": pending,
        "completion_percentage": round(100 * complete / total) if total else 0,
        "documents_total": docs.count(),
        "required_documents_missing": missing_docs,
        "inspections_total": inspections.count(),
        "required_inspections_pending": pending_inspections,
        "high_critical_defects_unverified": unresolved_count,
        "blockers": blockers,
    }


def latest_acceptance(handover):
    return handover.acceptance_records.order_by("-decided_at", "-id").first()


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated])
def handover_overview(request, project_id):
    project = project_for_user(request, project_id)
    if request.method == "POST":
        require_manager(request, project)
        if ProjectHandover.objects.filter(project=project).exists():
            return Response({"detail": "Handover already exists for this project."}, status=409)
        serializer = ProjectHandoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.validated_data.get("client")
        if client and (client.project_id != project.pk or client.organization_id != project.organization_id or client.role != "client"):
            raise ValidationError({"client": "Select a client stakeholder from this project."})
        obj = serializer.save(project=project, organization=project.organization, created_by=request.user)
        return Response(ProjectHandoverSerializer(obj).data, status=201)

    if request.method == "PATCH":
        require_manager(request, project)
        obj = get_handover(project)
        ensure_editable(obj)
        serializer = ProjectHandoverSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        client = serializer.validated_data.get("client", obj.client)
        if client and (client.project_id != project.pk or client.organization_id != project.organization_id or client.role != "client"):
            raise ValidationError({"client": "Select a client stakeholder from this project."})
        obj = serializer.save()
        if obj.status in ["ready_for_review", "rejected"]:
            obj.status = "in_progress"
            obj.save(update_fields=["status", "updated_at"])
        return Response(ProjectHandoverSerializer(obj).data)

    obj = ProjectHandover.objects.filter(project=project, organization=project.organization).first()
    if not obj:
        return Response({"handover": None, "readiness": None, "latest_acceptance": None})
    decision = latest_acceptance(obj)
    return Response({
        "handover": ProjectHandoverSerializer(obj).data,
        "readiness": readiness(obj),
        "latest_acceptance": HandoverAcceptanceSerializer(decision).data if decision else None,
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def checklist_collection(request, project_id):
    project = project_for_user(request, project_id)
    handover = get_handover(project)
    if request.method == "GET":
        return Response(HandoverChecklistItemSerializer(handover.checklist_items.all(), many=True).data)
    require_manager(request, project)
    ensure_editable(handover)
    serializer = HandoverChecklistItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assignee = serializer.validated_data.get("assigned_to")
    ensure_user_member(assignee.pk if assignee else None, project)
    item = serializer.save(handover=handover)
    if item.status == "completed":
        item.completed_at = timezone.now()
        item.completed_by = request.user
        item.save(update_fields=["completed_at", "completed_by"])
    return Response(HandoverChecklistItemSerializer(item).data, status=201)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def checklist_detail(request, project_id, item_id):
    project = project_for_user(request, project_id)
    handover = get_handover(project)
    item = get_object_or_404(HandoverChecklistItem, pk=item_id, handover=handover)
    if request.method == "GET":
        return Response(HandoverChecklistItemSerializer(item).data)
    require_manager(request, project)
    ensure_editable(handover)
    if request.method == "DELETE":
        item.delete()
        return Response(status=204)
    serializer = HandoverChecklistItemSerializer(item, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    assignee = serializer.validated_data.get("assigned_to", item.assigned_to)
    ensure_user_member(assignee.pk if assignee else None, project)
    previous_status = item.status
    item = serializer.save()
    if item.status == "completed" and (previous_status != "completed" or not item.completed_at):
        item.completed_at, item.completed_by = timezone.now(), request.user
        item.save(update_fields=["completed_at", "completed_by"])
    elif item.status != "completed" and item.completed_at:
        item.completed_at, item.completed_by = None, None
        item.save(update_fields=["completed_at", "completed_by"])
    return Response(HandoverChecklistItemSerializer(item).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def document_collection(request, project_id):
    project = project_for_user(request, project_id)
    handover = get_handover(project)
    if request.method == "GET":
        qs = handover.handover_documents.select_related("document", "added_by")
        return Response(HandoverDocumentSerializer(qs, many=True).data)
    require_manager(request, project)
    ensure_editable(handover)
    serializer = HandoverDocumentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    doc = serializer.validated_data["document"]
    if doc.project_id != project.pk:
        raise ValidationError({"document": "Document must belong to the selected project."})
    if handover.handover_documents.filter(document=doc).exists():
        raise ValidationError({"document": "Document already linked."})
    link = serializer.save(handover=handover, added_by=request.user)
    return Response(HandoverDocumentSerializer(link).data, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def document_detail(request, project_id, link_id):
    project = project_for_user(request, project_id)
    require_manager(request, project)
    handover = get_handover(project)
    ensure_editable(handover)
    link = get_object_or_404(HandoverDocument, pk=link_id, handover=handover)
    if request.method == "DELETE":
        link.delete()
        return Response(status=204)
    serializer = HandoverDocumentSerializer(link, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    doc = serializer.validated_data.get("document", link.document)
    if doc.project_id != project.pk:
        raise ValidationError({"document": "Document must belong to this project."})
    if handover.handover_documents.exclude(pk=link.pk).filter(document=doc).exists():
        raise ValidationError({"document": "Document already linked."})
    link = serializer.save()
    return Response(HandoverDocumentSerializer(link).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def inspection_collection(request, project_id):
    project = project_for_user(request, project_id)
    handover = get_handover(project)
    if request.method == "GET":
        return Response(HandoverInspectionSerializer(
            handover.handover_inspections.select_related("inspection"), many=True
        ).data)
    require_manager(request, project)
    ensure_editable(handover)
    serializer = HandoverInspectionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inspection = serializer.validated_data["inspection"]
    if inspection.project_id != project.pk:
        raise ValidationError({"inspection": "Inspection must belong to this project."})
    if handover.handover_inspections.filter(inspection=inspection).exists():
        raise ValidationError({"inspection": "Inspection already linked."})
    link = serializer.save(handover=handover)
    return Response(HandoverInspectionSerializer(link).data, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def inspection_detail(request, project_id, link_id):
    project = project_for_user(request, project_id)
    require_manager(request, project)
    handover = get_handover(project)
    ensure_editable(handover)
    link = get_object_or_404(HandoverInspection, pk=link_id, handover=handover)
    if request.method == "DELETE":
        link.delete()
        return Response(status=204)
    serializer = HandoverInspectionSerializer(link, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    inspection = serializer.validated_data.get("inspection", link.inspection)
    if inspection.project_id != project.pk:
        raise ValidationError({"inspection": "Inspection must belong to this project."})
    if handover.handover_inspections.exclude(pk=link.pk).filter(inspection=inspection).exists():
        raise ValidationError({"inspection": "Inspection already linked."})
    link = serializer.save()
    return Response(HandoverInspectionSerializer(link).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def handover_readiness(request, project_id):
    project = project_for_user(request, project_id)
    return Response(readiness(get_handover(project)))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_for_review(request, project_id):
    project = project_for_user(request, project_id)
    require_manager(request, project)
    with transaction.atomic():
        handover = get_object_or_404(ProjectHandover.objects.select_for_update(), project=project)
        ensure_editable(handover)
        report = readiness(handover)
        if not report["ready"]:
            return Response({"detail": "Handover is not ready.", "readiness": report}, status=400)
        handover.status = "ready_for_review"
        handover.save(update_fields=["status", "updated_at"])
    return Response({"handover": ProjectHandoverSerializer(handover).data, "readiness": report})


def can_decide(user, handover):
    """Client must be linked to a logged-in account. No proxy approval."""
    return bool(handover.client_id and handover.client.role == "client" and
                handover.client.status == "active" and handover.client.user_id == user.pk)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def acceptance_collection(request, project_id):
    project = project_for_user(request, project_id)
    handover = get_handover(project)
    if request.method == "GET":
        return Response(HandoverAcceptanceSerializer(handover.acceptance_records.all(), many=True).data)
    if not can_decide(request.user, handover):
        raise PermissionDenied("Only the linked client stakeholder can submit a decision.")
    input_serializer = HandoverDecisionInputSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        handover = get_object_or_404(
            ProjectHandover.objects.select_for_update().select_related("client"), pk=handover.pk
        )
        if handover.status != "ready_for_review":
            raise ValidationError({"detail": "Handover must be submitted for review first."})
        decision = input_serializer.validated_data["decision"]
        if decision == "accepted":
            report = readiness(handover)
            if not report["ready"]:
                return Response({"detail": "Handover is no longer ready.", "readiness": report}, status=400)
        acceptance = HandoverAcceptance.objects.create(
            handover=handover, client=handover.client, decision=decision,
            comments=input_serializer.validated_data["comments"], recorded_by=request.user,
        )
        handover.status = "accepted" if decision == "accepted" else "rejected"
        handover.review_notes = acceptance.comments
        handover.save(update_fields=["status", "review_notes", "updated_at"])
    return Response(HandoverAcceptanceSerializer(acceptance).data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reopen_handover(request, project_id):
    project = project_for_user(request, project_id)
    require_manager(request, project)
    with transaction.atomic():
        handover = get_object_or_404(ProjectHandover.objects.select_for_update(), project=project)
        if handover.status not in ["rejected", "ready_for_review", "accepted"]:
            raise ValidationError({"detail": "Only a review-stage or rejected/accepted handover can be reopened."})
        handover.status = "in_progress"
        handover.save(update_fields=["status", "updated_at"])
    return Response(ProjectHandoverSerializer(handover).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def finalize_handover(request, project_id):
    project = project_for_user(request, project_id)
    require_manager(request, project)
    serializer = HandoverFinalizeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        handover = get_object_or_404(
            ProjectHandover.objects.select_for_update(), project=project
        )
        if handover.status != "accepted":
            raise ValidationError({"detail": "Client acceptance is required before final handover."})
        decision = latest_acceptance(handover)
        if not decision or decision.decision != "accepted" or decision.client_id != handover.client_id:
            raise ValidationError({"detail": "A current client acceptance is required."})
        report = readiness(handover)
        if not report["ready"]:
            return Response({"detail": "Handover is no longer ready.", "readiness": report}, status=400)
        handover.status = "handed_over"
        handover.actual_handover_date = timezone.localdate()
        if "handover_notes" in serializer.validated_data:
            handover.handover_notes = serializer.validated_data["handover_notes"]
        handover.save(update_fields=["status", "actual_handover_date", "handover_notes", "updated_at"])
    return Response({"handover": ProjectHandoverSerializer(handover).data, "readiness": report})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def handover_options(request, project_id):
    project = project_for_user(request, project_id)
    return Response({
        "clients": list(ProjectStakeholder.objects.filter(
            project=project, organization_id=project.organization_id, role="client", status="active"
        ).values("id", "name", "company", "email", "user_id")),
        "documents": list(ProjectDocument.objects.filter(project=project).values("id", "title", "status", "category")),
        "inspections": list(QualityInspection.objects.filter(project=project).values(
            "id", "title", "inspection_number", "status"
        )),
        "assignees": list(OrganizationMembership.objects.filter(
            organization_id=project.organization_id, is_active=True
        ).values("user_id", "user__username", "user__first_name", "user__last_name").distinct()),
        "checklist_categories": list(HandoverChecklistItem.CATEGORY_CHOICES),
        "document_categories": list(HandoverDocument.CATEGORY_CHOICES),
    })