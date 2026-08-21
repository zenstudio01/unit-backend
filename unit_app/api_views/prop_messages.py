from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_messages(
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
            kaskazi.get_messages(
                booking.external_booking_id
            )
        )

        result = (
            result
            or {}
        )

    except Exception as error:
        print(
            "KASKAZI MESSAGES ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to load messages."
            },
            status=502,
        )

    return JsonResponse(
        {
            "messages":
                result.get(
                    "messages",
                    []
                ),
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_kaskazi_send_message(
    request,
    ticket_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    text = str(
        request.data.get(
            "text",
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

    if not text:
        return JsonResponse(
            {
                "message":
                    "Message cannot be empty."
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
            kaskazi.send_message(
                booking.external_booking_id,
                text,
            )
        )

    except Exception as error:
        print(
            "KASKAZI SEND MESSAGE ERROR:",
            repr(error)
        )

        return JsonResponse(
            {
                "message":
                    str(error)
                    or
                    "Unable to send message."
            },
            status=502,
        )

    return JsonResponse(
        {
            "message":
                "Message sent successfully.",

            "data":
                (
                    result.get(
                        "data"
                    )
                    if result
                    else None
                ),
        },
        status=201,
    )