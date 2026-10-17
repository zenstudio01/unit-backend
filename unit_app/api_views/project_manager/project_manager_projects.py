from unit_app.api_views.common_imports import *


ALLOWED_ROLES = {
    "project_manager",
    "organization_owner",
    "organization_admin",
    "site_manager",
    "site_engineer",
}

ADMIN_ROLES = {
    "organization_owner",
    "organization_admin",
}

PROJECT_TYPES = {
    "new_construction",
    "renovation",
    "extension",
    "fit_out",
    "infrastructure",
    "residential",
    "commercial",
    "industrial",
    "mixed_use",
    "other",
}

PROJECT_STATUSES = {
    "planning",
    "pending_approval",
    "approved",
    "in_progress",
    "on_hold",
    "completed",
    "cancelled",
}


def api_error(message, status=400):
    return JsonResponse(
        {
            "success": False,
            "message": message,
        },
        status=status,
    )


def get_membership_and_roles(user, organization_id):
    """
    Return the organization, active membership and active role codes.
    """

    try:
        organization_id = int(organization_id)
    except (TypeError, ValueError):
        return None, None, set(), api_error(
            "A valid organization_id is required.",
            400,
        )

    organization = Organization.objects.filter(
        id=organization_id,
    ).first()

    if not organization:
        return None, None, set(), api_error(
            "Organization not found.",
            404,
        )

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
        )
        .select_related("primary_role")
        .prefetch_related("roles")
        .first()
    )

    if not membership:
        return None, None, set(), api_error(
            "You do not have access to this organization.",
            403,
        )

    role_codes = set(
        membership.roles
        .filter(is_active=True)
        .values_list("code", flat=True)
    )

    primary_role = membership.primary_role

    if primary_role and primary_role.is_active:
        role_codes.add(primary_role.code)

    if not role_codes.intersection(ALLOWED_ROLES):
        return None, None, set(), api_error(
            "You do not have permission to manage projects.",
            403,
        )

    return organization, membership, role_codes, None


def project_to_dict(project, include_progress=True):
    task_summary = {
        "total": 0,
        "completed": 0,
        "average_progress": 0,
        "actual_cost": 0,
    }

    if include_progress:
        tasks = ProjectTask.objects.filter(project=project)

        aggregates = tasks.aggregate(
            total=Sum("actual_cost"),
            average_progress=Avg("completion_percentage"),
        )

        task_summary = {
            "total": tasks.count(),
            "completed": tasks.filter(status="completed").count(),
            "average_progress": round(
                float(aggregates["average_progress"] or 0),
                1,
            ),
            "actual_cost": float(aggregates["total"] or 0),
        }

    manager = project.project_manager

    manager_name = None

    if manager:
        manager_name = (
            f"{manager.first_name} {manager.last_name}".strip()
            or manager.username
        )

    return {
        "id": project.id,
        "project_code": project.project_code,
        "name": project.name,
        "project_type": project.project_type,
        "description": project.description,
        "status": project.status,
        "start_date": (
            project.start_date.isoformat()
            if project.start_date else None
        ),
        "expected_end_date": (
            project.expected_end_date.isoformat()
            if project.expected_end_date else None
        ),
        "actual_end_date": (
            project.actual_end_date.isoformat()
            if project.actual_end_date else None
        ),
        "approved_budget": float(project.approved_budget or 0),
        "property": (
            {
                "id": project.property.id,
                "name": project.property.name,
            }
            if project.property else None
        ),
        "project_manager": (
            {
                "id": manager.id,
                "name": manager_name,
            }
            if manager else None
        ),
        "task_summary": task_summary,
        "created_at": (
            project.created_at.isoformat()
            if project.created_at else None
        ),
        "updated_at": (
            project.updated_at.isoformat()
            if project.updated_at else None
        ),
    }


def validate_project_payload(data, creating=False):
    """
    Validate project input without using serializers.
    """

    errors = {}

    name = data.get("name")

    if creating and not str(name or "").strip():
        errors["name"] = "Project name is required."
    elif name is not None and not str(name).strip():
        errors["name"] = "Project name cannot be empty."

    project_type = data.get("project_type")

    if creating and not project_type:
        errors["project_type"] = "Project type is required."
    elif (
        project_type is not None
        and project_type not in PROJECT_TYPES
    ):
        errors["project_type"] = "Invalid project type."

    status = data.get("status")

    if status is not None and status not in PROJECT_STATUSES:
        errors["status"] = "Invalid project status."

    budget = data.get("approved_budget")

    if creating and budget in (None, ""):
        budget = "0"

    if budget not in (None, ""):
        try:
            budget_value = Decimal(str(budget))

            if not budget_value.is_finite() or budget_value < 0:
                errors["approved_budget"] = (
                    "Budget must be a valid non-negative amount."
                )
            elif budget_value.as_tuple().exponent < -2:
                errors["approved_budget"] = (
                    "Budget cannot have more than two decimal places."
                )
        except (InvalidOperation, TypeError, ValueError):
            errors["approved_budget"] = "Enter a valid budget amount."

    start_date = data.get("start_date")
    end_date = data.get("expected_end_date")
    actual_end_date = data.get("actual_end_date")

    parsed_start = None
    parsed_end = None
    parsed_actual_end = None

    if start_date not in (None, ""):
        parsed_start = parse_date(str(start_date))

        if not parsed_start:
            errors["start_date"] = "Enter a valid date in YYYY-MM-DD format."

    if end_date not in (None, ""):
        parsed_end = parse_date(str(end_date))

        if not parsed_end:
            errors["expected_end_date"] = (
                "Enter a valid date in YYYY-MM-DD format."
            )

    if actual_end_date not in (None, ""):
        parsed_actual_end = parse_date(str(actual_end_date))

        if not parsed_actual_end:
            errors["actual_end_date"] = (
                "Enter a valid date in YYYY-MM-DD format."
            )

    if (
        parsed_start
        and parsed_end
        and parsed_end < parsed_start
    ):
        errors["expected_end_date"] = (
            "Expected end date cannot be before the start date."
        )

    if (
        parsed_start
        and parsed_actual_end
        and parsed_actual_end < parsed_start
    ):
        errors["actual_end_date"] = (
            "Actual end date cannot be before the start date."
        )

    if errors:
        return None, errors

    cleaned = {}

    for field in (
        "name",
        "description",
        "project_type",
        "status",
    ):
        if field in data:
            value = data.get(field)

            if isinstance(value, str):
                value = value.strip()

            cleaned[field] = value

    if "approved_budget" in data or creating:
        cleaned["approved_budget"] = Decimal(
            str(data.get("approved_budget") or "0")
        )

    if "start_date" in data:
        cleaned["start_date"] = parsed_start

    if "expected_end_date" in data:
        cleaned["expected_end_date"] = parsed_end

    if "actual_end_date" in data:
        cleaned["actual_end_date"] = parsed_actual_end

    return cleaned, {}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_manager_projects(request):
    """
    GET:
      /api/v1/project-manager/projects/?organization_id=1

    Optional query parameters:
      search, status, project_type

    POST:
      Create a project in the selected organization.
    """

    organization_id = request.GET.get("organization_id")

    if request.method == "POST":
        organization_id = (
            request.data.get("organization_id")
            or organization_id
        )

    organization, membership, role_codes, error = (
        get_membership_and_roles(
            request.user,
            organization_id,
        )
    )

    if error:
        return error

    if request.method == "GET":
        projects = (
            ConstructionProject.objects
            .filter(organization=organization)
            .select_related("property", "project_manager")
            .order_by("-created_at")
        )

        # Project managers and site staff see their assigned projects.
        # Owners and admins can see all projects in their organization.
        if not role_codes.intersection(ADMIN_ROLES):
            projects = projects.filter(
                Q(project_manager=request.user)
                | Q(created_by=request.user)
            ).distinct()

        search = request.GET.get("search", "").strip()
        status = request.GET.get("status", "").strip()
        project_type = request.GET.get("project_type", "").strip()

        if search:
            projects = projects.filter(
                Q(name__icontains=search)
                | Q(project_code__icontains=search)
                | Q(description__icontains=search)
            )

        if status and status != "all":
            if status not in PROJECT_STATUSES:
                return api_error("Invalid project status.", 400)

            projects = projects.filter(status=status)

        if project_type and project_type != "all":
            if project_type not in PROJECT_TYPES:
                return api_error("Invalid project type.", 400)

            projects = projects.filter(project_type=project_type)

        project_list = [
            project_to_dict(project)
            for project in projects
        ]

        return JsonResponse(
            {
                "success": True,
                "organization": {
                    "id": organization.id,
                    "name": organization.name,
                },
                "count": len(project_list),
                "projects": project_list,
            },
            status=200,
        )

    # CREATE PROJECT
    payload = request.data.copy()

    cleaned, errors = validate_project_payload(
        payload,
        creating=True,
    )

    if errors:
        return JsonResponse(
            {
                "success": False,
                "message": "Please correct the project details.",
                "errors": errors,
            },
            status=400,
        )

    project_code = str(
        payload.get("project_code") or ""
    ).strip()

    if not project_code:
        project_code = (
            f"PRJ-{timezone.localdate():%Y%m%d}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

    if ConstructionProject.objects.filter(
        project_code=project_code
    ).exists():
        return api_error(
            "This project code already exists. Use another code.",
            400,
        )

    # New projects are assigned to their creator by default.
    project_manager = request.user

    manager_id = payload.get("project_manager_id")

    if manager_id not in (None, ""):
        try:
            manager_id = int(manager_id)
        except (TypeError, ValueError):
            return api_error("Invalid project manager ID.", 400)

        manager_membership = OrganizationMembership.objects.filter(
            organization=organization,
            user_id=manager_id,
            is_active=True,
        ).first()

        if not manager_membership:
            return api_error(
                "The selected project manager is not an active member "
                "of this organization.",
                400,
            )

        project_manager = manager_membership.user

    # The project manager must have an active role that permits
    # project management in this organization.
    manager_roles = set(
        manager_membership.roles.filter(is_active=True).values_list(
            "code", flat=True
        )
    ) if manager_id not in (None, "") else role_codes

    if manager_id not in (None, ""):
        if (
            manager_membership.primary_role
            and manager_membership.primary_role.is_active
        ):
            manager_roles.add(manager_membership.primary_role.code)

        if not manager_roles.intersection(ALLOWED_ROLES):
            return api_error(
                "The selected user cannot be assigned as project manager.",
                400,
            )

    try:
        with transaction.atomic():
            project = ConstructionProject.objects.create(
                organization=organization,
                project_code=project_code,
                name=cleaned["name"],
                project_type=cleaned["project_type"],
                description=cleaned.get("description", ""),
                status=cleaned.get("status", "planning"),
                start_date=cleaned.get("start_date"),
                expected_end_date=cleaned.get("expected_end_date"),
                actual_end_date=cleaned.get("actual_end_date"),
                approved_budget=cleaned.get(
                    "approved_budget",
                    Decimal("0.00"),
                ),
                project_manager=project_manager,
                created_by=request.user,
            )

    except Exception:
        # Log the real exception in server logs during development.
        # Do not expose database details to API clients.
        import logging
        logging.getLogger(__name__).exception(
            "Failed to create construction project."
        )

        return api_error(
            "The project could not be created. Check the project fields "
            "and try again.",
            400,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Project created successfully.",
            "project": project_to_dict(project),
        },
        status=201,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_manager_project_detail(request, project_id):
    """
    GET:
      Retrieve one project.

    PATCH:
      Update project fields.

    DELETE:
      Delete a project (organization owners/admins only).
    """

    organization_id = request.GET.get("organization_id")

    if request.method in ("PATCH", "DELETE"):
        organization_id = (
            request.data.get("organization_id")
            or organization_id
        )

    organization, membership, role_codes, error = (
        get_membership_and_roles(
            request.user,
            organization_id,
        )
    )

    if error:
        return error

    project = (
        ConstructionProject.objects
        .filter(
            id=project_id,
            organization=organization,
        )
        .select_related("property", "project_manager")
        .first()
    )

    if not project:
        return api_error("Project not found.", 404)

    if not role_codes.intersection(ADMIN_ROLES):
        if (
            project.project_manager_id != request.user.id
            and project.created_by_id != request.user.id
        ):
            return api_error(
                "You cannot access this project.",
                403,
            )

    if request.method == "GET":
        return JsonResponse(
            {
                "success": True,
                "project": project_to_dict(project),
            },
            status=200,
        )

    if request.method == "DELETE":
        if not role_codes.intersection(ADMIN_ROLES):
            return api_error(
                "Only organization owners or admins can delete projects.",
                403,
            )

        project.delete()

        return JsonResponse(
            {
                "success": True,
                "message": "Project deleted successfully.",
            },
            status=200,
        )

    # PATCH / UPDATE
    payload = request.data.copy()

    cleaned, errors = validate_project_payload(
        payload,
        creating=False,
    )

    if errors:
        return JsonResponse(
            {
                "success": False,
                "message": "Please correct the project details.",
                "errors": errors,
            },
            status=400,
        )

    if "project_code" in payload:
        new_code = str(payload.get("project_code") or "").strip()

        if not new_code:
            return api_error("Project code cannot be empty.", 400)

        duplicate = ConstructionProject.objects.filter(
            project_code=new_code
        ).exclude(id=project.id).exists()

        if duplicate:
            return api_error("That project code is already in use.", 400)

        project.project_code = new_code

    if "project_manager_id" in payload:
        manager_id = payload.get("project_manager_id")

        if manager_id in (None, ""):
            project.project_manager = None
        else:
            try:
                manager_id = int(manager_id)
            except (TypeError, ValueError):
                return api_error("Invalid project manager ID.", 400)

            manager_membership = OrganizationMembership.objects.filter(
                organization=organization,
                user_id=manager_id,
                is_active=True,
            ).select_related("user", "primary_role").prefetch_related(
                "roles"
            ).first()

            if not manager_membership:
                return api_error(
                    "The selected project manager is not an active "
                    "member of this organization.",
                    400,
                )

            manager_roles = set(
                manager_membership.roles.filter(
                    is_active=True
                ).values_list("code", flat=True)
            )

            if (
                manager_membership.primary_role
                and manager_membership.primary_role.is_active
            ):
                manager_roles.add(
                    manager_membership.primary_role.code
                )

            if not manager_roles.intersection(ALLOWED_ROLES):
                return api_error(
                    "The selected user cannot manage projects.",
                    400,
                )

            project.project_manager = manager_membership.user

    for field, value in cleaned.items():
        setattr(project, field, value)

    project.save()

    return JsonResponse(
        {
            "success": True,
            "message": "Project updated successfully.",
            "project": project_to_dict(project),
        },
        status=200,
    )
