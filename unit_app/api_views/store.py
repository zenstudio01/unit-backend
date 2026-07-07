from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_stores(request):
    try:
        stores = Store.objects.select_related("owner").order_by("-created_at")

        data = []

        for store in stores:
            data.append({
                "id": store.id,
                "name": store.name,
                "description": store.description,
                "owner": {
                    "id": store.owner.id,
                    "name": store.owner.full_name,
                    "email": store.owner.email,
                    "phone_number": store.owner.phone_number,
                    "profile_image": store.owner.profile_image,
                },
                "created_at": store.created_at,
                "updated_at": store.updated_at,
            })

        return Response({
            "success": True,
            "count": len(data),
            "stores": data
        }, status=200)

    except Exception as e:
        return Response({
            "success": False,
            "message": str(e)
        }, status=500)