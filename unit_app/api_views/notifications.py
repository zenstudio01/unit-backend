from .common_imports import *



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    notification_type = request.GET.get(
        "type"
    )

    unread = request.GET.get(
        "unread"
    )

    search = str(
        request.GET.get("search", "")
    ).strip()

    notifications = (
        Notification.objects
        .filter(user=user)
        .select_related(
            "organization",
            "property",
        )
    )

    # ----------------------------------------
    # Organization filter
    # ----------------------------------------

    if organization_id:
        notifications = notifications.filter(
            organization_id=organization_id
        )

    # ----------------------------------------
    # Notification type filter
    # ----------------------------------------

    if notification_type:
        notifications = notifications.filter(
            notification_type=
                notification_type
        )

    # ----------------------------------------
    # Unread filter
    # ----------------------------------------

    if unread == "true":
        notifications = notifications.filter(
            is_read=False
        )

    # ----------------------------------------
    # Search
    # ----------------------------------------

    if search:
        from django.db.models import Q

        notifications = (
            notifications.filter(
                Q(
                    title__icontains=
                        search
                )
                |
                Q(
                    message__icontains=
                        search
                )
                |
                Q(
                    property__name__icontains=
                        search
                )
            )
        )

    notifications = notifications.order_by(
        "-created_at"
    )

    data = []

    for notification in notifications:
        data.append(
            {
                "id":
                    notification.id,

                "type":
                    notification.notification_type,

                "title":
                    notification.title,

                "message":
                    notification.message,

                "reference_id":
                    notification.reference_id,

                "is_read":
                    notification.is_read,

                "read_at":
                    (
                        notification.read_at.isoformat()
                        if notification.read_at
                        else None
                    ),

                "created_at":
                    notification.created_at.isoformat(),

                "property": (
                    {
                        "id":
                            notification.property.id,

                        "name":
                            notification.property.name,
                    }
                    if notification.property
                    else None
                ),

                "property_name": (
                    notification.property.name
                    if notification.property
                    else None
                ),

                "organization": (
                    {
                        "id":
                            notification.organization.id,

                        "name":
                            notification.organization.name,
                    }
                    if notification.organization
                    else None
                ),
            }
        )

    unread_count = (
        notifications
        .filter(is_read=False)
        .count()
    )

    return JsonResponse(
        {
            "notifications":
                data,

            "count":
                len(data),

            "unread_count":
                unread_count,
        },
        status=200,
    )



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_notification_read(
    request,
    notification_id,
):
    user = request.user

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = (
            timezone.now()
        )

        notification.save(
            update_fields=[
                "is_read",
                "read_at",
            ]
        )

    return JsonResponse(
        {
            "message":
                "Notification marked as read.",

            "notification": {
                "id":
                    notification.id,

                "is_read":
                    notification.is_read,

                "read_at":
                    (
                        notification.read_at.isoformat()
                        if notification.read_at
                        else None
                    ),
            },
        },
        status=200,
    )



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    user = request.user

    organization_id = request.data.get(
        "organization_id"
    )

    notifications = (
        Notification.objects
        .filter(
            user=user,
            is_read=False,
        )
    )

    if organization_id:
        notifications = notifications.filter(
            organization_id=
                organization_id
        )

    updated = notifications.update(
        is_read=True,
        read_at=timezone.now(),
    )

    return JsonResponse(
        {
            "message":
                "All notifications marked as read.",

            "updated":
                updated,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    notifications = (
        Notification.objects
        .filter(
            user=user,
            is_read=False,
        )
    )

    if organization_id:
        notifications = notifications.filter(
            organization_id=
                organization_id
        )

    return JsonResponse(
        {
            "unread_count":
                notifications.count()
        },
        status=200,
    )