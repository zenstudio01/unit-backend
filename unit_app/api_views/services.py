from .common_imports import *


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_company_service(request):
    try:
        # Check company
        company = Company.objects.filter(owner=request.user).first()

        if not company:
            return JsonResponse({
                "success": False,
                "message": "Company profile not found."
            }, status=404)

        title = request.data.get("title")
        description = request.data.get("description")
        category = request.data.get("category")
        minimum_price = request.data.get("minimum_price")
        maximum_price = request.data.get("maximum_price")
        duration = request.data.get("duration")
        image = request.FILES.get("image")

        if not title:
            return JsonResponse({
                "success": False,
                "message": "Service title is required."
            }, status=400)

        if not minimum_price or not maximum_price:
            return JsonResponse({
                "success": False,
                "message": "Price range is required."
            }, status=400)

        image_url = None

        if image:
            upload = cloudinary.uploader.upload(
                image,
                folder="unit/company_services"
            )

            image_url = upload.get("secure_url")

        service = CompanyService.objects.create(
            company=company,
            title=title,
            description=description,
            category=category,
            minimum_price=minimum_price,
            maximum_price=maximum_price,
            duration=duration,
            image=image_url
        )

        return JsonResponse({
            "success": True,
            "message": "Service added successfully.",
            "service": {
                "id": service.id,
                "title": service.title,
                "description": service.description,
                "category": service.category,
                "minimum_price": str(service.minimum_price),
                "maximum_price": str(service.maximum_price),
                "duration": service.duration,
                "image": service.image,
                "is_active": service.is_active,
                "created_at": service.created_at
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_services(request):
    try:
        company = Company.objects.filter(owner=request.user).first()

        if not company:
            return JsonResponse({
                "success": False,
                "message": "Company profile not found."
            }, status=404)

        services = CompanyService.objects.filter(
            company=company
        ).order_by("-created_at")

        data = []

        for service in services:
            data.append({
                "id": service.id,
                "title": service.title,
                "description": service.description,
                "category": service.category,
                "minimum_price": str(service.minimum_price),
                "maximum_price": str(service.maximum_price),
                "duration": service.duration,
                "image": service.image,
                "is_active": service.is_active,
                "created_at": service.created_at,
            })

        return JsonResponse({
            "success": True,
            "services": data
        })

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_service(request, service_id):
    try:
        company = Company.objects.filter(owner=request.user).first()

        service = CompanyService.objects.filter(
            id=service_id,
            company=company
        ).first()

        if not service:
            return JsonResponse({
                "success": False,
                "message": "Service not found."
            }, status=404)

        return JsonResponse({
            "success": True,
            "service": {
                "id": service.id,
                "title": service.title,
                "description": service.description,
                "category": service.category,
                "minimum_price": str(service.minimum_price),
                "maximum_price": str(service.maximum_price),
                "duration": service.duration,
                "image": service.image,
                "is_active": service.is_active,
            }
        })

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_company_service(request, service_id):
    try:
        company = Company.objects.filter(owner=request.user).first()

        service = CompanyService.objects.filter(
            id=service_id,
            company=company
        ).first()

        if not service:
            return JsonResponse({
                "success": False,
                "message": "Service not found."
            }, status=404)

        service.title = request.data.get("title", service.title)
        service.description = request.data.get("description", service.description)
        service.category = request.data.get("category", service.category)
        service.minimum_price = request.data.get("minimum_price", service.minimum_price)
        service.maximum_price = request.data.get("maximum_price", service.maximum_price)
        service.duration = request.data.get("duration", service.duration)
        service.is_active = request.data.get("is_active", service.is_active)

        image = request.FILES.get("image")

        if image:
            upload = cloudinary.uploader.upload(
                image,
                folder="unit/company_services"
            )

            service.image = upload.get("secure_url")

        service.save()

        return JsonResponse({
            "success": True,
            "message": "Service updated successfully."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_company_service(request, service_id):
    try:
        company = Company.objects.filter(owner=request.user).first()

        service = CompanyService.objects.filter(
            id=service_id,
            company=company
        ).first()

        if not service:
            return JsonResponse({
                "success": False,
                "message": "Service not found."
            }, status=404)

        service.delete()

        return JsonResponse({
            "success": True,
            "message": "Service deleted successfully."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)





