from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_statements(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    requested_year = (
        request.GET.get(
            "year"
        )
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
                id=organization_id
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
                organization=organization,
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
        "accountant",
        "property_manager",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view organization statements."
            },
            status=403,
        )

    # =====================================================
    # YEAR
    # =====================================================

    current_year = (
        timezone.localdate().year
    )

    try:
        year = int(
            requested_year
            or current_year
        )

    except (
        TypeError,
        ValueError,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid year."
            },
            status=400,
        )

    if (
        year < 2000
        or
        year > 2200
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid statement year."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=organization
        )
        .select_related(
            "portifolio"
        )
        .order_by(
            "name"
        )
    )

    # =====================================================
    # PROPERTY FILTER RESPONSE
    # =====================================================

    property_filters = []

    for property_obj in properties:

        portfolio = getattr(
            property_obj,
            "portifolio",
            None,
        )

        property_filters.append(
            {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,

                "portfolio": (
                    {
                        "id":
                            portfolio.id,

                        "name":
                            portfolio.name,
                    }
                    if portfolio
                    else None
                ),
            }
        )

    # =====================================================
    # EMPTY ORGANIZATION
    # =====================================================

    if not properties.exists():
        return JsonResponse(
            {
                "organization": {
                    "id":
                        organization.id,

                    "name":
                        organization.name,
                },

                "year":
                    year,

                "summary": {
                    "gross_collected":
                        0,

                    "maintenance_costs":
                        0,

                    "net_income":
                        0,

                    "outstanding":
                        0,

                    "properties":
                        0,
                },

                "properties": [],

                "statements": [],
            },
            status=200,
        )

    # =====================================================
    # YEAR TOTALS
    # =====================================================

    year_gross_collected = (
        Decimal("0.00")
    )

    year_maintenance = (
        Decimal("0.00")
    )

    year_outstanding = (
        Decimal("0.00")
    )

    statements = []

    today = (
        timezone.localdate()
    )

    # =====================================================
    # EACH MONTH
    # =====================================================

    for month in range(
        1,
        13,
    ):

        # Skip future months
        if (
            year > today.year
            or
            (
                year == today.year
                and
                month > today.month
            )
        ):
            continue

        start_date = date(
            year,
            month,
            1,
        )

        if month == 12:
            end_date = date(
                year + 1,
                1,
                1,
            )

        else:
            end_date = date(
                year,
                month + 1,
                1,
            )

        month_gross = (
            Decimal("0.00")
        )

        month_maintenance = (
            Decimal("0.00")
        )

        month_outstanding = (
            Decimal("0.00")
        )

        statement_properties = []

        # =================================================
        # EACH ORGANIZATION PROPERTY
        # =================================================

        for property_obj in properties:

            # =============================================
            # RENT INVOICES
            # =============================================

            invoices = (
                Invoice.objects
                .filter(
                    organization=
                        organization,

                    property=
                        property_obj,

                    invoice_type=
                        "rent",

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

            # =============================================
            # OUTSTANDING RENT
            # =============================================

            property_outstanding = (
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

            # =============================================
            # COLLECTED RENT
            # =============================================

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

            # =============================================
            # MAINTENANCE COST
            # =============================================

            property_maintenance = (
                MaintenanceTicket.objects
                .filter(
                    organization=
                        organization,

                    property=
                        property_obj,

                    actual_cost__isnull=
                        False,

                    completed_at__date__gte=
                        start_date,

                    completed_at__date__lt=
                        end_date,
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

            # =============================================
            # NET PROPERTY INCOME
            # =============================================

            property_net_income = (
                property_collected
                -
                property_maintenance
            )

            # =============================================
            # MONTH TOTALS
            # =============================================

            month_gross += (
                property_collected
            )

            month_maintenance += (
                property_maintenance
            )

            month_outstanding += (
                property_outstanding
            )

            # =============================================
            # PROPERTY ITEM
            # =============================================

            if (
                property_collected > 0
                or
                property_outstanding > 0
                or
                property_maintenance > 0
            ):
                statement_properties.append(
                    {
                        "id":
                            property_obj.id,

                        "name":
                            property_obj.name,

                        "property_code":
                            property_obj
                            .property_code,

                        "gross_collected":
                            float(
                                property_collected
                            ),

                        "maintenance_cost":
                            float(
                                property_maintenance
                            ),

                        "outstanding":
                            float(
                                property_outstanding
                            ),

                        "net_income":
                            float(
                                property_net_income
                            ),
                    }
                )

        # =================================================
        # MONTH NET
        # =================================================

        month_net_income = (
            month_gross
            -
            month_maintenance
        )

        # =================================================
        # YEAR TOTALS
        # =================================================

        year_gross_collected += (
            month_gross
        )

        year_maintenance += (
            month_maintenance
        )

        year_outstanding += (
            month_outstanding
        )

        # =================================================
        # MONTH STATEMENT
        # =================================================

        statements.append(
            {
                "year":
                    year,

                "month":
                    month,

                "month_name":
                    month_name[
                        month
                    ],

                "period_start":
                    start_date
                    .isoformat(),

                "period_end":
                    end_date
                    .isoformat(),

                "gross_collected":
                    float(
                        month_gross
                    ),

                "maintenance_costs":
                    float(
                        month_maintenance
                    ),

                "outstanding":
                    float(
                        month_outstanding
                    ),

                "net_income":
                    float(
                        month_net_income
                    ),

                "properties_count":
                    len(
                        statement_properties
                    ),

                "properties":
                    statement_properties,
            }
        )

    # =====================================================
    # MOST RECENT FIRST
    # =====================================================

    statements.reverse()

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

            "year":
                year,

            "summary": {
                "gross_collected":
                    float(
                        year_gross_collected
                    ),

                "maintenance_costs":
                    float(
                        year_maintenance
                    ),

                "net_income":
                    float(
                        year_gross_collected
                        -
                        year_maintenance
                    ),

                "outstanding":
                    float(
                        year_outstanding
                    ),

                "properties":
                    properties.count(),
            },

            "properties":
                property_filters,

            "statements":
                statements,
        },
        status=200,
    )