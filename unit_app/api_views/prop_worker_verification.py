from .common_imports import *
from .helper import *
from unit_app.services.kaskazi_service import ( KaskaziService, )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_verify_worker(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    qr_value = str(
        request.data.get(
            "qr_value",
            ""
        )
        or ""
    ).strip()
    print(f"Qr code: {qr_value}")

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    if not qr_value:
        return JsonResponse(
            {
                "message":
                    "qr_value is required."
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
            KaskaziMaintenanceBooking.objects.get(
                maintenance_ticket=ticket
            )
        )

    except KaskaziMaintenanceBooking.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Kaskazi booking not found."
            },
            status=404,
        )

    try:
        kaskazi = (
            KaskaziService()
        )

        result = (
            kaskazi.verify_worker(
                booking.external_booking_id,
                qr_value,
            )
        )

        result = (
            result
            or {}
        )

    except Exception as error:
        print(
            "KASKAZI VERIFY WORKER ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to verify worker."
            },
            status=502,
        )

        # =====================================================
    # UPDATE UNIT BOOKING
    # =====================================================

    worker_data = (
        result.get(
            "worker"
        )
        or {}
    )

    booking.external_worker_id = (
        worker_data.get(
            "id"
        )
        or
        booking.external_worker_id
    )

    booking.worker_name = (
        worker_data.get(
            "name"
        )
        or
        booking.worker_name
    )

    booking.status = (
        "in_progress"
    )

    booking.metadata = {
        **(
            booking.metadata
            or {}
        ),

        "qr_verified":
            True,

        "qr_verified_at":
            result.get(
                "qr_verified_at"
            ),

        "worker":
            worker_data,
    }

    booking.save(
        update_fields=[
            "external_worker_id",
            "worker_name",
            "status",
            "metadata",
            "updated_at",
        ]
    )

    # =====================================================
    # UPDATE MAINTENANCE TICKET
    # =====================================================

    previous_status = (
        ticket.status
    )

    ticket.status = (
        "in_progress"
    )

    ticket.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    if (
        previous_status !=
        "in_progress"
    ):
        MaintenanceStatusHistory.objects.create(
            maintenance_ticket=
                ticket,

            previous_status=
                previous_status,

            new_status=
                "in_progress",

            changed_by=
                request.user,

            notes=(
                "Kaskazi worker verified "
                "by QR code and work started."
            ),
        )

    return JsonResponse(
        {
            "message":
                result.get(
                    "message"
                )
                or
                "Worker verified successfully.",

            "worker":
                worker_data,

            "job_status":
                result.get(
                    "job_status",
                    "ongoing",
                ),

            "qr_verified":
                True,

            "qr_verified_at":
                result.get(
                    "qr_verified_at"
                ),
        },
        status=200,
    )