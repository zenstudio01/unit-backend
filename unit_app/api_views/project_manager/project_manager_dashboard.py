from unit_app.api_views.common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_manager_dashboard(request):

    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not organization_id:

        return JsonResponse(
            {
                "success": False,
                "message":
                    "organization_id is required.",
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    organization = (
        Organization.objects
        .filter(
            id=
                organization_id
        )
        .first()
    )

    if not organization:

        return JsonResponse(
            {
                "success": False,
                "message":
                    "Organization not found.",
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .prefetch_related(
            "roles"
        )
        .select_related(
            "primary_role"
        )
        .first()
    )

    if not membership:

        return JsonResponse(
            {
                "success": False,
                "message":
                    "You do not have access to this organization.",
            },
            status=403,
        )

    # =====================================================
    # PERMISSION
    # =====================================================

    role_codes = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    allowed_roles = {
        "project_manager",
        "organization_owner",
        "organization_admin",
        "site_manager",
        "site_engineer",
    }

    if not role_codes.intersection(
        allowed_roles
    ):

        return JsonResponse(
            {
                "success": False,
                "message":
                    "You do not have permission to access the project management dashboard.",
            },
            status=403,
        )

    today = (
        timezone.localdate()
    )

    upcoming_limit = (
        today
        +
        timedelta(
            days=30
        )
    )

    # =====================================================
    # PROJECTS
    # =====================================================

    projects = (
        ConstructionProject.objects
        .filter(
            organization=
                organization
        )
        .select_related(
            "property",
            "project_manager",
        )
        .order_by(
            "-created_at"
        )
    )

    # If you want project managers to only see their projects,
    # uncomment this:
    #
    # if "organization_owner" not in role_codes and \
    #    "organization_admin" not in role_codes:
    #
    #     projects = projects.filter(
    #         Q(project_manager=user) |
    #         Q(project_manager__isnull=True)
    #     )

    project_ids = (
        projects
        .values_list(
            "id",
            flat=True,
        )
    )

    # =====================================================
    # PROJECT COUNTS
    # =====================================================

    total_projects = (
        projects.count()
    )

    active_projects = (
        projects
        .filter(
            status__in=[
                "approved",
                "in_progress",
            ]
        )
        .count()
    )

    completed_projects = (
        projects
        .filter(
            status="completed"
        )
        .count()
    )

    on_hold_projects = (
        projects
        .filter(
            status="on_hold"
        )
        .count()
    )

    # =====================================================
    # TASKS
    # =====================================================

    tasks = (
        ProjectTask.objects
        .filter(
            project_id__in=
                project_ids
        )
        .select_related(
            "project",
            "phase",
            "assigned_to",
        )
    )

    total_tasks = (
        tasks.count()
    )

    completed_tasks = (
        tasks
        .filter(
            status="completed"
        )
        .count()
    )

    overdue_tasks = (
        tasks
        .filter(
            due_date__lt=
                today
        )
        .exclude(
            status__in=[
                "completed",
                "cancelled",
            ]
        )
        .count()
    )

    my_open_tasks = (
        tasks
        .filter(
            assigned_to=
                user
        )
        .exclude(
            status__in=[
                "completed",
                "cancelled",
            ]
        )
        .count()
    )

    # =====================================================
    # MILESTONES
    # =====================================================

    milestones = (
        ProjectMilestone.objects
        .filter(
            project_id__in=
                project_ids
        )
        .select_related(
            "project",
            "phase",
        )
    )

    upcoming_milestones = (
        milestones
        .filter(
            due_date__gte=
                today,

            due_date__lte=
                upcoming_limit,
        )
        .exclude(
            status__in=[
                "completed",
                "cancelled",
            ]
        )
    )

    upcoming_milestones_count = (
        upcoming_milestones
        .count()
    )

    # =====================================================
    # BUDGET
    # =====================================================

    total_budget = (
        projects
        .aggregate(
            total=Sum(
                "approved_budget"
            )
        )["total"]
        or Decimal(
            "0.00"
        )
    )

    total_spent = (
        tasks
        .filter(
            actual_cost__isnull=
                False
        )
        .aggregate(
            total=Sum(
                "actual_cost"
            )
        )["total"]
        or Decimal(
            "0.00"
        )
    )

    budget_remaining = (
        total_budget
        -
        total_spent
    )

    budget_utilization = (
        round(
            (
                total_spent
                /
                total_budget
            )
            * 100,
            1,
        )
        if total_budget > 0
        else 0
    )

    # =====================================================
    # PROJECT COMPLETION
    # =====================================================

    project_cards = []

    for project in (
        projects[:5]
    ):

        project_tasks = (
            tasks.filter(
                project=
                    project
            )
        )

        task_count = (
            project_tasks.count()
        )

        if task_count > 0:

            project_progress = (
                project_tasks
                .aggregate(
                    total=Sum(
                        "completion_percentage"
                    )
                )["total"]
                or Decimal(
                    "0.00"
                )
            )

            project_progress = (
                project_progress
                /
                task_count
            )

        else:

            project_progress = (
                Decimal(
                    "0.00"
                )
            )

        spent = (
            project_tasks
            .filter(
                actual_cost__isnull=
                    False
            )
            .aggregate(
                total=Sum(
                    "actual_cost"
                )
            )["total"]
            or Decimal(
                "0.00"
            )
        )

        project_cards.append(
            {
                "id":
                    project.id,

                "project_code":
                    project.project_code,

                "name":
                    project.name,

                "project_type":
                    project.project_type,

                "status":
                    project.status,

                "start_date": (
                    project.start_date
                    .isoformat()
                    if project.start_date
                    else None
                ),

                "expected_end_date": (
                    project.expected_end_date
                    .isoformat()
                    if project.expected_end_date
                    else None
                ),

                "approved_budget":
                    float(
                        project.approved_budget
                    ),

                "spent":
                    float(
                        spent
                    ),

                "progress":
                    float(
                        round(
                            project_progress,
                            1,
                        )
                    ),

                "property": (
                    {
                        "id":
                            project.property.id,

                        "name":
                            project.property.name,
                    }
                    if project.property
                    else None
                ),

                "project_manager": (
                    {
                        "id":
                            project.project_manager.id,

                        "name":
                            (
                                f"{project.project_manager.first_name} "
                                f"{project.project_manager.last_name}"
                            ).strip()
                            or
                            project.project_manager.username,
                    }
                    if project.project_manager
                    else None
                ),
            }
        )

    # =====================================================
    # RECENT TASKS
    # =====================================================

    recent_tasks_queryset = (
        tasks
        .order_by(
            "-updated_at"
        )[:6]
    )

    recent_tasks = []

    for task in (
        recent_tasks_queryset
    ):

        recent_tasks.append(
            {
                "id":
                    task.id,

                "title":
                    task.title,

                "status":
                    task.status,

                "priority":
                    task.priority,

                "completion_percentage":
                    float(
                        task.completion_percentage
                    ),

                "due_date": (
                    task.due_date
                    .isoformat()
                    if task.due_date
                    else None
                ),

                "project": {
                    "id":
                        task.project.id,

                    "name":
                        task.project.name,
                },

                "assigned_to": (
                    {
                        "id":
                            task.assigned_to.id,

                        "name":
                            (
                                f"{task.assigned_to.first_name} "
                                f"{task.assigned_to.last_name}"
                            ).strip()
                            or
                            task.assigned_to.username,
                    }
                    if task.assigned_to
                    else None
                ),
            }
        )

    # =====================================================
    # SITE DIARY
    # =====================================================

    diary_entries = (
        SiteDiary.objects
        .filter(
            project_id__in=
                project_ids
        )
        .select_related(
            "project",
            "created_by",
        )
        .order_by(
            "-entry_date",
            "-created_at",
        )[:5]
    )

    recent_site_diary = []

    for diary in (
        diary_entries
    ):

        recent_site_diary.append(
            {
                "id":
                    diary.id,

                "entry_date":
                    diary.entry_date
                    .isoformat(),

                "weather":
                    diary.weather,

                "workers_present":
                    diary.workers_present,

                "work_completed":
                    diary.work_completed,

                "issues":
                    diary.issues,

                "project": {
                    "id":
                        diary.project.id,

                    "name":
                        diary.project.name,
                },

                "created_by": {
                    "id":
                        diary.created_by.id,

                    "name":
                        (
                            f"{diary.created_by.first_name} "
                            f"{diary.created_by.last_name}"
                        ).strip()
                        or
                        diary.created_by.username,
                },
            }
        )

    # =====================================================
    # RISKS
    # =====================================================

    risks = (
        ProjectRisk.objects
        .filter(
            project_id__in=
                project_ids
        )
        .exclude(
            status__in=[
                "closed",
                "mitigated",
            ]
        )
    )

    open_risks = (
        risks.count()
    )

    high_risks = (
        risks
        .filter(
            risk_score__gte=15
        )
        .count()
    )

    # =====================================================
    # UPCOMING MILESTONE DATA
    # =====================================================

    milestone_data = []

    for milestone in (
        upcoming_milestones
        .order_by(
            "due_date"
        )[:5]
    ):

        milestone_data.append(
            {
                "id":
                    milestone.id,

                "name":
                    milestone.name,

                "status":
                    milestone.status,

                "due_date": (
                    milestone.due_date
                    .isoformat()
                    if milestone.due_date
                    else None
                ),

                "project": {
                    "id":
                        milestone.project.id,

                    "name":
                        milestone.project.name,
                },

                "phase": (
                    {
                        "id":
                            milestone.phase.id,

                        "name":
                            milestone.phase.name,
                    }
                    if milestone.phase
                    else None
                ),
            }
        )

    # =====================================================
    # USER
    # =====================================================

    full_name = (
        f"{user.first_name} "
        f"{user.last_name}"
    ).strip()

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "success": True,

            "user": {
                "id":
                    user.id,

                "name":
                    full_name
                    or
                    user.username,

                "email":
                    user.email,

                "profile_image":
                    user.profile_image,
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,

                "logo":
                    organization.logo,
            },

            "summary": {
                "total_projects":
                    total_projects,

                "active_projects":
                    active_projects,

                "completed_projects":
                    completed_projects,

                "on_hold_projects":
                    on_hold_projects,

                "total_tasks":
                    total_tasks,

                "completed_tasks":
                    completed_tasks,

                "overdue_tasks":
                    overdue_tasks,

                "my_open_tasks":
                    my_open_tasks,

                "upcoming_milestones":
                    upcoming_milestones_count,

                "open_risks":
                    open_risks,

                "high_risks":
                    high_risks,
            },

            "financials": {
                "total_budget":
                    float(
                        total_budget
                    ),

                "total_spent":
                    float(
                        total_spent
                    ),

                "remaining":
                    float(
                        budget_remaining
                    ),

                "utilization_percentage":
                    budget_utilization,
            },

            "projects":
                project_cards,

            "recent_tasks":
                recent_tasks,

            "upcoming_milestones":
                milestone_data,

            "recent_site_diary":
                recent_site_diary,
        },
        status=200,
    )