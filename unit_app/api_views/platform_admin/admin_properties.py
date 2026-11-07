
from decimal import Decimal

from django.db.models import (
    Count, Q, Sum, Prefetch,
)
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Property,
    Unit,
    Building,
    PropertyOwnership,
)


class IsPlatformAdmin(BasePermission):
    message = "Platform administrator access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


class PropertyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def property_queryset():
    return (
        Property.objects
        .select_related("organization", "portifolio")
        .annotate(
            unit_count=Count("units", distinct=True),
            occupied_count=Count(
                "units",
                filter=Q(units__status="occupied"),
                distinct=True,
            ),
            available_count=Count(
                "units",
                filter=Q(units__status="available"),
                distinct=True,
            ),
            maintenance_count=Count(
                "units",
                filter=Q(units__status="under_maintenance"),
                distinct=True,
            ),
            building_count=Count("buildings", distinct=True),
        )
    )


def serialize_property(prop):
    total = prop.unit_count or 0
    occupied = prop.occupied_count or 0

    return {
        "id": prop.id,
        "name": prop.name,
        "property_code": prop.property_code,
        "property_type": prop.property_type,
        "ownership_type": prop.ownership_type,
        "description": prop.description,
        "status": prop.status,
        "address": prop.address,
        "city": prop.city,
        "county": prop.county,
        "country": prop.country,
        "year_built": prop.year_built,
        "created_at": prop.created_at,
        "organization": {
            "id": prop.organization_id,
            "name": prop.organization.name,
        },
        "portfolio": {
            "id": prop.portifolio_id,
            "name": prop.portifolio.name,
        },
        "total_units": total,
        "occupied_units": occupied,
        "available_units": prop.available_count or 0,
        "maintenance_units": prop.maintenance_count or 0,
        "total_buildings": prop.building_count or 0,
        "occupancy_rate": round(
            occupied / total * 100, 1
        ) if total else 0,
    }


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_properties(request):
    qs = property_queryset()

    search = request.query_params.get("search", "").strip()
    status = request.query_params.get("status", "").strip()
    prop_type = request.query_params.get("type", "").strip()
    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()
    county = request.query_params.get("county", "").strip()

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(property_code__icontains=search)
            | Q(address__icontains=search)
            | Q(city__icontains=search)
            | Q(county__icontains=search)
            | Q(organization__name__icontains=search)
        )

    if status:
        if status not in ("active", "inactive"):
            return Response(
                {"message": "Invalid property status."},
                status=400,
            )
        qs = qs.filter(status=status)

    if prop_type:
        qs = qs.filter(property_type=prop_type)

    if county:
        qs = qs.filter(county__icontains=county)

    if organization_id:
        if not organization_id.isdigit():
            return Response(
                {"message": "Invalid organization ID."},
                status=400,
            )
        qs = qs.filter(organization_id=int(organization_id))

    qs = qs.order_by("-created_at", "-id")

    paginator = PropertyPagination()
    page = paginator.paginate_queryset(qs, request)

    return paginator.get_paginated_response([
        serialize_property(prop)
        for prop in page
    ])


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_property_stats(request):
    properties = Property.objects.all()
    units = Unit.objects.all()

    unit_stats = units.aggregate(
        total=Count("id"),
        occupied=Count(
            "id", filter=Q(status="occupied")
        ),
        available=Count(
            "id", filter=Q(status="available")
        ),
        maintenance=Count(
            "id", filter=Q(status="under_maintenance")
        ),
        monthly_rent_potential=Sum("monthly_rent"),
        occupied_monthly_rent=Sum(
            "monthly_rent",
            filter=Q(status="occupied"),
        ),
    )

    total_units = unit_stats["total"] or 0
    occupied_units = unit_stats["occupied"] or 0

    return Response({
        "total_properties": properties.count(),
        "active_properties": properties.filter(
            status="active"
        ).count(),
        "inactive_properties": properties.filter(
            status="inactive"
        ).count(),
        "total_buildings": Building.objects.count(),
        "total_units": total_units,
        "occupied_units": occupied_units,
        "available_units": unit_stats["available"] or 0,
        "maintenance_units": unit_stats["maintenance"] or 0,
        "occupancy_rate": round(
            occupied_units / total_units * 100, 1
        ) if total_units else 0,
        "monthly_rent_potential": str(
            unit_stats["monthly_rent_potential"]
            or Decimal("0")
        ),
        "occupied_monthly_rent": str(
            unit_stats["occupied_monthly_rent"]
            or Decimal("0")
        ),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_property_detail(request, property_id):
    prop = get_object_or_404(
        property_queryset(),
        pk=property_id,
    )

    buildings = (
        Building.objects
        .filter(property=prop)
        .prefetch_related("floors")
        .order_by("name")
    )

    units = (
        Unit.objects
        .filter(property=prop)
        .select_related("building", "floor")
        .order_by("name")
    )

    ownerships = (
        PropertyOwnership.objects
        .filter(property=prop, is_active=True)
        .select_related("owner")
        .order_by("-created_at")
    )

    return Response({
        "property": serialize_property(prop),
        "buildings": [
            {
                "id": building.id,
                "name": building.name,
                "building_code": building.building_code,
                "status": building.status,
                "number_of_floors": building.number_of_floors,
                "floors": [
                    {
                        "id": floor.id,
                        "name": floor.name,
                        "floor_number": floor.floor_number,
                        "status": floor.status,
                    }
                    for floor in building.floors.all()
                ],
            }
            for building in buildings
        ],
        "units": [
            {
                "id": unit.id,
                "name": unit.name,
                "unit_code": unit.unit_code,
                "unit_type": unit.unit_type,
                "building": unit.building.name,
                "floor": unit.floor.name,
                "bedrooms": unit.bedrooms,
                "bathrooms": unit.bathrooms,
                "monthly_rent": str(unit.monthly_rent),
                "status": unit.status,
            }
            for unit in units
        ],
        "owners": [
            {
                "id": ownership.owner_id,
                "name": ownership.owner.name,
                "email": ownership.owner.email,
                "ownership_percentage": str(
                    ownership.ownership_percentage
                ),
            }
            for ownership in ownerships
        ],
    })
