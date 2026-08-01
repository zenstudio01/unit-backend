from .common_imports import *

import json
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.db import transaction


# ============================================================
# CONFIGURATION
# ============================================================

UNIT_MANAGEMENT_ROLES = {
    "admin",
    "property_manager",
    "leasing_officer",
}

VALID_UNIT_STATUSES = {
    "available",
    "occupied",
    "reserved",
    "under_maintenance",
    "inactive",
}


# ============================================================
# HELPERS
# ============================================================

def get_company_membership(user, company_id):
    """
    Return an active membership for the authenticated user.
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


def can_manage_units(membership):
    return (
        membership is not None
        and membership.role in UNIT_MANAGEMENT_ROLES
    )


def normalize_decimal(value):
    if value in [None, ""]:
        return None

    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return None


def normalize_integer(value):
    if value in [None, ""]:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def normalize_boolean(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return None

    normalized = str(value).strip().lower()

    if normalized in {
        "true",
        "1",
        "yes",
        "on",
    }:
        return True

    if normalized in {
        "false",
        "0",
        "no",
        "off",
    }:
        return False

    return None


def normalize_json_list(value):
    """
    Accept a Python list, a JSON string, or a comma-separated string.
    """

    if value is None:
        return None

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            parsed_value = json.loads(value)

            if isinstance(parsed_value, list):
                return parsed_value

            return None

        except json.JSONDecodeError:
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

    return None


def get_unit_rent(unit):
    """
    Support either rent or price_per_month during migration.
    """

    if hasattr(unit, "rent"):
        return unit.rent

    return getattr(
        unit,
        "price_per_month",
        Decimal("0.00"),
    )


def get_unit_name(unit):
    """
    Support either name or unit_number during migration.
    """

    return (
        getattr(unit, "name", None)
        or getattr(unit, "unit_number", None)
    )


def get_unit_amenities(unit):
    """
    Prefer unit amenities, then fall back to property amenities.
    """

    unit_amenities = getattr(
        unit,
        "amenities",
        None,
    )

    if unit_amenities:
        return unit_amenities

    return getattr(
        unit.property,
        "amenities",
        [],
    )


def get_unit_location(unit):
    property_instance = unit.property

    return (
        getattr(property_instance, "address", None)
        or getattr(property_instance, "location", None)
    )


def serialize_unit(
    unit,
    include_company=False,
):
    property_instance = unit.property
    rent = get_unit_rent(unit)

    images = getattr(unit, "images", None) or []
    amenities = get_unit_amenities(unit)

    data = {
        "id": unit.id,
        "name": get_unit_name(unit),
        "unit_number": getattr(
            unit,
            "unit_number",
            None,
        ),
        "description": getattr(
            unit,
            "description",
            None,
        ),
        "property": {
            "id": property_instance.id,
            "name": property_instance.name,
            "property_type": getattr(
                property_instance,
                "property_type",
                None,
            ),
            "location": get_unit_location(unit),
        },
        "property_id": property_instance.id,
        "property_name": property_instance.name,
        "property_type": getattr(
            property_instance,
            "property_type",
            None,
        ),
        "location": get_unit_location(unit),
        "price_per_month": float(
            rent or Decimal("0.00")
        ),
        "rent": float(
            rent or Decimal("0.00")
        ),
        "bedrooms": getattr(
            unit,
            "bedrooms",
            None,
        ),
        "bathrooms": getattr(
            unit,
            "bathrooms",
            None,
        ),
        "max_guests": getattr(
            unit,
            "max_guests",
            None,
        ),
        "status": unit.status,
        "amenities": amenities,
        "images": images,
        "image": images[0] if images else None,
        "is_featured": getattr(
            unit,
            "is_featured",
            False,
        ),
        "featured": getattr(
            unit,
            "is_featured",
            False,
        ),
        "created_at": (
            unit.created_at.isoformat()
            if getattr(unit, "created_at", None)
            else None
        ),
        "updated_at": (
            unit.updated_at.isoformat()
            if getattr(unit, "updated_at", None)
            else None
        ),
    }

    if include_company:
        data["company"] = {
            "id": property_instance.company_id,
            "name": property_instance.company.name,
        }

    return data


def get_company_unit(unit_id, company_id):
    return (
        Unit.objects
        .select_related(
            "property",
            "property__company",
        )
        .filter(
            id=unit_id,
            property__company_id=company_id,
        )
        .first()
    )


# ============================================================
# GET COMPANY UNITS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_units(request):
    try:
        company_id = request.GET.get("company_id")

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        status_filter = str(
            request.GET.get("status", "")
        ).strip().lower()

        property_id = request.GET.get(
            "property_id"
        )

        property_type = str(
            request.GET.get("property_type", "")
        ).strip()

        featured_param = request.GET.get(
            "is_featured"
        )

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

        if not can_manage_units(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's units."
                    ),
                },
                status=403,
            )

        units = (
            Unit.objects
            .filter(
                property__company_id=company_id,
            )
            .select_related(
                "property",
                "property__company",
            )
            .order_by("-created_at")
        )

        if property_id:
            units = units.filter(
                property_id=property_id
            )

        if status_filter:
            if (
                status_filter
                not in VALID_UNIT_STATUSES
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid unit status.",
                        "allowed_statuses": sorted(
                            VALID_UNIT_STATUSES
                        ),
                    },
                    status=400,
                )

            units = units.filter(
                status=status_filter
            )

        if property_type:
            units = units.filter(
                property__property_type__iexact=
                property_type
            )

        if featured_param is not None:
            is_featured = normalize_boolean(
                featured_param
            )

            if is_featured is None:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "is_featured must be true "
                            "or false."
                        ),
                    },
                    status=400,
                )

            units = units.filter(
                is_featured=is_featured
            )

        if search_query:
            units = units.filter(
                Q(name__icontains=search_query)
                | Q(
                    unit_number__icontains=
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
                    property__address__icontains=
                    search_query
                )
            )

        data = [
            serialize_unit(
                unit,
                include_company=True,
            )
            for unit in units
        ]

        summary = {
            "total": units.count(),
            "available": units.filter(
                status="available"
            ).count(),
            "occupied": units.filter(
                status="occupied"
            ).count(),
            "reserved": units.filter(
                status="reserved"
            ).count(),
            "under_maintenance": units.filter(
                status="under_maintenance"
            ).count(),
            "inactive": units.filter(
                status="inactive"
            ).count(),
        }

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "summary": summary,
                "units": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET COMPANY UNITS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the units."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# UPDATE COMPANY UNIT
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_unit(request, unit_id):
    try:
        company_id = request.data.get(
            "company_id"
        )

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

        if not can_manage_units(membership):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to update "
                        "units for this company."
                    ),
                },
                status=403,
            )

        unit = get_company_unit(
            unit_id,
            company_id,
        )

        if not unit:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Unit not found.",
                },
                status=404,
            )

        update_fields = []

        name = request.data.get("name")

        if name is not None:
            name = str(name).strip()

            if not name:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Unit name cannot be empty."
                        ),
                    },
                    status=400,
                )

            if hasattr(unit, "name"):
                unit.name = name
                update_fields.append("name")

        unit_number = request.data.get(
            "unit_number"
        )

        if unit_number is not None:
            unit_number = str(
                unit_number
            ).strip()

            if not unit_number:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Unit number cannot be empty."
                        ),
                    },
                    status=400,
                )

            duplicate_exists = (
                Unit.objects
                .filter(
                    property=unit.property,
                    unit_number__iexact=unit_number,
                )
                .exclude(id=unit.id)
                .exists()
            )

            if duplicate_exists:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Another unit in this property "
                            "already uses this unit number."
                        ),
                    },
                    status=409,
                )

            unit.unit_number = unit_number
            update_fields.append("unit_number")

        if "description" in request.data:
            unit.description = request.data.get(
                "description"
            )

            update_fields.append("description")

        price_value = request.data.get(
            "price_per_month",
            request.data.get("rent"),
        )

        if price_value is not None:
            price = normalize_decimal(
                price_value
            )

            if price is None:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Price per month must be "
                            "a valid number."
                        ),
                    },
                    status=400,
                )

            if price < Decimal("0.00"):
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Price per month cannot "
                            "be negative."
                        ),
                    },
                    status=400,
                )

            if hasattr(unit, "rent"):
                unit.rent = price
                update_fields.append("rent")

            elif hasattr(
                unit,
                "price_per_month",
            ):
                unit.price_per_month = price
                update_fields.append(
                    "price_per_month"
                )

        integer_fields = {
            "bedrooms": request.data.get(
                "bedrooms"
            ),
            "bathrooms": request.data.get(
                "bathrooms"
            ),
            "max_guests": request.data.get(
                "max_guests"
            ),
        }

        for field_name, field_value in (
            integer_fields.items()
        ):
            if field_value is None:
                continue

            normalized_value = normalize_integer(
                field_value
            )

            if (
                normalized_value is None
                or normalized_value < 0
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            f"{field_name.replace('_', ' ').title()} "
                            "must be a valid non-negative integer."
                        ),
                    },
                    status=400,
                )

            setattr(
                unit,
                field_name,
                normalized_value,
            )

            update_fields.append(field_name)

        unit_status = request.data.get("status")

        if unit_status is not None:
            unit_status = str(
                unit_status
            ).strip().lower()

            if unit_status not in VALID_UNIT_STATUSES:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid unit status.",
                        "allowed_statuses": sorted(
                            VALID_UNIT_STATUSES
                        ),
                    },
                    status=400,
                )

            unit.status = unit_status
            update_fields.append("status")

        if "is_featured" in request.data:
            is_featured = normalize_boolean(
                request.data.get("is_featured")
            )

            if is_featured is None:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "is_featured must be true "
                            "or false."
                        ),
                    },
                    status=400,
                )

            unit.is_featured = is_featured
            update_fields.append("is_featured")

        if "amenities" in request.data:
            amenities = normalize_json_list(
                request.data.get("amenities")
            )

            if amenities is None:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Amenities must be a list or "
                            "valid JSON array."
                        ),
                    },
                    status=400,
                )

            if hasattr(unit, "amenities"):
                unit.amenities = amenities
                update_fields.append("amenities")

        remove_image_urls = normalize_json_list(
            request.data.get("remove_images")
        )

        if remove_image_urls is None:
            remove_image_urls = []

        existing_images = (
            list(unit.images)
            if getattr(unit, "images", None)
            else []
        )

        existing_images = [
            image_url
            for image_url in existing_images
            if image_url not in remove_image_urls
        ]

        uploaded_images = []

        for image in request.FILES.getlist(
            "images"
        ):
            result = cloudinary.uploader.upload(
                image,
                folder=(
                    f"companies/{company_id}/"
                    f"properties/{unit.property_id}/"
                    f"units/{unit.id}"
                ),
                resource_type="image",
            )

            uploaded_images.append(
                result["secure_url"]
            )

        replace_images = normalize_boolean(
            request.data.get(
                "replace_images"
            )
        )

        if replace_images is None:
            replace_images = False

        if uploaded_images or remove_image_urls:
            if replace_images:
                unit.images = uploaded_images
            else:
                unit.images = (
                    existing_images
                    + uploaded_images
                )

            update_fields.append("images")

        if not update_fields:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "No valid fields were supplied "
                        "for update."
                    ),
                },
                status=400,
            )

        update_fields = list(
            dict.fromkeys(update_fields)
        )

        if hasattr(unit, "updated_at"):
            update_fields.append("updated_at")

        with transaction.atomic():
            unit.save(
                update_fields=update_fields
            )

        unit.refresh_from_db()

        unit = (
            Unit.objects
            .select_related(
                "property",
                "property__company",
            )
            .get(id=unit.id)
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Unit updated successfully."
                ),
                "unit": serialize_unit(
                    unit,
                    include_company=True,
                ),
            },
            status=200,
        )

    except Exception as error:
        print(
            "UPDATE UNIT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while updating "
                    "the unit."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET PUBLICLY AVAILABLE UNITS
# MOBILE APP
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_available_units(request):
    try:
        category = str(
            request.GET.get("category", "")
        ).strip()

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        location = str(
            request.GET.get("location", "")
        ).strip()

        company_id = request.GET.get(
            "company_id"
        )

        featured_param = request.GET.get(
            "featured"
        )

        min_price = normalize_decimal(
            request.GET.get("min_price")
        )

        max_price = normalize_decimal(
            request.GET.get("max_price")
        )

        min_bedrooms = normalize_integer(
            request.GET.get("min_bedrooms")
        )

        try:
            page = max(
                int(
                    request.GET.get(
                        "page",
                        1,
                    )
                ),
                1,
            )
        except (
            TypeError,
            ValueError,
        ):
            page = 1

        try:
            page_size = int(
                request.GET.get(
                    "page_size",
                    20,
                )
            )

            page_size = min(
                max(page_size, 1),
                100,
            )

        except (
            TypeError,
            ValueError,
        ):
            page_size = 20

        units = (
            Unit.objects
            .select_related(
                "property",
                "property__company",
            )
            .filter(
                status="available",
            )
            .order_by(
                "-is_featured",
                "-created_at",
            )
        )

        if company_id:
            units = units.filter(
                property__company_id=company_id
            )

        if (
            category
            and category.lower() != "all"
        ):
            units = units.filter(
                property__property_type__iexact=
                category
            )

        if location:
            units = units.filter(
                Q(
                    property__address__icontains=
                    location
                )
                | Q(
                    property__location__icontains=
                    location
                )
            )

        if search_query:
            units = units.filter(
                Q(name__icontains=search_query)
                | Q(
                    unit_number__icontains=
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
                    property__address__icontains=
                    search_query
                )
                | Q(
                    property__location__icontains=
                    search_query
                )
            )

        if featured_param is not None:
            featured = normalize_boolean(
                featured_param
            )

            if featured is None:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "featured must be true "
                            "or false."
                        ),
                    },
                    status=400,
                )

            units = units.filter(
                is_featured=featured
            )

        rent_field = (
            "rent"
            if hasattr(Unit, "rent")
            else "price_per_month"
        )

        if min_price is not None:
            units = units.filter(
                **{
                    f"{rent_field}__gte":
                    min_price
                }
            )

        if max_price is not None:
            units = units.filter(
                **{
                    f"{rent_field}__lte":
                    max_price
                }
            )

        if min_bedrooms is not None:
            units = units.filter(
                bedrooms__gte=min_bedrooms
            )

        total_count = units.count()

        start_index = (
            page - 1
        ) * page_size

        end_index = (
            start_index
            + page_size
        )

        units_page = units[
            start_index:end_index
        ]

        data = [
            serialize_unit(unit)
            for unit in units_page
        ]

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": end_index < total_count,
                "units": data,

                # Keep this temporarily for old mobile code.
                "properties": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET AVAILABLE UNITS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "available units."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET ONE UNIT
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_unit(request, unit_id):
    try:
        unit = (
            Unit.objects
            .select_related(
                "property",
                "property__company",
            )
            .filter(id=unit_id)
            .first()
        )

        if not unit:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Unit not found.",
                },
                status=404,
            )

        membership = (
            CompanyStaff.objects
            .filter(
                user=request.user,
                company_id=unit.property.company_id,
                is_active=True,
            )
            .first()
        )

        is_company_staff = (
            membership is not None
        )

        is_available = (
            unit.status == "available"
        )

        is_current_tenant = (
            Lease.objects
            .filter(
                tenant__user=request.user,
                unit=unit,
                status="active",
            )
            .exists()
        )

        landlord_user_id = getattr(
            getattr(
                unit.property,
                "landlord",
                None,
            ),
            "user_id",
            None,
        )

        is_landlord = (
            landlord_user_id
            == request.user.id
        )

        if not any([
            is_available,
            is_company_staff,
            is_current_tenant,
            is_landlord,
        ]):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this unit."
                    ),
                },
                status=403,
            )

        data = serialize_unit(
            unit,
            include_company=is_company_staff,
        )

        return JsonResponse(
            {
                "success": True,
                "unit": data,

                # Keep this temporarily if the mobile app
                # still reads response.property.
                "property": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "GET UNIT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the unit."
                ),
                "error": str(error),
            },
            status=500,
        )