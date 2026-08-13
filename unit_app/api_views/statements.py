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
        "landlord",
        "investor",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view owner statements."
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

    if year < 2000 or year > 2200:
        return JsonResponse(
            {
                "message":
                    "Invalid statement year."
            },
            status=400,
        )

    # =====================================================
    # OWNER RECORD
    # =====================================================

    try:
        owner = (
            Owner.objects.get(
                user=user,

                organization=
                    organization,

                status="active",
            )
        )

    except Owner.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "No active owner profile is linked to this account."
            },
            status=404,
        )

    except Owner.MultipleObjectsReturned:
        owner = (
            Owner.objects
            .filter(
                user=user,

                organization=
                    organization,

                status="active",
            )
            .first()
        )

    # =====================================================
    # OWNED PROPERTIES
    # =====================================================

    ownerships = (
        PropertyOwnership.objects
        .filter(
            owner=owner,
            is_active=True,
        )
        .select_related(
            "property",
            "property__portifolio",
        )
    )

    if not ownerships.exists():
        return JsonResponse(
            {
                "owner": {
                    "id":
                        owner.id,

                    "name":
                        owner.name,
                },

                "summary": {
                    "gross_collected": 0,
                    "owner_share": 0,
                    "maintenance_costs": 0,
                    "owner_maintenance_share": 0,
                    "net_income": 0,
                    "outstanding": 0,
                    "properties": 0,
                },

                "properties": [],

                "statements": [],
            },
            status=200,
        )

    # =====================================================
    # PROPERTY RESPONSE
    # =====================================================

    property_filters = []

    for ownership in ownerships:
        property_filters.append(
            {
                "id":
                    ownership.property.id,

                "name":
                    ownership.property.name,

                "property_code":
                    ownership.property.property_code,

                "ownership_percentage":
                    float(
                        ownership
                        .ownership_percentage
                    ),

                "portfolio": {
                    "id":
                        ownership
                        .property
                        .portifolio.id,

                    "name":
                        ownership
                        .property
                        .portifolio.name,
                },
            }
        )

    # =====================================================
    # YEAR TOTALS
    # =====================================================

    year_gross_collected = (
        Decimal("0.00")
    )

    year_owner_share = (
        Decimal("0.00")
    )

    year_maintenance = (
        Decimal("0.00")
    )

    year_owner_maintenance = (
        Decimal("0.00")
    )

    year_outstanding = (
        Decimal("0.00")
    )

    statements = []

    # =====================================================
    # EACH MONTH
    # =====================================================

    for month in range(
        1,
        13,
    ):
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

        month_owner_share = (
            Decimal("0.00")
        )

        month_maintenance = (
            Decimal("0.00")
        )

        month_owner_maintenance = (
            Decimal("0.00")
        )

        month_outstanding = (
            Decimal("0.00")
        )

        statement_properties = []

        # =================================================
        # EACH OWNED PROPERTY
        # =================================================

        for ownership in ownerships:

            property_obj = (
                ownership.property
            )

            ownership_percentage = (
                Decimal(
                    str(
                        ownership
                        .ownership_percentage
                    )
                )
            )

            ownership_ratio = (
                ownership_percentage
                / Decimal("100")
            )

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

            property_owner_share = (
                property_collected
                * ownership_ratio
            )

            # =============================================
            # MAINTENANCE COSTS
            # =============================================

            property_maintenance = (
                MaintenanceTicket.objects
                .filter(
                    organization=
                        organization,

                    property=
                        property_obj,

                    actual_cost__isnull=False,

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

            property_owner_maintenance = (
                property_maintenance
                * ownership_ratio
            )

            # =============================================
            # ADD TO MONTH
            # =============================================

            month_gross += (
                property_collected
            )

            month_owner_share += (
                property_owner_share
            )

            month_maintenance += (
                property_maintenance
            )

            month_owner_maintenance += (
                property_owner_maintenance
            )

            month_outstanding += (
                property_outstanding
                * ownership_ratio
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

                        "ownership_percentage":
                            float(
                                ownership_percentage
                            ),

                        "gross_collected":
                            float(
                                property_collected
                            ),

                        "owner_share":
                            float(
                                property_owner_share
                            ),

                        "maintenance_cost":
                            float(
                                property_maintenance
                            ),

                        "owner_maintenance_share":
                            float(
                                property_owner_maintenance
                            ),

                        "outstanding":
                            float(
                                property_outstanding
                                * ownership_ratio
                            ),

                        "net_income":
                            float(
                                property_owner_share
                                -
                                property_owner_maintenance
                            ),
                    }
                )

        # =================================================
        # MONTH NET
        # =================================================

        month_net_income = (
            month_owner_share
            -
            month_owner_maintenance
        )

        # =================================================
        # DO NOT SEND FUTURE MONTHS
        # =================================================

        today = (
            timezone.localdate()
        )

        is_future_month = (
            year > today.year
            or
            (
                year == today.year
                and
                month > today.month
            )
        )

        if is_future_month:
            continue

        # =================================================
        # ADD YEAR TOTALS
        # =================================================

        year_gross_collected += (
            month_gross
        )

        year_owner_share += (
            month_owner_share
        )

        year_maintenance += (
            month_maintenance
        )

        year_owner_maintenance += (
            month_owner_maintenance
        )

        year_outstanding += (
            month_outstanding
        )

        # =================================================
        # STATEMENT
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

                "owner_share":
                    float(
                        month_owner_share
                    ),

                "maintenance_costs":
                    float(
                        month_maintenance
                    ),

                "owner_maintenance_share":
                    float(
                        month_owner_maintenance
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
            "owner": {
                "id":
                    owner.id,

                "name":
                    owner.name,

                "owner_type":
                    owner.owner_type,

                "email":
                    owner.email,
            },

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

                "owner_share":
                    float(
                        year_owner_share
                    ),

                "maintenance_costs":
                    float(
                        year_maintenance
                    ),

                "owner_maintenance_share":
                    float(
                        year_owner_maintenance
                    ),

                "net_income":
                    float(
                        year_owner_share
                        -
                        year_owner_maintenance
                    ),

                "outstanding":
                    float(
                        year_outstanding
                    ),

                "properties":
                    ownerships.count(),
            },

            "properties":
                property_filters,

            "statements":
                statements,
        },
        status=200,
    )