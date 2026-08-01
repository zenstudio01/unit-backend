from .common_imports import *

import json

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum


# ============================================================
# CONFIGURATION
# ============================================================

PROPERTY_VIEW_ROLES = {
    "owner",
    "admin",
    "property_manager",
    "leasing_officer",
    "accountant",
}

PROPERTY_MANAGEMENT_ROLES = {
    "owner",
    "admin",
    "property_manager",
}

VALID_PROPERTY_STATUSES = {
    "available",
    "occupied",
    "under_maintenance",
    "inactive",
}

PROPERTY_TYPE_MAPPING = {
    "residential": "apartment",
    "apartment": "apartment",
    "commercial": "commercial",
    "townhouse": "townhouse",
    "mixed use": "condo",
    "mixed-use": "condo",
    "mixed_use": "condo",
    "condo": "condo",
    "office": "office",
    "warehouse": "warehouse",
    "retail": "retail",
}

PROPERTY_TYPE_LABELS = {
    "apartment": "Residential",
    "commercial": "Commercial",
    "townhouse": "Townhouse",
    "condo": "Mixed Use",
    "office": "Office",
    "warehouse": "Warehouse",
    "retail": "Retail",
}


# ============================================================
# HELPERS
# ============================================================

def get_company_membership(user, company_id):
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


def can_view_properties(membership):
    return (
        membership is not None
        and membership.role in PROPERTY_VIEW_ROLES
    )


def can_manage_properties(membership):
    return (
        membership is not None
        and membership.role in PROPERTY_MANAGEMENT_ROLES
    )


def normalize_decimal(value, default="0.00"):
    if value in [None, ""]:
        return Decimal(default)

    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return None


def normalize_integer(value, default=0):
    if value in [None, ""]:
        return default

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
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return parsed

        except json.JSONDecodeError:
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

    return None


def normalize_property_type(value):
    value = str(
        value or "residential"
    ).strip().lower()

    return PROPERTY_TYPE_MAPPING.get(value)


def get_property_type_label(value):
    return PROPERTY_TYPE_LABELS.get(
        value,
        str(value)
        .replace("_", " ")
        .title(),
    )


def get_unit_name(unit):
    return (
        getattr(unit, "unit_number", None)
        or getattr(unit, "name", None)
    )


def get_unit_rent(unit):
    return (
        getattr(unit, "rent", None)
        or getattr(unit, "price_per_month", None)
        or Decimal("0.00")
    )


def serialize_unit(unit):
    return {
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
            "",
        ),
        "rent": float(
            get_unit_rent(unit)
        ),
        "deposit": float(
            getattr(
                unit,
                "deposit",
                Decimal("0.00"),
            )
            or Decimal("0.00")
        ),
        "bedrooms": getattr(
            unit,
            "bedrooms",
            0,
        ),
        "bathrooms": getattr(
            unit,
            "bathrooms",
            0,
        ),
        "max_guests": getattr(
            unit,
            "max_guests",
            0,
        ),
        "status": unit.status,
        "images": getattr(
            unit,
            "images",
            [],
        ) or [],
    }


def serialize_property(
    property_instance,
    include_units=False,
):
    total_units = getattr(
        property_instance,
        "total_units_count",
        None,
    )

    if total_units is None:
        total_units = (
            property_instance.units.count()
        )

    occupied_units = getattr(
        property_instance,
        "occupied_units_count",
        None,
    )

    if occupied_units is None:
        occupied_units = (
            property_instance.units.filter(
                status="occupied"
            ).count()
        )

    monthly_rent = getattr(
        property_instance,
        "monthly_rent_total",
        None,
    )

    if monthly_rent is None:
        monthly_rent = (
            property_instance.units.aggregate(
                total=Sum("rent")
            )["total"]
            or Decimal("0.00")
        )

    landlord = getattr(
        property_instance,
        "landlord",
        None,
    )

    landlord_user = (
        landlord.user
        if landlord
        else None
    )

    images = (
        property_instance.images
        if getattr(
            property_instance,
            "images",
            None,
        )
        else []
    )

    data = {
        "id": property_instance.id,
        "company_id": property_instance.company_id,
        "company": {
            "id": property_instance.company_id,
            "name": property_instance.company.name,
        },
        "name": property_instance.name,
        "location": property_instance.address,
        "address": property_instance.address,
        "city": property_instance.city,
        "state": property_instance.state,
        "country": property_instance.country,
        "property_type": get_property_type_label(
            property_instance.property_type
        ),
        "property_type_value": (
            property_instance.property_type
        ),
        "status": property_instance.status,
        "description": property_instance.description,
        "legal_plot_number": getattr(
            property_instance,
            "legal_plot_number",
            None,
        ),
        "amenities": getattr(
            property_instance,
            "amenities",
            [],
        ) or [],
        "images": images,
        "image": (
            images[0]
            if images
            else None
        ),
        "total_units": total_units,
        "occupied_units": occupied_units,
        "available_units": max(
            total_units - occupied_units,
            0,
        ),
        "occupancy_rate": (
            round(
                (
                    occupied_units
                    / total_units
                ) * 100,
                2,
            )
            if total_units
            else 0
        ),
        "monthly_rent_amount": float(
            monthly_rent
        ),
        "monthly_rent": (
            f"KES {monthly_rent:,.0f}"
            if monthly_rent
            else "KES 0"
        ),
        "landlord": (
            {
                "id": landlord.id,
                "name": (
                    landlord_user.full_name
                    if landlord_user
                    else None
                ),
                "email": (
                    landlord_user.email
                    if landlord_user
                    else None
                ),
                "phone_number": (
                    landlord_user.phone_number
                    if landlord_user
                    else None
                ),
            }
            if landlord
            else None
        ),
        "created_at": (
            property_instance.created_at.isoformat()
            if getattr(
                property_instance,
                "created_at",
                None,
            )
            else None
        ),
    }

    if include_units:
        data["units"] = [
            serialize_unit(unit)
            for unit
            in property_instance.units.all()
        ]

    return data


# ============================================================
# GET COMPANY PROPERTIES
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_list(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        search = str(
            request.GET.get(
                "search",
                "",
            )
        ).strip()

        property_type = str(
            request.GET.get(
                "property_type",
                "",
            )
        ).strip().lower()

        property_status = str(
            request.GET.get(
                "status",
                "",
            )
        ).strip().lower()

        landlord_id = request.GET.get(
            "landlord_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_properties(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this company's properties."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        properties = (
            Property.objects
            .filter(
                company_id=company_id
            )
            .select_related(
                "company",
                "landlord",
                "landlord__user",
            )
            .annotate(
                total_units_count=Count(
                    "units",
                    distinct=True,
                ),
                occupied_units_count=Count(
                    "units",
                    filter=Q(
                        units__status="occupied"
                    ),
                    distinct=True,
                ),
                monthly_rent_total=Sum(
                    "units__rent"
                ),
            )
            .order_by("-created_at")
        )

        if property_status:
            if (
                property_status
                not in VALID_PROPERTY_STATUSES
            ):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Invalid property status."
                        ),
                        "allowed_statuses": sorted(
                            VALID_PROPERTY_STATUSES
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            properties = properties.filter(
                status=property_status
            )

        if property_type:
            normalized_type = (
                normalize_property_type(
                    property_type
                )
            )

            if not normalized_type:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Invalid property type."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            properties = properties.filter(
                property_type=normalized_type
            )

        if landlord_id:
            properties = properties.filter(
                landlord_id=landlord_id
            )

        if search:
            properties = properties.filter(
                Q(name__icontains=search)
                | Q(address__icontains=search)
                | Q(city__icontains=search)
                | Q(
                    legal_plot_number__icontains=
                    search
                )
                | Q(
                    landlord__user__full_name__icontains=
                    search
                )
            )

        property_data = [
            serialize_property(
                property_instance
            )
            for property_instance
            in properties
        ]

        total_units = sum(
            item["total_units"]
            for item in property_data
        )

        occupied_units = sum(
            item["occupied_units"]
            for item in property_data
        )

        monthly_rent = sum(
            Decimal(
                str(
                    item["monthly_rent_amount"]
                )
            )
            for item in property_data
        )

        return Response(
            {
                "success": True,
                "count": len(property_data),
                "summary": {
                    "total_properties": len(
                        property_data
                    ),
                    "total_units": total_units,
                    "occupied_units": (
                        occupied_units
                    ),
                    "available_units": max(
                        total_units
                        - occupied_units,
                        0,
                    ),
                    "occupancy_rate": (
                        round(
                            (
                                occupied_units
                                / total_units
                            ) * 100,
                            2,
                        )
                        if total_units
                        else 0
                    ),
                    "monthly_rent_amount": float(
                        monthly_rent
                    ),
                    "monthly_rent": (
                        f"KES {monthly_rent:,.0f}"
                    ),
                },
                "properties": property_data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "PROPERTY LIST ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "properties."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# CREATE PROPERTY
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def property_create(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        name = str(
            request.data.get(
                "name",
                "",
            )
        ).strip()

        address = str(
            request.data.get(
                "address",
                request.data.get(
                    "location",
                    "",
                ),
            )
        ).strip()

        property_type_input = (
            request.data.get(
                "property_type",
                "residential",
            )
        )

        description = str(
            request.data.get(
                "description",
                "",
            )
        ).strip()

        property_status = str(
            request.data.get(
                "status",
                "available",
            )
        ).strip().lower()

        city = str(
            request.data.get(
                "city",
                "",
            )
        ).strip()

        state_value = str(
            request.data.get(
                "state",
                "",
            )
        ).strip()

        country = str(
            request.data.get(
                "country",
                "Kenya",
            )
        ).strip()

        legal_plot_number = str(
            request.data.get(
                "legal_plot_number",
                "",
            )
        ).strip()

        landlord_id = request.data.get(
            "landlord_id"
        )

        rent = normalize_decimal(
            request.data.get(
                "rent",
                0,
            )
        )

        deposit = normalize_decimal(
            request.data.get(
                "deposit",
                0,
            )
        )

        total_units = normalize_integer(
            request.data.get(
                "total_units",
                0,
            )
        )

        bedrooms = normalize_integer(
            request.data.get(
                "bedrooms",
                1,
            )
        )

        bathrooms = normalize_integer(
            request.data.get(
                "bathrooms",
                1,
            )
        )

        max_guests = normalize_integer(
            request.data.get(
                "max_guests",
                2,
            )
        )

        amenities = normalize_json_list(
            request.data.get(
                "amenities"
            )
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_properties(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "create properties for this company."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not name:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Property name is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not address:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Property address is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        db_property_type = (
            normalize_property_type(
                property_type_input
            )
        )

        if not db_property_type:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid property type."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            property_status
            not in VALID_PROPERTY_STATUSES
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid property status."
                    ),
                    "allowed_statuses": sorted(
                        VALID_PROPERTY_STATUSES
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            rent is None
            or rent < Decimal("0.00")
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Rent must be a valid "
                        "non-negative amount."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            deposit is None
            or deposit < Decimal("0.00")
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Deposit must be a valid "
                        "non-negative amount."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        numeric_fields = {
            "total_units": total_units,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "max_guests": max_guests,
        }

        for field_name, value in (
            numeric_fields.items()
        ):
            if value is None or value < 0:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"{field_name.replace('_', ' ').title()} "
                            "must be a non-negative integer."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if amenities is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Amenities must be a list."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        landlord = None

        if landlord_id:
            landlord = (
                Landlord.objects
                .select_related(
                    "company",
                    "user",
                )
                .filter(
                    id=landlord_id,
                    company_id=company_id,
                    is_active=True,
                )
                .first()
            )

            if not landlord:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Landlord was not found in "
                            "this company."
                        ),
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        duplicate_exists = (
            Property.objects
            .filter(
                company_id=company_id,
                name__iexact=name,
                address__iexact=address,
            )
            .exists()
        )

        if duplicate_exists:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A property with this name and "
                        "address already exists."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        uploaded_images = []

        for image in request.FILES.getlist(
            "images"
        ):
            upload_result = (
                cloudinary.uploader.upload(
                    image,
                    folder=(
                        f"companies/"
                        f"{company_id}/properties"
                    ),
                    resource_type="image",
                )
            )

            uploaded_images.append(
                upload_result["secure_url"]
            )

        if not city:
            address_parts = [
                part.strip()
                for part in address.split(",")
                if part.strip()
            ]

            city = (
                address_parts[-2]
                if len(address_parts) >= 2
                else address_parts[0]
            )

        if not state_value:
            state_value = city

        if not legal_plot_number:
            legal_plot_number = (
                f"PENDING-"
                f"{timezone.now():%Y%m%d%H%M%S}"
            )

        with transaction.atomic():
            property_asset = (
                Property.objects.create(
                    company=membership.company,
                    landlord=landlord,
                    name=name,
                    address=address,
                    property_type=(
                        db_property_type
                    ),
                    description=description,
                    legal_plot_number=(
                        legal_plot_number
                    ),
                    city=city,
                    state=state_value,
                    country=country,
                    status=property_status,
                    images=uploaded_images,
                    amenities=amenities,
                )
            )

            if total_units > 0:
                units_to_create = []

                for number in range(
                    1,
                    total_units + 1,
                ):
                    unit_number = (
                        f"{number:02d}"
                    )

                    units_to_create.append(
                        Unit(
                            property=property_asset,
                            name=(
                                f"Unit {unit_number}"
                            ),
                            unit_number=(
                                unit_number
                            ),
                            description=(
                                "Automatically created "
                                "property unit."
                            ),
                            rent=rent,
                            deposit=deposit,
                            bedrooms=bedrooms,
                            bathrooms=bathrooms,
                            max_guests=max_guests,
                            status="available",
                        )
                    )

                Unit.objects.bulk_create(
                    units_to_create
                )

        property_asset = (
            Property.objects
            .select_related(
                "company",
                "landlord",
                "landlord__user",
            )
            .prefetch_related("units")
            .get(id=property_asset.id)
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Property created successfully."
                ),
                "property": serialize_property(
                    property_asset,
                    include_units=True,
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as error:
        print(
            "PROPERTY CREATE ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while creating "
                    "the property."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# GET PROPERTIES WITH UNITS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_properties_with_units(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        landlord_id = request.GET.get(
            "landlord_id"
        )

        include_all_units = (
            normalize_boolean(
                request.GET.get(
                    "include_all_units"
                )
            )
        )

        if include_all_units is None:
            include_all_units = False

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_properties(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this company's properties."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        units_queryset = (
            Unit.objects
            .order_by(
                "unit_number",
                "name",
            )
        )

        if not include_all_units:
            units_queryset = (
                units_queryset.filter(
                    status="available"
                )
            )

        properties = (
            Property.objects
            .filter(
                company_id=company_id
            )
            .select_related(
                "company",
                "landlord",
                "landlord__user",
            )
            .prefetch_related(
                Prefetch(
                    "units",
                    queryset=units_queryset,
                )
            )
            .order_by("name")
        )

        if landlord_id:
            properties = properties.filter(
                landlord_id=landlord_id
            )

        data = []

        for property_instance in properties:
            property_data = (
                serialize_property(
                    property_instance
                )
            )

            property_data["units"] = [
                serialize_unit(unit)
                for unit
                in property_instance.units.all()
            ]

            data.append(property_data)

        return Response(
            {
                "success": True,
                "count": len(data),
                "properties": data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET PROPERTIES WITH UNITS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "properties and units."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )