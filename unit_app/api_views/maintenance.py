from .common_imports import *

from django.db import transaction
from django.db.models import Q


# ============================================================
# CONFIGURATION
# ============================================================

MAINTENANCE_MANAGEMENT_ROLES = {
    "admin",
    "property_manager",
    "maintenance_officer",
}

MAINTENANCE_ASSIGNMENT_ROLES = {
    "admin",
    "property_manager",
    "maintenance_officer",
}

VALID_MAINTENANCE_STATUSES = {
    "pending",
    "assigned",
    "in_progress",
    "completed",
    "cancelled",
}


# ============================================================
# HELPERS
# ============================================================

def get_company_membership(user, company_id):
    """
    Return the authenticated user's active company membership.
    """

    return (
        CompanyStaff.objects
        .select_related(
            "company",
            "user",
        )
        .filter(
            user=user,
            company_id=company_id,
            is_active=True,
        )
        .first()
    )


def can_manage_maintenance(membership):
    return (
        membership is not None
        and membership.role in MAINTENANCE_MANAGEMENT_ROLES
    )


def can_assign_professional(membership):
    return (
        membership is not None
        and membership.role in MAINTENANCE_ASSIGNMENT_ROLES
    )


def get_maintenance_request_for_company(
    request_id,
    company_id,
):
    """
    Fetch a maintenance request belonging to a specific company.
    """

    return (
        MaintenanceRequest.objects
        .select_related(
            "company",
            "tenant__user",
            "property",
            "unit",
            "assigned_professional__user",
        )
        .filter(
            id=request_id,
            property__company_id=company_id,
        )
        .first()
    )


def serialize_maintenance_request(
    maintenance,
    current_user=None,
):
    tenant_user = (
        maintenance.tenant.user
        if maintenance.tenant
        and maintenance.tenant.user
        else None
    )

    professional_user = (
        maintenance.assigned_professional.user
        if maintenance.assigned_professional
        and maintenance.assigned_professional.user
        else None
    )

    return {
        "id": maintenance.id,
        "title": maintenance.title,
        "description": maintenance.description,
        "category": maintenance.category,
        "priority": maintenance.priority,
        "priority_label": (
            maintenance.priority.replace("_", " ").title()
            if maintenance.priority
            else None
        ),
        "status": maintenance.status,
        "status_label": (
            maintenance.status.replace("_", " ").title()
            if maintenance.status
            else None
        ),
        "company": {
            "id": maintenance.property.company_id,
            "name": maintenance.property.company.name,
        },
        "property": {
            "id": maintenance.property_id,
            "name": maintenance.property.name,
        },
        "unit": (
            {
                "id": maintenance.unit_id,
                "unit_number": maintenance.unit.unit_number,
            }
            if maintenance.unit
            else None
        ),
        "tenant": (
            {
                "id": maintenance.tenant_id,
                "user_id": tenant_user.id,
                "full_name": tenant_user.full_name,
                "email": tenant_user.email,
                "phone_number": tenant_user.phone_number,
                "profile_image": tenant_user.profile_image,
            }
            if tenant_user
            else None
        ),
        "assigned_professional": (
            {
                "id": maintenance.assigned_professional_id,
                "user_id": professional_user.id,
                "full_name": professional_user.full_name,
                "phone_number": professional_user.phone_number,
                "profile_image": professional_user.profile_image,
                "professional_title": (
                    maintenance
                    .assigned_professional
                    .professional_title
                ),
                "years_of_experience": (
                    maintenance
                    .assigned_professional
                    .years_of_experience
                ),
            }
            if professional_user
            else None
        ),
        "image": getattr(
            maintenance,
            "image",
            None,
        ),
        "created_at": maintenance.created_at.isoformat(),
        "updated_at": (
            maintenance.updated_at.isoformat()
            if getattr(maintenance, "updated_at", None)
            else None
        ),
        "is_reported_by_me": (
            tenant_user.id == current_user.id
            if tenant_user and current_user
            else False
        ),
    }


def safe_send_push_notification(
    user,
    title,
    body,
    data=None,
):
    expo_token = getattr(
        user,
        "expo_token",
        None,
    )

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
            "MAINTENANCE PUSH ERROR:",
            str(error),
        )

        return False


# ============================================================
# GET COMPANY MAINTENANCE REQUESTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_maintenance_requests(request):
    try:
        company_id = request.GET.get("company_id")
        status_filter = str(
            request.GET.get("status", "")
        ).strip().lower()

        priority_filter = str(
            request.GET.get("priority", "")
        ).strip().lower()

        property_id = request.GET.get("property_id")
        professional_id = request.GET.get(
            "professional_id"
        )

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

        if not can_manage_maintenance(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's maintenance requests."
                    ),
                },
                status=403,
            )

        maintenance_requests = (
            MaintenanceRequest.objects
            .filter(
                property__company_id=company_id,
            )
            .select_related(
                "property__company",
                "tenant__user",
                "unit",
                "assigned_professional__user",
            )
            .order_by("-created_at")
        )

        if status_filter:
            if status_filter not in VALID_MAINTENANCE_STATUSES:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid status filter.",
                        "allowed_statuses": sorted(
                            VALID_MAINTENANCE_STATUSES
                        ),
                    },
                    status=400,
                )

            maintenance_requests = (
                maintenance_requests.filter(
                    status=status_filter
                )
            )

        if priority_filter:
            maintenance_requests = (
                maintenance_requests.filter(
                    priority=priority_filter
                )
            )

        if property_id:
            maintenance_requests = (
                maintenance_requests.filter(
                    property_id=property_id
                )
            )

        if professional_id:
            maintenance_requests = (
                maintenance_requests.filter(
                    assigned_professional_id=
                    professional_id
                )
            )

        if search_query:
            maintenance_requests = (
                maintenance_requests.filter(
                    Q(
                        title__icontains=
                        search_query
                    )
                    | Q(
                        description__icontains=
                        search_query
                    )
                    | Q(
                        property__name__icontains=
                        search_query
                    )
                    | Q(
                        unit__unit_number__icontains=
                        search_query
                    )
                    | Q(
                        tenant__user__full_name__icontains=
                        search_query
                    )
                )
            )

        data = [
            serialize_maintenance_request(
                maintenance,
                request.user,
            )
            for maintenance in maintenance_requests
        ]

        summary = {
            "total": maintenance_requests.count(),
            "pending": maintenance_requests.filter(
                status="pending"
            ).count(),
            "assigned": maintenance_requests.filter(
                status="assigned"
            ).count(),
            "in_progress": maintenance_requests.filter(
                status="in_progress"
            ).count(),
            "completed": maintenance_requests.filter(
                status="completed"
            ).count(),
            "cancelled": maintenance_requests.filter(
                status="cancelled"
            ).count(),
        }

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "summary": summary,
                "requests": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET MAINTENANCE REQUESTS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "maintenance requests."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# ALIAS FOR EXISTING FRONTEND ENDPOINT
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_maintenance_requests(request):
    """
    Maintains compatibility with the existing frontend while
    using the same multi-tenant maintenance logic.
    """

    return property_manager_maintenance_requests(
        request
    )


# ============================================================
# GET SINGLE MAINTENANCE REQUEST
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_maintenance_request(
    request,
    request_id,
):
    try:
        company_id = request.GET.get("company_id")

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

        if not can_manage_maintenance(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this maintenance request."
                    ),
                },
                status=403,
            )

        maintenance = (
            get_maintenance_request_for_company(
                request_id,
                company_id,
            )
        )

        if not maintenance:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Maintenance request not found."
                    ),
                },
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "request": (
                    serialize_maintenance_request(
                        maintenance,
                        request.user,
                    )
                ),
            },
            status=200,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the maintenance request."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# UPDATE MAINTENANCE STATUS
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_maintenance_status(
    request,
    request_id,
):
    try:
        company_id = request.data.get("company_id")

        new_status = str(
            request.data.get("status", "")
        ).strip().lower()

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        if not new_status:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Status is required.",
                },
                status=400,
            )

        if new_status not in VALID_MAINTENANCE_STATUSES:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid status.",
                    "allowed_statuses": sorted(
                        VALID_MAINTENANCE_STATUSES
                    ),
                },
                status=400,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_maintenance(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to update "
                        "maintenance requests."
                    ),
                },
                status=403,
            )

        maintenance = (
            get_maintenance_request_for_company(
                request_id,
                company_id,
            )
        )

        if not maintenance:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Maintenance request not found."
                    ),
                },
                status=404,
            )

        old_status = maintenance.status

        if old_status == new_status:
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "Maintenance request already has "
                        "this status."
                    ),
                    "request": (
                        serialize_maintenance_request(
                            maintenance,
                            request.user,
                        )
                    ),
                },
                status=200,
            )

        # Optional workflow protection.
        if (
            new_status == "in_progress"
            and not maintenance.assigned_professional
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Assign a professional before moving "
                        "the request to in progress."
                    ),
                },
                status=400,
            )

        maintenance.status = new_status

        update_fields = ["status"]

        if (
            new_status == "completed"
            and hasattr(maintenance, "completed_at")
        ):
            maintenance.completed_at = timezone.now()
            update_fields.append("completed_at")

        if (
            old_status == "completed"
            and new_status != "completed"
            and hasattr(maintenance, "completed_at")
        ):
            maintenance.completed_at = None
            update_fields.append("completed_at")

        maintenance.save(
            update_fields=update_fields
        )

        tenant_user = (
            maintenance.tenant.user
            if maintenance.tenant
            and maintenance.tenant.user
            else None
        )

        notification_sent = False

        if tenant_user:
            notification_sent = (
                safe_send_push_notification(
                    tenant_user,
                    title="Maintenance update",
                    body=(
                        f'Your maintenance request '
                        f'"{maintenance.title}" is now '
                        f'{new_status.replace("_", " ")}.'
                    ),
                    data={
                        "screen": "MaintenanceDetails",
                        "maintenance_request_id": str(
                            maintenance.id
                        ),
                        "company_id": str(
                            company_id
                        ),
                    },
                )
            )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Maintenance status updated successfully."
                ),
                "old_status": old_status,
                "new_status": new_status,
                "notification_sent": notification_sent,
                "request": (
                    serialize_maintenance_request(
                        maintenance,
                        request.user,
                    )
                ),
            },
            status=200,
        )

    except Exception as error:
        print(
            "UPDATE MAINTENANCE STATUS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while updating "
                    "the maintenance status."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# ASSIGN PROFESSIONAL
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def assign_professional(
    request,
    request_id,
):
    try:
        company_id = request.data.get("company_id")
        professional_id = request.data.get(
            "professional_id"
        )

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        if not professional_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Professional is required."
                    ),
                },
                status=400,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_assign_professional(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to assign "
                        "maintenance professionals."
                    ),
                },
                status=403,
            )

        maintenance = (
            get_maintenance_request_for_company(
                request_id,
                company_id,
            )
        )

        if not maintenance:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Maintenance request not found."
                    ),
                },
                status=404,
            )

        professional = (
            Professional.objects
            .select_related(
                "user",
                "company",
            )
            .filter(
                id=professional_id,
                company_id=company_id,
            )
            .first()
        )

        if not professional:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Professional not found in this company."
                    ),
                },
                status=404,
            )

        if not professional.user.is_active:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "The selected professional's account "
                        "is inactive."
                    ),
                },
                status=400,
            )

        with transaction.atomic():
            maintenance.assigned_professional = (
                professional
            )

            if maintenance.status in {
                "pending",
                "cancelled",
            }:
                maintenance.status = "assigned"

            maintenance.save(
                update_fields=[
                    "assigned_professional",
                    "status",
                ]
            )

        professional_notification_sent = (
            safe_send_push_notification(
                professional.user,
                title="New maintenance assignment",
                body=(
                    f'You have been assigned to '
                    f'"{maintenance.title}" at '
                    f'{maintenance.property.name}.'
                ),
                data={
                    "screen": "ProfessionalMaintenanceDetails",
                    "maintenance_request_id": str(
                        maintenance.id
                    ),
                    "company_id": str(
                        company_id
                    ),
                },
            )
        )

        tenant_notification_sent = False

        if (
            maintenance.tenant
            and maintenance.tenant.user
        ):
            tenant_notification_sent = (
                safe_send_push_notification(
                    maintenance.tenant.user,
                    title="Professional assigned",
                    body=(
                        f'{professional.user.full_name} has '
                        f'been assigned to your maintenance '
                        f'request "{maintenance.title}".'
                    ),
                    data={
                        "screen": "MaintenanceDetails",
                        "maintenance_request_id": str(
                            maintenance.id
                        ),
                        "company_id": str(
                            company_id
                        ),
                    },
                )
            )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Professional assigned successfully."
                ),
                "professional_notification_sent": (
                    professional_notification_sent
                ),
                "tenant_notification_sent": (
                    tenant_notification_sent
                ),
                "request": (
                    serialize_maintenance_request(
                        maintenance,
                        request.user,
                    )
                ),
            },
            status=200,
        )

    except Exception as error:
        print(
            "ASSIGN PROFESSIONAL ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while assigning "
                    "the professional."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# REMOVE ASSIGNED PROFESSIONAL
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def unassign_professional(
    request,
    request_id,
):
    try:
        company_id = request.data.get("company_id")

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

        if not can_assign_professional(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "remove assigned professionals."
                    ),
                },
                status=403,
            )

        maintenance = (
            get_maintenance_request_for_company(
                request_id,
                company_id,
            )
        )

        if not maintenance:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Maintenance request not found."
                    ),
                },
                status=404,
            )

        if not maintenance.assigned_professional:
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "No professional is assigned to "
                        "this request."
                    ),
                },
                status=200,
            )

        previous_professional = (
            maintenance.assigned_professional
        )

        maintenance.assigned_professional = None

        if maintenance.status in {
            "assigned",
            "in_progress",
        }:
            maintenance.status = "pending"

        maintenance.save(
            update_fields=[
                "assigned_professional",
                "status",
            ]
        )

        safe_send_push_notification(
            previous_professional.user,
            title="Maintenance assignment removed",
            body=(
                f'You are no longer assigned to '
                f'"{maintenance.title}".'
            ),
            data={
                "screen": "ProfessionalMaintenance",
                "maintenance_request_id": str(
                    maintenance.id
                ),
                "company_id": str(company_id),
            },
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Professional removed successfully."
                ),
                "request": (
                    serialize_maintenance_request(
                        maintenance,
                        request.user,
                    )
                ),
            },
            status=200,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while removing "
                    "the professional."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET COMPANY PROFESSIONALS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_professionals(request):
    try:
        company_id = request.GET.get("company_id")

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        professional_title = str(
            request.GET.get("title", "")
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

        if not can_manage_maintenance(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's professionals."
                    ),
                },
                status=403,
            )

        professionals = (
            Professional.objects
            .filter(
                company_id=company_id,
                user__is_active=True,
            )
            .select_related(
                "user",
                "company",
            )
            .order_by("user__full_name")
        )

        if search_query:
            professionals = professionals.filter(
                Q(
                    user__full_name__icontains=
                    search_query
                )
                | Q(
                    user__email__icontains=
                    search_query
                )
                | Q(
                    user__phone_number__icontains=
                    search_query
                )
                | Q(
                    professional_title__icontains=
                    search_query
                )
            )

        if professional_title:
            professionals = professionals.filter(
                professional_title__icontains=
                professional_title
            )

        data = []

        for professional in professionals:
            active_assignments = (
                MaintenanceRequest.objects
                .filter(
                    assigned_professional=professional,
                    property__company_id=company_id,
                    status__in=[
                        "assigned",
                        "in_progress",
                    ],
                )
                .count()
            )

            completed_assignments = (
                MaintenanceRequest.objects
                .filter(
                    assigned_professional=professional,
                    property__company_id=company_id,
                    status="completed",
                )
                .count()
            )

            data.append({
                "id": professional.id,
                "user_id": professional.user_id,
                "name": professional.user.full_name,
                "email": professional.user.email,
                "phone": (
                    professional.user.phone_number
                ),
                "profile_image": (
                    professional.user.profile_image
                ),
                "title": (
                    professional.professional_title
                ),
                "experience": (
                    professional.years_of_experience
                ),
                "active_assignments": (
                    active_assignments
                ),
                "completed_assignments": (
                    completed_assignments
                ),
            })

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "professionals": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET COMPANY PROFESSIONALS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "company professionals."
                ),
                "error": str(error),
            },
            status=500,
        )