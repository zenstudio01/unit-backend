
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Organization,
    User,
    Property,
    Unit,
    Tenant,
    Lease,
    Payment,
    SubscriptionPayment,
    OrganizationSubscription,
    SubscriptionPackage,
    MaintenanceTicket,
    ConstructionProject,
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


def has_field(model, name):
    return any(
        f.name == name for f in model._meta.concrete_fields
    )


def get_params(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=365)

    try:
        start = date.fromisoformat(
            request.query_params.get(
                "start_date", default_start.isoformat()
            )
        )
        end = date.fromisoformat(
            request.query_params.get(
                "end_date", today.isoformat()
            )
        )
    except ValueError:
        return None, Response(
            {"message": "Dates must use YYYY-MM-DD."},
            status=400,
        )

    if start > end:
        return None, Response(
            {"message": "Start date cannot exceed end date."},
            status=400,
        )

    if (end - start).days > 1826:
        return None, Response(
            {"message": "Maximum reporting range is five years."},
            status=400,
        )

    org = request.query_params.get(
        "organization_id", ""
    ).strip()

    if org and (not org.isdigit() or int(org) < 1):
        return None, Response(
            {"message": "Invalid organization ID."},
            status=400,
        )

    if org and not Organization.objects.filter(
        pk=int(org)
    ).exists():
        return None, Response(
            {"message": "Organization not found."},
            status=404,
        )

    return {
        "start": start,
        "end": end,
        "organization_id": int(org) if org else None,
    }, None


def scoped(model, params, date_field=None, org_path="organization"):
    qs = model.objects.all()
    org_id = params["organization_id"]

    if org_id:
        qs = qs.filter(
            **{f"{org_path}_id": org_id}
        )

    if date_field and has_field(model, date_field):
        field = model._meta.get_field(date_field)
        field_type = field.get_internal_type()

        if field_type == "DateTimeField":
            start = timezone.make_aware(
                datetime.combine(params["start"], time.min)
            )
            end_exclusive = timezone.make_aware(
                datetime.combine(
                    params["end"] + timedelta(days=1),
                    time.min,
                )
            )
            qs = qs.filter(
                **{
                    f"{date_field}__gte": start,
                    f"{date_field}__lt": end_exclusive,
                }
            )
        else:
            qs = qs.filter(
                **{
                    f"{date_field}__gte": params["start"],
                    f"{date_field}__lte": params["end"],
                }
            )

    return qs


def currency_totals(queryset):
    return [
        {
            "currency": row["currency"],
            "amount": str(row["amount"] or Decimal("0")),
            "count": row["count"],
        }
        for row in queryset.values("currency").annotate(
            amount=Sum("amount"),
            count=Count("id"),
        ).order_by("currency")
    ]


def breakdown(queryset, field):
    return list(
        queryset.values(field)
        .annotate(count=Count("id"))
        .order_by("-count", field)
    )


def months(start, end):
    cursor = start.replace(day=1)
    last = end.replace(day=1)
    result = []

    while cursor <= last:
        result.append(cursor.strftime("%Y-%m"))

        if cursor.month == 12:
            cursor = cursor.replace(
                year=cursor.year + 1, month=1
            )
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    return result


def monthly_amounts(queryset, date_field):
    rows = (
        queryset.annotate(month=TruncMonth(date_field))
        .values("month", "currency")
        .annotate(total=Sum("amount"))
        .order_by("month", "currency")
    )

    return [
        {
            "month": row["month"].strftime("%Y-%m"),
            "currency": row["currency"],
            "amount": str(row["total"] or 0),
        }
        for row in rows if row["month"]
    ]


def ratio(part, whole):
    return round(part / whole * 100, 1) if whole else 0


def report_overview(params):
    organizations = scoped(
        Organization, params,
        "created_at", org_path="id"
    )
    properties = scoped(Property, params, "created_at")
    tenants = scoped(Tenant, params, "created_at")
    leases = scoped(Lease, params, "created_at")
    units = scoped(Unit, params)
    maintenance = scoped(
        MaintenanceTicket, params, "created_at"
    )
    construction = scoped(
        ConstructionProject, params, "created_at"
    )
    subscriptions = scoped(
        OrganizationSubscription, params
    )

    property_payments = scoped(
        Payment, params, "paid_at"
    ).filter(status="completed")

    saas_payments = scoped(
        SubscriptionPayment, params, "paid_at"
    ).filter(status="completed")

    if params["organization_id"]:
        users_count = User.objects.filter(
            organizationmembership__organization_id=(
                params["organization_id"]
            )
        ).distinct().count()
    else:
        users_count = User.objects.count()

    return {
        "organizations": organizations.count(),
        "users": users_count,
        "properties": properties.count(),
        "units": units.count(),
        "occupied_units": units.filter(
            status="occupied"
        ).count(),
        "available_units": units.filter(
            status="available"
        ).count(),
        "tenants": tenants.count(),
        "leases": leases.count(),
        "active_leases": leases.filter(
            status="active"
        ).count(),
        "maintenance_tickets": maintenance.count(),
        "construction_projects": construction.count(),
        "active_subscriptions": subscriptions.filter(
            status="active"
        ).count(),
        "property_collections": currency_totals(
            property_payments
        ),
        "saas_revenue": currency_totals(
            saas_payments
        ),
    }


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_overview(request):
    params, error = get_params(request)
    if error is not None:
        return error

    return Response({
        "period": {
            "start_date": params["start"].isoformat(),
            "end_date": params["end"].isoformat(),
            "organization_id": params["organization_id"],
        },
        **report_overview(params),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_revenue(request):
    params, error = get_params(request)
    if error is not None:
        return error

    property_qs = scoped(
        Payment, params, "paid_at"
    ).filter(status="completed")

    saas_qs = scoped(
        SubscriptionPayment, params, "paid_at"
    ).filter(status="completed")

    return Response({
        "months": months(params["start"], params["end"]),
        "property_payments": monthly_amounts(
            property_qs, "paid_at"
        ),
        "subscription_payments": monthly_amounts(
            saas_qs, "paid_at"
        ),
        "property_totals": currency_totals(property_qs),
        "saas_totals": currency_totals(saas_qs),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_occupancy(request):
    params, error = get_params(request)
    if error is not None:
        return error

    properties = scoped(Property, params)
    units = scoped(Unit, params)

    total = units.count()
    occupied = units.filter(status="occupied").count()

    by_property = list(
        units.values(
            "property_id",
            "property__name",
        )
        .annotate(
            total_units=Count("id"),
            occupied_units=Count(
                "id",
                filter=__import__(
                    "django.db.models", fromlist=["Q"]
                ).Q(status="occupied"),
            ),
        )
        .order_by("-total_units", "property__name")[:20]
    )

    return Response({
        "total_properties": properties.count(),
        "total_units": total,
        "occupied_units": occupied,
        "available_units": units.filter(
            status="available"
        ).count(),
        "under_maintenance_units": units.filter(
            status="under_maintenance"
        ).count(),
        "occupancy_rate": ratio(occupied, total),
        "unit_status_breakdown": breakdown(
            units, "status"
        ),
        "top_properties": [
            {
                **item,
                "occupancy_rate": ratio(
                    item["occupied_units"],
                    item["total_units"],
                ),
            }
            for item in by_property
        ],
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_maintenance(request):
    params, error = get_params(request)
    if error is not None:
        return error

    qs = scoped(
        MaintenanceTicket, params, "created_at"
    )

    total = qs.count()
    completed = qs.filter(
        status__in=["completed", "closed"]
    ).count()

    costs = qs.aggregate(
        estimated=Sum("estimated_cost"),
        actual=Sum("actual_cost"),
    )

    return Response({
        "total": total,
        "completed": completed,
        "completion_rate": ratio(completed, total),
        "unassigned": qs.filter(
            assigned_to__isnull=True
        ).exclude(
            status__in=["completed", "closed", "cancelled"]
        ).count(),
        "status_breakdown": breakdown(qs, "status"),
        "priority_breakdown": breakdown(qs, "priority"),
        "category_breakdown": breakdown(qs, "category"),
        "estimated_cost": str(costs["estimated"] or 0),
        "actual_cost": str(costs["actual"] or 0),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_construction(request):
    params, error = get_params(request)
    if error is not None:
        return error

    qs = scoped(
        ConstructionProject, params, "created_at"
    )

    total = qs.count()
    completed = qs.filter(status="completed").count()

    budgets = qs.aggregate(
        approved_budget=Sum("approved_budget")
    )

    return Response({
        "total": total,
        "completed": completed,
        "completion_rate": ratio(completed, total),
        "in_progress": qs.filter(
            status="in_progress"
        ).count(),
        "on_hold": qs.filter(
            status="on_hold"
        ).count(),
        "approved_budget": str(
            budgets["approved_budget"] or 0
        ),
        "status_breakdown": breakdown(qs, "status"),
        "type_breakdown": breakdown(qs, "project_type"),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_reports_subscriptions(request):
    params, error = get_params(request)
    if error is not None:
        return error

    subscriptions = scoped(
        OrganizationSubscription, params
    )

    payments = scoped(
        SubscriptionPayment, params, "paid_at"
    ).filter(status="completed")

    packages = (
        subscriptions.values(
            "package_id",
            "package__name",
        )
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return Response({
        "total": subscriptions.count(),
        "active": subscriptions.filter(
            status="active"
        ).count(),
        "trial": subscriptions.filter(
            status="trial"
        ).count(),
        "expired": subscriptions.filter(
            status="expired"
        ).count(),
        "past_due": subscriptions.filter(
            status="past_due"
        ).count(),
        "status_breakdown": breakdown(
            subscriptions, "status"
        ),
        "package_breakdown": list(packages),
        "revenue": currency_totals(payments),
    })
