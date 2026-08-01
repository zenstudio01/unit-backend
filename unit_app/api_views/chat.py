from .common_imports import *

from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone


# ============================================================
# CHAT PERMISSIONS
# ============================================================

COMPANY_CHAT_ROLES = {
    "admin",
    "property_manager",
    "customer_support",
    "leasing_officer",
}


def get_company_membership(user, company_id):
    """
    Return the user's active membership in a company.
    """

    return (
        CompanyStaff.objects
        .select_related("company", "user")
        .filter(
            user=user,
            company_id=company_id,
            is_active=True,
        )
        .first()
    )


def can_manage_company_chat(membership):
    """
    Determine whether a company staff member can manage chats.
    """

    return (
        membership is not None
        and membership.role in COMPANY_CHAT_ROLES
    )


def user_can_access_conversation(user, conversation):
    """
    A conversation may be accessed by:

    1. The customer who started it.
    2. An authorized staff member of the company.
    3. A platform superuser.
    """

    if user.is_superuser:
        return True

    if conversation.customer_id == user.id:
        return True

    membership = get_company_membership(
        user,
        conversation.company_id,
    )

    return can_manage_company_chat(membership)


def safe_send_push_notification(
    user,
    title,
    body,
    data=None,
):
    """
    Send a push notification without causing the API request
    to fail when a token is missing or the push service fails.
    """

    expo_token = getattr(user, "expo_token", None)

    if not expo_token:
        return False

    try:
        send_push_notification(
            expo_token,
            title=title,
            body=body,
            data=data or {},
        )

        return True

    except Exception as error:
        print(
            "PUSH NOTIFICATION ERROR:",
            str(error),
        )

        return False


def serialize_company_message(message, current_user):
    """
    Convert a CompanyMessage into a consistent JSON response.
    """

    return {
        "id": message.id,
        "message": message.message,
        "image": message.image,
        "sender": {
            "id": message.sender_id,
            "full_name": message.sender.full_name,
            "profile_image": message.sender.profile_image,
        },
        "is_me": message.sender_id == current_user.id,
        "is_read": message.is_read,
        "time": message.created_at.strftime(
            "%I:%M %p"
        ),
        "created_at": message.created_at.isoformat(),
    }


def serialize_company_conversation(
    conversation,
    current_user,
):
    """
    Serialize a conversation for either customer or company staff.
    """

    last_message = (
        conversation.messages
        .select_related("sender")
        .order_by("-created_at")
        .first()
    )

    unread_count = (
        conversation.messages
        .filter(is_read=False)
        .exclude(sender=current_user)
        .count()
    )

    return {
        "conversation_id": conversation.id,
        "company": {
            "id": conversation.company_id,
            "name": conversation.company.name,
            "logo": conversation.company.logo,
        },
        "customer": {
            "id": conversation.customer_id,
            "full_name": conversation.customer.full_name,
            "profile_image": (
                conversation.customer.profile_image
            ),
        },
        "last_message": (
            {
                "id": last_message.id,
                "message": last_message.message,
                "image": last_message.image,
                "sender_id": last_message.sender_id,
                "is_me": (
                    last_message.sender_id
                    == current_user.id
                ),
                "created_at": (
                    last_message.created_at.isoformat()
                ),
                "time": last_message.created_at.strftime(
                    "%I:%M %p"
                ),
            }
            if last_message
            else None
        ),
        "unread": unread_count,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def get_company_notification_recipients(
    company,
    exclude_user=None,
):
    """
    Return active company staff members who can manage chats.
    """

    queryset = (
        CompanyStaff.objects
        .select_related("user")
        .filter(
            company=company,
            is_active=True,
            role__in=COMPANY_CHAT_ROLES,
            user__is_active=True,
        )
    )

    if exclude_user:
        queryset = queryset.exclude(
            user=exclude_user
        )

    return [
        membership.user
        for membership in queryset
    ]


# ============================================================
# CUSTOMER SENDS MESSAGE TO COMPANY
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_company_message(request):
    try:
        company_id = request.data.get("company_id")

        message_text = str(
            request.data.get("message", "")
        ).strip()

        image = request.data.get("image")

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        if not message_text and not image:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "A message or image is required."
                    ),
                },
                status=400,
            )

        company = (
            Company.objects
            .select_related("owner")
            .filter(id=company_id)
            .first()
        )

        if not company:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company not found.",
                },
                status=404,
            )

        with transaction.atomic():
            conversation, created = (
                CompanyConversation.objects
                .get_or_create(
                    customer=request.user,
                    company=company,
                )
            )

            company_message = (
                CompanyMessage.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message=message_text,
                    image=image,
                    is_read=False,
                )
            )

            conversation.updated_at = timezone.now()

            conversation.save(
                update_fields=["updated_at"]
            )

        # Notify company staff who are allowed to manage chat.
        recipients = get_company_notification_recipients(
            company,
            exclude_user=request.user,
        )

        push_sent_count = 0

        for recipient in recipients:
            notification_sent = (
                safe_send_push_notification(
                    recipient,
                    title=request.user.full_name,
                    body=(
                        message_text
                        or "Sent an image"
                    ),
                    data={
                        "screen": "CompanyConversation",
                        "conversation_id": (
                            str(conversation.id)
                        ),
                        "company_id": str(company.id),
                        "message_id": (
                            str(company_message.id)
                        ),
                    },
                )
            )

            if notification_sent:
                push_sent_count += 1

        company_message = (
            CompanyMessage.objects
            .select_related("sender")
            .get(id=company_message.id)
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Message sent successfully.",
                "conversation_created": created,
                "conversation_id": conversation.id,
                "push_notifications_sent": (
                    push_sent_count
                ),
                "chat_message": serialize_company_message(
                    company_message,
                    request.user,
                ),
            },
            status=201,
        )

    except Exception as error:
        print(
            "SEND COMPANY MESSAGE ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while sending "
                    "the message."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# COMPANY STAFF REPLY
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def company_reply(request):
    try:
        conversation_id = request.data.get(
            "conversation_id"
        )

        message_text = str(
            request.data.get("message", "")
        ).strip()

        image = request.data.get("image")

        if not conversation_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Conversation is required."
                    ),
                },
                status=400,
            )

        if not message_text and not image:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "A message or image is required."
                    ),
                },
                status=400,
            )

        conversation = (
            CompanyConversation.objects
            .select_related(
                "company",
                "customer",
            )
            .filter(id=conversation_id)
            .first()
        )

        if not conversation:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Conversation not found.",
                },
                status=404,
            )

        membership = get_company_membership(
            request.user,
            conversation.company_id,
        )

        if not can_manage_company_chat(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "reply on behalf of this company."
                    ),
                },
                status=403,
            )

        with transaction.atomic():
            company_message = (
                CompanyMessage.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message=message_text,
                    image=image,
                    is_read=False,
                )
            )

            conversation.updated_at = timezone.now()

            conversation.save(
                update_fields=["updated_at"]
            )

        # Notify the customer, not the staff member who replied.
        push_sent = safe_send_push_notification(
            conversation.customer,
            title=conversation.company.name,
            body=message_text or "Sent an image",
            data={
                "screen": "CompanyChat",
                "conversation_id": (
                    str(conversation.id)
                ),
                "company_id": (
                    str(conversation.company_id)
                ),
                "message_id": (
                    str(company_message.id)
                ),
            },
        )

        company_message = (
            CompanyMessage.objects
            .select_related("sender")
            .get(id=company_message.id)
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Reply sent successfully.",
                "push_notification_sent": push_sent,
                "chat_message": serialize_company_message(
                    company_message,
                    request.user,
                ),
            },
            status=201,
        )

    except Exception as error:
        print(
            "COMPANY REPLY ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while sending "
                    "the company reply."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# CUSTOMER CHAT WITH A SPECIFIC COMPANY
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_chat(request, company_id):
    try:
        company = Company.objects.filter(
            id=company_id
        ).first()

        if not company:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company not found.",
                },
                status=404,
            )

        conversation = (
            CompanyConversation.objects
            .select_related(
                "customer",
                "company",
            )
            .filter(
                customer=request.user,
                company_id=company_id,
            )
            .first()
        )

        if not conversation:
            return JsonResponse(
                {
                    "success": True,
                    "conversation_id": None,
                    "messages": [],
                },
                status=200,
            )

        messages_queryset = (
            conversation.messages
            .select_related("sender")
            .order_by("created_at")
        )

        messages = [
            serialize_company_message(
                message,
                request.user,
            )
            for message in messages_queryset
        ]

        return JsonResponse(
            {
                "success": True,
                "conversation_id": conversation.id,
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "logo": company.logo,
                },
                "messages": messages,
            },
            status=200,
        )

    except Exception as error:
        print(
            "COMPANY CHAT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the conversation."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# COMPANY STAFF CONVERSATIONS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_conversations(request):
    try:
        company_id = request.GET.get("company_id")
        search_query = str(
            request.GET.get("search", "")
        ).strip()

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_company_chat(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's conversations."
                    ),
                },
                status=403,
            )

        conversations = (
            CompanyConversation.objects
            .filter(company_id=company_id)
            .select_related(
                "customer",
                "company",
            )
            .annotate(
                last_message_at=Max(
                    "messages__created_at"
                )
            )
            .order_by(
                "-last_message_at",
                "-updated_at",
            )
        )

        if search_query:
            conversations = conversations.filter(
                Q(
                    customer__full_name__icontains=
                    search_query
                )
                | Q(
                    customer__email__icontains=
                    search_query
                )
                | Q(
                    customer__phone_number__icontains=
                    search_query
                )
            )

        data = [
            serialize_company_conversation(
                conversation,
                request.user,
            )
            for conversation in conversations
        ]

        total_unread = (
            CompanyMessage.objects
            .filter(
                conversation__company_id=company_id,
                is_read=False,
            )
            .exclude(sender=request.user)
            .count()
        )

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "total_unread": total_unread,
                "conversations": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "COMPANY CONVERSATIONS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "company conversations."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# CUSTOMER CONVERSATIONS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_conversations(request):
    try:
        conversations = (
            CompanyConversation.objects
            .filter(customer=request.user)
            .select_related(
                "customer",
                "company",
            )
            .annotate(
                last_message_at=Max(
                    "messages__created_at"
                )
            )
            .order_by(
                "-last_message_at",
                "-updated_at",
            )
        )

        data = [
            serialize_company_conversation(
                conversation,
                request.user,
            )
            for conversation in conversations
        ]

        total_unread = (
            CompanyMessage.objects
            .filter(
                conversation__customer=request.user,
                is_read=False,
            )
            .exclude(sender=request.user)
            .count()
        )

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "total_unread": total_unread,
                "conversations": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "CUSTOMER CONVERSATIONS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "your conversations."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# MARK CONVERSATION MESSAGES AS READ
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_company_messages_read(request):
    try:
        conversation_id = request.data.get(
            "conversation_id"
        )

        if not conversation_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Conversation is required."
                    ),
                },
                status=400,
            )

        conversation = (
            CompanyConversation.objects
            .select_related(
                "customer",
                "company",
            )
            .filter(id=conversation_id)
            .first()
        )

        if not conversation:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Conversation not found.",
                },
                status=404,
            )

        if not user_can_access_conversation(
            request.user,
            conversation,
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have access to this "
                        "conversation."
                    ),
                },
                status=403,
            )

        updated_count = (
            CompanyMessage.objects
            .filter(
                conversation=conversation,
                is_read=False,
            )
            .exclude(sender=request.user)
            .update(is_read=True)
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Messages marked as read."
                ),
                "updated_count": updated_count,
            },
            status=200,
        )

    except Exception as error:
        print(
            "MARK MESSAGES READ ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while marking "
                    "messages as read."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# COMPANY STAFF VIEW CONVERSATION MESSAGES
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_conversation_messages(
    request,
    conversation_id,
):
    try:
        conversation = (
            CompanyConversation.objects
            .select_related(
                "customer",
                "company",
            )
            .filter(id=conversation_id)
            .first()
        )

        if not conversation:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Conversation not found.",
                },
                status=404,
            )

        membership = get_company_membership(
            request.user,
            conversation.company_id,
        )

        if not can_manage_company_chat(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this conversation."
                    ),
                },
                status=403,
            )

        messages_queryset = (
            conversation.messages
            .select_related("sender")
            .order_by("created_at")
        )

        messages = [
            serialize_company_message(
                message,
                request.user,
            )
            for message in messages_queryset
        ]

        return JsonResponse(
            {
                "success": True,
                "conversation": {
                    "id": conversation.id,
                    "company": {
                        "id": conversation.company_id,
                        "name": conversation.company.name,
                        "logo": conversation.company.logo,
                    },
                    "customer": {
                        "id": conversation.customer_id,
                        "full_name": (
                            conversation.customer.full_name
                        ),
                        "email": (
                            conversation.customer.email
                        ),
                        "phone_number": (
                            conversation.customer.phone_number
                        ),
                        "profile_image": (
                            conversation.customer.profile_image
                        ),
                    },
                },
                "messages": messages,
            },
            status=200,
        )

    except Exception as error:
        print(
            "COMPANY CONVERSATION MESSAGES ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "conversation messages."
                ),
                "error": str(error),
            },
            status=500,
        )