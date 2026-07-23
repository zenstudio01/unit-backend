from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_maintenance_requests(request):
    user = request.user

    properties = Property.objects.filter(owner=user)

    requests = (
        MaintenanceRequest.objects
        .filter(property__in=properties)
        .select_related(
            "tenant",
            "tenant__user",
            "property",
            "unit"
        )
        .order_by("-created_at")
    )

    data = []

    for item in requests:
        data.append({
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "category": item.category,
            "priority": item.priority,
            "status": item.status,
            "property": item.property.name,
            "unit": item.unit.name,
            "tenant": item.tenant.user.full_name,
            "created_at": item.created_at,
            # "image": item.image,
        })

    return JsonResponse({
        "requests": data
    })



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_maintenance_status(request, request_id):
    maintenance = MaintenanceRequest.objects.filter(
        id=request_id
    ).first()

    if not maintenance:
        return JsonResponse({
            "message": "Maintenance request not found."
        }, status=404)

    status = request.data.get("status")

    if status not in [
        "pending",
        "assigned",
        "in_progress",
        "completed",
        "cancelled"
    ]:
        return JsonResponse({
            "message": "Invalid status."
        }, status=400)

    maintenance.status = status
    maintenance.save()

    return JsonResponse({
        "success": True,
        "message": "Status updated successfully."
    })




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_maintenance_requests(request):
    user = request.user

    requests = MaintenanceRequest.objects.filter(
        property__manager=user
    ).select_related(
        "tenant",
        "property",
        "unit"
    ).order_by("-created_at")

    data = []

    for item in requests:
        data.append({
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "priority": item.priority.title(),
            "status": item.status.title(),
            "category": item.category,
            "property": item.property.name,
            "unit": item.unit.unit_number,
            "reportedBy": item.tenant.user.full_name,
            "assigned_to": (
                item.assigned_professional.user.full_name
                if item.assigned_professional
                else None
            ),
            "created_at": item.created_at,
        })

    return JsonResponse({
        "requests": data
    })



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_maintenance_status(request, request_id):

    maintenance = MaintenanceRequest.objects.filter(
        id=request_id
    ).first()

    if not maintenance:
        return JsonResponse({
            "message": "Maintenance request not found."
        }, status=404)

    status = request.data.get("status")

    maintenance.status = status
    maintenance.save()

    return JsonResponse({
        "message": "Status updated successfully."
    })


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def assign_professional(request, request_id):

    maintenance = MaintenanceRequest.objects.filter(
        id=request_id
    ).first()

    if not maintenance:
        return JsonResponse({
            "message": "Maintenance request not found."
        }, status=404)

    professional_id = request.data.get("professional_id")

    professional = Professional.objects.filter(
        id=professional_id
    ).first()

    if not professional:
        return JsonResponse({
            "message": "Professional not found."
        }, status=404)

    maintenance.assigned_professional = professional
    maintenance.status = "assigned"
    maintenance.save()

    return JsonResponse({
        "message": "Professional assigned successfully."
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_professionals(request):

    user = request.user

    company = Company.objects.filter(
        owner=user
    ).first()

    professionals = Professional.objects.filter(
        company=company
    ).select_related("user")

    data = []

    for professional in professionals:
        data.append({
            "id": professional.id,
            "name": professional.user.full_name,
            "phone": professional.company.phone_number,
            "title": professional.professional_title,
            "experience": professional.years_of_experience,
        })

    return JsonResponse({
        "professionals": data
    })