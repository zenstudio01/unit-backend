from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def manager_dashboard(request):
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
    # VERIFY ORGANIZATION
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
    # VERIFY USER MEMBERSHIP
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
    # PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=organization,
            status="active",
        )
        .order_by("-created_at")
    )

    property_count = properties.count()

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

    total_units = units.count()

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

    # =====================================================
    # ACTIVE LEASES
    # =====================================================

    active_leases = (
        Lease.objects
        .filter(
            organization=organization,
            status="active",
        )
        .select_related(
            "unit",
            "unit__property",
        )
        .prefetch_related(
            "lease_tenants",
            "lease_tenants__tenant",
        )
    )

    # =====================================================
    # TENANTS
    #
    # Lease does not have tenant_id directly.
    # Tenant relationships are stored in LeaseTenant.
    # =====================================================

    tenants_count = (
        active_leases
        .values(
            "lease_tenants__tenant_id"
        )
        .exclude(
            lease_tenants__tenant_id__isnull=True
        )
        .distinct()
        .count()
    )

    # =====================================================
    # CURRENT BILLING PERIOD
    # =====================================================

    now = timezone.now()

    month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    if month_start.month == 12:
        next_month = (
            month_start.replace(
                year=
                    month_start.year + 1,
                month=1,
            )
        )

    else:
        next_month = (
            month_start.replace(
                month=
                    month_start.month + 1
            )
        )

    # =====================================================
    # EXPECTED RENT
    #
    # Lease uses monthly_rent.
    # =====================================================

    rent_expected = (
        active_leases
        .aggregate(
            total=Sum(
                "monthly_rent"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # RENT COLLECTED
    # =====================================================

    rent_collected = (
        Payment.objects
        .filter(
            organization=organization,
            status="completed",
            paid_at__gte=
                month_start,
            paid_at__lt=
                next_month,
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # ARREARS
    # =====================================================

    arrears = max(
        rent_expected - rent_collected,
        Decimal("0.00"),
    )

    # =====================================================
    # MAINTENANCE
    # =====================================================

    maintenance = (
        MaintenanceTicket.objects
        .filter(
            organization=organization
        )
    )

    open_maintenance = (
        maintenance
        .exclude(
            status__in=[
                "completed",
                "closed",
                "cancelled",
            ]
        )
        .count()
    )

    urgent_maintenance = (
        maintenance
        .filter(
            priority="urgent"
        )
        .exclude(
            status__in=[
                "completed",
                "closed",
                "cancelled",
            ]
        )
        .count()
    )

    in_progress_maintenance = (
        maintenance
        .filter(
            status="in_progress"
        )
        .count()
    )

    completed_maintenance = (
        maintenance
        .filter(
            status="completed"
        )
        .count()
    )

    # =====================================================
    # LEASE EXPIRIES
    # =====================================================

    today = timezone.now().date()

    expiry_limit = (
        today
        + timedelta(days=30)
    )

    expiring_leases = (
        active_leases
        .filter(
            end_date__gte=today,
            end_date__lte=
                expiry_limit,
        )
        .order_by("end_date")
    )

    # =====================================================
    # EXPIRING LEASE DATA
    # =====================================================

    leases_data = []

    for lease in expiring_leases[:5]:

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
            tenant_name = " ".join(
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
                            "middle_name",
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

        property_obj = None

        if (
            lease.unit
            and getattr(
                lease.unit,
                "property",
                None,
            )
        ):
            property_obj = (
                lease.unit.property
            )

        leases_data.append(
            {
                "id":
                    lease.id,

                "lease_number":
                    getattr(
                        lease,
                        "lease_number",
                        "",
                    ),

                "tenant_name":
                    tenant_name,

                "property_name":
                    (
                        property_obj.name
                        if property_obj
                        else ""
                    ),

                "unit_number":
                    (
                        lease.unit.unit_number
                        if lease.unit
                        else ""
                    ),

                "monthly_rent":
                    float(
                        lease.monthly_rent
                        or 0
                    ),

                "end_date":
                    (
                        lease.end_date
                        .isoformat()
                    ),

                "days_remaining":
                    (
                        lease.end_date
                        - today
                    ).days,
            }
        )

    # =====================================================
    # PROPERTY CARDS
    # =====================================================

    property_data = []

    for property_obj in properties[:10]:

        property_units = (
            units.filter(
                property=property_obj
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

        property_vacant_units = (
            property_units
            .filter(
                status="vacant"
            )
            .count()
        )

        # -------------------------------------------------
        # Property Rent Collection
        # -------------------------------------------------
        #
        # If Payment has a property FK,
        # this query works directly.
        #
        # -------------------------------------------------

        property_payments = (
    PaymentAllocation.objects
    .filter(
        payment__organization=
            organization,

        payment__status=
            "completed",

        payment__paid_at__gte=
            month_start,

        payment__paid_at__lt=
            next_month,

        invoice__property=
            property_obj,

        invoice__invoice_type=
            "rent",
    )
    .aggregate(
        total=Sum(
            "allocated_amount"
        )
    )["total"]
    or Decimal("0.00")
)

        # -------------------------------------------------
        # Property image
        # -------------------------------------------------

        property_image = getattr(
            property_obj,
            "image",
            None,
        )

        if property_image:
            try:
                property_image = (
                    property_image.url
                )
            except Exception:
                property_image = str(
                    property_image
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
                                getattr(
                                    property_obj,
                                    "city",
                                    "",
                                ),

                                getattr(
                                    property_obj,
                                    "county",
                                    "",
                                ),
                            ],
                        )
                    ),

                "image":
                    property_image,

                "total_units":
                    property_total_units,

                "occupied_units":
                    property_occupied_units,

                "vacant_units":
                    property_vacant_units,

                "rent_collected":
                    float(
                        property_payments
                    ),
            }
        )

    # =====================================================
    # ARREARS SUMMARY
    # =====================================================
    #
    # Once Invoice is fully wired,
    # calculate this from invoice balances.
    #
    # =====================================================

    tenants_in_arrears = 0

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    unread_notifications = (
        Notification.objects
        .filter(
            user=user,
            organization=organization,
            is_read=False,
        )
        .count()
    )

    # =====================================================
    # RECENT ACTIVITIES
    #
    # We currently use notifications as dashboard
    # activity records.
    # =====================================================

    recent_notifications = (
        Notification.objects
        .filter(
            user=user,
            organization=organization,
        )
        .select_related(
            "property"
        )
        .order_by(
            "-created_at"
        )[:6]
    )

    activities = []

    for notification in recent_notifications:

        activities.append(
            {
                "id":
                    notification.id,

                "type":
                    notification
                    .notification_type,

                "title":
                    notification.title,

                "description":
                    notification.message,

                "reference_id":
                    notification.reference_id,

                "property_name":
                    (
                        notification
                        .property.name
                        if notification.property
                        else None
                    ),

                "is_read":
                    notification.is_read,

                "created_at":
                    notification
                    .created_at
                    .isoformat(),
            }
        )

    # =====================================================
    # USER ROLES
    # =====================================================

    roles = []

    for role in (
        membership.roles
        .filter(
            is_active=True
        )
    ):

        roles.append(
            {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.get_name_display(),
            }
        )

    # =====================================================
    # PROFILE IMAGE
    # =====================================================

    profile_image = getattr(
        user,
        "profile_image",
        None,
    )

    if profile_image:
        try:
            profile_image = (
                profile_image.url
            )
        except Exception:
            profile_image = str(
                profile_image
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

                "middle_name":
                    getattr(
                        user,
                        "middle_name",
                        "",
                    ),

                "last_name":
                    user.last_name,

                "email":
                    user.email,

                "profile_image":
                    profile_image,
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,

                "organization_type":
                    organization
                    .organization_type,

                "is_verified":
                    organization
                    .is_verified,

                "roles":
                    roles,
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

                "tenants":
                    tenants_count,

                "rent_expected":
                    float(
                        rent_expected
                    ),

                "rent_collected":
                    float(
                        rent_collected
                    ),

                "arrears":
                    float(
                        arrears
                    ),

                "open_maintenance":
                    open_maintenance,
            },

            "maintenance_summary": {
                "urgent":
                    urgent_maintenance,

                "in_progress":
                    in_progress_maintenance,

                "completed":
                    completed_maintenance,
            },

            "properties":
                property_data,

            "lease_expiries": {
                "count":
                    expiring_leases
                    .count(),

                "within_days":
                    30,

                "leases":
                    leases_data,
            },

            "recent_activities":
                activities,

            "arrears_summary": {
                "amount":
                    float(
                        arrears
                    ),

                "tenants_count":
                    tenants_in_arrears,
            },

            "unread_notifications":
                unread_notifications,
        },
        status=200,
    )