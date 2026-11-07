
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Organization,
    Property,
    Unit,
    Tenant,
    Lease,
    Payment,
    MaintenanceTicket,
    SubscriptionPackage,
    OrganizationSubscription,
    SubscriptionPayment,
    ConstructionProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectTask,
    BOQItem,
)


class IsPlatformAdmin(BasePermission):
    message = "Only UNIT platform administrators can access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


def optional_model(name):
    try:
        return apps.get_model("unit_app", name)
    except LookupError:
        return None


def count_model(name, **filters):
    model = optional_model(name)
    if model is None:
        return None

    field_names = {
        f.name for f in model._meta.get_fields()
    }

    if not all(key.split("__")[0] in field_names for key in filters):
        return None

    return model.objects.filter(**filters).count()


def amount_model(name, field="amount", **filters):
    model = optional_model(name)
    if model is None:
        return None

    fields = {f.name for f in model._meta.get_fields()}
    if field not in fields:
        return None

    if not all(key.split("__")[0] in fields for key in filters):
        return None

    return model.objects.filter(**filters).aggregate(
        total=Sum(field)
    )["total"] or Decimal("0")


def format_money(value):
    return str(value) if value is not None else None


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_dashboard(request):
    now = timezone.now()
    month_start = now.replace(
        day=1, hour=0, minute=0,
        second=0, microsecond=0,
    )

    User = get_user_model()

    # Organizations and users
    total_organizations = Organization.objects.count()
    new_organizations = Organization.objects.filter(
        created_at__gte=month_start
    ).count()

    total_users = User.objects.count()
    active_users = User.objects.filter(
        is_active=True
    ).count()
    new_users = User.objects.filter(
        created_at__gte=month_start
    ).count()

    # Properties and rental management
    total_properties = Property.objects.count()
    total_units = Unit.objects.count()
    occupied_units = Unit.objects.filter(
        status="occupied"
    ).count()

    occupancy_rate = round(
        occupied_units / total_units * 100, 1
    ) if total_units else 0

    total_tenants = Tenant.objects.count()
    active_leases = Lease.objects.filter(
        status="active"
    ).count()

    rent_collected = Payment.objects.filter(
        status="completed",
        currency="KES",
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    # Maintenance
    open_maintenance = MaintenanceTicket.objects.exclude(
        status__in=["completed", "closed", "cancelled"]
    ).count()

    recent_maintenance = (
        MaintenanceTicket.objects
        .select_related("property", "organization")
        .order_by("-created_at")[:6]
    )

    # Subscriptions
    subscriptions = OrganizationSubscription.objects.all()

    active_subscriptions = subscriptions.filter(
        status="active",
        current_period_end__gt=now,
    ).count()

    active_trials = subscriptions.filter(
        status="trial",
        trial_end__gt=now,
    ).count()

    expired_subscriptions = subscriptions.filter(
        status="expired"
    ).count()

    completed_payments = SubscriptionPayment.objects.filter(
        status="completed",
        currency="KES",
    )

    revenue_this_month = completed_payments.filter(
        paid_at__gte=month_start,
        paid_at__lte=now,
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    total_subscription_revenue = completed_payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    revenue_series = list(
        completed_payments.filter(
            paid_at__gte=month_start - timedelta(days=365)
        )
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    plan_distribution = list(
        subscriptions.filter(
            status="active",
            current_period_end__gt=now,
        )
        .values("package__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Construction
    total_projects = ConstructionProject.objects.count()

    active_projects = ConstructionProject.objects.filter(
        status="in_progress"
    ).count()

    completed_projects = ConstructionProject.objects.filter(
        status="completed"
    ).count()

    recent_projects = (
        ConstructionProject.objects
        .select_related("organization")
        .order_by("-created_at")[:6]
    )

    # Optional module models
    procurement_orders = count_model(
        "ProcurementPurchaseOrder"
    )
    pending_purchase_orders = count_model(
        "ProcurementPurchaseOrder",
        status="pending",
    )
    suppliers = count_model("ProcurementSupplier")
    deliveries = count_model("ProcurementDelivery")

    workforce_workers = count_model("WorkforceWorker")
    workforce_assignments = count_model(
        "WorkforceAssignment",
        is_active=True,
    )
    workforce_payments = amount_model(
        "WorkforcePayment"
    )

    inspections = count_model("QualityInspection")
    open_defects = count_model("QualityDefect", status="open")
    critical_defects = count_model(
        "QualityDefect",
        severity="critical",
        status="open",
    )

    project_budgets = amount_model(
        "ProjectBudget",
        field="amount",
    )
    project_expenses = amount_model(
        "ProjectExpense",
        field="amount",
    )

    # Recent organizations with aggregated counts
    organizations = (
        Organization.objects
        .select_related("created_by")
        .annotate(
            property_count=Count("properties", distinct=True),
            project_count=Count(
                "construction_projects", distinct=True
            ),
        )
        .order_by("-created_at")[:6]
    )

    organization_data = []
    for org in organizations:
        subscription = OrganizationSubscription.objects.filter(
            organization=org
        ).select_related("package").first()

        organization_data.append({
            "id": org.id,
            "name": org.name,
            "owner": org.created_by.get_full_name()
                or org.created_by.username,
            "properties": org.property_count,
            "projects": org.project_count,
            "units": Unit.objects.filter(
                property__organization=org
            ).count(),
            "plan": (
                subscription.package.name
                if subscription else "No Plan"
            ),
            "status": (
                subscription.status
                if subscription else "none"
            ),
            "created_at": org.created_at.isoformat(),
        })

    return Response({
        "overview": {
            "organizations": total_organizations,
            "new_organizations_this_month": new_organizations,
            "users": total_users,
            "active_users": active_users,
            "new_users_this_month": new_users,
            "properties": total_properties,
            "units": total_units,
            "tenants": total_tenants,
            "occupancy_rate": occupancy_rate,
            "active_leases": active_leases,
        },
        "subscriptions": {
            "plans": SubscriptionPackage.objects.count(),
            "active": active_subscriptions,
            "trials": active_trials,
            "expired": expired_subscriptions,
            "revenue_this_month": str(revenue_this_month),
            "total_revenue": str(total_subscription_revenue),
            "plan_distribution": [
                {
                    "name": item["package__name"],
                    "count": item["count"],
                }
                for item in plan_distribution
            ],
            "monthly_revenue": [
                {
                    "month": item["month"].strftime("%Y-%m"),
                    "amount": str(item["total"]),
                }
                for item in revenue_series
            ],
        },
        "property_management": {
            "properties": total_properties,
            "units": total_units,
            "occupied_units": occupied_units,
            "available_units": Unit.objects.filter(
                status="available"
            ).count(),
            "tenants": total_tenants,
            "active_leases": active_leases,
            "occupancy_rate": occupancy_rate,
            "collected_payments_kes": str(rent_collected),
            "open_maintenance": open_maintenance,
        },
        "construction": {
            "projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "phases": ProjectPhase.objects.count(),
            "milestones": ProjectMilestone.objects.count(),
            "tasks": ProjectTask.objects.count(),
            "boq_items": BOQItem.objects.count(),
            "budget_total": format_money(project_budgets),
            "expenses_total": format_money(project_expenses),
        },
        "procurement": {
            "purchase_orders": procurement_orders,
            "pending_orders": pending_purchase_orders,
            "suppliers": suppliers,
            "deliveries": deliveries,
        },
        "workforce": {
            "workers": workforce_workers,
            "active_assignments": workforce_assignments,
            "payments_total": format_money(workforce_payments),
        },
        "quality": {
            "inspections": inspections,
            "open_defects": open_defects,
            "critical_defects": critical_defects,
        },
        "recent_organizations": organization_data,
        "recent_projects": [
            {
                "id": p.id,
                "name": p.name,
                "code": p.project_code,
                "organization": p.organization.name,
                "status": p.status,
            }
            for p in recent_projects
        ],
        "recent_maintenance": [
            {
                "id": m.id,
                "ticket": m.ticket_number,
                "title": m.title,
                "property": m.property.name,
                "status": m.status,
            }
            for m in recent_maintenance
        ],
    })
