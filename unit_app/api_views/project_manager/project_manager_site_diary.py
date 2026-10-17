from unit_app.api_views.common_imports import *



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


def diary_error(message, status=400):
    return JsonResponse(
        {"success": False, "message": message},
        status=status,
    )


def get_diary_access(user, organization_id):
    """
    Validate organization membership and the user's site-diary role.

    This version assumes Role.name stores the role identifier and
    Role.is_active indicates whether the role is active.
    """
    if not organization_id:
        return None, set(), diary_error(
            "organization_id is required."
        )

    try:
        membership = OrganizationMembership.objects.filter(
            organization_id=organization_id,
            user=user,
            is_active=True,
        ).select_related(
            "organization",
            "primary_role",
        ).prefetch_related("roles").first()
    except (ValueError, TypeError):
        membership = None

    if not membership:
        return None, set(), diary_error(
            "You do not have an active membership in this organization.",
            403,
        )

    roles = set(
        membership.roles.filter(
            is_active=True
        ).values_list("name", flat=True)
    )

    primary_role = membership.primary_role

    if primary_role and primary_role.is_active:
        roles.add(primary_role.name)

    if not roles.intersection(ALLOWED_ROLES):
        return None, set(), diary_error(
            "You do not have permission to access the site diary.",
            403,
        )

    return membership, roles, None


def accessible_diary_projects(user, organization, roles):
    projects = ConstructionProject.objects.filter(
        organization=organization
    )

    if not roles.intersection(ADMIN_ROLES):
        projects = projects.filter(
            Q(project_manager=user) | Q(created_by=user)
        )

    return projects.distinct()


def accessible_diary_entries(user, organization, roles):
    projects = accessible_diary_projects(
        user, organization, roles
    )

    return SiteDiary.objects.filter(
        project__in=projects
    )


def serialize_diary(entry):
    project = entry.project
    creator = entry.created_by

    return {
        "id": entry.id,
        "project": {
            "id": project.id,
            "name": project.name,
            "project_code": project.project_code,
        },
        "entry_date": (
            entry.entry_date.isoformat()
            if entry.entry_date else None
        ),
        "weather": entry.weather or "",
        "workers_present": entry.workers_present,
        "work_completed": entry.work_completed or "",
        "materials_received": entry.materials_received or "",
        "equipment_used": entry.equipment_used or "",
        "issues": entry.issues or "",
        "created_by": {
            "id": creator.id,
            "name": creator.get_full_name() or creator.username,
        } if creator else None,
        "created_at": (
            entry.created_at.isoformat()
            if entry.created_at else None
        ),
    }


def validate_diary_payload(data, current_entry=None):
    cleaned = {}

    raw_date = data.get(
        "entry_date",
        current_entry.entry_date.isoformat()
        if current_entry and current_entry.entry_date
        else timezone.localdate().isoformat(),
    )

    if isinstance(raw_date, date):
        parsed_date = raw_date
    else:
        parsed_date = parse_date(str(raw_date)) if raw_date else None

    if not parsed_date:
        return None, "entry_date must use YYYY-MM-DD format."

    cleaned["entry_date"] = parsed_date

    for field in (
        "weather",
        "work_completed",
        "materials_received",
        "equipment_used",
        "issues",
    ):
        if field in data:
            value = data.get(field)
        elif current_entry:
            value = getattr(current_entry, field, "")
        else:
            value = ""

        cleaned[field] = str(value or "").strip()

    raw_workers = data.get(
        "workers_present",
        current_entry.workers_present if current_entry else 0,
    )

    try:
        workers = int(raw_workers)
    except (ValueError, TypeError):
        return None, "workers_present must be a whole number."

    if workers < 0:
        return None, "workers_present cannot be negative."

    cleaned["workers_present"] = workers

    return cleaned, None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_manager_site_diary(request):
    """
    GET:
      ?organization_id=1
      ?project_id=5
      ?entry_date=2026-10-17
      ?date_from=2026-10-01
      ?date_to=2026-10-31
      ?search=foundation

    POST:
      {
        "organization_id": 1,
        "project_id": 5,
        "entry_date": "2026-10-17",
        "weather": "Sunny",
        "workers_present": 12,
        "work_completed": "Foundation work completed.",
        "materials_received": "20 bags of cement",
        "equipment_used": "Concrete mixer",
        "issues": "No major issues"
      }
    """
    data = (
        request.query_params
        if request.method == "GET"
        else request.data
    )

    organization_id = data.get("organization_id")

    membership, roles, error = get_diary_access(
        request.user, organization_id
    )

    if error:
        return error

    organization = membership.organization

    if request.method == "GET":
        entries = accessible_diary_entries(
            request.user, organization, roles
        ).select_related(
            "project", "created_by"
        )

        project_id = data.get("project_id")
        if project_id:
            entries = entries.filter(project_id=project_id)

        entry_date = data.get("entry_date")
        if entry_date:
            parsed = parse_date(str(entry_date))
            if not parsed:
                return diary_error(
                    "entry_date must use YYYY-MM-DD format."
                )
            entries = entries.filter(entry_date=parsed)

        date_from = data.get("date_from")
        if date_from:
            parsed = parse_date(str(date_from))
            if not parsed:
                return diary_error(
                    "date_from must use YYYY-MM-DD format."
                )
            entries = entries.filter(entry_date__gte=parsed)

        date_to = data.get("date_to")
        if date_to:
            parsed = parse_date(str(date_to))
            if not parsed:
                return diary_error(
                    "date_to must use YYYY-MM-DD format."
                )
            entries = entries.filter(entry_date__lte=parsed)

        search = str(data.get("search", "")).strip()
        if search:
            entries = entries.filter(
                Q(work_completed__icontains=search)
                | Q(materials_received__icontains=search)
                | Q(equipment_used__icontains=search)
                | Q(issues__icontains=search)
                | Q(project__name__icontains=search)
                | Q(project__project_code__icontains=search)
            )

        entries = entries.order_by(
            "-entry_date", "-created_at"
        )

        results = [serialize_diary(entry) for entry in entries]

        return JsonResponse({
            "success": True,
            "count": len(results),
            "entries": results,
        })

    # Create a new diary entry.
    project_id = data.get("project_id")

    if not project_id:
        return diary_error("project_id is required.")

    try:
        project = accessible_diary_projects(
            request.user, organization, roles
        ).get(id=project_id)
    except (
        ConstructionProject.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return diary_error(
            "Project not found or you do not have permission to record its diary.",
            404,
        )

    cleaned, message = validate_diary_payload(data)

    if message:
        return diary_error(message)

    try:
        with transaction.atomic():
            entry = SiteDiary.objects.create(
                project=project,
                created_by=request.user,
                **cleaned,
            )

        return JsonResponse({
            "success": True,
            "message": "Site diary entry created successfully.",
            "entry": serialize_diary(entry),
        }, status=201)

    except Exception:
        return diary_error(
            "Unable to create the diary entry. Check your data and model fields.",
            400,
        )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_manager_site_diary_detail(request, entry_id):
    """
    GET: retrieve an entry.
    PATCH: update an entry.
    DELETE: delete an entry (organization owner/admin only).
    """
    organization_id = (
        request.query_params.get("organization_id")
        or request.data.get("organization_id")
    )

    membership, roles, error = get_diary_access(
        request.user, organization_id
    )

    if error:
        return error

    organization = membership.organization

    try:
        entry = accessible_diary_entries(
            request.user, organization, roles
        ).select_related(
            "project", "created_by"
        ).get(id=entry_id)
    except (SiteDiary.DoesNotExist, ValueError, TypeError):
        return diary_error("Site diary entry not found.", 404)

    can_manage = (
        bool(roles.intersection(ADMIN_ROLES))
        or entry.project.project_manager_id == request.user.id
        or entry.project.created_by_id == request.user.id
    )

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "entry": serialize_diary(entry),
        })

    if request.method == "DELETE":
        if not roles.intersection(ADMIN_ROLES):
            return diary_error(
                "Only organization owners or administrators can delete diary entries.",
                403,
            )

        entry.delete()

        return JsonResponse({
            "success": True,
            "message": "Site diary entry deleted successfully.",
        })

    if not can_manage:
        return diary_error(
            "You do not have permission to edit this diary entry.",
            403,
        )

    if "project_id" in request.data:
        if str(request.data["project_id"]) != str(entry.project_id):
            return diary_error(
                "Moving a diary entry to another project is not supported."
            )

    cleaned, message = validate_diary_payload(
        request.data,
        current_entry=entry,
    )

    if message:
        return diary_error(message)

    try:
        with transaction.atomic():
            for field, value in cleaned.items():
                setattr(entry, field, value)

            entry.save()

        entry.refresh_from_db()

        return JsonResponse({
            "success": True,
            "message": "Site diary entry updated successfully.",
            "entry": serialize_diary(entry),
        })

    except Exception:
        return diary_error(
            "Unable to update the diary entry. Check your data and try again.",
            400,
        )
