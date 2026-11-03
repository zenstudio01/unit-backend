from unit_app.api_views.common_imports import *


from .serializers import (
    ProjectPhaseSerializer,
    ProjectMilestoneSerializer,
)

from .helper import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_planning_projects(request):
    projects = allowed_projects(request.user).order_by("name")

    return Response({
        "results": [
            {
                "id": p.id,
                "name": p.name,
                "project_code": p.project_code,
                "status": p.status,
                "organization_id": p.organization_id,
            }
            for p in projects
        ]
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_phases(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"message": "project_id is required."},
                status=400
            )

        project = get_accessible_project(
            request.user, project_id
        )

        phases = ProjectPhase.objects.filter(
            project=project
        ).annotate(
            milestone_count=Count("milestones")
        ).order_by("sequence", "id")

        return Response({
            "results": ProjectPhaseSerializer(
                phases, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return Response(
            {"project": ["This field is required."]},
            status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )
    if not can_manage_project(request.user, project):
        return write_denied()

    serializer = ProjectPhaseSerializer(
        data={**request.data, "project": project.id}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_phase_detail(request, phase_id):
    phase = get_object_or_404(
        ProjectPhase.objects.select_related("project"),
        pk=phase_id,
        project__in=allowed_projects(request.user),
    )

    if request.method == "GET":
        return Response(
            ProjectPhaseSerializer(phase).data
        )

    if not can_manage_project(request.user, phase.project):
        return write_denied()

    if request.method == "DELETE":
        if phase.milestones.exists():
            return Response({
                "message":
                    "Reassign or delete this phase's milestones first."
            }, status=400)

        phase.delete()
        return Response(status=204)

    if (
        "project" in request.data
        and str(request.data["project"]) != str(phase.project_id)
    ):
        return Response({
            "project": ["Moving phases between projects is not supported."]
        }, status=400)

    serializer = ProjectPhaseSerializer(
        phase,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_milestones(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"message": "project_id is required."},
                status=400
            )

        project = get_accessible_project(
            request.user, project_id
        )

        milestones = ProjectMilestone.objects.filter(
            project=project
        ).select_related("phase", "project").order_by(
            "due_date", "id"
        )

        return Response({
            "results": ProjectMilestoneSerializer(
                milestones, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return Response(
            {"project": ["This field is required."]},
            status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )
    if not can_manage_project(request.user, project):
        return write_denied()

    phase_id = request.data.get("phase")
    if phase_id:
        get_object_or_404(
            ProjectPhase,
            pk=phase_id,
            project=project
        )

    serializer = ProjectMilestoneSerializer(
        data={**request.data, "project": project.id}
    )
    serializer.is_valid(raise_exception=True)

    milestone = serializer.save()

    if milestone.status == "completed":
        milestone.completed_at = timezone.now()
        milestone.save(update_fields=["completed_at"])

    return Response(
        ProjectMilestoneSerializer(milestone).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_milestone_detail(request, milestone_id):
    milestone = get_object_or_404(
        ProjectMilestone.objects.select_related(
            "project", "phase"
        ),
        pk=milestone_id,
        project__in=allowed_projects(request.user),
    )

    if request.method == "GET":
        return Response(
            ProjectMilestoneSerializer(milestone).data
        )

    if not can_manage_project(request.user, milestone.project):
        return write_denied()

    if request.method == "DELETE":
        milestone.delete()
        return Response(status=204)

    if (
        "project" in request.data
        and str(request.data["project"]) != str(milestone.project_id)
    ):
        return Response({
            "project": ["Moving milestones between projects is not supported."]
        }, status=400)

    phase_id = request.data.get("phase", milestone.phase_id)
    if phase_id:
        get_object_or_404(
            ProjectPhase,
            pk=phase_id,
            project=milestone.project
        )

    serializer = ProjectMilestoneSerializer(
        milestone,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)

    previous_status = milestone.status
    milestone = serializer.save()

    if milestone.status == "completed":
        if previous_status != "completed" or not milestone.completed_at:
            milestone.completed_at = timezone.now()
            milestone.save(update_fields=["completed_at"])
    elif milestone.completed_at is not None:
        milestone.completed_at = None
        milestone.save(update_fields=["completed_at"])

    return Response(
        ProjectMilestoneSerializer(milestone).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_planning_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return Response(
            {"message": "project_id is required."},
            status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )

    phases = ProjectPhase.objects.filter(project=project)
    milestones = ProjectMilestone.objects.filter(
        project=project
    )

    today = timezone.localdate()

    overdue = milestones.filter(
        due_date__lt=today
    ).exclude(
        status__in=["completed", "cancelled"]
    ).count()

    active_phases = phases.exclude(
        status="cancelled"
    )
    total_phases = active_phases.count()

    avg_progress = (
        sum(
            float(p.completion_percentage)
            for p in active_phases
        ) / total_phases
        if total_phases else 0
    )

    return Response({
        "project_id": project.id,
        "total_phases": phases.count(),
        "completed_phases": phases.filter(
            status="completed"
        ).count(),
        "in_progress_phases": phases.filter(
            status="in_progress"
        ).count(),
        "total_milestones": milestones.count(),
        "completed_milestones": milestones.filter(
            status="completed"
        ).count(),
        "overdue_milestones": overdue,
        "average_phase_progress": round(avg_progress, 2),
    })
