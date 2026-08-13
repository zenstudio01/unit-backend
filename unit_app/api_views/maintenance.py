from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_manager_maintenance_tickets(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    # =====================================================
    # ORGANIZATION REQUIRED
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    # =====================================================
    # GET ORGANIZATION
    # =====================================================

    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    # =====================================================
    # VERIFY MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related("roles")
            .get(
                organization=organization,
                user=user,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # VERIFY ROLE
    # =====================================================

    allowed_roles = {
        "organization_owner",
        "organization_admin",
        "property_manager",
        "caretaker",
    }

    role_codes = set(
        membership.roles
        .filter(is_active=True)
        .values_list(
            "code",
            flat=True,
        )
    )

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view maintenance requests."
            },
            status=403,
        )

    # =====================================================
    # QUERY PARAMETERS
    # =====================================================

    search = str(
        request.GET.get(
            "search",
            ""
        )
    ).strip()

    status_filter = str(
        request.GET.get(
            "status",
            ""
        )
    ).strip()

    priority_filter = str(
        request.GET.get(
            "priority",
            ""
        )
    ).strip()

    category_filter = str(
        request.GET.get(
            "category",
            ""
        )
    ).strip()

    property_id = request.GET.get(
        "property_id"
    )

    assigned_to = request.GET.get(
        "assigned_to"
    )

    # =====================================================
    # BASE QUERY
    # =====================================================

    tickets = (
        MaintenanceTicket.objects
        .filter(
            organization=organization
        )
        .select_related(
            "property",
            "building",
            "unit",
            "lease",
            "reported_by",
            "assigned_to",
        )
        .prefetch_related(
            "media"
        )
        .order_by(
            "-created_at"
        )
    )

    # =====================================================
    # FILTER BY STATUS
    # =====================================================

    if status_filter:
        tickets = tickets.filter(
            status=status_filter
        )

    # =====================================================
    # FILTER BY PRIORITY
    # =====================================================

    if priority_filter:
        tickets = tickets.filter(
            priority=priority_filter
        )

    # =====================================================
    # FILTER BY CATEGORY
    # =====================================================

    if category_filter:
        tickets = tickets.filter(
            category=category_filter
        )

    # =====================================================
    # FILTER BY PROPERTY
    # =====================================================

    if property_id:
        tickets = tickets.filter(
            property_id=property_id
        )

    # =====================================================
    # FILTER BY ASSIGNEE
    # =====================================================

    if assigned_to:
        tickets = tickets.filter(
            assigned_to_id=assigned_to
        )

    # =====================================================
    # SEARCH
    # =====================================================

    if search:
        tickets = tickets.filter(
            Q(
                ticket_number__icontains=search
            )
            |
            Q(
                title__icontains=search
            )
            |
            Q(
                description__icontains=search
            )
            |
            Q(
                property__name__icontains=search
            )
            |
            Q(
                unit__name__icontains=search
            )
            |
            Q(
                unit__unit_code__icontains=search
            )
            |
            Q(
                category__icontains=search
            )
            |
            Q(
                reported_by__first_name__icontains=search
            )
            |
            Q(
                reported_by__last_name__icontains=search
            )
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    all_organization_tickets = (
        MaintenanceTicket.objects
        .filter(
            organization=organization
        )
    )

    total_count = (
        all_organization_tickets.count()
    )

    open_count = (
        all_organization_tickets
        .filter(
            status="open"
        )
        .count()
    )

    active_count = (
        all_organization_tickets
        .filter(
            status__in=[
                "under_review",
                "approved",
                "published_to_kaskazi",
                "assigned",
                "in_progress",
                "awaiting_approval",
            ]
        )
        .count()
    )

    completed_count = (
        all_organization_tickets
        .filter(
            status="completed"
        )
        .count()
    )

    urgent_count = (
        all_organization_tickets
        .filter(
            priority__in=[
                "urgent",
                "emergency",
            ]
        )
        .exclude(
            status__in=[
                "completed",
                "closed",
                "cancelled",
            ]
        )
        .count()
    )

    # =====================================================
    # SERIALIZE TICKETS
    # =====================================================

    ticket_data = []

    for ticket in tickets:

        # -------------------------------------------------
        # Reporter name
        # -------------------------------------------------

        reported_by_name = "Unknown"

        if ticket.reported_by:
            reported_by_name = " ".join(
                filter(
                    None,
                    [
                        ticket.reported_by.first_name,
                        getattr(
                            ticket.reported_by,
                            "middle_name",
                            "",
                        ),
                        ticket.reported_by.last_name,
                    ],
                )
            )

            if not reported_by_name:
                reported_by_name = (
                    ticket.reported_by.email
                )

        # -------------------------------------------------
        # Assigned user
        # -------------------------------------------------

        assigned_to_name = None

        if ticket.assigned_to:
            assigned_to_name = " ".join(
                filter(
                    None,
                    [
                        ticket.assigned_to.first_name,
                        getattr(
                            ticket.assigned_to,
                            "middle_name",
                            "",
                        ),
                        ticket.assigned_to.last_name,
                    ],
                )
            )

            if not assigned_to_name:
                assigned_to_name = (
                    ticket.assigned_to.email
                )

        # -------------------------------------------------
        # Unit
        #
        # Your Unit model uses name + unit_code,
        # not unit_number.
        # We map name to unit_number so your current
        # React Native screen can continue using
        # item.unit_number.
        # -------------------------------------------------

        unit_number = "Common Area"
        unit_code = None

        if ticket.unit:
            unit_number = (
                ticket.unit.name
                or ticket.unit.unit_code
            )

            unit_code = (
                ticket.unit.unit_code
            )

        # -------------------------------------------------
        # Building
        # -------------------------------------------------

        building_name = None

        if ticket.building:
            building_name = (
                ticket.building.name
            )

        # -------------------------------------------------
        # First reported image
        # -------------------------------------------------

        first_image = (
            ticket.media
            .filter(
                file_type="image"
            )
            .order_by("created_at")
            .first()
        )

        # -------------------------------------------------
        # Build response
        # -------------------------------------------------

        ticket_data.append(
            {
                "id":
                    ticket.id,

                "ticket_number":
                    ticket.ticket_number,

                "title":
                    ticket.title,

                "description":
                    ticket.description,

                "category":
                    ticket.category,

                "category_display":
                    ticket.get_category_display(),

                "priority":
                    ticket.priority,

                "priority_display":
                    ticket.get_priority_display(),

                "source":
                    ticket.source,

                "source_display":
                    ticket.get_source_display(),

                "status":
                    ticket.status,

                "status_display":
                    ticket.get_status_display(),

                # -----------------------------
                # Property
                # -----------------------------

                "property_id":
                    ticket.property_id,

                "property_name":
                    ticket.property.name,

                # -----------------------------
                # Building
                # -----------------------------

                "building_id": (
                    ticket.building_id
                    if ticket.building
                    else None
                ),

                "building_name":
                    building_name,

                # -----------------------------
                # Unit
                # -----------------------------

                "unit_id": (
                    ticket.unit_id
                    if ticket.unit
                    else None
                ),

                "unit_number":
                    unit_number,

                "unit_code":
                    unit_code,

                # -----------------------------
                # Lease
                # -----------------------------

                "lease_id": (
                    ticket.lease_id
                    if ticket.lease
                    else None
                ),

                "lease_number": (
                    ticket.lease.lease_number
                    if ticket.lease
                    else None
                ),

                # -----------------------------
                # Reporter
                # -----------------------------

                "reported_by_id":
                    ticket.reported_by_id,

                "reported_by":
                    reported_by_name,

                # -----------------------------
                # Assignment
                # -----------------------------

                "assigned_to_id": (
                    ticket.assigned_to_id
                    if ticket.assigned_to
                    else None
                ),

                "assigned_to":
                    assigned_to_name,

                # -----------------------------
                # Scheduling
                # -----------------------------

                "preferred_date": (
                    ticket.preferred_date.isoformat()
                    if ticket.preferred_date
                    else None
                ),

                "scheduled_at": (
                    ticket.scheduled_at.isoformat()
                    if ticket.scheduled_at
                    else None
                ),

                "completed_at": (
                    ticket.completed_at.isoformat()
                    if ticket.completed_at
                    else None
                ),

                # -----------------------------
                # Financial
                # -----------------------------

                "estimated_cost": (
                    float(
                        ticket.estimated_cost
                    )
                    if ticket.estimated_cost
                    is not None
                    else None
                ),

                "actual_cost": (
                    float(
                        ticket.actual_cost
                    )
                    if ticket.actual_cost
                    is not None
                    else None
                ),

                # -----------------------------
                # Image
                # -----------------------------

                "image": (
                    first_image.file_url
                    if first_image
                    else None
                ),

                # -----------------------------
                # Dates
                # -----------------------------

                "created_at":
                    ticket.created_at.isoformat(),

                "updated_at":
                    ticket.updated_at.isoformat(),
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "summary": {
                "total":
                    total_count,

                "open":
                    open_count,

                "active":
                    active_count,

                "completed":
                    completed_count,

                "urgent":
                    urgent_count,
            },

            "tickets":
                ticket_data,

            "count":
                len(ticket_data),
        },
        status=200,
    )