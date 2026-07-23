from .common_imports import *

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_announcement(request):
    try:
        title = request.data.get("title")
        message = request.data.get("message")
        target = request.data.get("target")

        property_id = request.data.get("property_id")
        unit_id = request.data.get("unit_id")

        if not title or not message:
            return JsonResponse({
                "success": False,
                "message": "Title and message are required."
            }, status=400)

        announcement = Announcement(
            created_by=request.user,
            title=title,
            message=message,
            target=target
        )

        if target == "property":
            if not property_id:
                return JsonResponse({
                    "success": False,
                    "message": "Property is required."
                }, status=400)

            property = Property.objects.filter(
                id=property_id
            ).first()

            if not property:
                return JsonResponse({
                    "success": False,
                    "message": "Property not found."
                }, status=404)

            announcement.property = property

        elif target == "unit":
            if not unit_id:
                return JsonResponse({
                    "success": False,
                    "message": "Unit is required."
                }, status=400)

            unit = Unit.objects.filter(
                id=unit_id
            ).first()

            if not unit:
                return JsonResponse({
                    "success": False,
                    "message": "Unit not found."
                }, status=404)

            announcement.property = unit.property
            announcement.unit = unit

        announcement.save()

        return JsonResponse({
            "success": True,
            "message": "Announcement created successfully."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_announcements(request):

    announcements = Announcement.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    data = []

    for announcement in announcements:

        data.append({
            "id": announcement.id,
            "title": announcement.title,
            "message": announcement.message,
            "target": announcement.target,
            "property": announcement.property.name if announcement.property else None,
            "unit": announcement.unit.unit_number if announcement.unit else None,
            "is_active": announcement.is_active,
            "created_at": announcement.created_at.strftime("%d %b %Y %I:%M %p")
        })

    return JsonResponse({
        "announcements": data
    })



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_announcement(request, announcement_id):

    announcement = Announcement.objects.filter(
        id=announcement_id,
        created_by=request.user
    ).first()

    if not announcement:
        return JsonResponse({
            "message": "Announcement not found."
        }, status=404)

    announcement.title = request.data.get(
        "title",
        announcement.title
    )

    announcement.message = request.data.get(
        "message",
        announcement.message
    )

    announcement.is_active = request.data.get(
        "is_active",
        announcement.is_active
    )

    announcement.save()

    return JsonResponse({
        "success": True,
        "message": "Announcement updated successfully."
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_announcement(request, announcement_id):

    announcement = Announcement.objects.filter(
        id=announcement_id,
        created_by=request.user
    ).first()

    if not announcement:
        return JsonResponse({
            "message": "Announcement not found."
        }, status=404)

    announcement.delete()

    return JsonResponse({
        "success": True,
        "message": "Announcement deleted successfully."
    })



