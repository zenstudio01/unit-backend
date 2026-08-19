from .common_imports import *



def get_manager_context(
    user,
    organization_id,
):
    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Organization not found."
                },
                status=404,
            ),
        )

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization=organization,
                user=user,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "You do not belong to this organization."
                },
                status=403,
            ),
        )

    roles = set(
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
        "organization_owner",
        "organization_admin",
        "property_manager",
    }

    if not roles.intersection(
        allowed_roles
    ):
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Property manager access is required."
                },
                status=403,
            ),
        )

    return (
        organization,
        membership,
        None,
    )


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





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def manager_maintenance_detail(
    request,
    ticket_id,
):
    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    (
        organization,
        membership,
        error_response,
    ) = get_manager_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        ticket = (
            MaintenanceTicket.objects
            .select_related(
                "property",
                "building",
                "unit",
                "lease",
                "reported_by",
                "assigned_to",
            )
            .prefetch_related(
                "media",
                "comments",
                "comments__user",
                "status_history",
                "status_history__changed_by",
                "approvals",
                "approvals__requested_from",
                "warranties",
            )
            .get(
                id=ticket_id,
                organization=organization,
            )
        )

    except MaintenanceTicket.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Maintenance request not found."
            },
            status=404,
        )

    def user_data(user):
        if not user:
            return None

        name = (
            user.get_full_name()
            if hasattr(
                user,
                "get_full_name"
            )
            else ""
        )

        return {
            "id":
                user.id,

            "name":
                name
                or getattr(
                    user,
                    "first_name",
                    ""
                )
                or getattr(
                    user,
                    "email",
                    "User"
                ),

            "email":
                getattr(
                    user,
                    "email",
                    None,
                ),

            "phone_number":
                getattr(
                    user,
                    "phone_number",
                    None,
                ),
        }

    # =====================================================
    # MEDIA
    # =====================================================

    media = [
        {
            "id":
                item.id,

            "file_url":
                item.file_url,

            "file_type":
                item.file_type,

            "file_type_display":
                item.get_file_type_display(),

            "media_stage":
                item.media_stage,

            "media_stage_display":
                item.get_media_stage_display(),

            "caption":
                item.caption,

            "uploaded_by":
                user_data(
                    item.uploaded_by
                ),

            "created_at":
                item.created_at
                .isoformat(),
        }

        for item
        in ticket.media
        .all()
        .order_by(
            "created_at"
        )
    ]

    # =====================================================
    # COMMENTS
    #
    # Managers can see BOTH public and internal comments.
    # =====================================================

    comments = [
        {
            "id":
                item.id,

            "comment":
                item.comment,

            "is_internal":
                item.is_internal,

            "user":
                user_data(
                    item.user
                ),

            "created_at":
                item.created_at
                .isoformat(),

            "updated_at":
                item.updated_at
                .isoformat(),
        }

        for item
        in ticket.comments
        .all()
        .order_by(
            "created_at"
        )
    ]

    # =====================================================
    # STATUS HISTORY
    # =====================================================

    history = [
        {
            "id":
                item.id,

            "previous_status":
                item.previous_status,

            "new_status":
                item.new_status,

            "new_status_display":
                item.get_new_status_display(),

            "changed_by":
                user_data(
                    item.changed_by
                ),

            "notes":
                item.notes,

            "created_at":
                item.created_at
                .isoformat(),
        }

        for item
        in ticket.status_history
        .all()
        .order_by(
            "created_at"
        )
    ]

    # =====================================================
    # APPROVALS
    # =====================================================

    approvals = [
        {
            "id":
                item.id,

            "approval_type":
                item.approval_type,

            "approval_type_display":
                item.get_approval_type_display(),

            "requested_from":
                user_data(
                    item.requested_from
                ),

            "status":
                item.status,

            "status_display":
                item.get_status_display(),

            "comments":
                item.comments,

            "approved_at": (
                item.approved_at
                .isoformat()
                if item.approved_at
                else None
            ),

            "created_at":
                item.created_at
                .isoformat(),
        }

        for item
        in ticket.approvals
        .all()
        .order_by(
            "-created_at"
        )
    ]

    # =====================================================
    # WARRANTIES
    # =====================================================

    warranties = [
        {
            "id":
                item.id,

            "provider_type":
                item.provider_type,

            "provider_type_display":
                item.get_provider_type_display(),

            "external_provider_id":
                item.external_provider_id,

            "start_date":
                str(
                    item.start_date
                ),

            "end_date":
                str(
                    item.end_date
                ),

            "terms":
                item.terms,

            "status":
                item.status,

            "status_display":
                item.get_status_display(),
        }

        for item
        in ticket.warranties
        .all()
        .order_by(
            "-created_at"
        )
    ]

    # =====================================================
    # ASSIGNABLE USERS
    # =====================================================

    memberships = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            is_active=True,
            user__is_active=True,
        )
        .select_related(
            "user"
        )
        .prefetch_related(
            "roles"
        )
        .order_by(
            "user__first_name",
            "user__email",
        )
    )

    assignable_users = []

    for member in memberships:
        member_roles = list(
            member.roles
            .filter(
                is_active=True
            )
            .values_list(
                "code",
                flat=True,
            )
        )

        name = (
            member.user
            .get_full_name()
        )

        assignable_users.append(
            {
                "id":
                    member.user.id,

                "name":
                    name
                    or member.user.email,

                "email":
                    member.user.email,

                "roles":
                    member_roles,
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "ticket": {
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

                "preferred_date": (
                    str(
                        ticket.preferred_date
                    )
                    if ticket.preferred_date
                    else None
                ),

                "scheduled_at": (
                    ticket.scheduled_at
                    .isoformat()
                    if ticket.scheduled_at
                    else None
                ),

                "completed_at": (
                    ticket.completed_at
                    .isoformat()
                    if ticket.completed_at
                    else None
                ),

                "closed_at": (
                    ticket.closed_at
                    .isoformat()
                    if ticket.closed_at
                    else None
                ),

                "estimated_cost": (
                    str(
                        ticket.estimated_cost
                    )
                    if ticket.estimated_cost
                    is not None
                    else None
                ),

                "actual_cost": (
                    str(
                        ticket.actual_cost
                    )
                    if ticket.actual_cost
                    is not None
                    else None
                ),

                "property": {
                    "id":
                        ticket.property.id,

                    "name":
                        ticket.property.name,
                },

                "building": (
                    {
                        "id":
                            ticket.building.id,

                        "name":
                            ticket.building.name,
                    }
                    if ticket.building
                    else None
                ),

                "unit": (
                    {
                        "id":
                            ticket.unit.id,

                        "name":
                            ticket.unit.name,

                        "unit_code":
                            ticket.unit.unit_code,
                    }
                    if ticket.unit
                    else None
                ),

                "lease_id":
                    ticket.lease_id,

                "reported_by":
                    user_data(
                        ticket.reported_by
                    ),

                "assigned_to":
                    user_data(
                        ticket.assigned_to
                    ),

                "created_at":
                    ticket.created_at
                    .isoformat(),

                "updated_at":
                    ticket.updated_at
                    .isoformat(),
            },

            "media":
                media,

            "comments":
                comments,

            "status_history":
                history,

            "approvals":
                approvals,

            "warranties":
                warranties,

            "assignable_users":
                assignable_users,

            "status_choices": [
                {
                    "value":
                        value,

                    "label":
                        label,
                }

                for value, label
                in MaintenanceTicket.STATUS_CHOICES
            ],
        },
        status=200,
    )



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def manager_update_maintenance_status(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    new_status = str(
        request.data.get(
            "status",
            ""
        )
        or ""
    ).strip()

    notes = str(
        request.data.get(
            "notes",
            ""
        )
        or ""
    ).strip()

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    (
        organization,
        membership,
        error_response,
    ) = get_manager_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    valid_statuses = {
        value
        for value, label
        in MaintenanceTicket.STATUS_CHOICES
    }

    if (
        new_status not in
        valid_statuses
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid maintenance status."
            },
            status=400,
        )

    try:
        with transaction.atomic():

            ticket = (
                MaintenanceTicket.objects
                .select_for_update()
                .get(
                    id=ticket_id,
                    organization=organization,
                )
            )

            previous_status = (
                ticket.status
            )

            if (
                previous_status ==
                new_status
            ):
                return JsonResponse(
                    {
                        "message":
                            "Maintenance request already has this status."
                    },
                    status=400,
                )

            ticket.status = (
                new_status
            )

            update_fields = [
                "status",
                "updated_at",
            ]

            # =============================================
            # STATUS SPECIFIC DATES
            # =============================================

            if (
                new_status ==
                "completed"
            ):
                ticket.completed_at = (
                    timezone.now()
                )

                update_fields.append(
                    "completed_at"
                )

            if (
                new_status ==
                "closed"
            ):
                ticket.closed_at = (
                    timezone.now()
                )

                update_fields.append(
                    "closed_at"
                )

            ticket.save(
                update_fields=
                    update_fields
            )

            MaintenanceStatusHistory.objects.create(
                maintenance_ticket=
                    ticket,

                previous_status=
                    previous_status,

                new_status=
                    new_status,

                changed_by=
                    request.user,

                notes=
                    notes,
            )

    except MaintenanceTicket.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Maintenance request not found."
            },
            status=404,
        )

    return JsonResponse(
        {
            "message":
                "Maintenance status updated successfully.",

            "status":
                ticket.status,

            "status_display":
                ticket.get_status_display(),
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def manager_assign_maintenance(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    user_id = (
        request.data.get(
            "user_id"
        )
    )

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    (
        organization,
        membership,
        error_response,
    ) = get_manager_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        ticket = (
            MaintenanceTicket.objects
            .get(
                id=ticket_id,
                organization=organization,
            )
        )

    except MaintenanceTicket.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Maintenance request not found."
            },
            status=404,
        )

    # =====================================================
    # UNASSIGN
    # =====================================================

    if not user_id:
        ticket.assigned_to = (
            None
        )

        ticket.save(
            update_fields=[
                "assigned_to",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "Maintenance request unassigned successfully."
            },
            status=200,
        )

    # =====================================================
    # VERIFY USER BELONGS TO ORGANIZATION
    # =====================================================

    try:
        target_membership = (
            OrganizationMembership.objects
            .select_related(
                "user"
            )
            .get(
                organization=organization,
                user_id=user_id,
                is_active=True,
                user__is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Selected user is not an active member of this organization."
            },
            status=400,
        )

    previous_status = (
        ticket.status
    )

    ticket.assigned_to = (
        target_membership.user
    )

    # Assignment can move an open/approved
    # ticket into assigned status.

    if ticket.status in [
        "open",
        "under_review",
        "approved",
    ]:
        ticket.status = (
            "assigned"
        )

    ticket.save(
        update_fields=[
            "assigned_to",
            "status",
            "updated_at",
        ]
    )

    if (
        previous_status !=
        ticket.status
    ):
        MaintenanceStatusHistory.objects.create(
            maintenance_ticket=
                ticket,

            previous_status=
                previous_status,

            new_status=
                ticket.status,

            changed_by=
                request.user,

            notes=(
                "Maintenance request assigned to "
                f"{target_membership.user.get_full_name() or target_membership.user.email}."
            ),
        )

    return JsonResponse(
        {
            "message":
                "Maintenance request assigned successfully.",

            "assigned_to": {
                "id":
                    target_membership.user.id,

                "name": (
                    target_membership.user
                    .get_full_name()
                    or
                    target_membership.user.email
                ),

                "email":
                    target_membership.user.email,
            },

            "status":
                ticket.status,
        },
        status=200,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manager_add_maintenance_comment(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    comment_text = str(
        request.data.get(
            "comment",
            ""
        )
        or ""
    ).strip()

    is_internal = (
        request.data.get(
            "is_internal",
            False
        )
    )

    if isinstance(
        is_internal,
        str
    ):
        is_internal = (
            is_internal.lower()
            in [
                "true",
                "1",
                "yes",
            ]
        )

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    if not comment_text:
        return JsonResponse(
            {
                "message":
                    "Comment is required."
            },
            status=400,
        )

    (
        organization,
        membership,
        error_response,
    ) = get_manager_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        ticket = (
            MaintenanceTicket.objects.get(
                id=ticket_id,
                organization=organization,
            )
        )

    except MaintenanceTicket.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Maintenance request not found."
            },
            status=404,
        )

    item = (
        MaintenanceComment.objects.create(
            maintenance_ticket=
                ticket,

            user=
                request.user,

            comment=
                comment_text,

            is_internal=
                is_internal,
        )
    )

    return JsonResponse(
        {
            "message":
                "Comment added successfully.",

            "comment": {
                "id":
                    item.id,

                "comment":
                    item.comment,

                "is_internal":
                    item.is_internal,

                "created_at":
                    item.created_at
                    .isoformat(),
            },
        },
        status=201,
    )



