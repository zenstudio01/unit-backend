from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def manager_finance_dashboard(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

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
    # VERIFY MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related("roles")
            .get(
                organization=organization,
                user=user,
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

    # =====================================================
    # VERIFY FINANCE ACCESS
    # =====================================================

    allowed_roles = {
        "organization_owner",
        "organization_admin",
        "property_manager",
        "accountant",
        "landlord",
    }

    role_codes = set(
        membership.roles
        .filter(is_active=True)
        .values_list(
            "code",
            flat=True,
        )
    )

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to access finance information."
            },
            status=403,
        )

    # =====================================================
    # CURRENT MONTH
    # =====================================================

    today = timezone.localdate()

    month_start = today.replace(
        day=1
    )

    if month_start.month == 12:
        next_month = month_start.replace(
            year=month_start.year + 1,
            month=1,
        )

    else:
        next_month = month_start.replace(
            month=month_start.month + 1
        )

    # =====================================================
    # RENT INVOICES FOR CURRENT MONTH
    # =====================================================

    monthly_rent_invoices = (
        Invoice.objects
        .filter(
            organization=organization,
            invoice_type="rent",
            issue_date__gte=month_start,
            issue_date__lt=next_month,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
    )

    # =====================================================
    # EXPECTED RENT
    # =====================================================

    expected_rent = (
        monthly_rent_invoices
        .aggregate(
            total=Sum("total_amount")
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # RENT COLLECTED
    #
    # We calculate through PaymentAllocation so only money
    # allocated to rent invoices counts as rent collected.
    # =====================================================

    rent_allocations = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=organization,
            invoice__invoice_type="rent",

            invoice__issue_date__gte=
                month_start,

            invoice__issue_date__lt=
                next_month,

            payment__status="completed",
        )
    )

    collected_rent = (
        rent_allocations
        .aggregate(
            total=Sum(
                "allocated_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # OUTSTANDING RENT
    # =====================================================

    outstanding = (
        monthly_rent_invoices
        .filter(
            balance__gt=0,
        )
        .aggregate(
            total=Sum("balance")
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # EXPENSES
    #
    # You currently do NOT have an Expense model.
    #
    # For now we use actual maintenance costs as property
    # expenses. Replace this once Expense is introduced.
    # =====================================================

    maintenance_expenses_query = (
        MaintenanceTicket.objects
        .filter(
            organization=organization,

            actual_cost__isnull=False,

            completed_at__date__gte=
                month_start,

            completed_at__date__lt=
                next_month,
        )
        .exclude(
            status="cancelled"
        )
    )

    expenses = (
        maintenance_expenses_query
        .aggregate(
            total=Sum("actual_cost")
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # NET INCOME
    # =====================================================

    net_income = (
        collected_rent - expenses
    )

    # =====================================================
    # COLLECTION RATE
    # =====================================================

    if expected_rent > 0:
        collection_rate = round(
            (
                collected_rent
                / expected_rent
            ) * 100
        )

    else:
        collection_rate = 0

    # =====================================================
    # OVERDUE RENT INVOICES
    #
    # Include invoices explicitly marked overdue AND
    # invoices whose due date has passed but still have
    # a balance.
    # =====================================================

    overdue_invoices = (
        Invoice.objects
        .filter(
            organization=organization,
            invoice_type="rent",
            balance__gt=0,
        )
        .filter(
            Q(status="overdue")
            |
            Q(
                due_date__lt=today,
                status__in=[
                    "issued",
                    "partially_paid",
                ],
            )
        )
        .select_related(
            "tenant",
            "property",
            "lease",
            "lease__unit",
        )
        .order_by(
            "due_date"
        )
    )

    # =====================================================
    # OVERDUE TENANTS
    # =====================================================

    overdue_tenants = []

    for invoice in overdue_invoices[:10]:

        tenant_name = (
            invoice.tenant.full_name
            if invoice.tenant
            else "Unknown Tenant"
        )

        property_name = (
            invoice.property.name
            if invoice.property
            else ""
        )

        unit_name = ""

        if (
            invoice.lease
            and invoice.lease.unit
        ):
            unit_name = (
                invoice.lease.unit.name
            )

        days_overdue = max(
            (
                today
                - invoice.due_date
            ).days,
            0,
        )

        overdue_tenants.append(
            {
                "id":
                    invoice.tenant_id
                    or invoice.id,

                "tenant_id":
                    invoice.tenant_id,

                "invoice_id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "tenant":
                    tenant_name,

                "property":
                    property_name,

                "unit":
                    unit_name,

                "amount":
                    float(
                        invoice.balance
                    ),

                "due_date":
                    invoice.due_date.isoformat(),

                "days_overdue":
                    days_overdue,
            }
        )

    # =====================================================
    # PAYMENT TRANSACTIONS
    # =====================================================

    payments = (
        Payment.objects
        .filter(
            organization=organization,
        )
        .select_related(
            "tenant",
        )
        .prefetch_related(
            "allocations",
            "allocations__invoice",
            "allocations__invoice__property",
            "allocations__invoice__lease",
            "allocations__invoice__lease__unit",
        )
        .order_by(
            "-created_at"
        )[:20]
    )

    transactions = []

    for payment in payments:

        allocation = (
            payment.allocations
            .all()
            .first()
        )

        invoice = (
            allocation.invoice
            if allocation
            else None
        )

        property_name = ""
        unit_name = ""

        if (
            invoice
            and invoice.property
        ):
            property_name = (
                invoice.property.name
            )

        if (
            invoice
            and invoice.lease
            and invoice.lease.unit
        ):
            unit_name = (
                invoice.lease.unit.name
            )

        tenant_name = (
            payment.tenant.full_name
            if payment.tenant
            else None
        )

        title = "Payment"

        if invoice:
            title = (
                invoice.get_invoice_type_display()
                + " Payment"
            )

        payment_date = (
            payment.paid_at
            or payment.created_at
        )

        transactions.append(
            {
                "id":
                    payment.id,

                "reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "type":
                    "rent_payment"
                    if (
                        invoice
                        and invoice.invoice_type
                        == "rent"
                    )
                    else "payment",

                "source_type":
                    "payment",

                "title":
                    title,

                "tenant":
                    tenant_name,

                "tenant_id":
                    payment.tenant_id,

                "property":
                    property_name,

                "unit":
                    unit_name,

                "amount":
                    float(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "method":
                    payment
                    .get_payment_method_display(),

                "provider":
                    payment
                    .get_provider_display(),

                "status":
                    payment.status,

                "date":
                    payment_date
                    .date()
                    .isoformat(),

                "created_at":
                    payment
                    .created_at
                    .isoformat(),
            }
        )

    # =====================================================
    # MAINTENANCE EXPENSE TRANSACTIONS
    # =====================================================

    maintenance_transactions = (
        MaintenanceTicket.objects
        .filter(
            organization=organization,
            actual_cost__isnull=False,
        )
        .select_related(
            "property",
            "unit",
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )[:10]
    )

    for maintenance in maintenance_transactions:

        transactions.append(
            {
                "id":
                    maintenance.id,

                "reference":
                    maintenance.ticket_number,

                "type":
                    "expense",

                "source_type":
                    "maintenance",

                "title":
                    maintenance.title,

                "tenant":
                    None,

                "tenant_id":
                    None,

                "property":
                    (
                        maintenance.property.name
                        if maintenance.property
                        else ""
                    ),

                "unit":
                    (
                        maintenance.unit.name
                        if maintenance.unit
                        else "Common Area"
                    ),

                "amount":
                    float(
                        maintenance.actual_cost
                        or 0
                    ),

                "currency":
                    "KES",

                "method":
                    "Maintenance",

                "provider":
                    None,

                "status":
                    maintenance.status,

                "date": (
                    maintenance.completed_at
                    .date()
                    .isoformat()
                    if maintenance.completed_at
                    else maintenance
                    .created_at
                    .date()
                    .isoformat()
                ),

                "created_at":
                    maintenance
                    .created_at
                    .isoformat(),
            }
        )

    # =====================================================
    # SORT COMBINED TRANSACTIONS
    # =====================================================

    transactions.sort(
        key=lambda item:
            item["created_at"],
        reverse=True,
    )

    transactions = (
        transactions[:20]
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

            "financial_summary": {
                "expected_rent":
                    float(
                        expected_rent
                    ),

                "collected_rent":
                    float(
                        collected_rent
                    ),

                "outstanding":
                    float(
                        outstanding
                    ),

                "expenses":
                    float(
                        expenses
                    ),

                "net_income":
                    float(
                        net_income
                    ),

                "collection_rate":
                    collection_rate,
            },

            "overdue_tenants":
                overdue_tenants,

            "transactions":
                transactions,

            "transaction_count":
                len(transactions),

            "overdue_count":
                overdue_invoices.count(),
        },
        status=200,
    )