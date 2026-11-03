from unit_app.api_views.common_imports import *

from .serializers import (
    WorkforceSubcontractorSerializer as SubcontractorSerializer,
    WorkforceWorkerSerializer as WorkerSerializer,
    WorkforceAssignmentSerializer as AssignmentSerializer,
    WorkforceAttendanceSerializer as AttendanceSerializer,
    WorkforceTaskSerializer as TaskSerializer,
    WorkforcePaymentSerializer as PaymentSerializer,
)
from .helper import *


def failure(message, status=400):
    return Response({"message": message}, status=status)


def project_for(request, project_id):
    return get_accessible_project(request.user, project_id)


def writable(request, project):
    return can_manage_project(request.user, project)


def get_assignment(project, assignment_id):
    return get_object_or_404(
        Assignment.objects.select_related("worker", "project"),
        pk=assignment_id,
        project=project,
    )


def assignment_earnings(assignment):
    return sum(
        (row.earned_amount for row in
         assignment.attendance_records.all()),
        Decimal("0"),
    )


def assignment_paid(assignment):
    return (
        WorkforcePayment.objects.filter(
            assignment=assignment
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_subcontractors(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project_id")
    )
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = Subcontractor.objects.filter(
            organization=project.organization
        ).order_by("name")
        return Response({
            "results": SubcontractorSerializer(
                records, many=True
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = SubcontractorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    obj = serializer.save(
        organization=project.organization
    )
    return Response(
        SubcontractorSerializer(obj).data, status=201
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_workers(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project_id")
    )
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = Worker.objects.filter(
            organization=project.organization
        ).order_by("full_name")
        return Response({
            "results": WorkerSerializer(
                records, many=True
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = WorkerSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    subcontractor = serializer.validated_data.get(
        "subcontractor"
    )
    if subcontractor and (
        subcontractor.organization_id != project.organization_id
    ):
        return failure("Subcontractor belongs to another organization.")

    obj = serializer.save(
        organization=project.organization
    )
    return Response(WorkerSerializer(obj).data, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_assignments(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project")
    )
    if not project_id:
        return failure("project is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = Assignment.objects.filter(
            project=project
        ).select_related("worker")
        return Response({
            "results": AssignmentSerializer(
                records, many=True
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    worker = get_object_or_404(
        Worker,
        pk=request.data.get("worker"),
        organization=project.organization,
        is_active=True,
    )

    if Assignment.objects.filter(
        project=project,
        worker=worker,
        is_active=True,
    ).exists():
        return failure("Worker already has an active assignment.")

    serializer = AssignmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    obj = serializer.save(
        project=project,
        worker=worker,
    )
    return Response(
        AssignmentSerializer(obj).data, status=201
    )



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def workforce_assignment_detail(request, assignment_id):
    assignment = get_object_or_404(
        Assignment.objects.select_related("project"),
        pk=assignment_id,
    )
    project = project_for(request, assignment.project_id)

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = AssignmentSerializer(
        assignment,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_attendance(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project_id")
    )
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = Attendance.objects.filter(
            assignment__project=project
        ).select_related("assignment__worker")

        date = request.query_params.get("date")
        if date:
            records = records.filter(date=date)

        return Response({
            "results": AttendanceSerializer(
                records.order_by("-date", "id"),
                many=True,
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = AttendanceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    assignment = get_assignment(
        project, data["assignment"].pk
    )

    if not assignment.is_active:
        return failure("Assignment is inactive.")

    day = data["date"]
    if day < assignment.start_date or (
        assignment.end_date and day > assignment.end_date
    ):
        return failure("Date is outside assignment period.")

    with transaction.atomic():
        ConstructionProject.objects.select_for_update().get(
            pk=project.pk
        )

        attendance, created = Attendance.objects.update_or_create(
            assignment=assignment,
            date=day,
            defaults={
                "status": data["status"],
                "notes": data.get("notes", ""),
                "daily_rate_snapshot": (
                    assignment.daily_rate
                    if not Attendance.objects.filter(
                        assignment=assignment, date=day
                    ).exists()
                    else Attendance.objects.get(
                        assignment=assignment, date=day
                    ).daily_rate_snapshot
                ),
                "recorded_by": request.user,
            },
        )

    return Response(
        AttendanceSerializer(attendance).data,
        status=201 if created else 200,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_tasks(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project_id")
    )
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = WorkTask.objects.filter(
            assignment__project=project
        ).select_related("assignment__worker")
        return Response({
            "results": TaskSerializer(
                records, many=True
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = TaskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assignment = serializer.validated_data["assignment"]

    if assignment.project_id != project.pk or not assignment.is_active:
        return failure("Invalid project assignment.")

    obj = serializer.save()
    return Response(TaskSerializer(obj).data, status=201)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def workforce_task_detail(request, task_id):
    task = get_object_or_404(
        WorkTask.objects.select_related(
            "assignment__project"
        ),
        pk=task_id,
    )
    project = project_for(
        request, task.assignment.project_id
    )

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = TaskSerializer(
        task, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)

    if (
        "assignment" in serializer.validated_data
        and serializer.validated_data["assignment"].pk
        != task.assignment_id
    ):
        return failure("Task reassignment is not supported.")

    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def workforce_payments(request):
    project_id = (
        request.query_params.get("project_id")
        if request.method == "GET"
        else request.data.get("project_id")
    )
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)

    if request.method == "GET":
        records = WorkforcePayment.objects.filter( assignment__project=project)
        return Response({
            "results": PaymentSerializer(
                records.order_by("-payment_date", "-id"),
                many=True,
            ).data
        })

    if not writable(request, project):
        return failure("Permission denied.", 403)

    serializer = PaymentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    assignment = serializer.validated_data["assignment"]

    if assignment.project_id != project.pk:
        return failure("Invalid project assignment.")

    with transaction.atomic():
        ConstructionProject.objects.select_for_update().get(
            pk=project.pk
        )

        earned = assignment_earnings(assignment)
        paid = assignment_paid(assignment)
        amount = serializer.validated_data["amount"]

        if amount > earned - paid:
            return failure(
                f"Payment exceeds outstanding wages: "
                f"{earned - paid}."
            )

        obj = serializer.save(recorded_by=request.user)

    return Response(
        PaymentSerializer(obj).data, status=201
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workforce_payroll(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return failure("project_id is required.")

    project = project_for(request, project_id)
    assignments = Assignment.objects.filter(
        project=project
    ).select_related("worker").prefetch_related(
        "attendance_records", "payments"
    )

    results = []
    for assignment in assignments:
        earned = assignment_earnings(assignment)
        paid = assignment_paid(assignment)

        results.append({
            "assignment": assignment.id,
            "worker": assignment.worker_id,
            "worker_name": assignment.worker.full_name,
            "earned": str(earned),
            "paid": str(paid),
            "outstanding": str(earned - paid),
        })

    return Response({"results": results})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workforce_summary(request):
    project_id = request.query_params.get("project_id")

    if not project_id:
        return Response(
            {"message": "project_id is required."},
            status=400,
        )

    project = project_for(request, project_id)
    today = timezone.localdate()

    assignments = Assignment.objects.filter(
        project=project
    )

    active_assignments = assignments.filter(
        is_active=True,
        start_date__lte=today,
    ).filter(
        Q(end_date__isnull=True) |
        Q(end_date__gte=today)
    )

    today_attendance = Attendance.objects.filter(
        assignment__project=project,
        date=today,
    )

    all_attendance = Attendance.objects.filter(
        assignment__project=project
    )

    total_earned = sum(
        (
            record.earned_amount
            for record in all_attendance
        ),
        Decimal("0.00"),
    )

    total_paid = (
        WorkforcePayment.objects.filter(
            assignment__project=project
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    present_today = today_attendance.filter(
        status="present"
    ).count()

    half_day_today = today_attendance.filter(
        status="half_day"
    ).count()

    absent_today = today_attendance.filter(
        status="absent"
    ).count()

    marked_today = today_attendance.filter(
        assignment__in=active_assignments
    ).count()

    unmarked_today = max(
        0,
        active_assignments.count() - marked_today
    )

    total_tasks = WorkTask.objects.filter(
        assignment__project=project
    ).count()

    return Response({
        "project_id": project.id,
        "date": today.isoformat(),

        "assigned_workers": active_assignments.count(),
        "present_today": present_today,
        "half_day_today": half_day_today,
        "absent_today": absent_today,
        "unmarked_today": unmarked_today,

        "total_earned": str(total_earned),
        "total_paid": str(total_paid),
        "outstanding": str(
            total_earned - total_paid
        ),

        "total_tasks": total_tasks,
    })

