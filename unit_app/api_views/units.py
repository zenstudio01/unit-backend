from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_units(request):
    try:
        owner = request.user

        units = Unit.objects.filter(
            property__owner=owner
        ).select_related("property").order_by("-created_at")

        data = []

        for unit in units:
            data.append({
                "id": unit.id,
                "name": unit.name,
                "description": unit.description,
                "property_id": unit.property.id,
                "property_name": unit.property.name,
                "price_per_month": float(unit.price_per_month),
                "bedrooms": unit.bedrooms,
                "bathrooms": unit.bathrooms,
                "max_guests": unit.max_guests,
                "status": unit.status,
                "amenities": unit.amenities,
                "images": unit.images,
                "is_featured": unit.is_featured,
                "created_at": unit.created_at,
            })

        return JsonResponse({
            "success": True,
            "units": data
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_unit(request, unit_id):
    try:
        owner = request.user

        unit = Unit.objects.get(
            id=unit_id,
            property__owner=owner
        )

        unit.name = request.data.get("name", unit.name)
        unit.description = request.data.get("description", unit.description)
        unit.price_per_month = request.data.get(
            "price_per_month",
            unit.price_per_month
        )
        unit.bedrooms = request.data.get(
            "bedrooms",
            unit.bedrooms
        )
        unit.bathrooms = request.data.get(
            "bathrooms",
            unit.bathrooms
        )
        unit.max_guests = request.data.get(
            "max_guests",
            unit.max_guests
        )
        unit.status = request.data.get(
            "status",
            unit.status
        )
        unit.amenities = request.data.get(
            "amenities",
            unit.amenities
        )

        unit.is_featured = request.data.get(
            "is_featured",
            unit.is_featured
        )

        unit.save()

        return JsonResponse({
            "success": True,
            "message": "Unit updated successfully."
        })

    except Unit.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Unit not found."
        }, status=404)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)