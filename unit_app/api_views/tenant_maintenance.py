from .common_imports import *
from .helper import *


def get_tenant_context(
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
                user=user,
                organization=organization,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return (
            None,
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

    if "tenant" not in roles:
        return (
            None,
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Tenant access is required."
                },
                status=403,
            ),
        )

    try:
        tenant = (
            Tenant.objects.get(
                organization=
                    organization,

                user=
                    user,

                status=
                    "active",
            )
        )

    except Tenant.DoesNotExist:
        return (
            None,
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Tenant profile not found."
                },
                status=404,
            ),
        )

    assignment = (
        TenantUnitAssignment.objects
        .filter(
            organization=
                organization,

            tenant=
                tenant,

            is_active=
                True,
        )
        .select_related(
            "property",
            "unit",
            "unit__building",
            "unit__floor",
        )
        .order_by(
            "-assigned_at"
        )
        .first()
    )

    return (
        organization,
        tenant,
        assignment,
        None,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_maintenance_create_options(
    request
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
        tenant,
        assignment,
        error_response,
    ) = get_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    # =====================================================
    # ASSIGNMENT
    # =====================================================

    assignment_data = None

    if assignment:
        unit = (
            assignment.unit
        )

        property_obj = (
            assignment.property
        )

        assignment_data = {
            "id":
                assignment.id,

            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,
            },

            "unit": {
                "id":
                    unit.id,

                "name":
                    unit.name,

                "unit_code":
                    unit.unit_code,

                "unit_type":
                    unit.unit_type,

                "building_name": (
                    unit.building.name
                    if unit.building
                    else None
                ),

                "floor_name": (
                    unit.floor.name
                    if unit.floor
                    else None
                ),
            },
        }

    # =====================================================
    # CATEGORIES
    # =====================================================

    categories = [
        {
            "value":
                value,

            "label":
                label,
        }
        for value, label
        in MaintenanceTicket.CATEGORY_CHOICES
    ]

    # =====================================================
    # PRIORITIES
    # =====================================================

    priority_descriptions = {
        "low":
            "Minor issue that can be handled during normal maintenance.",

        "medium":
            "Normal maintenance issue that should be attended to soon.",

        "high":
            "Important issue affecting normal use of your unit.",

        "urgent":
            "Serious issue requiring quick attention.",

        "emergency":
            "Immediate safety risk or serious property damage.",
    }

    priorities = [
        {
            "value":
                value,

            "label":
                label,

            "description":
                priority_descriptions.get(
                    value,
                    "",
                ),
        }
        for value, label
        in MaintenanceTicket.PRIORITY_CHOICES
    ]

    return JsonResponse(
        {
            "assignment":
                assignment_data,

            "categories":
                categories,

            "priorities":
                priorities,
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([
    MultiPartParser,
    FormParser,
])
def tenant_create_maintenance(
    request
):
    user = request.user
    data = request.data

    # =====================================================
    # INPUT
    # =====================================================

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    title = str(
        data.get(
            "title",
            ""
        )
        or ""
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
        or ""
    ).strip()

    category = str(
        data.get(
            "category",
            ""
        )
        or ""
    ).strip()

    priority = str(
        data.get(
            "priority",
            "medium"
        )
        or "medium"
    ).strip()

    preferred_date_raw = (
        data.get(
            "preferred_date"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    if not title:
        return JsonResponse(
            {
                "message":
                    "Issue title is required."
            },
            status=400,
        )

    if len(title) > 255:
        return JsonResponse(
            {
                "message":
                    "Issue title cannot exceed 255 characters."
            },
            status=400,
        )

    if not description:
        return JsonResponse(
            {
                "message":
                    "Issue description is required."
            },
            status=400,
        )

    if len(description) < 10:
        return JsonResponse(
            {
                "message":
                    "Please provide a more detailed description."
            },
            status=400,
        )

    valid_categories = {
        value
        for value, label
        in MaintenanceTicket.CATEGORY_CHOICES
    }

    if (
        category not in
        valid_categories
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid maintenance category."
            },
            status=400,
        )

    valid_priorities = {
        value
        for value, label
        in MaintenanceTicket.PRIORITY_CHOICES
    }

    if (
        priority not in
        valid_priorities
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid maintenance priority."
            },
            status=400,
        )

    # =====================================================
    # PREFERRED DATE
    # =====================================================

    preferred_date = None

    if preferred_date_raw:
        preferred_date = (
            parse_date(
                str(
                    preferred_date_raw
                )
            )
        )

        if not preferred_date:
            return JsonResponse(
                {
                    "message":
                        "Preferred date must use YYYY-MM-DD."
                },
                status=400,
            )

        if (
            preferred_date <
            timezone.localdate()
        ):
            return JsonResponse(
                {
                    "message":
                        "Preferred date cannot be in the past."
                },
                status=400,
            )

    # =====================================================
    # TENANT CONTEXT
    # =====================================================

    (
        organization,
        tenant,
        assignment,
        error_response,
    ) = get_tenant_context(
        user,
        organization_id,
    )

    if error_response:
        return error_response

    if not assignment:
        return JsonResponse(
            {
                "message":
                    "You do not have an active unit assignment."
            },
            status=400,
        )

    property_obj = (
        assignment.property
    )

    unit = (
        assignment.unit
    )

    building = (
        unit.building
    )

    # =====================================================
    # FIND CURRENT LEASE
    # =====================================================

    lease_tenant = (
        LeaseTenant.objects
        .filter(
            tenant=
                tenant,

            lease__organization=
                organization,

            lease__unit=
                unit,

            lease__status__in=[
                "active",
                "pending_signature",
            ],
        )
        .select_related(
            "lease"
        )
        .order_by(
            "-lease__created_at"
        )
        .first()
    )

    lease = (
        lease_tenant.lease
        if lease_tenant
        else None
    )

    # =====================================================
    # FILES
    # =====================================================

    images = (
        request.FILES
        .getlist(
            "images"
        )
    )

    if len(images) > 5:
        return JsonResponse(
            {
                "message":
                    "You can upload a maximum of 5 images."
            },
            status=400,
        )

    allowed_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }

    max_size = (
        10 *
        1024 *
        1024
    )

    for image in images:

        content_type = (
            image.content_type
            or ""
        ).lower()

        if (
            content_type
            not in allowed_types
        ):
            return JsonResponse(
                {
                    "message":
                        f"{image.name} is not a supported image format."
                },
                status=400,
            )

        if image.size > max_size:
            return JsonResponse(
                {
                    "message":
                        f"{image.name} exceeds the 10 MB size limit."
                },
                status=400,
            )

    # =====================================================
    # CREATE TICKET
    # =====================================================

    try:
        with transaction.atomic():

            # =================================================
            # TICKET NUMBER
            # =================================================

            while True:
                ticket_number = (
                    "MNT-"
                    f"{organization.id}-"
                    f"{uuid.uuid4().hex[:10].upper()}"
                )

                exists = (
                    MaintenanceTicket.objects
                    .filter(
                        ticket_number=
                            ticket_number
                    )
                    .exists()
                )

                if not exists:
                    break

            # =================================================
            # CREATE
            # =================================================

            ticket = (
                MaintenanceTicket.objects.create(
                    organization=
                        organization,

                    property=
                        property_obj,

                    building=
                        building,

                    unit=
                        unit,

                    lease=
                        lease,

                    reported_by=
                        user,

                    assigned_to=
                        None,

                    ticket_number=
                        ticket_number,

                    category=
                        category,

                    title=
                        title,

                    description=
                        description,

                    priority=
                        priority,

                    source=
                        "tenant",

                    status=
                        "open",

                    preferred_date=
                        preferred_date,
                )
            )

            # =================================================
            # INITIAL STATUS HISTORY
            # =================================================

            MaintenanceStatusHistory.objects.create(
                maintenance_ticket=
                    ticket,

                previous_status=
                    None,

                new_status=
                    "open",

                changed_by=
                    user,

                notes=
                    "Maintenance request submitted by tenant.",
            )

            # =================================================
            # IMAGES
            # =================================================

            uploaded_media = []

            for image in images:

                upload_result = (
                    upload_maintenance_image(
                        image_file=
                            image,

                        organization_id=
                            organization.id,
                    )
                )

                file_url = (
                    upload_result.get(
                        "url"
                    )
                )

                if not file_url:
                    raise Exception(
                        f"Unable to upload {image.name}."
                    )

                media = (
                    MaintenanceMedia.objects.create(
                        maintenance_ticket=
                            ticket,

                        uploaded_by=
                            user,

                        file_url=
                            file_url,

                        file_type=
                            "image",

                        media_stage=
                            "reported",

                        caption=
                            "Reported by tenant",
                    )
                )

                uploaded_media.append(
                    {
                        "id":
                            media.id,

                        "file_url":
                            media.file_url,

                        "file_type":
                            media.file_type,

                        "media_stage":
                            media.media_stage,

                        "caption":
                            media.caption,
                    }
                )

        # =====================================================
        # SUCCESS
        # =====================================================

        return JsonResponse(
            {
                "message":
                    "Maintenance request submitted successfully.",

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

                    "category_label":
                        ticket
                        .get_category_display(),

                    "priority":
                        ticket.priority,

                    "priority_label":
                        ticket
                        .get_priority_display(),

                    "source":
                        ticket.source,

                    "source_label":
                        ticket
                        .get_source_display(),

                    "status":
                        ticket.status,

                    "status_label":
                        ticket
                        .get_status_display(),

                    "preferred_date": (
                        str(
                            ticket.preferred_date
                        )
                        if ticket.preferred_date
                        else None
                    ),

                    "property": {
                        "id":
                            property_obj.id,

                        "name":
                            property_obj.name,
                    },

                    "building": (
                        {
                            "id":
                                building.id,

                            "name":
                                building.name,
                        }
                        if building
                        else None
                    ),

                    "unit": {
                        "id":
                            unit.id,

                        "name":
                            unit.name,

                        "unit_code":
                            unit.unit_code,
                    },

                    "lease_id": (
                        lease.id
                        if lease
                        else None
                    ),

                    "created_at":
                        ticket.created_at
                        .isoformat(),
                },

                "media":
                    uploaded_media,
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE TENANT MAINTENANCE ERROR:",
            error
        )

        return JsonResponse(
            {
                "message":
                    "Unable to submit maintenance request.",

                "error":
                    str(error),
            },
            status=500,
        )