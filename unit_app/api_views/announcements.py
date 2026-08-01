from .common_imports import *

from django.db import transaction
from django.utils import timezone


# ============================================================
# HELPERS
# ============================================================

ANNOUNCEMENT_ALLOWED_ROLES = {
    "admin",
    "property_manager",
    "leasing_officer",
}


def normalize_boolean(value, default=None):
    """
    Convert JSON or multipart form-data values into boolean values.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized_value = value.strip().lower()

        if normalized_value in {
            "true",
            "1",
            "yes",
            "on",
        }:
            return True

        if normalized_value in {
            "false",
            "0",
            "no",
            "off",
        }:
            return False

    return bool(value)


def get_company_staff(user, company_id):
    """
    Return the active CompanyStaff membership for the user.
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


def can_manage_announcements(membership):
    """
    Check whether the staff member can create, update,
    or delete company announcements.
    """

    return (
        membership
        and membership.role in ANNOUNCEMENT_ALLOWED_ROLES
    )


def serialize_announcement(announcement):
    return {
        "id": announcement.id,
        "company": {
            "id": announcement.company_id,
            "name": announcement.company.name,
        },
        "created_by": (
            {
                "membership_id": announcement.created_by_id,
                "user_id": announcement.created_by.user_id,
                "full_name": (
                    announcement.created_by.user.full_name
                ),
                "role": announcement.created_by.role,
            }
            if announcement.created_by
            else None
        ),
        "title": announcement.title,
        "message": announcement.message,
        "target": announcement.target,
        "property": (
            {
                "id": announcement.property_id,
                "name": announcement.property.name,
            }
            if announcement.property
            else None
        ),
        "unit": (
            {
                "id": announcement.unit_id,
                "unit_number": announcement.unit.unit_number,
            }
            if announcement.unit
            else None
        ),
        "is_active": announcement.is_active,
        "published_at": (
            announcement.published_at.isoformat()
            if announcement.published_at
            else None
        ),
        "expires_at": (
            announcement.expires_at.isoformat()
            if announcement.expires_at
            else None
        ),
        "created_at": announcement.created_at.isoformat(),
        "updated_at": announcement.updated_at.isoformat(),
    }


# ============================================================
# CREATE ANNOUNCEMENT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_announcement(request):
    try:
        company_id = request.data.get("company_id")
        title = str(
            request.data.get("title", "")
        ).strip()

        message = str(
            request.data.get("message", "")
        ).strip()

        target = str(
            request.data.get("target", "all")
        ).strip().lower()

        property_id = request.data.get("property_id")
        unit_id = request.data.get("unit_id")
        expires_at = request.data.get("expires_at")

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        if not title:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Title is required.",
                },
                status=400,
            )

        if not message:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Message is required.",
                },
                status=400,
            )

        allowed_targets = {
            "all",
            "property",
            "unit",
        }

        if target not in allowed_targets:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid announcement target.",
                    "allowed_targets": list(allowed_targets),
                },
                status=400,
            )

        membership = get_company_staff(
            request.user,
            company_id,
        )

        if not membership:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not belong to this company."
                    ),
                },
                status=403,
            )

        if not can_manage_announcements(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to create "
                        "company announcements."
                    ),
                },
                status=403,
            )

        selected_property = None
        selected_unit = None

        # ----------------------------------------------------
        # Property target
        # ----------------------------------------------------

        if target == "property":
            if not property_id:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Property is required when the "
                            "target is property."
                        ),
                    },
                    status=400,
                )

            selected_property = (
                Property.objects
                .filter(
                    id=property_id,
                    company_id=company_id,
                )
                .first()
            )

            if not selected_property:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Property was not found in this company."
                        ),
                    },
                    status=404,
                )

        # ----------------------------------------------------
        # Unit target
        # ----------------------------------------------------

        elif target == "unit":
            if not unit_id:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Unit is required when the target "
                            "is unit."
                        ),
                    },
                    status=400,
                )

            selected_unit = (
                Unit.objects
                .select_related("property")
                .filter(
                    id=unit_id,
                    property__company_id=company_id,
                )
                .first()
            )

            if not selected_unit:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Unit was not found in this company."
                        ),
                    },
                    status=404,
                )

            selected_property = selected_unit.property

        with transaction.atomic():
            announcement = Announcement.objects.create(
                company=membership.company,
                created_by=membership,
                property=selected_property,
                unit=selected_unit,
                title=title,
                message=message,
                target=target,
                is_active=True,
                published_at=timezone.now(),
                expires_at=expires_at or None,
            )

        announcement = (
            Announcement.objects
            .select_related(
                "company",
                "created_by__user",
                "property",
                "unit",
            )
            .get(id=announcement.id)
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Announcement created successfully."
                ),
                "announcement": serialize_announcement(
                    announcement
                ),
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE ANNOUNCEMENT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while creating "
                    "the announcement."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET COMPANY ANNOUNCEMENTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_announcements(request):
    try:
        company_id = request.GET.get("company_id")
        target = str(
            request.GET.get("target", "")
        ).strip().lower()

        active_filter = request.GET.get("is_active")
        property_id = request.GET.get("property_id")
        unit_id = request.GET.get("unit_id")

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=400,
            )

        membership = get_company_staff(
            request.user,
            company_id,
        )

        if not membership:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not belong to this company."
                    ),
                },
                status=403,
            )

        announcements = (
            Announcement.objects
            .select_related(
                "company",
                "created_by__user",
                "property",
                "unit",
            )
            .filter(company_id=company_id)
            .order_by("-created_at")
        )

        if target:
            allowed_targets = {
                "all",
                "property",
                "unit",
            }

            if target not in allowed_targets:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Invalid announcement target."
                        ),
                    },
                    status=400,
                )

            announcements = announcements.filter(
                target=target
            )

        if property_id:
            announcements = announcements.filter(
                property_id=property_id
            )

        if unit_id:
            announcements = announcements.filter(
                unit_id=unit_id
            )

        if active_filter is not None:
            is_active = normalize_boolean(
                active_filter,
                default=None,
            )

            if is_active is not None:
                announcements = announcements.filter(
                    is_active=is_active
                )

        data = [
            serialize_announcement(announcement)
            for announcement in announcements
        ]

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "announcements": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET ANNOUNCEMENTS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "announcements."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET SINGLE ANNOUNCEMENT
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_announcement(request, announcement_id):
    try:
        announcement = (
            Announcement.objects
            .select_related(
                "company",
                "created_by__user",
                "property",
                "unit",
            )
            .filter(id=announcement_id)
            .first()
        )

        if not announcement:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Announcement not found.",
                },
                status=404,
            )

        membership = get_company_staff(
            request.user,
            announcement.company_id,
        )

        if not membership:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have access to this announcement."
                    ),
                },
                status=403,
            )

        return JsonResponse(
            {
                "success": True,
                "announcement": serialize_announcement(
                    announcement
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
                    "the announcement."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# UPDATE ANNOUNCEMENT
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_announcement(request, announcement_id):
    try:
        announcement = (
            Announcement.objects
            .select_related(
                "company",
                "created_by__user",
                "property",
                "unit",
            )
            .filter(id=announcement_id)
            .first()
        )

        if not announcement:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Announcement not found.",
                },
                status=404,
            )

        membership = get_company_staff(
            request.user,
            announcement.company_id,
        )

        if not membership:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not belong to this company."
                    ),
                },
                status=403,
            )

        if not can_manage_announcements(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to update "
                        "company announcements."
                    ),
                },
                status=403,
            )

        title = request.data.get("title")
        message = request.data.get("message")
        target = request.data.get("target")

        property_id = request.data.get("property_id")
        unit_id = request.data.get("unit_id")

        if title is not None:
            title = str(title).strip()

            if not title:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Title cannot be empty.",
                    },
                    status=400,
                )

            announcement.title = title

        if message is not None:
            message = str(message).strip()

            if not message:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Message cannot be empty.",
                    },
                    status=400,
                )

            announcement.message = message

        if target is not None:
            target = str(target).strip().lower()

            allowed_targets = {
                "all",
                "property",
                "unit",
            }

            if target not in allowed_targets:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Invalid announcement target."
                        ),
                        "allowed_targets": list(
                            allowed_targets
                        ),
                    },
                    status=400,
                )

            announcement.target = target

            if target == "all":
                announcement.property = None
                announcement.unit = None

            elif target == "property":
                if not property_id:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": (
                                "Property is required when "
                                "the target is property."
                            ),
                        },
                        status=400,
                    )

                selected_property = (
                    Property.objects
                    .filter(
                        id=property_id,
                        company_id=announcement.company_id,
                    )
                    .first()
                )

                if not selected_property:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": (
                                "Property was not found in "
                                "this company."
                            ),
                        },
                        status=404,
                    )

                announcement.property = selected_property
                announcement.unit = None

            elif target == "unit":
                if not unit_id:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": (
                                "Unit is required when "
                                "the target is unit."
                            ),
                        },
                        status=400,
                    )

                selected_unit = (
                    Unit.objects
                    .select_related("property")
                    .filter(
                        id=unit_id,
                        property__company_id=(
                            announcement.company_id
                        ),
                    )
                    .first()
                )

                if not selected_unit:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": (
                                "Unit was not found in "
                                "this company."
                            ),
                        },
                        status=404,
                    )

                announcement.unit = selected_unit
                announcement.property = (
                    selected_unit.property
                )

        if "is_active" in request.data:
            announcement.is_active = normalize_boolean(
                request.data.get("is_active"),
                default=announcement.is_active,
            )

        if "expires_at" in request.data:
            announcement.expires_at = (
                request.data.get("expires_at") or None
            )

        announcement.save()

        updated_announcement = (
            Announcement.objects
            .select_related(
                "company",
                "created_by__user",
                "property",
                "unit",
            )
            .get(id=announcement.id)
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Announcement updated successfully."
                ),
                "announcement": serialize_announcement(
                    updated_announcement
                ),
            },
            status=200,
        )

    except Exception as error:
        print(
            "UPDATE ANNOUNCEMENT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while updating "
                    "the announcement."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# DELETE ANNOUNCEMENT
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_announcement(request, announcement_id):
    try:
        announcement = (
            Announcement.objects
            .select_related("company")
            .filter(id=announcement_id)
            .first()
        )

        if not announcement:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Announcement not found.",
                },
                status=404,
            )

        membership = get_company_staff(
            request.user,
            announcement.company_id,
        )

        if not membership:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not belong to this company."
                    ),
                },
                status=403,
            )

        if not can_manage_announcements(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to delete "
                        "company announcements."
                    ),
                },
                status=403,
            )

        deleted_announcement = {
            "id": announcement.id,
            "title": announcement.title,
            "company_id": announcement.company_id,
        }

        announcement.delete()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Announcement deleted successfully."
                ),
                "deleted_announcement": (
                    deleted_announcement
                ),
            },
            status=200,
        )

    except Exception as error:
        print(
            "DELETE ANNOUNCEMENT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while deleting "
                    "the announcement."
                ),
                "error": str(error),
            },
            status=500,
        )