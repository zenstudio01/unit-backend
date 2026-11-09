
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from unit_app.models import (
    ConstructionProject,
    ProjectStakeholder,
)
from unit_app.serializers.project_stakeholder_serializers import (
    ProjectStakeholderSerializer,
    StakeholderWriteSerializer,
)


def get_accessible_project(request, project_id):
    """
    Restrict project access to active organization members.
    Superusers can access all projects.
    """
    qs = ConstructionProject.objects.select_related(
        "organization"
    )

    if not request.user.is_superuser:
        qs = qs.filter(
            organization__memberships__user=request.user,
            organization__memberships__is_active=True,
        ).distinct()

    return get_object_or_404(qs, pk=project_id)


def get_stakeholder(project, stakeholder_id):
    return get_object_or_404(
        ProjectStakeholder.objects.select_related(
            "project", "user"
        ),
        pk=stakeholder_id,
        project=project,
        organization=project.organization,
    )


def stakeholder_options():
    return {
        "roles": [
            {"value": key, "label": label}
            for key, label in ProjectStakeholder.ROLE_CHOICES
        ],
        "types": [
            {"value": key, "label": label}
            for key, label in ProjectStakeholder.TYPE_CHOICES
        ],
        "statuses": [
            {"value": key, "label": label}
            for key, label in ProjectStakeholder.STATUS_CHOICES
        ],
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_stakeholders(request, project_id):
    project = get_accessible_project(request, project_id)

    if request.method == "GET":
        qs = ProjectStakeholder.objects.filter(
            project=project,
            organization=project.organization,
        ).select_related("user")

        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "").strip()
        state = request.query_params.get("status", "").strip()
        stakeholder_type = request.query_params.get(
            "stakeholder_type", ""
        ).strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(company__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(responsibilities__icontains=search)
            )

        if role:
            qs = qs.filter(role=role)

        if state:
            qs = qs.filter(status=state)

        if stakeholder_type:
            qs = qs.filter(
                stakeholder_type=stakeholder_type
            )

        return Response({
            "project": {
                "id": project.id,
                "name": project.name,
                "project_code": project.project_code,
            },
            "count": qs.count(),
            "results": ProjectStakeholderSerializer(
                qs.order_by("name", "id"),
                many=True,
            ).data,
            "options": stakeholder_options(),
        })

    serializer = StakeholderWriteSerializer(
        data=request.data,
        context={"project": project},
    )
    serializer.is_valid(raise_exception=True)

    stakeholder = serializer.save(
        project=project,
        organization=project.organization,
        created_by=request.user,
    )

    return Response(
        {
            "message": "Stakeholder added successfully.",
            "stakeholder": ProjectStakeholderSerializer(
                stakeholder
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_stakeholder_stats(request, project_id):
    project = get_accessible_project(request, project_id)

    qs = ProjectStakeholder.objects.filter(
        project=project,
        organization=project.organization,
    )

    roles = list(
        qs.values("role")
        .annotate(count=Count("id"))
        .order_by("-count", "role")
    )

    return Response({
        "total": qs.count(),
        "active": qs.filter(status="active").count(),
        "inactive": qs.filter(status="inactive").count(),
        "internal": qs.filter(
            stakeholder_type="internal"
        ).count(),
        "external": qs.filter(
            stakeholder_type="external"
        ).count(),
        "primary_contacts": qs.filter(
            is_primary_contact=True
        ).count(),
        "roles": roles,
    })


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_stakeholder_detail(
    request, project_id, stakeholder_id
):
    project = get_accessible_project(request, project_id)
    stakeholder = get_stakeholder(
        project, stakeholder_id
    )

    if request.method == "GET":
        return Response(
            ProjectStakeholderSerializer(stakeholder).data
        )

    if request.method == "PATCH":
        serializer = StakeholderWriteSerializer(
            stakeholder,
            data=request.data,
            partial=True,
            context={"project": project},
        )
        serializer.is_valid(raise_exception=True)
        stakeholder = serializer.save()

        return Response({
            "message": "Stakeholder updated successfully.",
            "stakeholder": ProjectStakeholderSerializer(
                stakeholder
            ).data,
        })

    stakeholder.delete()

    return Response(
        {"message": "Stakeholder removed successfully."},
        status=status.HTTP_200_OK,
    )
