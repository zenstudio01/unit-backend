from .common_imports import *

from unit_app.services.kaskazi_service import ( KaskaziService, )



def get_manager_organization(
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
        None,
    )


# retrieve kaskazi services
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def kaskazi_services(
    request
):
    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    category = (
        request.GET.get(
            "category"
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
        error_response,
    ) = get_manager_organization(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        service = (
            KaskaziService()
        )

        result = (
            service.get_services(
                category=category
            )
        )

        return JsonResponse(
            result,
            status=200,
            safe=False,
        )

    except Exception as error:
        print(
            "KASKAZI SERVICES ERROR:",
            error
        )

        return JsonResponse(
            {
                "message":
                    "Unable to load Kaskazi services."
            },
            status=502,
        )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_kaskazi_worker(
    request,
    ticket_id,
):
    # =====================================================
    # REQUEST DATA
    # =====================================================

    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    service_code = str(
        request.data.get(
            "service_code",
            ""
        )
        or ""
    ).strip()

    budget_raw = (
        request.data.get(
            "budget"
        )
    )

    scheduled_date = str(
        request.data.get(
            "scheduled_date",
            ""
        )
        or ""
    ).strip()

    scheduled_time = str(
        request.data.get(
            "scheduled_time",
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

    if not service_code:
        return JsonResponse(
            {
                "message":
                    "service_code is required."
            },
            status=400,
        )

    if budget_raw in [
        None,
        "",
    ]:
        return JsonResponse(
            {
                "message":
                    "budget is required."
            },
            status=400,
        )

    try:
        budget = Decimal(
            str(
                budget_raw
            )
        )

        if budget <= 0:
            raise ValueError()

    except Exception:
        return JsonResponse(
            {
                "message":
                    "Enter a valid budget greater than zero."
            },
            status=400,
        )

    if not scheduled_date:
        return JsonResponse(
            {
                "message":
                    "scheduled_date is required."
            },
            status=400,
        )

    parsed_date = (
        parse_date(
            scheduled_date
        )
    )

    if not parsed_date:
        return JsonResponse(
            {
                "message":
                    "scheduled_date must use YYYY-MM-DD."
            },
            status=400,
        )

    if not scheduled_time:
        return JsonResponse(
            {
                "message":
                    "scheduled_time is required."
            },
            status=400,
        )

    parsed_time = (
        parse_time(
            scheduled_time
        )
    )

    if not parsed_time:
        return JsonResponse(
            {
                "message":
                    "scheduled_time must use HH:MM."
            },
            status=400,
        )

    # Optional but recommended:
    # prevent booking jobs in the past.

    scheduled_datetime = (
        timezone.make_aware(
            datetime.combine(
                parsed_date,
                parsed_time,
            )
        )
    )

    if (
        scheduled_datetime <
        timezone.now()
    ):
        return JsonResponse(
            {
                "message":
                    "Scheduled date and time cannot be in the past."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION ACCESS
    # =====================================================

    (
        organization,
        error_response,
    ) = get_manager_organization(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    # =====================================================
    # MAINTENANCE TICKET
    # =====================================================

    try:
        ticket = (
            MaintenanceTicket.objects
            .select_related(
                "property",
                "building",
                "unit",
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

    # =====================================================
    # PREVENT DUPLICATE KASKAZI BOOKING
    # =====================================================

    try:
        existing_booking = (
            ticket.kaskazi_booking
        )

    except KaskaziMaintenanceBooking.DoesNotExist:
        existing_booking = None

    if existing_booking:
        return JsonResponse(
            {
                "message":
                    "This maintenance request already has a Kaskazi booking.",

                "booking": {
                    "id":
                        existing_booking.id,

                    "external_booking_id":
                        existing_booking
                        .external_booking_id,

                    "status":
                        existing_booking.status,
                },
            },
            status=400,
        )

    # =====================================================
    # PROPERTY DETAILS
    # =====================================================

    property_obj = (
        ticket.property
    )

    building = (
        ticket.building
    )

    unit = (
        ticket.unit
    )

    # =====================================================
    # LOCATION STRING
    #
    # Kaskazi Job.location is a text/string field,
    # so do NOT send an object here.
    # =====================================================

    location_parts = []

    # Use actual property address/location first
    # if your Property model has one.

    property_address = (
        getattr(
            property_obj,
            "address",
            None
        )
        or
        getattr(
            property_obj,
            "location",
            None
        )
    )

    if property_address:
        location_parts.append(
            str(
                property_address
            ).strip()
        )

    elif property_obj.name:
        location_parts.append(
            property_obj.name
        )

    if building:
        location_parts.append(
            building.name
        )

    if unit:
        location_parts.append(
            unit.name
        )

    property_location = (
        ", ".join(
            [
                part
                for part
                in location_parts
                if part
            ]
        )
    )

    if not property_location:
        return JsonResponse(
            {
                "message":
                    "This property does not have a valid location."
            },
            status=400,
        )

    # =====================================================
    # COORDINATES
    # =====================================================

    latitude = (
        getattr(
            property_obj,
            "latitude",
            None
        )
    )

    longitude = (
        getattr(
            property_obj,
            "longitude",
            None
        )
    )

    # =====================================================
    # KASKAZI PAYLOAD
    # =====================================================

    payload = {
        "external_reference":
            ticket.ticket_number,

        "ticket_id":
            str(
                ticket.id
            ),

        "service_code":
            service_code,

        "category":
            ticket.category,

        "title":
            ticket.title,

        "description":
            ticket.description,

        "priority":
            ticket.priority,

        "budget":
            str(
                budget
            ),

        "scheduled_date":
            scheduled_date,

        "scheduled_time":
            scheduled_time,

        "location":
            property_location,

        "latitude": (
            str(
                latitude
            )
            if latitude
            is not None
            else None
        ),

        "longitude": (
            str(
                longitude
            )
            if longitude
            is not None
            else None
        ),

        "organization": {
            "id":
                organization.id,

            "name":
                organization.name,
        },

        "property": {
            "id":
                property_obj.id,

            "name":
                property_obj.name,
        },

        # Optional additional information.
        # Kaskazi can ignore this if its
        # endpoint does not use it yet.

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

        "unit": (
            {
                "id":
                    unit.id,

                "name":
                    unit.name,

                "unit_code":
                    getattr(
                        unit,
                        "unit_code",
                        None
                    ),
            }
            if unit
            else None
        ),

        "notes":
            notes,
    }

    print(
        "======================================"
    )

    print(
        "UNIT -> KASKAZI PAYLOAD:"
    )

    print(
        payload
    )

    print(
        "======================================"
    )

    # =====================================================
    # CREATE KASKAZI BOOKING
    # =====================================================

    try:
        kaskazi = (
            KaskaziService()
        )

        result = (
            kaskazi.create_booking(
                payload
            )
        )

    except Exception as error:

        print(
            "KASKAZI BOOKING ERROR:",
            repr(
                error
            )
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to create booking on Kaskazi."
            },
            status=502,
        )

    # =====================================================
    # KASKAZI RESPONSE
    # =====================================================

    booking_data = (
        result.get(
            "booking",
            result,
        )
        or {}
    )

    print(
        "KASKAZI BOOKING RESPONSE:",
        booking_data
    )

    # =====================================================
    # EXTERNAL BOOKING ID
    # =====================================================

    external_booking_id = (
        booking_data.get(
            "booking_id"
        )
        or
        booking_data.get(
            "id"
        )
        or
        booking_data.get(
            "job_id"
        )
    )

    if not external_booking_id:
        return JsonResponse(
            {
                "message":
                    "Kaskazi created the job but did not return a booking ID.",

                "kaskazi_response":
                    booking_data,
            },
            status=502,
        )

    # =====================================================
    # WORKER DATA
    # =====================================================

    worker_data = (
        booking_data.get(
            "worker"
        )
        or {}
    )

    external_worker_id = (
        worker_data.get(
            "id"
        )
        or
        booking_data.get(
            "worker_id"
        )
    )

    worker_name = (
        worker_data.get(
            "name"
        )
        or
        booking_data.get(
            "worker_name"
        )
    )

    worker_phone = (
        worker_data.get(
            "phone_number"
        )
        or
        worker_data.get(
            "phone"
        )
        or
        booking_data.get(
            "worker_phone"
        )
    )

    # =====================================================
    # SCHEDULE
    # =====================================================

    scheduled_at = (
        booking_data.get(
            "scheduled_at"
        )
    )

    # Kaskazi may return separate
    # scheduled_date/scheduled_time instead.

    if not scheduled_at:

        response_date = (
            booking_data.get(
                "scheduled_date"
            )
        )

        response_time = (
            booking_data.get(
                "scheduled_time"
            )
        )

        if (
            response_date
            and
            response_time
        ):
            try:
                parsed_response_date = (
                    parse_date(
                        str(
                            response_date
                        )
                    )
                )

                parsed_response_time = (
                    parse_time(
                        str(
                            response_time
                        )
                )

                )

                if (
                    parsed_response_date
                    and
                    parsed_response_time
                ):
                    scheduled_at = (
                        timezone.make_aware(
                            datetime.combine(
                                parsed_response_date,
                                parsed_response_time,
                            )
                        )
                    )

            except Exception:
                scheduled_at = None

    # =====================================================
    # PRICE
    # =====================================================

    quoted_amount = (
        booking_data.get(
            "quoted_amount"
        )
        or
        booking_data.get(
            "budget"
        )
    )

    # =====================================================
    # SERVICE NAME
    # =====================================================

    service_name = (
        booking_data.get(
            "service_name"
        )
        or
        service_code
        .replace(
            "_",
            " "
        )
        .title()
    )

    # =====================================================
    # SAVE UNIT INTEGRATION RECORD
    # =====================================================

    try:
        with transaction.atomic():

            booking = (
                KaskaziMaintenanceBooking.objects.create(
                    maintenance_ticket=
                        ticket,

                    organization=
                        organization,

                    external_booking_id=
                        str(
                            external_booking_id
                        ),

                    external_worker_id=(
                        str(
                            external_worker_id
                        )
                        if external_worker_id
                        is not None
                        else None
                    ),

                    worker_name=
                        worker_name,

                    worker_phone=
                        worker_phone,

                    service_code=
                        service_code,

                    service_name=
                        service_name,

                    status=
                        booking_data.get(
                            "status",
                            "pending",
                        ),

                    scheduled_at=
                        scheduled_at,

                    quoted_amount=
                        quoted_amount,

                    external_reference=
                        ticket.ticket_number,

                    metadata=
                        booking_data,
                )
            )

            # =================================================
            # UPDATE UNIT MAINTENANCE STATUS
            # =================================================

            previous_status = (
                ticket.status
            )

            ticket.status = (
                "published_to_kaskazi"
            )

            ticket.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            # =================================================
            # STATUS HISTORY
            # =================================================

            MaintenanceStatusHistory.objects.create(
                maintenance_ticket=
                    ticket,

                previous_status=
                    previous_status,

                new_status=
                    "published_to_kaskazi",

                changed_by=
                    request.user,

                notes=(
                    "Maintenance request submitted "
                    "to Kaskazi. "
                    f"Booking reference: "
                    f"{external_booking_id}"
                ),
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        return JsonResponse(
            {
                "message":
                    "Kaskazi booking created successfully.",

                "booking": {
                    "id":
                        booking.id,

                    "external_booking_id":
                        booking.external_booking_id,

                    "external_reference":
                        booking.external_reference,

                    "status":
                        booking.status,

                    "service_code":
                        booking.service_code,

                    "service_name":
                        booking.service_name,

                    "worker_name":
                        booking.worker_name,

                    "worker_phone":
                        booking.worker_phone,

                    "scheduled_at": (
                        booking.scheduled_at
                        .isoformat()
                        if booking.scheduled_at
                        else None
                    ),

                    "quoted_amount": (
                        str(
                            booking.quoted_amount
                        )
                        if booking.quoted_amount
                        is not None
                        else None
                    ),
                },
            },
            status=201,
        )

    except Exception as error:

        print(
            "SAVE KASKAZI BOOKING ERROR:",
            repr(
                error
            )
        )

        return JsonResponse(
            {
                "message":
                    (
                        "Kaskazi created the booking "
                        "but UNIT could not save it."
                    ),

                "external_booking_id":
                    str(
                        external_booking_id
                    ),

                "error":
                    str(
                        error
                    ),
            },
            status=500,
        )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_booking(
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
        error_response,
    ) = get_manager_organization(
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

    try:
        booking = (
            ticket.kaskazi_booking
        )

    except KaskaziMaintenanceBooking.DoesNotExist:
        booking = None

    if not booking:
        return JsonResponse(
            {
                "booking":
                    None,
            },
            status=200,
        )

    return JsonResponse(
        {
            "booking": {
                "id":
                    booking.id,

                "external_booking_id":
                    booking.external_booking_id,

                "external_worker_id":
                    booking.external_worker_id,

                "worker_name":
                    booking.worker_name,

                "worker_phone":
                    booking.worker_phone,

                "service_code":
                    booking.service_code,

                "service_name":
                    booking.service_name,

                "status":
                    booking.status,

                "scheduled_at": (
                    booking.scheduled_at
                    .isoformat()
                    if booking.scheduled_at
                    else None
                ),

                "quoted_amount": (
                    str(
                        booking.quoted_amount
                    )
                    if booking.quoted_amount
                    is not None
                    else None
                ),

                "final_amount": (
                    str(
                        booking.final_amount
                    )
                    if booking.final_amount
                    is not None
                    else None
                ),
            },
        },
        status=200,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_applications(
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
        error_response,
    ) = get_manager_organization(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        ticket = (
            MaintenanceTicket.objects
            .select_related(
                "organization"
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

    try:
        booking = (
            KaskaziMaintenanceBooking.objects.get(
                maintenance_ticket=ticket
            )
        )

    except KaskaziMaintenanceBooking.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "This maintenance request has not been sent to Kaskazi."
            },
            status=404,
        )

    try:
        kaskazi = (
            KaskaziService()
        )

        result = (
            kaskazi.get_applications(
                booking.external_booking_id
            )
        )

    except Exception as error:
        print(
            "KASKAZI APPLICATIONS ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to load Kaskazi worker applications."
            },
            status=502,
        )

    return JsonResponse(
        {
            "count":
                result.get(
                    "count",
                    0
                ),

            "applications":
                result.get(
                    "applications",
                    []
                ),
        },
        status=200,
    )