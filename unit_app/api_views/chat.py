from .common_imports import *

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_company_message(request):

    company_id = request.data.get("company_id")
    message = request.data.get("message")

    if not message:
        return JsonResponse({
            "success": False,
            "message": "Message required."
        })

    try:
        company = Company.objects.get(id=company_id)

    except Company.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Company not found."
        })

    conversation, created = CompanyConversation.objects.get_or_create(
        customer=request.user,
        company=company
    )

    CompanyMessage.objects.create(
        conversation=conversation,
        sender=request.user,
        message=message
    )

    # send push notifications
    send_push_notification(
        company.owner.expo_token, 
        title=request.user.full_name,
        body=f"{message}",
        data={"screen": "BookingDetails", "message_id": ""}
    )

    return JsonResponse({
        "success": True,
        "message": "Message sent."
    })


# company reply
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def company_reply(request):

    conversation_id = request.data.get("conversation_id")
    message = request.data.get("message")

    try:
        conversation = CompanyConversation.objects.get(
            id=conversation_id,
            company__owner=request.user
        )

    except CompanyConversation.DoesNotExist:

        return JsonResponse({
            "success": False
        })

    CompanyMessage.objects.create(
        conversation=conversation,
        sender=request.user,
        message=message
    )

    # send push notifications
    send_push_notification(
        request.user.expo_token, 
        title=request.user.full_name,
        body=f"{message}",
        data={"screen": "chat", "message_id": ""}
    )

    return JsonResponse({
        "success": True
    })


# company chat
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_chat(request, company_id):

    try:
        conversation = CompanyConversation.objects.get(
            customer=request.user,
            company_id=company_id
        )

    except CompanyConversation.DoesNotExist:

        return JsonResponse({
            "messages": []
        })

    messages = []

    for msg in conversation.messages.select_related("sender").order_by("created_at"):

        messages.append({

            "id": msg.id,

            "message": msg.message,

            "image": msg.image,

            "sender": msg.sender.full_name,

            "is_me": msg.sender == request.user,

            "time": msg.created_at.strftime("%I:%M %p"),

            "created_at": msg.created_at,
        })

    return JsonResponse({
        "messages": messages
    })


# company conversations
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_conversations(request):

    conversations = CompanyConversation.objects.filter(
        company__owner=request.user
    ).select_related(
        "customer",
        "company"
    ).order_by("-updated_at")

    data = []

    for conversation in conversations:

        last = conversation.messages.order_by("-created_at").first()

        unread = conversation.messages.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).count()

        data.append({

            "conversation_id": conversation.id,

            "customer_name": conversation.customer.full_name,

            "customer_image": conversation.customer.profile_image,

            "company_name": conversation.company.name,

            "last_message": last.message if last else "",

            "last_time": (
                last.created_at.strftime("%I:%M %p")
                if last else ""
            ),

            "unread": unread

        })

    return JsonResponse({
        "conversations": data
    })



# customer conversations
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_conversations(request):

    conversations = CompanyConversation.objects.filter(
        customer=request.user
    ).select_related(
        "company"
    ).order_by("-updated_at")

    data = []

    for conversation in conversations:

        last = conversation.messages.order_by("-created_at").first()

        unread = conversation.messages.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).count()

        data.append({

            "conversation_id": conversation.id,

            "company_id": conversation.company.id,

            "company_name": conversation.company.name,

            "company_logo": conversation.company.logo,

            "last_message": last.message if last else "",

            "last_time": (
                last.created_at.strftime("%I:%M %p")
                if last else ""
            ),

            "unread": unread

        })

    return JsonResponse({
        "conversations": data
    })


# mark messages as read
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_company_messages_read(request):

    conversation_id = request.data.get("conversation_id")

    CompanyMessage.objects.filter(
        conversation_id=conversation_id
    ).exclude(
        sender=request.user
    ).update(
        is_read=True
    )

    return JsonResponse({
        "success": True
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_conversation_messages(request, conversation_id):

    conversation = CompanyConversation.objects.get(
        id=conversation_id,
        company__owner=request.user
    )

    messages = []

    for msg in conversation.messages.select_related("sender").order_by("created_at"):

        messages.append({
            "id": msg.id,
            "message": msg.message,
            "time": msg.created_at.strftime("%I:%M %p"),
            "is_me": msg.sender == request.user,
            "sender": msg.sender.full_name,
        })

    return JsonResponse({
        "messages": messages
    })