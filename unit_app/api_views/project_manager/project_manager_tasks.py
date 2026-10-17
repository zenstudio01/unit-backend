from unit_app.api_views.common_imports import *


User = get_user_model()


ALLOWED_ROLES = {
    "organization_owner",
    "organization_admin",
    "project_manager",
    "site_manager",
    "site_engineer",
}

ADMIN_ROLES = {
    "organization_owner",
    "organization_admin",
}

TASK_STATUSES = {
    "todo",
    "in_progress",
    "blocked",
    "under_review",
    "completed",
    "cancelled",
}

TASK_PRIORITIES = {
    "low",
    "medium",
    "high",
    "urgent",
    "critical",
}


def error_response(message, status=400):
    return JsonResponse(
        {"success": False, "message": message},
        status=status,
    )


def get_membership(user, organization_id):
    """
    Validate the user's active membership in an organization.

    This implementation assumes Role uses a `code` field and
    has an `is_active` field. Adjust these names if your model differs.
    """
    if not organization_id:
        return None, set(), error_response(
            "organization_id is required."
        )

    try:
        organization = Organization.objects.get(id=organization_id)
    except (Organization.DoesNotExist, ValueError, TypeError):
        return None, set(), error_response(
            "Organization not found.", 404
        )

    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).prefetch_related("roles").first()

    if not membership:
        return None, set(), error_response(
            "You do not have an active membership in this organization.",
            403,
        )

    roles = set(
        membership.roles.filter(
            is_active=True
        ).values_list("code", flat=True)
    )

    primary_role = membership.primary_role

    if (
        primary_role
        and primary_role.is_active
    ):
        roles.add(primary_role.code)

    if not roles.intersection(ALLOWED_ROLES):
        return None, set(), error_response(
            "You do not have permission to manage project tasks.",
            403,
        )

    return membership, roles, None


def serialize_task(task):
    assigned_user = task.assigned_to
    phase = task.phase
    project = task.project

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "project": {
            "id": project.id,
            "name": project.name,
            "project_code": project.project_code,
        },
        "phase": (
            {
                "id": phase.id,
                "name": phase.name,
            }
            if phase else None
        ),
        "parent_task_id": task.parent_task_id,
        "assigned_to": (
            {
                "id": assigned_user.id,
                "name": assigned_user.get_full_name()
                or assigned_user.username,
                "email": assigned_user.email,
            }
            if assigned_user else None
        ),
        "start_date": (
            task.start_date.isoformat()
            if task.start_date else None
        ),
        "due_date": (
            task.due_date.isoformat()
            if task.due_date else None
        ),
        "priority": task.priority,
        "status": task.status,
        "completion_percentage": task.completion_percentage,
        "estimated_cost": (
            str(task.estimated_cost)
            if task.estimated_cost is not None else None
        ),
        "actual_cost": (
            str(task.actual_cost)
            if task.actual_cost is not None else None
        ),
        "created_at": (
            task.created_at.isoformat()
            if task.created_at else None
        ),
        "updated_at": (
            task.updated_at.isoformat()
            if task.updated_at else None
        ),
    }


def get_accessible_projects(user, organization, roles):
    projects = ConstructionProject.objects.filter(
        organization=organization
    )

    # Owners and organization administrators can access all projects.
    # Other authorized roles see projects they manage or created.
    if not roles.intersection(ADMIN_ROLES):
        projects = projects.filter(
            Q(project_manager=user) | Q(created_by=user)
        )

    return projects.distinct()


def get_accessible_tasks(user, organization, roles):
    projects = get_accessible_projects(
        user, organization, roles
    )

    tasks = ProjectTask.objects.filter(
        project__in=projects
    )

    # Non-administrators can also see tasks assigned to them
    # in projects within their organization.
    if not roles.intersection(ADMIN_ROLES):
        tasks = tasks | ProjectTask.objects.filter(
            project__organization=organization,
            assigned_to=user,
        )

    return tasks.distinct()


def parse_optional_date(value, field_name):
    if value in (None, ""):
        return None, None

    parsed = parse_date(str(value))

    if not parsed:
        return None, f"{field_name} must use YYYY-MM-DD format."

    return parsed, None


def validate_task_payload(data, project, current_task=None):
    cleaned = {}

    title = data.get(
        "title",
        current_task.title if current_task else "",
    )
    title = str(title).strip() if title is not None else ""

    if not title:
        return None, "Task title is required."

    cleaned["title"] = title

    description = data.get(
        "description",
        current_task.description if current_task else "",
    )
    cleaned["description"] = description or ""

    priority = data.get(
        "priority",
        current_task.priority if current_task else "medium",
    )

    if priority not in TASK_PRIORITIES:
        return None, "Invalid task priority."

    cleaned["priority"] = priority

    status = data.get(
        "status",
        current_task.status if current_task else "todo",
    )

    if status not in TASK_STATUSES:
        return None, "Invalid task status."

    cleaned["status"] = status

    try:
        completion = int(
            data.get(
                "completion_percentage",
                current_task.completion_percentage
                if current_task else 0,
            )
        )
    except (ValueError, TypeError):
        return None, "Completion percentage must be a whole number."

    if not 0 <= completion <= 100:
        return None, "Completion percentage must be between 0 and 100."

    cleaned["completion_percentage"] = completion

    if status == "completed":
        cleaned["completion_percentage"] = 100

    for field in ("start_date", "due_date"):
        if field in data:
            raw_value = data.get(field)
        elif current_task:
            existing = getattr(current_task, field)
            raw_value = existing.isoformat() if existing else None
        else:
            raw_value = None

        parsed, error = parse_optional_date(raw_value, field)

        if error:
            return None, error

        cleaned[field] = parsed

    if (
        cleaned["start_date"]
        and cleaned["due_date"]
        and cleaned["due_date"] < cleaned["start_date"]
    ):
        return None, "Due date cannot be before the start date."

    for field in ("estimated_cost", "actual_cost"):
        if field in data:
            raw_value = data.get(field)
        elif current_task:
            raw_value = getattr(current_task, field)
        else:
            raw_value = None

        if raw_value in (None, ""):
            cleaned[field] = None
            continue

        try:
            amount = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            return None, f"{field} must be a valid amount."

        if not amount.is_finite() or amount < 0:
            return None, f"{field} cannot be negative or invalid."

        cleaned[field] = amount

    # Phase must belong to the selected project.
    if "phase_id" in data:
        phase_id = data.get("phase_id")
    elif current_task:
        phase_id = current_task.phase_id
    else:
        phase_id = None

    if phase_id in (None, ""):
        cleaned["phase"] = None
    else:
        try:
            cleaned["phase"] = ProjectPhase.objects.get(
                id=phase_id,
                project=project,
            )
        except (ProjectPhase.DoesNotExist, ValueError, TypeError):
            return None, "Selected phase does not belong to this project."

    # Parent task must belong to the same project.
    if "parent_task_id" in data:
        parent_id = data.get("parent_task_id")
    elif current_task:
        parent_id = current_task.parent_task_id
    else:
        parent_id = None

    if parent_id in (None, ""):
        cleaned["parent_task"] = None
    else:
        try:
            parent = ProjectTask.objects.get(
                id=parent_id,
                project=project,
            )

            if current_task and parent.id == current_task.id:
                return None, "A task cannot be its own parent."

            cleaned["parent_task"] = parent
        except (ProjectTask.DoesNotExist, ValueError, TypeError):
            return None, "Parent task does not belong to this project."

    return cleaned, None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_manager_tasks(request):
    """
    GET:
      ?organization_id=1
      ?project_id=5
      ?status=in_progress
      ?priority=high
      ?search=foundation

    POST:
      {
        "organization_id": 1,
        "project_id": 5,
        "title": "Complete foundation",
        "description": "Finish the foundation work",
        "priority": "high",
        "status": "todo",
        "assigned_to_id": 3,
        "phase_id": 2,
        "start_date": "2026-10-17",
        "due_date": "2026-10-25",
        "estimated_cost": "25000",
        "completion_percentage": 0
      }
    """
    if request.method == "GET":
        organization_id = request.query_params.get("organization_id")
        data = request.query_params
    else:
        organization_id = request.data.get("organization_id")
        data = request.data

    membership, roles, error = get_membership(
        request.user, organization_id
    )

    if error:
        return error

    organization = membership.organization

    if request.method == "GET":
        tasks = get_accessible_tasks(
            request.user, organization, roles
        ).select_related(
            "project",
            "phase",
            "assigned_to",
            "parent_task",
        )

        project_id = data.get("project_id")
        if project_id:
            tasks = tasks.filter(project_id=project_id)

        status = data.get("status")
        if status and status != "all":
            if status not in TASK_STATUSES:
                return error_response("Invalid task status.")
            tasks = tasks.filter(status=status)

        priority = data.get("priority")
        if priority and priority != "all":
            if priority not in TASK_PRIORITIES:
                return error_response("Invalid task priority.")
            tasks = tasks.filter(priority=priority)

        search = data.get("search", "").strip()
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(project__project_code__icontains=search)
            )

        tasks = tasks.order_by(
            "due_date", "-created_at"
        )

        task_data = [serialize_task(task) for task in tasks]

        return JsonResponse({
            "success": True,
            "count": len(task_data),
            "tasks": task_data,
        })

    # POST: create a task.
    project_id = data.get("project_id")

    if not project_id:
        return error_response("project_id is required.")

    try:
        project = get_accessible_projects(
            request.user, organization, roles
        ).get(id=project_id)
    except (ConstructionProject.DoesNotExist, ValueError, TypeError):
        return error_response(
            "Project not found or you cannot manage it.", 404
        )

    cleaned, error_message = validate_task_payload(
        data, project
    )

    if error_message:
        return error_response(error_message)

    assigned_to = None
    assigned_to_id = data.get("assigned_to_id")

    if assigned_to_id not in (None, ""):
        try:
            assigned_to = User.objects.get(
                id=assigned_to_id,
                organization_memberships__organization=organization,
                organization_memberships__is_active=True,
            )
        except (User.DoesNotExist, ValueError, TypeError):
            return error_response(
                "Assigned user must be an active member of the organization."
            )

    # Non-administrators cannot assign tasks to another person
    # unless they are managing a project they can access.
    if (
        assigned_to
        and assigned_to.id != request.user.id
        and not roles.intersection(ADMIN_ROLES)
        and project.project_manager_id != request.user.id
    ):
        return error_response(
            "You cannot assign tasks to another user in this project.",
            403,
        )

    try:
        with transaction.atomic():
            task = ProjectTask.objects.create(
                project=project,
                assigned_to=assigned_to,
                **cleaned,
            )

        return JsonResponse({
            "success": True,
            "message": "Task created successfully.",
            "task": serialize_task(task),
        }, status=201)

    except Exception:
        return error_response(
            "Unable to create task. Check the submitted data and try again.",
            400,
        )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_manager_task_detail(request, task_id):
    """
    GET: retrieve a task
    PATCH: update task details or progress
    DELETE: delete a task (organization owner/admin only)
    """
    organization_id = (
        request.query_params.get("organization_id")
        or request.data.get("organization_id")
    )

    membership, roles, error = get_membership(
        request.user, organization_id
    )

    if error:
        return error

    organization = membership.organization

    try:
        task = get_accessible_tasks(
            request.user, organization, roles
        ).select_related(
            "project", "phase", "assigned_to", "parent_task"
        ).get(id=task_id)
    except (ProjectTask.DoesNotExist, ValueError, TypeError):
        return error_response("Task not found.", 404)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "task": serialize_task(task),
        })

    if request.method == "DELETE":
        if not roles.intersection(ADMIN_ROLES):
            return error_response(
                "Only organization owners or administrators can delete tasks.",
                403,
            )

        task.delete()

        return JsonResponse({
            "success": True,
            "message": "Task deleted successfully.",
        })

    # PATCH: only admins or project managers of the task's project
    # (or the user who created the project) may edit task details.
    can_manage = (
        bool(roles.intersection(ADMIN_ROLES))
        or task.project.project_manager_id == request.user.id
        or task.project.created_by_id == request.user.id
    )

    # Assigned users may update progress/status without editing
    # project assignment or costs.
    is_assignee = task.assigned_to_id == request.user.id

    if not can_manage and not is_assignee:
        return error_response(
            "You do not have permission to update this task.",
            403,
        )

    if not can_manage:
        allowed_fields = {
            "status",
            "completion_percentage",
        }
        submitted_fields = set(request.data.keys()) - {
            "organization_id"
        }

        if not submitted_fields.issubset(allowed_fields):
            return error_response(
                "Assigned users can only update task status and progress.",
                403,
            )

    project = task.project

    # Prevent PATCH from silently moving the task to another project.
    if "project_id" in request.data:
        if str(request.data["project_id"]) != str(project.id):
            return error_response(
                "Changing a task's project is not supported."
            )

    cleaned, error_message = validate_task_payload(
        request.data, project, current_task=task
    )

    if error_message:
        return error_response(error_message)

    if can_manage and "assigned_to_id" in request.data:
        assigned_to_id = request.data.get("assigned_to_id")

        if assigned_to_id in (None, ""):
            cleaned["assigned_to"] = None
        else:
            try:
                cleaned["assigned_to"] = User.objects.get(
                    id=assigned_to_id,
                    organization_memberships__organization=organization,
                    organization_memberships__is_active=True,
                )
            except (User.DoesNotExist, ValueError, TypeError):
                return error_response(
                    "Assigned user must be an active member of the organization."
                )

    elif not can_manage:
        # Do not let the payload affect assignment or costs.
        cleaned = {
            key: value
            for key, value in cleaned.items()
            if key in {"status", "completion_percentage"}
        }

    try:
        with transaction.atomic():
            for field, value in cleaned.items():
                setattr(task, field, value)

            if "assigned_to" in cleaned:
                task.assigned_to = cleaned["assigned_to"]

            task.save()

        task.refresh_from_db()

        return JsonResponse({
            "success": True,
            "message": "Task updated successfully.",
            "task": serialize_task(task),
        })

    except Exception:
        return error_response(
            "Unable to update task. Check the submitted data and try again.",
            400,
        )
