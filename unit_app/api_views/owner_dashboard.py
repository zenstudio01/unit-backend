from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def owner_dashboard(request):
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
    # MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization=
                    organization,

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
    # OWNER PERMISSION
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
        "owner",
        "landlord",
        "organization_admin",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have owner dashboard access."
            },
            status=403,
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
        .order_by(
            "-created_at"
        )
    )

    property_count = (
        properties.count()
    )

    # =====================================================
    # PORTFOLIOS
    # =====================================================

    portfolios = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            status="active",
        )
    )

    portfolio_count = (
        portfolios.count()
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
        units
        .filter(
            status="occupied"
        )
        .count()
    )

    vacant_units = (
        units
        .filter(
            status="vacant"
        )
        .count()
    )

    occupancy_rate = 0

    if total_units > 0:
        occupancy_rate = round(
            (
                occupied_units /
                total_units
            ) * 100
        )

    # =====================================================
    # CURRENT MONTH
    # =====================================================

    today = (
        timezone.localdate()
    )

    month_start = (
        today.replace(
            day=1
        )
    )

    if (
        month_start.month
        == 12
    ):
        next_month = (
            month_start.replace(
                year=
                    month_start.year +
                    1,

                month=1,
            )
        )

    else:
        next_month = (
            month_start.replace(
                month=
                    month_start.month +
                    1
            )
        )

    # =====================================================
    # RENT INVOICES
    # =====================================================

    rent_invoices = (
        Invoice.objects
        .filter(
            organization=
                organization,

            invoice_type="rent",

            issue_date__gte=
                month_start,

            issue_date__lt=
                next_month,
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

    rent_expected = (
        rent_invoices
        .aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # COLLECTED RENT
    # =====================================================

    rent_collected = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            invoice__invoice_type=
                "rent",

            invoice__issue_date__gte=
                month_start,

            invoice__issue_date__lt=
                next_month,

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

    # =====================================================
    # OUTSTANDING
    # =====================================================

    outstanding = (
        rent_invoices
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
    # COLLECTION RATE
    # =====================================================

    collection_rate = 0

    if rent_expected > 0:
        collection_rate = round(
            (
                rent_collected /
                rent_expected
            ) * 100
        )

    # =====================================================
    # PROPERTY PERFORMANCE
    # =====================================================

    property_data = []

    for property_obj in properties[:6]:

        property_units = (
            Unit.objects
            .filter(
                property=
                    property_obj
            )
        )

        property_total_units = (
            property_units.count()
        )

        property_occupied_units = (
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
                    property_occupied_units /
                    property_total_units
                ) * 100
            )

        # ===============================================
        # Cover image
        # ===============================================

        cover_image = (
            PropertyImage.objects
            .filter(
                property=
                    property_obj,

                is_cover=True,
            )
            .first()
        )

        if not cover_image:
            cover_image = (
                PropertyImage.objects
                .filter(
                    property=
                        property_obj
                )
                .first()
            )

        property_data.append(
            {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "location":
                    ", ".join(
                        filter(
                            None,
                            [
                                property_obj.city,
                                property_obj.county,
                            ],
                        )
                    ),

                "property_type":
                    property_obj
                    .property_type,

                "total_units":
                    property_total_units,

                "occupied_units":
                    property_occupied_units,

                "vacant_units":
                    (
                        property_total_units -
                        property_occupied_units
                    ),

                "occupancy_rate":
                    property_occupancy,

                "cover_image": (
                    cover_image.image_url
                    if cover_image
                    else None
                ),
            }
        )

    # =====================================================
    # LEASE EXPIRIES
    # =====================================================

    expiry_date = (
        today
        + timedelta(
            days=30
        )
    )

    expiring_leases = (
        Lease.objects
        .filter(
            organization=
                organization,

            status="active",

            end_date__gte=
                today,

            end_date__lte=
                expiry_date,
        )
        .select_related(
            "unit",
            "unit__property",
        )
        .prefetch_related(
            "lease_tenants",
            "lease_tenants__tenant",
        )
        .order_by(
            "end_date"
        )
    )

    lease_expiry_data = []

    for lease in (
        expiring_leases[:6]
    ):

        lease_tenant = (
            lease.lease_tenants
            .select_related(
                "tenant"
            )
            .first()
        )

        tenant = (
            lease_tenant.tenant
            if lease_tenant
            else None
        )

        tenant_name = ""

        if tenant:
            tenant_name = (
                getattr(
                    tenant,
                    "full_name",
                    ""
                )
                or " ".join(
                    filter(
                        None,
                        [
                            getattr(
                                tenant,
                                "first_name",
                                "",
                            ),

                            getattr(
                                tenant,
                                "last_name",
                                "",
                            ),
                        ],
                    )
                )
            )

        property_name = ""

        if (
            lease.unit
            and lease.unit.property
        ):
            property_name = (
                lease.unit
                .property
                .name
            )

        lease_expiry_data.append(
            {
                "id":
                    lease.id,

                "lease_number":
                    lease.lease_number,

                "tenant_name":
                    tenant_name,

                "property_name":
                    property_name,

                "unit_name": (
                    lease.unit.name
                    if lease.unit
                    else ""
                ),

                "end_date":
                    lease.end_date
                    .isoformat(),

                "days_remaining":
                    (
                        lease.end_date -
                        today
                    ).days,
            }
        )

    # =====================================================
    # RECENT TRANSACTIONS
    # =====================================================

    recent_allocations = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            payment__status=
                "completed",
        )
        .select_related(
            "payment",
            "invoice",
            "invoice__property",
        )
        .order_by(
            "-payment__created_at"
        )[:6]
    )

    recent_transactions = []

    for allocation in (
        recent_allocations
    ):

        payment = (
            allocation.payment
        )

        invoice = (
            allocation.invoice
        )

        recent_transactions.append(
            {
                "id":
                    payment.id,

                "title": (
                    invoice
                    .get_invoice_type_display()
                    + " Payment"
                ),

                "amount":
                    float(
                        allocation
                        .allocated_amount
                    ),

                "property_name": (
                    invoice.property.name
                    if invoice.property
                    else ""
                ),

                "reference":
                    payment
                    .payment_reference,

                "date": (
                    payment.paid_at
                    .isoformat()
                    if payment.paid_at
                    else payment
                    .created_at
                    .isoformat()
                ),
            }
        )

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    unread_notifications = (
        Notification.objects
        .filter(
            user=user,

            organization=
                organization,

            is_read=False,
        )
        .count()
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "user": {
                "id":
                    user.id,

                "first_name":
                    user.first_name,

                "last_name":
                    user.last_name,

                "profile_image":
                    getattr(
                        user,
                        "profile_image",
                        None,
                    ),
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "statistics": {
                "properties":
                    property_count,

                "units":
                    total_units,

                "occupied_units":
                    occupied_units,

                "vacant_units":
                    vacant_units,

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
            },

            "portfolio_summary": {
                "total":
                    portfolio_count,

                "properties":
                    property_count,
            },

            "properties":
                property_data,

            "lease_expiries":
                lease_expiry_data,

            "recent_transactions":
                recent_transactions,

            "unread_notifications":
                unread_notifications,
        },
        status=200,
    )