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







# ============================================================
# OWNER STATEMENT DETAILS
# ============================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_statement_details(request):

    user = request.user

    print(
        "========================================"
    )

    print(
        "OWNER STATEMENT DETAILS API"
    )

    print(
        "QUERY:",
        request.GET.dict()
    )

    print(
        "REQUESTED BY:",
        user.id,
        user.username
    )

    print(
        "========================================"
    )

    # =====================================================
    # REQUEST DATA
    # =====================================================

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    year_raw = (
        request.GET.get(
            "year"
        )
    )

    month_raw = (
        request.GET.get(
            "month"
        )
    )

    # =====================================================
    # REQUIRED FIELDS
    # =====================================================

    missing_fields = []

    if not organization_id:
        missing_fields.append(
            "organization_id"
        )

    if not year_raw:
        missing_fields.append(
            "year"
        )

    if not month_raw:
        missing_fields.append(
            "month"
        )

    if missing_fields:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Missing required fields.",

                "fields":
                    missing_fields,
            },
            status=400,
        )

    # =====================================================
    # NORMALIZE VALUES
    # =====================================================

    try:

        organization_id = int(
            organization_id
        )

        year = int(
            year_raw
        )

        month = int(
            month_raw
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "organization_id, year and month must be valid numbers."
            },
            status=400,
        )

    # =====================================================
    # YEAR VALIDATION
    # =====================================================

    if (
        year < 2000
        or
        year > 2200
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid statement year."
            },
            status=400,
        )

    # =====================================================
    # MONTH VALIDATION
    # =====================================================

    if (
        month < 1
        or
        month > 12
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Month must be between 1 and 12."
            },
            status=400,
        )

    # =====================================================
    # PERIOD
    # =====================================================

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

    today = (
        timezone.localdate()
    )

    if start_date > today:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Statements cannot be viewed for a future month."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    organization = (
        Organization.objects
        .filter(
            id=
                organization_id
        )
        .first()
    )

    if not organization:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Organization not found."
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .prefetch_related(
            "roles"
        )
        .first()
    )

    if not membership:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # PERMISSION
    # =====================================================

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
        "owner",
        "landlord",
    }

    if not role_codes.intersection(
        allowed_roles
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "You do not have permission to view organization statements."
            },
            status=403,
        )

    # =====================================================
    # ORGANIZATION PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=
                organization
        )
        .select_related(
            "portifolio"
        )
        .order_by(
            "name"
        )
    )

    # =====================================================
    # TOTALS
    # =====================================================

    gross_collected = Decimal(
        "0.00"
    )

    maintenance_costs = Decimal(
        "0.00"
    )

    outstanding = Decimal(
        "0.00"
    )

    property_results = []

    all_payments = []

    all_maintenance = []

    all_outstanding_invoices = []

    # =====================================================
    # EACH PROPERTY
    # =====================================================

    for property_obj in properties:

        # =================================================
        # RENT INVOICES EXISTING BY END OF PERIOD
        # =================================================

        rent_invoices = (
            Invoice.objects
            .filter(
                organization=
                    organization,

                property=
                    property_obj,

                invoice_type=
                    "rent",

                issue_date__lt=
                    end_date,
            )
            .exclude(
                status__in=[
                    "cancelled",
                    "void",
                ]
            )
            .select_related(
                "tenant",
                "lease",
            )
            .order_by(
                "-issue_date"
            )
        )

        # =================================================
        # OUTSTANDING RENT
        # =================================================

        outstanding_queryset = (
            rent_invoices
            .filter(
                balance__gt=0
            )
        )

        property_outstanding = (
            outstanding_queryset
            .aggregate(
                total=Sum(
                    "balance"
                )
            )[
                "total"
            ]
            or Decimal(
                "0.00"
            )
        )

        # =================================================
        # RENT COLLECTED DURING MONTH
        # =================================================

        allocations = (
            PaymentAllocation.objects
            .filter(
                invoice__organization=
                    organization,

                invoice__property=
                    property_obj,

                invoice__invoice_type=
                    "rent",

                payment__status=
                    "completed",

                payment__paid_at__date__gte=
                    start_date,

                payment__paid_at__date__lt=
                    end_date,
            )
            .select_related(
                "payment",
                "payment__tenant",
                "payment__received_by",
                "invoice",
                "invoice__tenant",
                "invoice__lease",
            )
            .order_by(
                "-payment__paid_at",
                "-payment__created_at",
            )
        )

        property_collected = (
            allocations
            .aggregate(
                total=Sum(
                    "allocated_amount"
                )
            )[
                "total"
            ]
            or Decimal(
                "0.00"
            )
        )

        # =================================================
        # MAINTENANCE
        # =================================================

        maintenance_queryset = (
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
                status=
                    "cancelled"
            )
            .select_related(
                "property",
                "building",
                "unit",
                "reported_by",
                "assigned_to",
            )
            .order_by(
                "-completed_at"
            )
        )

        property_maintenance = (
            maintenance_queryset
            .aggregate(
                total=Sum(
                    "actual_cost"
                )
            )[
                "total"
            ]
            or Decimal(
                "0.00"
            )
        )

        # =================================================
        # NET PROPERTY INCOME
        # =================================================

        property_net_income = (
            property_collected
            -
            property_maintenance
        )

        # =================================================
        # TOTALS
        # =================================================

        gross_collected += (
            property_collected
        )

        maintenance_costs += (
            property_maintenance
        )

        outstanding += (
            property_outstanding
        )

        # =================================================
        # PAYMENTS
        # =================================================

        property_payments = []

        for allocation in allocations:

            payment = (
                allocation.payment
            )

            invoice = (
                allocation.invoice
            )

            allocated_amount = (
                allocation
                .allocated_amount
                or Decimal(
                    "0.00"
                )
            )

            payment_item = {
                "allocation_id":
                    allocation.id,

                "payment_id":
                    payment.id,

                "invoice_id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "tenant": (
                    {
                        "id":
                            invoice.tenant.id,

                        "name":
                            invoice.tenant.full_name,

                        "email":
                            invoice.tenant.email,

                        "phone_number":
                            invoice.tenant.phone_number,
                    }
                    if invoice.tenant
                    else None
                ),

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "provider":
                    payment.provider,

                "payment_method":
                    payment.payment_method,

                "currency":
                    payment.currency,

                "amount":
                    float(
                        allocated_amount
                    ),

                "paid_at": (
                    payment
                    .paid_at
                    .isoformat()
                    if payment.paid_at
                    else None
                ),

                "received_by": (
                    {
                        "id":
                            payment.received_by.id,

                        "name": (
                            getattr(
                                payment.received_by,
                                "full_name",
                                None
                            )
                            or
                            f"{payment.received_by.first_name} "
                            f"{payment.received_by.last_name}".strip()
                            or
                            payment.received_by.username
                        ),

                        "username":
                            payment.received_by.username,
                    }
                    if payment.received_by
                    else None
                ),

                "property_id":
                    property_obj.id,

                "property_name":
                    property_obj.name,
            }

            property_payments.append(
                payment_item
            )

            all_payments.append(
                payment_item
            )

        # =================================================
        # MAINTENANCE ITEMS
        # =================================================

        property_maintenance_items = []

        for ticket in maintenance_queryset:

            cost = (
                ticket.actual_cost
                or Decimal(
                    "0.00"
                )
            )

            maintenance_item = {
                "id":
                    ticket.id,

                "ticket_number":
                    ticket.ticket_number,

                "title":
                    ticket.title,

                "description":
                    ticket.description,

                "category":
                    ticket.category,

                "priority":
                    ticket.priority,

                "status":
                    ticket.status,

                "actual_cost":
                    float(
                        cost
                    ),

                "completed_at": (
                    ticket
                    .completed_at
                    .isoformat()
                    if ticket.completed_at
                    else None
                ),

                "property_id":
                    property_obj.id,

                "property_name":
                    property_obj.name,

                "unit": (
                    {
                        "id":
                            ticket.unit.id,

                        "name":
                            ticket.unit.name,

                        "unit_code":
                            ticket.unit.unit_code,
                    }
                    if ticket.unit
                    else None
                ),
            }

            property_maintenance_items.append(
                maintenance_item
            )

            all_maintenance.append(
                maintenance_item
            )

        # =================================================
        # OUTSTANDING INVOICES
        # =================================================

        outstanding_invoices = []

        for invoice in outstanding_queryset:

            invoice_balance = (
                invoice.balance
                or Decimal(
                    "0.00"
                )
            )

            invoice_item = {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "tenant": (
                    {
                        "id":
                            invoice.tenant.id,

                        "name":
                            invoice.tenant.full_name,

                        "email":
                            invoice.tenant.email,

                        "phone_number":
                            invoice.tenant.phone_number,
                    }
                    if invoice.tenant
                    else None
                ),

                "lease": (
                    {
                        "id":
                            invoice.lease.id,

                        "lease_number":
                            invoice.lease.lease_number,
                    }
                    if invoice.lease
                    else None
                ),

                "total_amount":
                    float(
                        invoice.total_amount
                    ),

                "paid_amount":
                    float(
                        invoice.paid_amount
                    ),

                "balance":
                    float(
                        invoice_balance
                    ),

                "status":
                    invoice.status,

                "issue_date":
                    invoice
                    .issue_date
                    .isoformat(),

                "due_date": (
                    invoice
                    .due_date
                    .isoformat()
                    if invoice.due_date
                    else None
                ),

                "property_id":
                    property_obj.id,

                "property_name":
                    property_obj.name,
            }

            outstanding_invoices.append(
                invoice_item
            )

            all_outstanding_invoices.append(
                invoice_item
            )

        # =================================================
        # PROPERTY RESPONSE
        # =================================================

        if (
            property_collected > 0
            or
            property_outstanding > 0
            or
            property_maintenance > 0
        ):

            property_results.append(
                {
                    "id":
                        property_obj.id,

                    "name":
                        property_obj.name,

                    "property_code":
                        property_obj.property_code,

                    "property_type":
                        property_obj.property_type,

                    "city":
                        property_obj.city,

                    "county":
                        property_obj.county,

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

                    "payments_count":
                        len(
                            property_payments
                        ),

                    "maintenance_count":
                        len(
                            property_maintenance_items
                        ),

                    "outstanding_invoices_count":
                        len(
                            outstanding_invoices
                        ),
                }
            )

    # =====================================================
    # NET INCOME
    # =====================================================

    net_income = (
        gross_collected
        -
        maintenance_costs
    )

    # =====================================================
    # SORT
    # =====================================================

    all_payments.sort(
        key=lambda item:
            item.get(
                "paid_at"
            )
            or "",
        reverse=True,
    )

    all_maintenance.sort(
        key=lambda item:
            item.get(
                "completed_at"
            )
            or "",
        reverse=True,
    )

    all_outstanding_invoices.sort(
        key=lambda item:
            item.get(
                "due_date"
            )
            or ""
    )

    # =====================================================
    # REQUESTED BY
    # =====================================================

    requester_name = (
        getattr(
            user,
            "full_name",
            None
        )
        or
        f"{user.first_name} {user.last_name}".strip()
        or
        user.username
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    response_data = {
        "success":
            True,

        "requested_by": {
            "id":
                user.id,

            "name":
                requester_name,

            "email":
                user.email,

            "username":
                user.username,

            "roles":
                list(
                    membership.roles
                    .filter(
                        is_active=True
                    )
                    .values_list(
                        "code",
                        flat=True,
                    )
                ),
        },

        "organization": {
            "id":
                organization.id,

            "name":
                organization.name,

            "logo":
                organization.logo,

            "email":
                organization.email,

            "phone_number":
                organization.phone_number,
        },

        "statement": {
            "year":
                year,

            "month":
                month,

            "month_name":
                month_name[
                    month
                ],

            "period_start":
                start_date.isoformat(),

            "period_end_exclusive":
                end_date.isoformat(),

            "gross_collected":
                float(
                    gross_collected
                ),

            "maintenance_costs":
                float(
                    maintenance_costs
                ),

            "outstanding":
                float(
                    outstanding
                ),

            "net_income":
                float(
                    net_income
                ),

            "properties_count":
                len(
                    property_results
                ),

            "payments_count":
                len(
                    all_payments
                ),

            "maintenance_count":
                len(
                    all_maintenance
                ),

            "outstanding_invoices_count":
                len(
                    all_outstanding_invoices
                ),
        },

        "properties":
            property_results,

        "payments": {
            "count":
                len(
                    all_payments
                ),

            "items":
                all_payments,
        },

        "maintenance": {
            "count":
                len(
                    all_maintenance
                ),

            "items":
                all_maintenance,
        },

        "outstanding_invoices": {
            "count":
                len(
                    all_outstanding_invoices
                ),

            "items":
                all_outstanding_invoices,
        },
    }

    # =====================================================
    # DEBUG
    # =====================================================

    print(
        "REQUESTED BY:",
        user.id,
        requester_name
    )

    print(
        "ORGANIZATION:",
        organization.id,
        organization.name
    )

    print(
        "PERIOD:",
        year,
        month
    )

    print(
        "GROSS COLLECTED:",
        gross_collected
    )

    print(
        "MAINTENANCE:",
        maintenance_costs
    )

    print(
        "OUTSTANDING:",
        outstanding
    )

    print(
        "NET INCOME:",
        net_income
    )

    print(
        "PAYMENTS:",
        len(
            all_payments
        )
    )

    print(
        "========================================"
    )

    return JsonResponse(
        response_data,
        status=200,
    )