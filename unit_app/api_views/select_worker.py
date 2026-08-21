from .common_imports import *
from .helper import *
from unit_app.services.kaskazi_service import ( KaskaziService, )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_select_worker(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    application_id = (
        request.data.get(
            "application_id"
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

    if not application_id:
        return JsonResponse(
            {
                "message":
                    "application_id is required."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION / MANAGER ACCESS
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
    # LOCAL KASKAZI BOOKING
    # =====================================================

    try:
        booking = (
            KaskaziMaintenanceBooking.objects
            .get(
                maintenance_ticket=ticket,
                organization=organization,
            )
        )

    except KaskaziMaintenanceBooking.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "This maintenance request has no Kaskazi booking."
            },
            status=404,
        )

    if not booking.external_booking_id:
        return JsonResponse(
            {
                "message":
                    "The Kaskazi booking ID is missing."
            },
            status=400,
        )

    # =====================================================
    # CALL KASKAZI
    # =====================================================

    try:
        kaskazi = (
            KaskaziService()
        )

        result = (
            kaskazi.select_worker(
                booking.external_booking_id,
                application_id,
            )
        )

        result = (
            result
            or {}
        )

    except Exception as error:
        print(
            "KASKAZI SELECT WORKER ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to select worker on Kaskazi."
            },
            status=502,
        )

    # =====================================================
    # KASKAZI RESPONSE
    # =====================================================

    booking_data = (
        result.get(
            "booking"
        )
        or
        result.get(
            "job"
        )
        or
        result
    )

    worker_data = (
        booking_data.get(
            "worker"
        )
        or
        result.get(
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
        worker_data.get(
            "full_name"
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
    # UPDATE UNIT
    # =====================================================

    try:
        with transaction.atomic():

            booking.external_worker_id = (
                str(
                    external_worker_id
                )
                if external_worker_id
                is not None
                else booking.external_worker_id
            )

            booking.worker_name = (
                worker_name
                or
                booking.worker_name
            )

            booking.worker_phone = (
                worker_phone
                or
                booking.worker_phone
            )

            booking.status = (
                booking_data.get(
                    "status"
                )
                or
                "accepted"
            )

            booking.metadata = {
                **(
                    booking.metadata
                    or {}
                ),

                "worker":
                    worker_data,

                "selected_application_id":
                    application_id,

                "kaskazi_select_worker_response":
                    result,
            }

            booking.save(
                update_fields=[
                    "external_worker_id",
                    "worker_name",
                    "worker_phone",
                    "status",
                    "metadata",
                    "updated_at",
                ]
            )

            # =================================================
            # UPDATE MAINTENANCE TICKET
            # =================================================

            previous_status = (
                ticket.status
            )

            ticket.status = (
                "assigned"
            )

            ticket.assigned_to = (
                None
            )

            ticket.save(
                update_fields=[
                    "status",
                    "assigned_to",
                    "updated_at",
                ]
            )

            # =================================================
            # STATUS HISTORY
            # =================================================

            if (
                previous_status !=
                "assigned"
            ):
                MaintenanceStatusHistory.objects.create(
                    maintenance_ticket=
                        ticket,

                    previous_status=
                        previous_status,

                    new_status=
                        "assigned",

                    changed_by=
                        request.user,

                    notes=(
                        "Kaskazi worker selected. "
                        f"Worker: "
                        f"{worker_name or 'Kaskazi worker'}."
                    ),
                )

    except Exception as error:
        print(
            "SAVE SELECTED KASKAZI WORKER ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    "Kaskazi selected the worker, but UNIT could not update the local booking.",

                "error":
                    str(error),
            },
            status=500,
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "message":
                result.get(
                    "message"
                )
                or
                "Worker selected successfully.",

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

                "external_worker_id":
                    booking.external_worker_id,

                "worker_name":
                    booking.worker_name,

                "worker_phone":
                    booking.worker_phone,

                "worker":
                    worker_data,
            },
        },
        status=200,
    )