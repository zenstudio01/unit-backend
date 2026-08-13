from .common_imports import *


def get_report_date_range(
    period
):
    today = timezone.localdate()

    if period == "year":
        start_date = date(
            today.year,
            1,
            1,
        )

        end_date = date(
            today.year + 1,
            1,
            1,
        )

        return (
            start_date,
            end_date,
        )

    if period == "quarter":
        quarter = (
            (
                today.month - 1
            )
            // 3
        )

        start_month = (
            quarter * 3
        ) + 1

        start_date = date(
            today.year,
            start_month,
            1,
        )

        if start_month == 10:
            end_date = date(
                today.year + 1,
                1,
                1,
            )

        else:
            end_date = date(
                today.year,
                start_month + 3,
                1,
            )

        return (
            start_date,
            end_date,
        )

    # Default = current month

    start_date = (
        today.replace(
            day=1
        )
    )

    if start_date.month == 12:
        end_date = date(
            start_date.year + 1,
            1,
            1,
        )

    else:
        end_date = date(
            start_date.year,
            start_date.month + 1,
            1,
        )

    return (
        start_date,
        end_date,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_reports(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    period = str(
        request.GET.get(
            "period",
            "month",
        )
    ).strip().lower()

    # =====================================================
    # VALIDATE PERIOD
    # =====================================================

    valid_periods = {
        "month",
        "quarter",
        "year",
    }

    if period not in valid_periods:
        return JsonResponse(
            {
                "message":
                    "Invalid report period."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                user=user,

                organization=
                    organization,

                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    role_codes = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    allowed_roles = {
        "organization_owner",
        "organization_admin",
        "owner",
        "landlord",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view owner reports."
            },
            status=403,
        )

    # =====================================================
    # DATE RANGE
    # =====================================================

    (
        start_date,
        end_date,
    ) = get_report_date_range(
        period
    )

    # =====================================================
    # PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=
                organization,

            status="active",
        )
        .select_related(
            "portifolio"
        )
    )

    # =====================================================
    # UNITS
    # =====================================================

    units = (
        Unit.objects
        .filter(
            property__organization=
                organization
        )
    )

    total_units = (
        units.count()
    )

    occupied_units = (
        units.filter(
            status="occupied"
        ).count()
    )

    available_units = (
        units.filter(
            status="available"
        ).count()
    )

    maintenance_units = (
        units.filter(
            status=
                "under_maintenance"
        ).count()
    )

    occupancy_rate = 0

    if total_units > 0:
        occupancy_rate = round(
            (
                occupied_units
                / total_units
            )
            * 100
        )

    # =====================================================
    # INVOICES
    # =====================================================

    invoices = (
        Invoice.objects
        .filter(
            organization=
                organization,

            invoice_type="rent",

            issue_date__gte=
                start_date,

            issue_date__lt=
                end_date,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
    )

    rent_expected = (
        invoices.aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    outstanding = (
        invoices
        .filter(
            balance__gt=0
        )
        .aggregate(
            total=Sum(
                "balance"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # RENT COLLECTED
    # =====================================================

    rent_collected = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            invoice__invoice_type=
                "rent",

            invoice__issue_date__gte=
                start_date,

            invoice__issue_date__lt=
                end_date,

            payment__status=
                "completed",
        )
        .aggregate(
            total=Sum(
                "allocated_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    collection_rate = 0

    if rent_expected > 0:
        collection_rate = round(
            (
                rent_collected
                / rent_expected
            )
            * 100
        )

    # =====================================================
    # MAINTENANCE EXPENSES
    # =====================================================

    expenses = (
        MaintenanceTicket.objects
        .filter(
            organization=
                organization,

            completed_at__date__gte=
                start_date,

            completed_at__date__lt=
                end_date,

            actual_cost__isnull=False,
        )
        .exclude(
            status="cancelled"
        )
        .aggregate(
            total=Sum(
                "actual_cost"
            )
        )["total"]
        or Decimal("0.00")
    )

    net_income = (
        rent_collected
        - expenses
    )

    # =====================================================
    # PORTFOLIO PERFORMANCE
    # =====================================================

    portfolios = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            status="active",
        )
        .order_by(
            "name"
        )
    )

    portfolio_performance = []

    for portfolio in portfolios:

        portfolio_properties = (
            properties.filter(
                portifolio=
                    portfolio
            )
        )

        portfolio_units = (
            units.filter(
                property__in=
                    portfolio_properties
            )
        )

        portfolio_total_units = (
            portfolio_units.count()
        )

        portfolio_occupied = (
            portfolio_units
            .filter(
                status="occupied"
            )
            .count()
        )

        portfolio_occupancy = 0

        if (
            portfolio_total_units
            > 0
        ):
            portfolio_occupancy = round(
                (
                    portfolio_occupied
                    /
                    portfolio_total_units
                )
                * 100
            )

        portfolio_invoices = (
            invoices.filter(
                property__in=
                    portfolio_properties
            )
        )

        portfolio_expected = (
            portfolio_invoices
            .aggregate(
                total=Sum(
                    "total_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        portfolio_outstanding = (
            portfolio_invoices
            .filter(
                balance__gt=0
            )
            .aggregate(
                total=Sum(
                    "balance"
                )
            )["total"]
            or Decimal("0.00")
        )

        portfolio_collected = (
            PaymentAllocation.objects
            .filter(
                invoice__organization=
                    organization,

                invoice__property__in=
                    portfolio_properties,

                invoice__invoice_type=
                    "rent",

                invoice__issue_date__gte=
                    start_date,

                invoice__issue_date__lt=
                    end_date,

                payment__status=
                    "completed",
            )
            .aggregate(
                total=Sum(
                    "allocated_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        portfolio_collection_rate = 0

        if portfolio_expected > 0:
            portfolio_collection_rate = (
                round(
                    (
                        portfolio_collected
                        /
                        portfolio_expected
                    )
                    * 100
                )
            )

        portfolio_performance.append(
            {
                "id":
                    portfolio.id,

                "name":
                    portfolio.name,

                "code":
                    portfolio.code,

                "properties_count":
                    portfolio_properties
                    .count(),

                "units":
                    portfolio_total_units,

                "occupied_units":
                    portfolio_occupied,

                "occupancy_rate":
                    portfolio_occupancy,

                "rent_expected":
                    float(
                        portfolio_expected
                    ),

                "rent_collected":
                    float(
                        portfolio_collected
                    ),

                "outstanding":
                    float(
                        portfolio_outstanding
                    ),

                "collection_rate":
                    portfolio_collection_rate,
            }
        )

    # =====================================================
    # PROPERTY PERFORMANCE
    # =====================================================

    property_performance = []

    for property_obj in properties:

        property_units = (
            units.filter(
                property=
                    property_obj
            )
        )

        property_total_units = (
            property_units.count()
        )

        property_occupied = (
            property_units
            .filter(
                status="occupied"
            )
            .count()
        )

        property_occupancy = 0

        if property_total_units > 0:
            property_occupancy = round(
                (
                    property_occupied
                    /
                    property_total_units
                )
                * 100
            )

        property_invoices = (
            invoices.filter(
                property=
                    property_obj
            )
        )

        property_expected = (
            property_invoices
            .aggregate(
                total=Sum(
                    "total_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_outstanding = (
            property_invoices
            .filter(
                balance__gt=0
            )
            .aggregate(
                total=Sum(
                    "balance"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_collected = (
            PaymentAllocation.objects
            .filter(
                invoice__organization=
                    organization,

                invoice__property=
                    property_obj,

                invoice__invoice_type=
                    "rent",

                invoice__issue_date__gte=
                    start_date,

                invoice__issue_date__lt=
                    end_date,

                payment__status=
                    "completed",
            )
            .aggregate(
                total=Sum(
                    "allocated_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_collection_rate = 0

        if property_expected > 0:
            property_collection_rate = (
                round(
                    (
                        property_collected
                        /
                        property_expected
                    )
                    * 100
                )
            )

        property_performance.append(
            {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj
                    .property_code,

                "city":
                    property_obj.city,

                "county":
                    property_obj.county,

                "portfolio": {
                    "id":
                        property_obj
                        .portifolio.id,

                    "name":
                        property_obj
                        .portifolio.name,
                },

                "units":
                    property_total_units,

                "occupied_units":
                    property_occupied,

                "occupancy_rate":
                    property_occupancy,

                "rent_expected":
                    float(
                        property_expected
                    ),

                "rent_collected":
                    float(
                        property_collected
                    ),

                "outstanding":
                    float(
                        property_outstanding
                    ),

                "collection_rate":
                    property_collection_rate,
            }
        )

    # Highest-performing first.

    property_performance.sort(
        key=lambda item: (
            item[
                "collection_rate"
            ],
            item[
                "occupancy_rate"
            ],
            item[
                "rent_collected"
            ],
        ),
        reverse=True,
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "period": {
                "type":
                    period,

                "start_date":
                    start_date
                    .isoformat(),

                "end_date":
                    end_date
                    .isoformat(),
            },

            "summary": {
                "properties":
                    properties.count(),

                "units":
                    total_units,

                "occupied_units":
                    occupied_units,

                "available_units":
                    available_units,

                "maintenance_units":
                    maintenance_units,

                "occupancy_rate":
                    occupancy_rate,

                "rent_expected":
                    float(
                        rent_expected
                    ),

                "rent_collected":
                    float(
                        rent_collected
                    ),

                "outstanding":
                    float(
                        outstanding
                    ),

                "collection_rate":
                    collection_rate,

                "expenses":
                    float(
                        expenses
                    ),

                "net_income":
                    float(
                        net_income
                    ),
            },

            "portfolio_performance":
                portfolio_performance,

            "property_performance":
                property_performance,
        },
        status=200,
    )