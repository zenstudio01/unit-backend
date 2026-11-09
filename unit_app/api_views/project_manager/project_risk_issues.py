
import uuid

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from django.db.models import Count, F, IntegerField, ExpressionWrapper
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from unit_app.models import (
    ConstructionProject,
    ProjectRiskIssue,
    ProjectStakeholder,
)
from unit_app.serializers.project_risk_issue_serializers import (
    ProjectRiskIssueSerializer,
    ProjectRiskIssueWriteSerializer,
)


def accessible_project(request, project_id):
    qs = ConstructionProject.objects.select_related("organization")

    if not request.user.is_superuser:
        qs = qs.filter(
            organization__memberships__user=request.user,
            organization__memberships__is_active=True,
        ).distinct()

    return get_object_or_404(qs, pk=project_id)


def scoped_items(project):
    return ProjectRiskIssue.objects.filter(
        project=project,
        organization_id=project.organization_id,
    ).select_related("stakeholder", "project")


def make_reference(item_type):
    prefix = "RISK" if item_type == "risk" else "ISSUE"
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def options_payload():
    return {
        "types": [
            {"value": k, "label": v}
            for k, v in ProjectRiskIssue.TYPE_CHOICES
        ],
        "categories": [
            {"value": k, "label": v}
            for k, v in ProjectRiskIssue.CATEGORY_CHOICES
        ],
        "statuses": [
            {"value": k, "label": v}
            for k, v in ProjectRiskIssue.STATUS_CHOICES
        ],
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_risk_issues(request, project_id):
    project = accessible_project(request, project_id)

    if request.method == "GET":
        qs = scoped_items(project)

        search = request.query_params.get("search", "").strip()
        item_type = request.query_params.get("type", "").strip()
        item_status = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()

        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(reference__icontains=search)
                | Q(mitigation_plan__icontains=search)
            )

        if item_type in ("risk", "issue"):
            qs = qs.filter(item_type=item_type)

        if item_status:
            qs = qs.filter(status=item_status)

        if severity == "high":
            qs = qs.extra(
                where=["likelihood * impact >= 15"]
            )
        elif severity == "medium":
            qs = qs.extra(
                where=[
                    "likelihood * impact >= 8 "
                    "AND likelihood * impact < 15"
                ]
            )
        elif severity == "low":
            qs = qs.extra(
                where=["likelihood * impact < 8"]
            )

        return Response({
            "count": qs.count(),
            "results": ProjectRiskIssueSerializer(
                qs.order_by("-created_at"),
                many=True,
            ).data,
            "options": options_payload(),
        })

    serializer = ProjectRiskIssueWriteSerializer(
        data=request.data,
        context={"project": project},
    )
    serializer.is_valid(raise_exception=True)

    item_type = serializer.validated_data.get(
        "item_type", "risk"
    )
    item_status = serializer.validated_data.get(
        "status", "open"
    )

    item = serializer.save(
        project=project,
        organization=project.organization,
        reference=make_reference(item_type),
        created_by=request.user,
        resolved_at=(
            timezone.now()
            if item_status in ("resolved", "closed")
            else None
        ),
    )

    return Response(
        {
            "message": "Record created successfully.",
            "item": ProjectRiskIssueSerializer(item).data,
        },
        status=status.HTTP_201_CREATED,
    )






@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_risk_issue_stats(request, project_id):
    project = accessible_project(request, project_id)

    qs = ProjectRiskIssue.objects.filter(
        project=project,
        organization_id=project.organization_id,
    )

    # Calculate likelihood × impact directly in database
    qs = qs.annotate(
        calculated_score=ExpressionWrapper(
            F("likelihood") * F("impact"),
            output_field=IntegerField(),
        )
    )

    # Open records exclude resolved and closed
    open_qs = qs.exclude(
        status__in=["resolved", "closed"]
    )

    return Response({
        "total": qs.count(),

        "risks": qs.filter(
            item_type="risk"
        ).count(),

        "issues": qs.filter(
            item_type="issue"
        ).count(),

        "open": open_qs.count(),

        "resolved": qs.filter(
            status__in=["resolved", "closed"]
        ).count(),

        "high_priority": open_qs.filter(
            calculated_score__gte=15
        ).count(),

        "medium_priority": open_qs.filter(
            calculated_score__gte=8,
            calculated_score__lt=15
        ).count(),

        "low_priority": open_qs.filter(
            calculated_score__lt=8
        ).count(),

        "overdue": open_qs.filter(
            target_date__lt=timezone.localdate()
        ).count(),

        "by_status": list(
            qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        ),
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_risk_issue_options(request, project_id):
    project = accessible_project(request, project_id)

    stakeholders = ProjectStakeholder.objects.filter(
        project=project,
        organization=project.organization,
        status="active",
    ).order_by("name")

    return Response({
        **options_payload(),
        "stakeholders": list(
            stakeholders.values("id", "name", "role")
        ),
    })


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_risk_issue_detail(
    request, project_id, item_id
):
    project = accessible_project(request, project_id)
    item = get_object_or_404(
        scoped_items(project),
        pk=item_id,
    )

    if request.method == "GET":
        return Response(
            ProjectRiskIssueSerializer(item).data
        )

    if request.method == "PATCH":
        serializer = ProjectRiskIssueWriteSerializer(
            item,
            data=request.data,
            partial=True,
            context={"project": project},
        )
        serializer.is_valid(raise_exception=True)

        next_status = serializer.validated_data.get(
            "status", item.status
        )

        resolved_at = item.resolved_at
        if next_status in ("resolved", "closed"):
            resolved_at = resolved_at or timezone.now()
        else:
            resolved_at = None

        item = serializer.save(resolved_at=resolved_at)

        return Response({
            "message": "Record updated successfully.",
            "item": ProjectRiskIssueSerializer(item).data,
        })

    item.delete()

    return Response(
        {"message": "Record deleted successfully."},
        status=status.HTTP_200_OK,
    )
