from .common_imports import *

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Count,
    Prefetch,
    Q,
    Sum,
)
from django.db.models.functions import (
    Coalesce,
    TruncMonth,
)
from django.utils import timezone


# ============================================================
# CONFIGURATION
# ============================================================

DASHBOARD_VIEW_ROLES = {
    "owner",
    "admin",
    "property_manager",
    "leasing_officer",
    "accountant",
}

PAYMENT_VIEW_ROLES = {
    "owner",
    "admin",
    "property_manager",
    "accountant",
}

MAINTENANCE_VIEW_ROLES = {
    "owner",
    "admin",
    "property_manager",
    "maintenance_manager",
}

MAINTENANCE_UPDATE_ROLES = {
    "owner",
    "admin",
    "property_manager",
    "maintenance_manager",
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


def can_view_dashboard(membership):
    return (
        membership is not None
        and membership.role
        in DASHBOARD_VIEW_ROLES
    )


def can_view_payments(membership):
    return (
        membership is not None
        and membership.role
        in PAYMENT_VIEW_ROLES
    )


def can_view_maintenance(membership):
    return (
        membership is not None
        and membership.role
        in MAINTENANCE_VIEW_ROLES
    )


def can_update_maintenance(membership):
    return (
        membership is not None
        and membership.role
        in MAINTENANCE_UPDATE_ROLES
    )


def get_unit_name(unit):
    if not unit:
        return None

    return (
        getattr(unit, "unit_number", None)
        or getattr(unit, "name", None)
    )


def get_payment_date(payment):
    return (
        getattr(payment, "paid_at", None)
        or getattr(payment, "payment_date", None)
        or getattr(payment, "created_at", None)
    )


def get_payment_status(payment):
    payment_status = getattr(
        payment,
        "status",
        None,
    )

    if payment_status:
        return payment_status

    return (
        "success"
        if getattr(payment, "is_paid", False)
        else "pending"
    )


def is_successful_payment(payment):
    return get_payment_status(payment) in {
        "success",
        "paid",
        "completed",
    }


def serialize_payment(payment):
    invoice = getattr(
        payment,
        "invoice",
        None,
    )

    lease = (
        invoice.lease
        if invoice
        else None
    )

    tenant = getattr(
        payment,
        "tenant",
        None,
    )

    if tenant is None and lease:
        tenant = lease.tenant

    unit = (
        lease.unit
        if lease
        else getattr(
            tenant,
            "unit",
            None,
        )
    )

    property_instance = (
        unit.property
        if unit
        else None
    )

    payment_status = get_payment_status(
        payment
    )

    payment_date = get_payment_date(
        payment
    )

    tenant_user = (
        tenant.user
        if tenant
        else None
    )

    return {
        "id": payment.id,
        "invoice_id": (
            invoice.id
            if invoice
            else None
        ),
        "tenant_id": (
            tenant.id
            if tenant
            else None
        ),
        "tenant_name": (
            tenant_user.full_name
            if tenant_user
            else None
        ),
        "phone_number": (
            tenant_user.phone_number
            if tenant_user
            else None
        ),
        "property": (
            {
                "id": property_instance.id,
                "name": property_instance.name,
            }
            if property_instance
            else None
        ),
        "property_name": (
            property_instance.name
            if property_instance
            else None
        ),
        "unit": (
            {
                "id": unit.id,
                "name": get_unit_name(unit),
            }
            if unit
            else None
        ),
        "unit_name": get_unit_name(unit),
        "amount": float(
            payment.amount
            or Decimal("0.00")
        ),
        "currency": getattr(
            payment,
            "currency",
            "KES",
        ),
        "status": payment_status,
        "status_label": (
            payment_status
            .replace("_", " ")
            .title()
        ),
        "is_paid": is_successful_payment(
            payment
        ),
        "payment_method": getattr(
            payment,
            "payment_method",
            None,
        ),
        "transaction_code": (
            getattr(
                payment,
                "transaction_id",
                None,
            )
            or getattr(
                payment,
                "reference",
                None,
            )
        ),
        "payment_date": (
            payment_date.isoformat()
            if payment_date
            else None
        ),
        "created_at": (
            payment.created_at.isoformat()
            if getattr(
                payment,
                "created_at",
                None,
            )
            else None
        ),
    }


def serialize_maintenance_request(
    maintenance,
):
    tenant_user = (
        maintenance.tenant.user
        if maintenance.tenant
        else None
    )

    assigned_professional = getattr(
        maintenance,
        "assigned_professional",
        None,
    )

    assigned_user = (
        assigned_professional.user
        if assigned_professional
        else None
    )

    return {
        "id": maintenance.id,
        "tenant": (
            {
                "id": maintenance.tenant_id,
                "name": (
                    tenant_user.full_name
                    if tenant_user
                    else None
                ),
                "phone_number": (
                    tenant_user.phone_number
                    if tenant_user
                    else None
                ),
            }
            if maintenance.tenant
            else None
        ),
        "tenant_name": (
            tenant_user.full_name
            if tenant_user
            else None
        ),
        "property": {
            "id": maintenance.property_id,
            "name": maintenance.property.name,
        },
        "property_name": (
            maintenance.property.name
        ),
        "unit": {
            "id": maintenance.unit_id,
            "name": get_unit_name(
                maintenance.unit
            ),
        },
        "unit_name": get_unit_name(
            maintenance.unit
        ),
        "title": maintenance.title,
        "description": (
            maintenance.description
        ),
        "category": getattr(
            maintenance,
            "category",
            None,
        ),
        "priority": maintenance.priority,
        "status": maintenance.status,
        "images": (
            maintenance.images or []
        ),
        "assigned_professional": (
            {
                "id": (
                    assigned_professional.id
                ),
                "name": (
                    assigned_user.full_name
                    if assigned_user
                    else None
                ),
            }
            if assigned_professional
            else None
        ),
        "created_at": (
            maintenance.created_at
            .isoformat()
        ),
        "updated_at": (
            maintenance.updated_at
            .isoformat()
            if getattr(
                maintenance,
                "updated_at",
                None,
            )
            else None
        ),
    }


def get_company_payments(company_id):
    """
    The current architecture assumes:

    RentPayment -> invoice -> lease -> unit
    -> property -> company
    """

    return (
        RentPayment.objects
        .filter(
            invoice__lease__unit__property__company_id=
            company_id
        )
        .select_related(
            "tenant__user",
            "invoice",
            "invoice__lease",
            "invoice__lease__tenant__user",
            "invoice__lease__unit",
            "invoice__lease__unit__property",
        )
    )


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_statistics(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_dashboard(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this company's dashboard."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        properties = (
            Property.objects
            .filter(
                company_id=company_id
            )
        )

        units = (
            Unit.objects
            .filter(
                property__company_id=
                company_id
            )
        )

        leases = (
            Lease.objects
            .filter(
                unit__property__company_id=
                company_id
            )
        )

        active_leases = leases.filter(
            status="active",
            lease_end__gte=
            timezone.localdate(),
        )

        total_properties = (
            properties.count()
        )

        total_units = units.count()

        occupied_units = (
            units.filter(
                status="occupied"
            ).count()
        )

        vacant_units = (
            units.filter(
                status="available"
            ).count()
        )

        unavailable_units = (
            total_units
            - occupied_units
            - vacant_units
        )

        occupancy_rate = (
            round(
                (
                    occupied_units
                    / total_units
                ) * 100,
                1,
            )
            if total_units
            else 0
        )

        total_tenants = (
            active_leases
            .values("tenant_id")
            .distinct()
            .count()
        )

        total_landlords = (
            properties
            .exclude(landlord__isnull=True)
            .values("landlord_id")
            .distinct()
            .count()
        )

        payments = get_company_payments(
            company_id
        )

        successful_payments = (
            payments.filter(
                status="success"
            )
        )

        current_date = timezone.now()

        monthly_revenue = (
            successful_payments
            .filter(
                paid_at__year=
                current_date.year,
                paid_at__month=
                current_date.month,
            )
            .aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )["total"]
        )

        pending_maintenance = (
            MaintenanceRequest.objects
            .filter(
                property__company_id=
                company_id,
                status__in=[
                    "pending",
                    "assigned",
                    "in_progress",
                ],
            )
            .count()
        )

        completed_maintenance = (
            MaintenanceRequest.objects
            .filter(
                property__company_id=
                company_id,
                status="completed",
            )
            .count()
        )

        recent_properties = (
            properties
            .annotate(
                unit_count=Count(
                    "units",
                    distinct=True,
                ),
                occupied_count=Count(
                    "units",
                    filter=Q(
                        units__status=
                        "occupied"
                    ),
                    distinct=True,
                ),
            )
            .order_by("-created_at")[:5]
        )

        recent_data = []

        for property_instance in (
            recent_properties
        ):
            recent_data.append({
                "id": property_instance.id,
                "name": property_instance.name,
                "city": property_instance.city,
                "address": (
                    property_instance.address
                ),
                "status": (
                    property_instance.status
                ),
                "property_type": (
                    property_instance
                    .property_type
                ),
                "units": (
                    property_instance
                    .unit_count
                ),
                "occupied_units": (
                    property_instance
                    .occupied_count
                ),
                "available_units": max(
                    property_instance.unit_count
                    - property_instance
                    .occupied_count,
                    0,
                ),
                "created_at": (
                    property_instance
                    .created_at
                    .isoformat()
                    if property_instance
                    .created_at
                    else None
                ),
            })

        # --------------------------------------------
        # REVENUE GRAPH FOR THE LAST SIX MONTHS
        # --------------------------------------------

        six_months_ago = (
            current_date
            - timedelta(days=180)
        )

        revenue_results = (
            successful_payments
            .filter(
                paid_at__gte=six_months_ago
            )
            .annotate(
                month=TruncMonth(
                    "paid_at"
                )
            )
            .values("month")
            .annotate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )
            .order_by("month")
        )

        revenue_by_month = {
            item["month"].strftime(
                "%Y-%m"
            ): item["total"]
            for item in revenue_results
            if item["month"]
        }

        revenue_graph = []

        for months_back in range(
            5,
            -1,
            -1,
        ):
            month_date = (
                current_date
                - timedelta(
                    days=months_back * 30
                )
            )

            month_key = (
                month_date.strftime(
                    "%Y-%m"
                )
            )

            revenue_graph.append({
                "month": (
                    month_date.strftime(
                        "%b"
                    )
                ),
                "month_key": month_key,
                "revenue": float(
                    revenue_by_month.get(
                        month_key,
                        Decimal("0.00"),
                    )
                ),
            })

        occupancy_graph = [
            {
                "name": "Occupied",
                "value": occupied_units,
            },
            {
                "name": "Vacant",
                "value": vacant_units,
            },
            {
                "name": "Unavailable",
                "value": max(
                    unavailable_units,
                    0,
                ),
            },
        ]

        return Response(
            {
                "success": True,
                "company": {
                    "id": membership.company.id,
                    "name": (
                        membership.company.name
                    ),
                },
                "statistics": {
                    "properties": (
                        total_properties
                    ),
                    "units": total_units,
                    "tenants": total_tenants,
                    "landlords": (
                        total_landlords
                    ),
                    "occupied_units": (
                        occupied_units
                    ),
                    "vacant_units": (
                        vacant_units
                    ),
                    "unavailable_units": max(
                        unavailable_units,
                        0,
                    ),
                    "occupancy_rate": (
                        occupancy_rate
                    ),
                    "monthly_revenue": float(
                        monthly_revenue
                    ),
                    "monthly_revenue_formatted": (
                        f"KES "
                        f"{monthly_revenue:,.2f}"
                    ),
                    "pending_maintenance": (
                        pending_maintenance
                    ),
                    "completed_maintenance": (
                        completed_maintenance
                    ),
                },
                "revenue_graph": (
                    revenue_graph
                ),
                "occupancy_graph": (
                    occupancy_graph
                ),
                "recent_properties": (
                    recent_data
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "DASHBOARD STATISTICS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "dashboard statistics."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PAYMENT SUMMARY
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_summary(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_payments(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this company's payments."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payments = get_company_payments(
            company_id
        )

        successful_payments = (
            payments.filter(
                status="success"
            )
        )

        pending_payments = (
            payments.filter(
                status="pending"
            )
        )

        failed_payments = (
            payments.filter(
                status="failed"
            )
        )

        total_collected = (
            successful_payments.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )["total"]
        )

        total_pending = (
            pending_payments.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )["total"]
        )

        total_failed = (
            failed_payments.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )["total"]
        )

        current_date = timezone.now()

        collected_this_month = (
            successful_payments
            .filter(
                paid_at__year=
                current_date.year,
                paid_at__month=
                current_date.month,
            )
            .aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                )
            )["total"]
        )

        return Response(
            {
                "success": True,
                "summary": {
                    "total_collected": float(
                        total_collected
                    ),
                    "total_collected_formatted": (
                        f"KES "
                        f"{total_collected:,.2f}"
                    ),
                    "total_pending": float(
                        total_pending
                    ),
                    "total_pending_formatted": (
                        f"KES "
                        f"{total_pending:,.2f}"
                    ),
                    "total_failed": float(
                        total_failed
                    ),
                    "collected_this_month": (
                        float(
                            collected_this_month
                        )
                    ),
                    "paid_transactions": (
                        successful_payments
                        .count()
                    ),
                    "pending_transactions": (
                        pending_payments.count()
                    ),
                    "failed_transactions": (
                        failed_payments.count()
                    ),
                    "total_transactions": (
                        payments.count()
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "PAYMENT SUMMARY ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the payment summary."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# GET PAYMENTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payments(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        payment_status = str(
            request.GET.get(
                "status",
                "",
            )
        ).strip().lower()

        search_query = str(
            request.GET.get(
                "search",
                "",
            )
        ).strip()

        property_id = request.GET.get(
            "property_id"
        )

        payment_method = str(
            request.GET.get(
                "payment_method",
                "",
            )
        ).strip().lower()

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_payments(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view this company's payments."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payments = (
            get_company_payments(
                company_id
            )
            .order_by("-created_at")
        )

        if payment_status:
            payments = payments.filter(
                status=payment_status
            )

        if property_id:
            payments = payments.filter(
                invoice__lease__unit__property_id=
                property_id
            )

        if payment_method:
            payments = payments.filter(
                payment_method__iexact=
                payment_method
            )

        if search_query:
            payments = payments.filter(
                Q(
                    tenant__user__full_name__icontains=
                    search_query
                )
                | Q(
                    tenant__user__email__icontains=
                    search_query
                )
                | Q(
                    tenant__user__phone_number__icontains=
                    search_query
                )
                | Q(
                    invoice__lease__tenant__user__full_name__icontains=
                    search_query
                )
                | Q(
                    invoice__lease__unit__property__name__icontains=
                    search_query
                )
                | Q(
                    invoice__lease__unit__unit_number__icontains=
                    search_query
                )
                | Q(
                    reference__icontains=
                    search_query
                )
                | Q(
                    transaction_id__icontains=
                    search_query
                )
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
            page_size = min(
                max(
                    int(
                        request.GET.get(
                            "page_size",
                            20,
                        )
                    ),
                    1,
                ),
                100,
            )
        except (
            TypeError,
            ValueError,
        ):
            page_size = 20

        total_count = payments.count()

        start_index = (
            page - 1
        ) * page_size

        end_index = (
            start_index
            + page_size
        )

        payment_page = payments[
            start_index:end_index
        ]

        results = [
            serialize_payment(payment)
            for payment in payment_page
        ]

        return Response(
            {
                "success": True,
                "count": len(results),
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": (
                    end_index
                    < total_count
                ),
                "payments": results,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET PAYMENTS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "payments."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PROPERTY MANAGER PROFILE
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_profile(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not membership:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have access to "
                        "this company."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user = request.user
        company = membership.company

        subscription = (
            Subscription.objects
            .select_related(
                "package",
                "company",
            )
            .filter(
                company=company,
                is_active=True,
            )
            .first()
        )

        if (
            subscription
            and subscription.end_date
            and subscription.end_date
            <= timezone.now()
        ):
            subscription.is_active = False

            subscription.save(
                update_fields=[
                    "is_active",
                ]
            )

        properties = (
            Property.objects
            .filter(company=company)
        )

        property_count = (
            properties.count()
        )

        unit_count = (
            Unit.objects
            .filter(
                property__company=
                company
            )
            .count()
        )

        active_leases = (
            Lease.objects
            .filter(
                unit__property__company=
                company,
                status="active",
                lease_end__gte=
                timezone.localdate(),
            )
        )

        tenant_count = (
            active_leases
            .values("tenant_id")
            .distinct()
            .count()
        )

        landlord_count = (
            properties
            .exclude(
                landlord__isnull=True
            )
            .values("landlord_id")
            .distinct()
            .count()
        )

        if (
            subscription
            and subscription.is_active
        ):
            remaining_days = max(
                (
                    subscription.end_date.date()
                    - timezone.localdate()
                ).days,
                0,
            )

            package = (
                subscription.package
            )

            package_unit_limit = (
                package.number_of_units
            )

            subscription_data = {
                "id": subscription.id,
                "package": (
                    package.name.title()
                ),
                "package_id": package.id,
                "status": "Active",
                "billing_cycle": (
                    subscription
                    .billing_cycle
                    .title()
                ),
                "monthly_price": float(
                    package.monthly_price
                ),
                "yearly_price": float(
                    package.yearly_price
                ),
                "start_date": (
                    subscription.start_date
                    .isoformat()
                ),
                "expires_at": (
                    subscription.end_date
                    .strftime("%d %B %Y")
                ),
                "end_date": (
                    subscription.end_date
                    .isoformat()
                ),
                "remaining_days": (
                    remaining_days
                ),
                "limits": {
                    "units": (
                        package_unit_limit
                    ),

                    # Use a separate package field
                    # if properties have their own limit.
                    "properties": (
                        package_unit_limit
                    ),
                },
                "usage": {
                    "properties": (
                        property_count
                    ),
                    "units": unit_count,
                },
                "remaining_capacity": {
                    "units": max(
                        package_unit_limit
                        - unit_count,
                        0,
                    ),
                    "properties": max(
                        package_unit_limit
                        - property_count,
                        0,
                    ),
                },
                "features": [
                    "Property Management",
                    "Unit Management",
                    "Tenant Management",
                    "Rent Collection",

                    *(
                        ["M-Pesa Daraja"]
                        if package.mpesa_daraja
                        else []
                    ),

                    *(
                        ["Email Notifications"]
                        if (
                            package
                            .email_notifications
                        )
                        else []
                    ),

                    (
                        f"Logs "
                        f"({package.logs_duration} Days)"
                    ),
                ],
            }

        else:
            subscription_data = {
                "id": None,
                "package": (
                    "No Active Package"
                ),
                "package_id": None,
                "status": "Inactive",
                "billing_cycle": "",
                "monthly_price": 0,
                "yearly_price": 0,
                "start_date": None,
                "expires_at": "",
                "end_date": None,
                "remaining_days": 0,
                "limits": {
                    "properties": 0,
                    "units": 0,
                },
                "usage": {
                    "properties": (
                        property_count
                    ),
                    "units": unit_count,
                },
                "remaining_capacity": {
                    "properties": 0,
                    "units": 0,
                },
                "features": [],
            }

        return Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "name": user.full_name,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": (
                        user.phone_number
                    ),
                    "profile_image": (
                        user.profile_image
                    ),
                    "role": (
                        membership.role
                        .replace("_", " ")
                        .title()
                    ),
                    "location": getattr(
                        user,
                        "location",
                        None,
                    ),
                    "joined": (
                        user.created_at
                        .strftime("%d %B %Y")
                        if getattr(
                            user,
                            "created_at",
                            None,
                        )
                        else None
                    ),
                    "verified": getattr(
                        user,
                        "is_verified",
                        False,
                    ),
                },
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "role": membership.role,
                    "membership_id": (
                        membership.id
                    ),
                },
                "statistics": {
                    "properties": (
                        property_count
                    ),
                    "units": unit_count,
                    "tenants": tenant_count,
                    "landlords": (
                        landlord_count
                    ),
                },
                "subscription": (
                    subscription_data
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "PROPERTY MANAGER PROFILE ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the profile."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PROPERTY MANAGER MAINTENANCE REQUESTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_maintenance_requests(
    request,
):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        status_filter = str(
            request.GET.get(
                "status",
                "",
            )
        ).strip().lower()

        priority = str(
            request.GET.get(
                "priority",
                "",
            )
        ).strip().lower()

        property_id = request.GET.get(
            "property_id"
        )

        search_query = str(
            request.GET.get(
                "search",
                "",
            )
        ).strip()

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=400,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_view_maintenance(
            membership
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "view maintenance requests."
                    ),
                },
                status=403,
            )

        maintenance_requests = (
            MaintenanceRequest.objects
            .filter(
                property__company_id=
                company_id
            )
            .select_related(
                "tenant__user",
                "property",
                "unit",
                "assigned_professional",
                "assigned_professional__user",
            )
            .order_by("-created_at")
        )

        if status_filter:
            if (
                status_filter
                not in VALID_MAINTENANCE_STATUSES
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Invalid maintenance status."
                        ),
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

        if priority:
            maintenance_requests = (
                maintenance_requests.filter(
                    priority=priority
                )
            )

        if property_id:
            maintenance_requests = (
                maintenance_requests.filter(
                    property_id=property_id
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
                        tenant__user__full_name__icontains=
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
                )
            )

        data = [
            serialize_maintenance_request(
                item
            )
            for item
            in maintenance_requests
        ]

        summary = {
            "total": len(data),
            "pending": (
                maintenance_requests
                .filter(
                    status="pending"
                )
                .count()
            ),
            "assigned": (
                maintenance_requests
                .filter(
                    status="assigned"
                )
                .count()
            ),
            "in_progress": (
                maintenance_requests
                .filter(
                    status="in_progress"
                )
                .count()
            ),
            "completed": (
                maintenance_requests
                .filter(
                    status="completed"
                )
                .count()
            ),
            "cancelled": (
                maintenance_requests
                .filter(
                    status="cancelled"
                )
                .count()
            ),
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
            "GET MANAGER MAINTENANCE ERROR:",
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
# UPDATE MAINTENANCE STATUS
# ============================================================

@api_view(["PATCH", "PUT", "POST"])
@permission_classes([IsAuthenticated])
def update_maintenance_status(
    request,
    request_id,
):
    try:
        company_id = request.data.get(
            "company_id"
        )

        new_status = str(
            request.data.get(
                "status",
                "",
            )
        ).strip().lower()

        if not company_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Company is required."
                    ),
                },
                status=400,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_update_maintenance(
            membership
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "update maintenance requests."
                    ),
                },
                status=403,
            )

        if (
            new_status
            not in VALID_MAINTENANCE_STATUSES
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Invalid maintenance status."
                    ),
                    "allowed_statuses": sorted(
                        VALID_MAINTENANCE_STATUSES
                    ),
                },
                status=400,
            )

        with transaction.atomic():
            maintenance = (
                MaintenanceRequest.objects
                .select_for_update()
                .select_related(
                    "tenant__user",
                    "property",
                    "unit",
                )
                .filter(
                    id=request_id,
                    property__company_id=
                    company_id,
                )
                .first()
            )

            if not maintenance:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            "Maintenance request was "
                            "not found in this company."
                        ),
                    },
                    status=404,
                )

            previous_status = (
                maintenance.status
            )

            if previous_status == new_status:
                return JsonResponse(
                    {
                        "success": True,
                        "message": (
                            "Maintenance request already "
                            f"has status '{new_status}'."
                        ),
                        "request": (
                            serialize_maintenance_request(
                                maintenance
                            )
                        ),
                    },
                    status=200,
                )

            maintenance.status = new_status

            update_fields = ["status"]

            if (
                new_status == "completed"
                and hasattr(
                    maintenance,
                    "completed_at",
                )
            ):
                maintenance.completed_at = (
                    timezone.now()
                )

                update_fields.append(
                    "completed_at"
                )

            if (
                new_status != "completed"
                and hasattr(
                    maintenance,
                    "completed_at",
                )
            ):
                maintenance.completed_at = None

                update_fields.append(
                    "completed_at"
                )

            if hasattr(
                maintenance,
                "updated_at",
            ):
                update_fields.append(
                    "updated_at"
                )

            maintenance.save(
                update_fields=update_fields
            )

            if maintenance.tenant:
                Notification.objects.create(
                    user=(
                        maintenance
                        .tenant
                        .user
                    ),
                    company=membership.company,
                    title=(
                        "Maintenance Status Updated"
                    ),
                    message=(
                        f'Your maintenance request '
                        f'"{maintenance.title}" changed '
                        f"from "
                        f"{previous_status.replace('_', ' ')} "
                        f"to "
                        f"{new_status.replace('_', ' ')}."
                    ),
                    notification_type=(
                        "maintenance"
                    ),
                    data={
                        "maintenance_request_id": (
                            maintenance.id
                        ),
                        "company_id": (
                            membership.company_id
                        ),
                        "previous_status": (
                            previous_status
                        ),
                        "status": new_status,
                    },
                )

        tenant_user = (
            maintenance.tenant.user
            if maintenance.tenant
            else None
        )

        if (
            tenant_user
            and getattr(
                tenant_user,
                "expo_token",
                None,
            )
        ):
            try:
                send_push_notification(
                    tenant_user.expo_token,
                    title=(
                        "Maintenance Status Updated"
                    ),
                    body=(
                        f'Your request '
                        f'"{maintenance.title}" is now '
                        f"{new_status.replace('_', ' ')}."
                    ),
                    data={
                        "screen": (
                            "MaintenanceDetails"
                        ),
                        "maintenance_request_id": str(
                            maintenance.id
                        ),
                    },
                )

            except Exception as push_error:
                print(
                    "MAINTENANCE PUSH ERROR:",
                    str(push_error),
                )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Maintenance request updated "
                    "successfully."
                ),
                "previous_status": (
                    previous_status
                ),
                "request": (
                    serialize_maintenance_request(
                        maintenance
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
                    "the maintenance request."
                ),
                "error": str(error),
            },
            status=500,
        )