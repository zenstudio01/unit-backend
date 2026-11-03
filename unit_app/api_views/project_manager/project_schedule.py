from unit_app.api_views.common_imports import *
from .serializers import ProjectScheduleActivitySerializer
from .helper import *


def activities_for(user):
    return ProjectScheduleActivity.objects.filter(
        project__in=allowed_projects(user)
    )


def validate_schedule_links(project, data, instance=None):
    relationships = {
        "phase": (ProjectPhase, "project_id"),
        "task": (ProjectTask, "project_id"),
        "milestone": (ProjectMilestone, "project_id"),
        "predecessor": (ProjectScheduleActivity, "project_id"),
    }

    for field, (model, project_field) in relationships.items():
        if field not in data:
            continue

        value = data.get(field)
        if value in (None, ""):
            continue

        if not model.objects.filter(
            pk=value,
            **{project_field: project.pk}
        ).exists():
            return {field: ["Invalid record for this project."]}

    predecessor_id = data.get(
        "predecessor",
        instance.predecessor_id if instance else None
    )

    if predecessor_id:
        if instance and str(predecessor_id) == str(instance.pk):
            return {
                "predecessor": ["An activity cannot depend on itself."]
            }

        # Prevent cycles in the predecessor chain.
        visited = set()
        current_id = predecessor_id

        while current_id:
            if current_id in visited:
                return {
                    "predecessor": ["Circular dependency detected."]
                }

            visited.add(current_id)

            if instance and str(current_id) == str(instance.pk):
                return {
                    "predecessor": ["Circular dependency detected."]
                }

            current_id = (
                ProjectScheduleActivity.objects.filter(
                    pk=current_id, project=project
                ).values_list("predecessor_id", flat=True).first()
            )

    return None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def schedule_activities(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"message": "project_id is required."}, status=400
            )

        project = get_accessible_project(
            request.user, project_id
        )

        queryset = activities_for(request.user).filter(
            project=project
        ).select_related("phase", "predecessor")

        status_value = request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        return Response({
            "results": ProjectScheduleActivitySerializer(
                queryset, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return Response(
            {"project": ["This field is required."]}, status=400
        )

    project = get_accessible_project(request.user, project_id)

    if not can_manage_project(request.user, project):
        return Response({"message": "Permission denied."}, status=403)

    errors = validate_schedule_links(project, request.data)
    if errors:
        return Response(errors, status=400)

    serializer = ProjectScheduleActivitySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    activity = serializer.save(project=project)

    return Response(
        ProjectScheduleActivitySerializer(activity).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def schedule_activity_detail(request, activity_id):
    activity = get_object_or_404(
        activities_for(request.user).select_related("project"),
        pk=activity_id
    )

    if request.method == "GET":
        return Response(
            ProjectScheduleActivitySerializer(activity).data
        )

    if not can_manage_project(request.user, activity.project):
        return Response({"message": "Permission denied."}, status=403)

    if request.method == "DELETE":
        activity.delete()
        return Response(status=204)

    errors = validate_schedule_links(
        activity.project, request.data, activity
    )
    if errors:
        return Response(errors, status=400)

    serializer = ProjectScheduleActivitySerializer(
        activity, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def schedule_gantt(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return Response(
            {"message": "project_id is required."}, status=400
        )

    project = get_accessible_project(request.user, project_id)

    activities = ProjectScheduleActivity.objects.filter(
        project=project
    ).select_related("phase", "predecessor")

    today = timezone.localdate()

    results = []

    for activity in activities:
        duration = (activity.end_date - activity.start_date).days + 1

        results.append({
            "id": activity.id,
            "name": activity.name,
            "start_date": activity.start_date.isoformat(),
            "end_date": activity.end_date.isoformat(),
            "duration_days": duration,
            "progress": float(activity.completion_percentage),
            "status": activity.status,
            "phase_id": activity.phase_id,
            "phase_name": activity.phase.name if activity.phase else None,
            "predecessor_id": activity.predecessor_id,
            "is_critical": activity.is_critical,
            "is_overdue": (
                activity.end_date < today
                and activity.status not in ("completed", "cancelled")
            ),
        })

    return Response({
        "project_id": project.id,
        "today": today.isoformat(),
        "activities": results,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def schedule_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return Response(
            {"message": "project_id is required."}, status=400
        )

    project = get_accessible_project(request.user, project_id)
    activities = ProjectScheduleActivity.objects.filter(project=project)
    today = timezone.localdate()

    totals = activities.aggregate(
        total=Count("id"),
        completed=Count(
            "id", filter=Q(status="completed")
        ),
        in_progress=Count(
            "id", filter=Q(status="in_progress")
        ),
        overdue=Count(
            "id",
            filter=Q(end_date__lt=today)
            & ~Q(status__in=["completed", "cancelled"])
        ),
        critical=Count(
            "id", filter=Q(is_critical=True)
        ),
        average_progress=Avg("completion_percentage"),
    )

    return Response({
        "project_id": project.id,
        "total_activities": totals["total"],
        "completed": totals["completed"],
        "in_progress": totals["in_progress"],
        "overdue": totals["overdue"],
        "critical": totals["critical"],
        "average_progress": totals["average_progress"] or Decimal("0"),
    })
