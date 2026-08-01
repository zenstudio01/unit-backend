from .common_imports import *

from django.db.models import Q


# ============================================================
# HELPERS
# ============================================================

def normalize_boolean(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return None

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    return None


def serialize_notification(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "notification_type": getattr(
            notification,
            "notification_type",
            None,
        ),
        "company": (
            {
                "id": notification.company_id,
                "name": notification.company.name,
            }
            if getattr(notification, "company_id", None)
            else None
        ),
        "data": getattr(
            notification,
            "data",
            None,
        ),
        "created_at": notification.created_at.isoformat(),
        "updated_at": (
            notification.updated_at.isoformat()
            if getattr(notification, "updated_at", None)
            else None
        ),
    }


# ============================================================
# GET USER NOTIFICATIONS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    try:
        company_id = request.GET.get("company_id")

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        notification_type = str(
            request.GET.get("type", "")
        ).strip()

        is_read_param = request.GET.get("is_read")

        try:
            page = max(
                int(request.GET.get("page", 1)),
                1,
            )
        except (TypeError, ValueError):
            page = 1

        try:
            page_size = int(
                request.GET.get("page_size", 20)
            )

            page_size = min(
                max(page_size, 1),
                100,
            )

        except (TypeError, ValueError):
            page_size = 20

        notifications = (
            Notification.objects
            .filter(user=request.user)
            .select_related("company")
            .order_by("-created_at")
        )

        if company_id:
            membership_exists = (
                CompanyStaff.objects
                .filter(
                    user=request.user,
                    company_id=company_id,
                    is_active=True,
                )
                .exists()
            )

            if not membership_exists:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "You do not have access to this "
                            "company's notifications."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            notifications = notifications.filter(
                company_id=company_id
            )

        if notification_type:
            notifications = notifications.filter(
                notification_type=notification_type
            )

        if is_read_param is not None:
            is_read = normalize_boolean(
                is_read_param
            )

            if is_read is None:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "is_read must be true or false."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            notifications = notifications.filter(
                is_read=is_read
            )

        if search_query:
            notifications = notifications.filter(
                Q(title__icontains=search_query)
                | Q(message__icontains=search_query)
            )

        total_count = notifications.count()

        unread_count = notifications.filter(
            is_read=False
        ).count()

        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        notifications_page = notifications[
            start_index:end_index
        ]

        data = [
            serialize_notification(notification)
            for notification in notifications_page
        ]

        return Response(
            {
                "success": True,
                "count": len(data),
                "total_count": total_count,
                "unread_count": unread_count,
                "page": page,
                "page_size": page_size,
                "has_next": end_index < total_count,
                "notifications": data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET NOTIFICATIONS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "notifications."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# GET SINGLE NOTIFICATION
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notification(request, notification_id):
    try:
        notification = (
            Notification.objects
            .select_related("company")
            .filter(
                id=notification_id,
                user=request.user,
            )
            .first()
        )

        if not notification:
            return Response(
                {
                    "success": False,
                    "message": "Notification not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "notification": serialize_notification(
                    notification
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the notification."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# MARK ONE NOTIFICATION AS READ
# ============================================================

@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def mark_notification_read(
    request,
    notification_id,
):
    try:
        notification = (
            Notification.objects
            .filter(
                id=notification_id,
                user=request.user,
            )
            .first()
        )

        if not notification:
            return Response(
                {
                    "success": False,
                    "message": "Notification not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if notification.is_read:
            return Response(
                {
                    "success": True,
                    "message": (
                        "Notification is already marked "
                        "as read."
                    ),
                    "notification": (
                        serialize_notification(
                            notification
                        )
                    ),
                },
                status=status.HTTP_200_OK,
            )

        notification.is_read = True

        notification.save(
            update_fields=["is_read"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Notification marked as read."
                ),
                "notification": serialize_notification(
                    notification
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while marking "
                    "the notification as read."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# MARK ONE NOTIFICATION AS UNREAD
# ============================================================

@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def mark_notification_unread(
    request,
    notification_id,
):
    try:
        notification = (
            Notification.objects
            .filter(
                id=notification_id,
                user=request.user,
            )
            .first()
        )

        if not notification:
            return Response(
                {
                    "success": False,
                    "message": "Notification not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.is_read = False

        notification.save(
            update_fields=["is_read"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Notification marked as unread."
                ),
                "notification": serialize_notification(
                    notification
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while marking "
                    "the notification as unread."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# MARK ALL USER NOTIFICATIONS AS READ
# ============================================================

@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    try:
        company_id = request.data.get("company_id")

        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False,
        )

        if company_id:
            membership_exists = (
                CompanyStaff.objects
                .filter(
                    user=request.user,
                    company_id=company_id,
                    is_active=True,
                )
                .exists()
            )

            if not membership_exists:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "You do not have access to this "
                            "company's notifications."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            notifications = notifications.filter(
                company_id=company_id
            )

        updated_count = notifications.update(
            is_read=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Notifications marked as read."
                ),
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while marking "
                    "notifications as read."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# DELETE ONE NOTIFICATION
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_notification(
    request,
    notification_id,
):
    try:
        notification = Notification.objects.filter(
            id=notification_id,
            user=request.user,
        ).first()

        if not notification:
            return Response(
                {
                    "success": False,
                    "message": "Notification not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.delete()

        return Response(
            {
                "success": True,
                "message": (
                    "Notification deleted successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while deleting "
                    "the notification."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# DELETE ALL READ NOTIFICATIONS
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_read_notifications(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        notifications = Notification.objects.filter(
            user=request.user,
            is_read=True,
        )

        if company_id:
            membership_exists = (
                CompanyStaff.objects
                .filter(
                    user=request.user,
                    company_id=company_id,
                    is_active=True,
                )
                .exists()
            )

            if not membership_exists:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "You do not have access to this "
                            "company's notifications."
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            notifications = notifications.filter(
                company_id=company_id
            )

        deleted_count, _ = notifications.delete()

        return Response(
            {
                "success": True,
                "message": (
                    "Read notifications deleted successfully."
                ),
                "deleted_count": deleted_count,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while deleting "
                    "read notifications."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )