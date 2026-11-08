
from datetime import timedelta
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Tenant,
    TenantUnitAssignment,
    TenantScreening,
    Lease,
    LeaseTenant,
    Unit,
)


class IsPlatformAdmin(BasePermission):
    message = "UNIT platform administrator access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


class TenantPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def iso(value):
    return value.isoformat() if value else None


def choices(model, field_name):
    return [
        {"value": key, "label": str(label)}
        for key, label in model._meta.get_field(
            field_name
        ).flatchoices
        if key not in ("", None)
    ]


def tenant_queryset():
    return Tenant.objects.select_related("organization")


def serialize_tenant(tenant):
    assignments = TenantUnitAssignment.objects.filter(
        tenant_id=tenant.pk,
        is_active=True,
    )

    active_leases = LeaseTenant.objects.filter(
        tenant_id=tenant.pk,
        lease__status="active",
        left_at__isnull=True,
    ).count()

    return {
        "id": tenant.pk,
        "full_name": tenant.full_name,
        "email": tenant.email,
        "phone_number": tenant.phone_number,
        "tenant_type": tenant.tenant_type,
        "status": tenant.status,
        "organization": {
            "id": tenant.organization_id,
            "name": tenant.organization.name,
        },
        "active_units": assignments.count(),
        "active_leases": active_leases,
        "created_at": iso(tenant.created_at),
    }


def serialize_lease(lease):
    tenants = LeaseTenant.objects.filter(
        lease_id=lease.pk,
        left_at__isnull=True,
    ).select_related("tenant").order_by(
        "-is_primary", "id"
    )

    return {
        "id": lease.pk,
        "lease_number": lease.lease_number,
        "status": lease.status,
        "organization": {
            "id": lease.organization_id,
            "name": lease.organization.name,
        },
        "property": {
            "id": lease.unit.property_id,
            "name": lease.unit.property.name,
        },
        "unit": {
            "id": lease.unit_id,
            "name": lease.unit.name,
            "unit_code": lease.unit.unit_code,
        },
        "tenants": [
            {
                "id": item.tenant_id,
                "name": item.tenant.full_name,
                "role": item.tenant_role,
                "is_primary": item.is_primary,
            }
            for item in tenants
        ],
        "monthly_rent": str(lease.monthly_rent),
        "deposit_amount": str(lease.deposit_amount),
        "payment_frequency": lease.payment_frequency,
        "start_date": iso(lease.start_date),
        "end_date": iso(lease.end_date),
        "created_at": iso(lease.created_at),
    }


def paginate(request, queryset, serializer):
    paginator = TenantPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([
        serializer(item) for item in page
    ])


def organization_filter(request, queryset):
    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    if not organization_id:
        return queryset, None

    if not organization_id.isdigit():
        return None, Response(
            {"message": "Invalid organization ID."},
            status=400,
        )

    return queryset.filter(
        organization_id=int(organization_id)
    ), None


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_tenants(request):
    queryset = tenant_queryset()

    search = request.query_params.get(
        "search", ""
    ).strip()

    status = request.query_params.get(
        "status", ""
    ).strip()

    tenant_type = request.query_params.get(
        "type", ""
    ).strip()

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(organization__name__icontains=search)
        )

    for field, selected in (
        ("status", status),
        ("tenant_type", tenant_type),
    ):
        if selected:
            valid = {
                item["value"]
                for item in choices(Tenant, field)
            }

            if selected not in valid:
                return Response(
                    {"message": f"Invalid {field}."},
                    status=400,
                )

            queryset = queryset.filter(
                **{field: selected}
            )

    queryset, error = organization_filter(
        request, queryset
    )
    if error is not None:
        return error

    return paginate(
        request,
        queryset.order_by("-created_at", "-pk"),
        serialize_tenant,
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_tenant_stats(request):
    tenants = Tenant.objects.all()
    leases = Lease.objects.all()
    assignments = TenantUnitAssignment.objects.all()

    today = timezone.localdate()
    next_30 = today + timedelta(days=30)

    active_lease_ids = LeaseTenant.objects.filter(
        lease__status="active",
        left_at__isnull=True,
    ).values_list("tenant_id", flat=True)

    return Response({
        "total_tenants": tenants.count(),
        "active_tenants": tenants.filter(
            status="active"
        ).count(),
        "inactive_tenants": tenants.filter(
            status="inactive"
        ).count(),
        "blocked_tenants": tenants.filter(
            status="blocked"
        ).count(),
        "tenants_with_active_leases": tenants.filter(
            id__in=active_lease_ids
        ).count(),
        "active_unit_assignments": assignments.filter(
            is_active=True
        ).count(),
        "total_units": Unit.objects.count(),
        "occupied_units": Unit.objects.filter(
            status="occupied"
        ).count(),
        "available_units": Unit.objects.filter(
            status="available"
        ).count(),
        "total_leases": leases.count(),
        "active_leases": leases.filter(
            status="active"
        ).count(),
        "expired_leases": leases.filter(
            status="expired"
        ).count(),
        "leases_expiring_30_days": leases.filter(
            status="active",
            end_date__gte=today,
            end_date__lte=next_30,
        ).count(),
        "overdue_active_leases": leases.filter(
            status="active",
            end_date__lt=today,
        ).count(),
        "pending_screenings": TenantScreening.objects.filter(
            status__in=["pending", "in_progress"]
        ).count(),
        "tenant_type_breakdown": list(
            tenants.values("tenant_type")
            .annotate(count=Count("id"))
            .order_by("tenant_type")
        ),
        "status_choices": choices(Tenant, "status"),
        "type_choices": choices(Tenant, "tenant_type"),
        "lease_status_choices": choices(Lease, "status"),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_tenant_detail(request, tenant_id):
    tenant = get_object_or_404(
        tenant_queryset(),
        pk=tenant_id,
    )

    assignments = (
        TenantUnitAssignment.objects
        .filter(tenant_id=tenant.pk)
        .select_related("property", "unit")
        .order_by("-created_at")[:100]
    )

    lease_links = (
        LeaseTenant.objects
        .filter(tenant_id=tenant.pk)
        .select_related(
            "lease__organization",
            "lease__unit__property",
        )
        .order_by("-created_at")[:100]
    )

    screenings = (
        TenantScreening.objects
        .filter(tenant_id=tenant.pk)
        .order_by("-created_at")[:100]
    )

    return Response({
        "tenant": serialize_tenant(tenant),
        "assignments": [
            {
                "id": item.pk,
                "property": item.property.name,
                "unit": item.unit.name,
                "unit_code": item.unit.unit_code,
                "move_in_date": iso(item.move_in_date),
                "is_active": item.is_active,
                "assigned_at": iso(item.assigned_at),
                "ended_at": iso(item.ended_at),
            }
            for item in assignments
        ],
        "leases": [
            {
                **serialize_lease(item.lease),
                "tenant_role": item.tenant_role,
                "is_primary": item.is_primary,
                "joined_at": iso(item.joined_at),
                "left_at": iso(item.left_at),
            }
            for item in lease_links
        ],
        "screenings": [
            {
                "id": item.pk,
                "screening_type": item.screening_type,
                "status": item.status,
                "result": item.result,
                "requested_at": iso(item.requested_at),
                "completed_at": iso(item.completed_at),
            }
            for item in screenings
        ],
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_tenant_leases(request):
    queryset = Lease.objects.select_related(
        "organization",
        "unit__property",
    )

    search = request.query_params.get(
        "search", ""
    ).strip()

    status = request.query_params.get(
        "status", ""
    ).strip()

    expiring = request.query_params.get(
        "expiring", ""
    ).strip()

    if search:
        queryset = queryset.filter(
            Q(lease_number__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(unit__unit_code__icontains=search)
            | Q(lease_tenants__tenant__full_name__icontains=search)
        ).distinct()

    if status:
        valid = {
            item["value"]
            for item in choices(Lease, "status")
        }
        if status not in valid:
            return Response(
                {"message": "Invalid lease status."},
                status=400,
            )
        queryset = queryset.filter(status=status)

    if expiring:
        if expiring != "30":
            return Response(
                {"message": "Invalid expiring filter."},
                status=400,
            )

        today = timezone.localdate()
        queryset = queryset.filter(
            status="active",
            end_date__gte=today,
            end_date__lte=today + timedelta(days=30),
        )

    queryset, error = organization_filter(
        request, queryset
    )
    if error is not None:
        return error

    return paginate(
        request,
        queryset.order_by("-created_at", "-pk"),
        serialize_lease,
    )
