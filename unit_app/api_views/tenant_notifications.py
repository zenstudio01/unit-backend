from .common_imports import *

def get_notification_tenant_context(
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
                user=user,
                organization=organization,
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

    role_codes = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    if "tenant" not in role_codes:
        return (
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
                organization=organization,
                user=user,
                status="active",
            )
        )

    except Tenant.DoesNotExist:
        return (
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

    return (
        organization,
        tenant,
        None,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_notifications(request):
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
        error_response,
    ) = get_notification_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    notifications = (
        Notification.objects
        .filter(
            organization=organization,
            user=request.user,
        )
        .order_by(
            "-created_at"
        )
    )

    results = []

    for notification in notifications:

        # These field names assume your
        # Notification model has them.
        #
        # If your model uses different
        # names, change them here only.

        results.append(
            {
                "id":
                    notification.id,

                "title":
                    notification.title,

                "message":
                    notification.message,

                "notification_type":
                    getattr(
                        notification,
                        "notification_type",
                        None,
                    ),

                "reference_type":
                    getattr(
                        notification,
                        "reference_type",
                        None,
                    ),

                "reference_id":
                    getattr(
                        notification,
                        "reference_id",
                        None,
                    ),

                "is_read":
                    notification.is_read,

                "read_at": (
                    notification.read_at
                    .isoformat()
                    if getattr(
                        notification,
                        "read_at",
                        None,
                    )
                    else None
                ),

                "created_at":
                    notification.created_at
                    .isoformat(),
            }
        )

    unread_count = (
        notifications
        .filter(
            is_read=False
        )
        .count()
    )

    return JsonResponse(
        {
            "unread_count":
                unread_count,

            "count":
                notifications.count(),

            "notifications":
                results,
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def tenant_notification_mark_read(
    request,
    notification_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
        or
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
        error_response,
    ) = get_notification_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        notification = (
            Notification.objects.get(
                id=notification_id,
                organization=organization,
                user=request.user,
            )
        )

    except Notification.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Notification not found."
            },
            status=404,
        )

    notification.is_read = True

    update_fields = [
        "is_read",
    ]

    if hasattr(notification,"read_at"):
        notification.read_at = (
            timezone.now()
        )

        update_fields.append(
            "read_at"
        )

        notification.save(update_fields=update_fields)

    return JsonResponse(
        {
            "message":
                "Notification marked as read.",

            "notification": {
                "id":
                    notification.id,

                "is_read":
                    notification.is_read,

                "read_at": (
                    notification.read_at
                    .isoformat()
                    if getattr(
                        notification,
                        "read_at",
                        None,
                    )
                    else None
                ),
            },
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def tenant_notifications_mark_all_read(
    request
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
        or
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
        error_response,
    ) = get_notification_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    notifications = (
        Notification.objects
        .filter(
            organization=organization,
            user=request.user,
            is_read=False,
        )
    )

    count = (
        notifications.count()
    )

    notifications.update(is_read=True, read_at=timezone.now())

    return JsonResponse({"message": "All notifications marked as read.", "updated": count}, status=200)
    

     