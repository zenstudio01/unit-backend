from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=user,

            is_active=True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    notifications = (
        Notification.objects
        .filter(
            user=user,

            organization=
                organization,
        )
        .select_related(
            "property"
        )
        .order_by(
            "-created_at"
        )
    )

    # =====================================================
    # SUMMARY
    # =====================================================

    total_count = (
        notifications.count()
    )

    unread_count = (
        notifications
        .filter(
            is_read=False
        )
        .count()
    )

    # =====================================================
    # SERIALIZE
    # =====================================================

    notification_data = []

    for notification in notifications:

        notification_data.append(
            {
                "id":
                    notification.id,

                "type":
                    notification
                    .notification_type,

                "type_display":
                    notification
                    .get_notification_type_display(),

                "title":
                    notification.title,

                "message":
                    notification.message,

                "reference_id":
                    notification
                    .reference_id,

                "property_id": (
                    notification
                    .property_id
                ),

                "property_name": (
                    notification
                    .property.name
                    if notification
                    .property
                    else None
                ),

                "is_read":
                    notification
                    .is_read,

                "read_at": (
                    notification
                    .read_at
                    .isoformat()

                    if notification
                    .read_at

                    else None
                ),

                "created_at":
                    notification
                    .created_at
                    .isoformat(),
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "summary": {
                "total":
                    total_count,

                "unread":
                    unread_count,
            },

            "notifications":
                notification_data,

            "count":
                len(
                    notification_data
                ),
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

    try:
        notification = (
            Notification.objects
            .get(
                id=
                    notification_id,

                user=user,
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
                    notification
                    .is_read,

                "read_at": (
                    notification
                    .read_at
                    .isoformat()

                    if notification
                    .read_at

                    else None
                ),
            },
        },
        status=200,
    )



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(
    request
):
    user = request.user

    organization_id = (
        request.data.get(
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

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            user=user,

            organization=
                organization,

            is_active=True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    now = timezone.now()

    updated_count = (
        Notification.objects
        .filter(
            user=user,

            organization=
                organization,

            is_read=False,
        )
        .update(
            is_read=True,
            read_at=now,
        )
    )

    return JsonResponse(
        {
            "message":
                "All notifications marked as read.",

            "updated_count":
                updated_count,

            "unread":
                0,
        },
        status=200,
    )