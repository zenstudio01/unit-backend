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

    preferred_date = (
        request.data.get(
            "preferred_date"
        )
    )

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

    if not service_code:
        return JsonResponse(
            {
                "message":
                    "service_code is required."
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

    if hasattr(
        ticket,
        "kaskazi_booking"
    ):
        return JsonResponse(
            {
                "message":
                    "This maintenance request already has a Kaskazi booking."
            },
            status=400,
        )

    property_obj = (
        ticket.property
    )

    unit = (
        ticket.unit
    )

    building = (
        ticket.building
    )

    payload = {
        "external_reference":
            ticket.ticket_number,

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

        "preferred_date":
            preferred_date
            or (
                str(
                    ticket.preferred_date
                )
                if ticket.preferred_date
                else None
            ),

        "notes":
            notes,

        "customer": {
            "organization_id":
                organization.id,

            "organization_name":
                organization.name,
        },

        "location": {
            "property_id":
                property_obj.id,

            "property_name":
                property_obj.name,

            "building": (
                building.name
                if building
                else None
            ),

            "unit": (
                unit.name
                if unit
                else None
            ),

            "unit_code": (
                unit.unit_code
                if unit
                else None
            ),
        },
    }

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
            error
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create booking on Kaskazi."
            },
            status=502,
        )

    booking_data = (
        result.get(
            "booking",
            result,
        )
    )

    external_booking_id = (
        booking_data.get(
            "id"
        )
        or
        booking_data.get(
            "booking_id"
        )
    )

    if not external_booking_id:
        return JsonResponse(
            {
                "message":
                    "Kaskazi did not return a booking ID."
            },
            status=502,
        )

    try:
        with transaction.atomic():

            booking = (
                KaskaziMaintenanceBooking.objects.create(
                    maintenance_ticket=
                        ticket,

                    organization=
                        organization,

                    external_booking_id=
                        external_booking_id,

                    external_worker_id=
                        booking_data.get(
                            "worker_id"
                        ),

                    worker_name=
                        booking_data.get(
                            "worker_name"
                        ),

                    worker_phone=
                        booking_data.get(
                            "worker_phone"
                        ),

                    service_code=
                        service_code,

                    service_name=
                        booking_data.get(
                            "service_name"
                        ),

                    status=
                        booking_data.get(
                            "status",
                            "requested",
                        ),

                    scheduled_at=
                        booking_data.get(
                            "scheduled_at"
                        ),

                    quoted_amount=
                        booking_data.get(
                            "quoted_amount"
                        ),

                    external_reference=
                        ticket.ticket_number,

                    metadata=
                        booking_data,
                )
            )

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
                    "Maintenance request submitted to Kaskazi. "
                    f"Booking reference: {external_booking_id}"
                ),
            )

        return JsonResponse(
            {
                "message":
                    "Kaskazi booking created successfully.",

                "booking": {
                    "id":
                        booking.id,

                    "external_booking_id":
                        booking.external_booking_id,

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
            error
        )

        return JsonResponse(
            {
                "message":
                    "Kaskazi created the booking but UNIT could not save it.",

                "external_booking_id":
                    external_booking_id,
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