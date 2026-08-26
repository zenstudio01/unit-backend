from .common_imports import *
from .helper import *


# ============================================================
# CREATE LEASE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_lease(
    request
):
    user = request.user
    data = request.data

    # ========================================================
    # REQUEST DATA
    # ========================================================

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    tenant_id = (
        data.get(
            "tenant_id"
        )
    )

    property_id = (
        data.get(
            "property_id"
        )
    )

    unit_id = (
        data.get(
            "unit_id"
        )
    )

    start_date_raw = str(
        data.get(
            "start_date",
            ""
        )
        or ""
    ).strip()

    end_date_raw = str(
        data.get(
            "end_date",
            ""
        )
        or ""
    ).strip()

    rent_raw = (
        data.get(
            "rent_amount"
        )
    )

    deposit_raw = (
        data.get(
            "deposit_amount",
            0
        )
    )

    billing_cycle = str(
        data.get(
            "billing_cycle",
            "monthly"
        )
        or "monthly"
    ).strip().lower()

    billing_day_raw = (
        data.get(
            "billing_day",
            1
        )
    )

    grace_period_raw = (
        data.get(
            "grace_period_days",
            0
        )
    )

    notice_period_raw = (
        data.get(
            "notice_period_days",
            30
        )
    )

    late_fee_raw = (
        data.get(
            "late_fee",
            0
        )
    )

    notes = str(
        data.get(
            "notes",
            ""
        )
        or ""
    ).strip()

    requested_status = str(
        data.get(
            "status",
            "draft"
        )
        or "draft"
    ).strip().lower()

    # ========================================================
    # DEBUG
    # ========================================================

    print(
        "========================================"
    )

    print(
        "CREATE LEASE REQUEST"
    )

    print(
        "DATA:",
        data
    )

    print(
        "========================================"
    )

    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    missing_fields = []

    if not organization_id:
        missing_fields.append(
            "organization_id"
        )

    if not tenant_id:
        missing_fields.append(
            "tenant_id"
        )

    if not property_id:
        missing_fields.append(
            "property_id"
        )

    if not unit_id:
        missing_fields.append(
            "unit_id"
        )

    if not start_date_raw:
        missing_fields.append(
            "start_date"
        )

    if not end_date_raw:
        missing_fields.append(
            "end_date"
        )

    if rent_raw in [
        None,
        "",
    ]:
        missing_fields.append(
            "rent_amount"
        )

    if missing_fields:
        print("Missing fields...")

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

    # ========================================================
    # NORMALIZE IDS
    # ========================================================

    try:
        organization_id = int(
            organization_id
        )

        tenant_id = int(
            tenant_id
        )

        property_id = int(
            property_id
        )

        unit_id = int(
            unit_id
        )

    except (
        TypeError,
        ValueError,
    ):
        print("Organization, tenant, property and unit IDs must be valid numbers.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Organization, tenant, property and unit IDs must be valid numbers."
            },
            status=400,
        )

    # ========================================================
    # DATES
    # ========================================================

    start_date = (
        parse_date(
            start_date_raw
        )
    )

    if not start_date:
        print("start_date must use YYYY-MM-DD format.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "start_date must use YYYY-MM-DD format."
            },
            status=400,
        )

    end_date = (
        parse_date(
            end_date_raw
        )
    )

    if not end_date:
        print("end_date must use YYYY-MM-DD format.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "end_date must use YYYY-MM-DD format."
            },
            status=400,
        )

    if end_date <= start_date:
        print("Lease end date must be after the start date.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Lease end date must be after the start date."
            },
            status=400,
        )

    # ========================================================
    # MONEY VALUES
    # ========================================================

    try:
        monthly_rent = Decimal(
            str(
                rent_raw
            )
        )

        deposit_amount = Decimal(
            str(
                deposit_raw
                or 0
            )
        )

        late_fee = Decimal(
            str(
                late_fee_raw
                or 0
            )
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        print("Rent, deposit and late fee must be valid amounts.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Rent, deposit and late fee must be valid amounts."
            },
            status=400,
        )

    if monthly_rent <= 0:
        print("Monthly rent must be greater than zero.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Monthly rent must be greater than zero."
            },
            status=400,
        )

    if deposit_amount < 0:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Deposit amount cannot be negative."
            },
            status=400,
        )

    if late_fee < 0:
        print("Late fee cannot be negative.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Late fee cannot be negative."
            },
            status=400,
        )

    # ========================================================
    # BILLING DAY
    # ========================================================

    try:
        billing_day = int(
            billing_day_raw
        )

    except (
        ValueError,
        TypeError,
    ):
        print("Billing day must be a number.")
        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Billing day must be a number."
            },
            status=400,
        )

    if (
        billing_day < 1
        or
        billing_day > 31
    ):
        print("Billing day must be between 1 and 31.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Billing day must be between 1 and 31."
            },
            status=400,
        )

    # ========================================================
    # GRACE PERIOD
    # ========================================================

    try:
        grace_period_days = int(
            grace_period_raw
            or 0
        )

        notice_period_days = int(
            notice_period_raw
            or 30
        )

    except (
        TypeError,
        ValueError,
    ):
        print("Grace period and notice period must be valid numbers.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Grace period and notice period must be valid numbers."
            },
            status=400,
        )

    if grace_period_days < 0:
        print("Grace period cannot be negative.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Grace period cannot be negative."
            },
            status=400,
        )

    if notice_period_days < 0:
        print("Notice period cannot be negative.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Notice period cannot be negative."
            },
            status=400,
        )

    # ========================================================
    # PAYMENT FREQUENCY
    # ========================================================

    BILLING_CYCLE_MAPPING = {
        "daily":
            "daily",

        "weekly":
            "weekly",

        "monthly":
            "monthly",

        "quarterly":
            "quarterly",

        "semi_annually":
            "semi_annually",

        "yearly":
            "annually",

        "annually":
            "annually",
    }

    payment_frequency = (
        BILLING_CYCLE_MAPPING.get(
            billing_cycle
        )
    )

    if not payment_frequency:
        print("Invalid billing cycle.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid billing cycle.",

                "allowed_cycles": [
                    "daily",
                    "weekly",
                    "monthly",
                    "quarterly",
                    "semi_annually",
                    "yearly",
                ],
            },
            status=400,
        )

    # ========================================================
    # LEASE STATUS
    # ========================================================

    valid_statuses = {
        choice[0]
        for choice
        in Lease.STATUS_CHOICES
    }

    if (
        requested_status
        not in valid_statuses
    ):
        print("Invalid lease status.")

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid lease status.",

                "allowed_statuses":
                    list(
                        valid_statuses
                    ),
            },
            status=400,
        )

    # For mobile creation, do not allow someone to bypass
    # approval/signature workflow by directly creating active.
    allowed_creation_statuses = {
        "draft",
        "pending_approval",
    }

    if (
        requested_status
        not in allowed_creation_statuses
    ):
        print("A new lease can only be created as draft or pending approval.")
        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "A new lease can only be created as draft or pending approval."
            },
            status=400,
        )

    # ========================================================
    # ORGANIZATION
    # ========================================================

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

    # ========================================================
    # MEMBERSHIP
    # ========================================================

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

    # ========================================================
    # PERMISSION
    # ========================================================

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
        "property_manager",
        "leasing_agent",
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
                    "You do not have permission to create leases."
            },
            status=403,
        )

    # ========================================================
    # PROPERTY
    # ========================================================

    property_obj = (
        Property.objects
        .filter(
            id=
                property_id,

            organization=
                organization,
        )
        .first()
    )

    if not property_obj:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Property not found in this organization."
            },
            status=404,
        )

    # ========================================================
    # TENANT
    # ========================================================

    tenant = (
        Tenant.objects
        .filter(
            id=
                tenant_id,

            organization=
                organization,
        )
        .first()
    )

    if not tenant:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Tenant not found in this organization."
            },
            status=404,
        )

    # ========================================================
    # TRANSACTION
    # ========================================================

    try:

        with transaction.atomic():

            # =================================================
            # LOCK UNIT
            # =================================================

            unit = (
                Unit.objects
                .select_for_update()
                .select_related(
                    "property",
                    "building",
                    "floor",
                )
                .filter(
                    id=
                        unit_id,

                    property=
                        property_obj,
                )
                .first()
            )

            if not unit:

                return JsonResponse(
                    {
                        "success":
                            False,

                        "message":
                            "Unit not found in the selected property."
                    },
                    status=404,
                )

            # =================================================
            # UNIT AVAILABILITY
            # =================================================

            if (
                unit.status
                != "available"
            ):

                return JsonResponse(
                    {
                        "success":
                            False,

                        "message":
                            "This unit is not available for leasing.",

                        "unit_status":
                            unit.status,
                    },
                    status=400,
                )

            # =================================================
            # PREVENT OVERLAPPING LEASES
            # =================================================

            overlapping_lease = (
                Lease.objects
                .filter(
                    unit=
                        unit,

                    start_date__lte=
                        end_date,

                    end_date__gte=
                        start_date,
                )
                .exclude(
                    status__in=[
                        "terminated",
                        "cancelled",
                        "expired",
                    ]
                )
                .first()
            )

            if overlapping_lease:

                return JsonResponse(
                    {
                        "success":
                            False,

                        "message":
                            "This unit already has a lease covering the selected dates.",

                        "existing_lease": {
                            "id":
                                overlapping_lease.id,

                            "lease_number":
                                overlapping_lease.lease_number,

                            "start_date":
                                str(
                                    overlapping_lease.start_date
                                ),

                            "end_date":
                                str(
                                    overlapping_lease.end_date
                                ),

                            "status":
                                overlapping_lease.status,
                        },
                    },
                    status=400,
                )

            # =================================================
            # PREVENT TENANT FROM DUPLICATE LEASE ON UNIT
            # =================================================

            tenant_existing_lease = (
                LeaseTenant.objects
                .filter(
                    tenant=
                        tenant,

                    lease__unit=
                        unit,

                    lease__start_date__lte=
                        end_date,

                    lease__end_date__gte=
                        start_date,
                )
                .exclude(
                    lease__status__in=[
                        "terminated",
                        "cancelled",
                        "expired",
                    ]
                )
                .first()
            )

            if tenant_existing_lease:

                return JsonResponse(
                    {
                        "success":
                            False,

                        "message":
                            "This tenant already has a lease for this unit during the selected period."
                    },
                    status=400,
                )

            # =================================================
            # LEASE NUMBER
            # =================================================

            lease_number = (
                "LSE-"
                f"{organization.id}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

            while (
                Lease.objects
                .filter(
                    lease_number=
                        lease_number
                )
                .exists()
            ):

                lease_number = (
                    "LSE-"
                    f"{organization.id}-"
                    f"{uuid.uuid4().hex[:10].upper()}"
                )

            # =================================================
            # CREATE LEASE
            # =================================================

            lease = (
                Lease.objects.create(
                    organization=
                        organization,

                    unit=
                        unit,

                    lease_number=
                        lease_number,

                    start_date=
                        start_date,

                    end_date=
                        end_date,

                    monthly_rent=
                        monthly_rent,

                    deposit_amount=
                        deposit_amount,

                    billing_day=
                        billing_day,

                    payment_frequency=
                        payment_frequency,

                    grace_period_days=
                        grace_period_days,

                    status=
                        requested_status,

                    created_by=
                        user,
                )
            )

            # =================================================
            # PRIMARY TENANT
            # =================================================

            lease_tenant = (
                LeaseTenant.objects.create(
                    lease=
                        lease,

                    tenant=
                        tenant,

                    tenant_role=
                        "primary",

                    is_primary=
                        True,

                    joined_at=
                        start_date,
                )
            )

            # =================================================
            # SECURITY DEPOSIT
            # =================================================

            lease_deposit = None

            if deposit_amount > 0:

                lease_deposit = (
                    LeaseDeposit.objects.create(
                        lease=
                            lease,

                        deposit_type=
                            "security",

                        required_amount=
                            deposit_amount,

                        paid_amount=
                            Decimal(
                                "0.00"
                            ),

                        status=
                            "pending",

                        notes=
                            "Security deposit created when lease was created.",
                    )
                )

            # =================================================
            # RENT CHARGE
            # =================================================

            lease_charge = (
                LeaseCharge.objects.create(
                    lease=
                        lease,

                    charge_type=
                        "rent",

                    description=
                        "Rent",

                    amount=
                        monthly_rent,

                    frequency=
                        payment_frequency,

                    start_date=
                        start_date,

                    end_date=
                        end_date,

                    is_active=
                        True,
                )
            )

            # =================================================
            # UNIT STATUS
            # =================================================
            #
            # Because this frontend creates the lease as
            # "draft", I would NOT mark the unit occupied yet.
            #
            # The unit should normally become occupied when
            # the lease becomes active/signed.
            #
            # So leave:
            #
            # unit.status = "available"
            #
            # for now.
            # =================================================

            # =================================================
            # RESPONSE
            # =================================================

            response_data = {

                "success":
                    True,

                "message":
                    "Lease created successfully.",

                "lease": {

                    "id":
                        lease.id,

                    "lease_number":
                        lease.lease_number,

                    "status":
                        lease.status,

                    "start_date":
                        str(
                            lease.start_date
                        ),

                    "end_date":
                        str(
                            lease.end_date
                        ),

                    "monthly_rent":
                        str(
                            lease.monthly_rent
                        ),

                    "deposit_amount":
                        str(
                            lease.deposit_amount
                        ),

                    "billing_day":
                        lease.billing_day,

                    "payment_frequency":
                        lease.payment_frequency,

                    "grace_period_days":
                        lease.grace_period_days,

                    "organization": {
                        "id":
                            organization.id,

                        "name":
                            organization.name,
                    },

                    "property": {
                        "id":
                            property_obj.id,

                        "name":
                            property_obj.name,
                    },

                    "unit": {
                        "id":
                            unit.id,

                        "name":
                            unit.name,

                        "unit_code":
                            unit.unit_code,

                        "status":
                            unit.status,

                        "monthly_rent":
                            str(
                                unit.monthly_rent
                            ),

                        "building": (
                            {
                                "id":
                                    unit.building.id,

                                "name":
                                    unit.building.name,
                            }
                            if unit.building
                            else None
                        ),

                        "floor": (
                            {
                                "id":
                                    unit.floor.id,

                                "name":
                                    unit.floor.name,
                            }
                            if unit.floor
                            else None
                        ),
                    },

                    "tenant": {
                        "id":
                            tenant.id,

                        "full_name":
                            tenant.full_name,

                        "email":
                            tenant.email,

                        "phone_number":
                            tenant.phone_number,

                        "is_primary":
                            lease_tenant.is_primary,

                        "tenant_role":
                            lease_tenant.tenant_role,
                    },

                    "rent_charge": {
                        "id":
                            lease_charge.id,

                        "amount":
                            str(
                                lease_charge.amount
                            ),

                        "frequency":
                            lease_charge.frequency,
                    },

                    "deposit": (
                        {
                            "id":
                                lease_deposit.id,

                            "required_amount":
                                str(
                                    lease_deposit.required_amount
                                ),

                            "paid_amount":
                                str(
                                    lease_deposit.paid_amount
                                ),

                            "status":
                                lease_deposit.status,
                        }
                        if lease_deposit
                        else None
                    ),

                    # These values are currently accepted
                    # from the frontend but are NOT fields
                    # on your Lease model.
                    "additional_terms": {
                        "notice_period_days":
                            notice_period_days,

                        "late_fee":
                            str(
                                late_fee
                            ),

                        "notes":
                            notes,
                    },
                },
            }

            print(
                "========================================"
            )

            print(
                "LEASE CREATED SUCCESSFULLY"
            )

            print(
                "LEASE:",
                lease.id
            )

            print(
                "LEASE NUMBER:",
                lease.lease_number
            )

            print(
                "TENANT:",
                tenant.id
            )

            print(
                "UNIT:",
                unit.id
            )

            print(
                "========================================"
            )

            return JsonResponse(
                response_data,
                status=201,
            )

    except Exception as error:

        print(
            "========================================"
        )

        print(
            "CREATE LEASE ERROR:"
        )

        print(
            repr(
                error
            )
        )

        print(
            "========================================"
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Unable to create lease.",

                "error":
                    str(
                        error
                    ),
            },
            status=500,
        )


from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_organization_tenants(
    request
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # OPTIONAL FILTERS
    # =====================================================

    search = str(
        request.GET.get(
            "search",
            ""
        )
        or ""
    ).strip()

    status_filter = str(
        request.GET.get(
            "status",
            ""
        )
        or ""
    ).strip()

    # =====================================================
    # TENANTS
    # =====================================================

    tenants = (
        Tenant.objects
        .filter(
            organization=
                organization
        )
        .order_by(
            "-created_at"
        )
    )

    if status_filter:
        tenants = (
            tenants.filter(
                status=
                    status_filter
            )
        )

    if search:
        tenants = (
            tenants.filter(
                Q(
                    full_name__icontains=
                        search
                )
                |
                Q(
                    email__icontains=
                        search
                )
                |
                Q(
                    phone_number__icontains=
                        search
                )
                |
                Q(
                    national_id_number__icontains=
                        search
                )
            )
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    tenant_data = []

    for tenant in tenants:

        active_lease_link = (
            LeaseTenant.objects
            .filter(
                tenant=
                    tenant,

                left_at__isnull=
                    True,

                lease__status__in=[
                    "draft",
                    "pending_approval",
                    "pending_signature",
                    "active",
                ],
            )
            .select_related(
                "lease",
                "lease__unit",
                "lease__unit__property",
            )
            .order_by(
                "-lease__created_at"
            )
            .first()
        )

        active_lease = (
            active_lease_link.lease
            if active_lease_link
            else None
        )

        tenant_data.append(
            {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "email":
                    tenant.email,

                "phone_number":
                    tenant.phone_number,

                "tenant_type":
                    getattr(
                        tenant,
                        "tenant_type",
                        None,
                    ),

                "national_id_number":
                    getattr(
                        tenant,
                        "national_id_number",
                        None,
                    ),

                "kra_pin":
                    getattr(
                        tenant,
                        "kra_pin",
                        None,
                    ),

                "occupation":
                    getattr(
                        tenant,
                        "occupation",
                        None,
                    ),

                "employer":
                    getattr(
                        tenant,
                        "employer",
                        None,
                    ),

                "status":
                    getattr(
                        tenant,
                        "status",
                        "active",
                    ),

                "has_active_lease":
                    bool(
                        active_lease
                    ),

                "active_lease": (
                    {
                        "id":
                            active_lease.id,

                        "lease_number":
                            active_lease.lease_number,

                        "status":
                            active_lease.status,

                        "unit": {
                            "id":
                                active_lease.unit.id,

                            "name":
                                active_lease.unit.name,

                            "unit_code":
                                active_lease.unit.unit_code,
                        },

                        "property": {
                            "id":
                                active_lease.unit.property.id,

                            "name":
                                active_lease.unit.property.name,
                        },
                    }
                    if active_lease
                    else None
                ),

                "created_at": (
                    tenant.created_at.isoformat()
                    if getattr(
                        tenant,
                        "created_at",
                        None,
                    )
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "count":
                len(
                    tenant_data
                ),

            "tenants":
                tenant_data,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_property_units_for_lease(
    request,
    property_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # PROPERTY
    # =====================================================

    try:
        property_obj = (
            Property.objects.get(
                id=
                    property_id,

                organization=
                    organization,
            )
        )

    except Property.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Property not found."
            },
            status=404,
        )

    # =====================================================
    # UNITS
    # =====================================================

    units = (
        Unit.objects
        .filter(
            property=
                property_obj
        )
        .select_related(
            "building",
            "floor",
        )
        .order_by(
            "unit_code"
        )
    )

    unit_data = []

    for unit in units:

        active_lease = (
            Lease.objects
            .filter(
                unit=
                    unit,

                status__in=[
                    "draft",
                    "pending_approval",
                    "pending_signature",
                    "active",
                ],
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        unit_data.append(
            {
                "id":
                    unit.id,

                "name":
                    unit.name,

                "unit_code":
                    unit.unit_code,

                "unit_type":
                    unit.unit_type,

                "monthly_rent":
                    str(
                        unit.monthly_rent
                    ),

                "status":
                    unit.status,

                "building": (
                    {
                        "id":
                            unit.building.id,

                        "name":
                            unit.building.name,
                    }
                    if unit.building
                    else None
                ),

                "floor": (
                    {
                        "id":
                            unit.floor.id,

                        "name":
                            unit.floor.name,
                    }
                    if unit.floor
                    else None
                ),

                "has_current_lease":
                    bool(
                        active_lease
                    ),

                "current_lease": (
                    {
                        "id":
                            active_lease.id,

                        "lease_number":
                            active_lease.lease_number,

                        "status":
                            active_lease.status,

                        "start_date":
                            str(
                                active_lease.start_date
                            ),

                        "end_date":
                            str(
                                active_lease.end_date
                            ),
                    }
                    if active_lease
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,
            },

            "count":
                len(
                    unit_data
                ),

            "units":
                unit_data,
        },
        status=200,
    )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lease_details(
    request,
    lease_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

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
        .first()
    )

    if not membership:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # LEASE
    # =====================================================

    try:
        lease = (
            Lease.objects
            .select_related(
                "organization",
                "unit",
                "unit__property",
                "unit__building",
                "unit__floor",
                "created_by",
                "approved_by",
            )
            .get(
                id=lease_id,
                organization=organization,
            )
        )

    except Lease.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Lease not found."
            },
            status=404,
        )

    # =====================================================
    # PROPERTY / UNIT
    # =====================================================

    unit = (
        lease.unit
    )

    property_obj = (
        unit.property
        if unit
        else None
    )

    # =====================================================
    # TENANTS
    # =====================================================

    lease_tenants = (
        LeaseTenant.objects
        .filter(
            lease=lease
        )
        .select_related(
            "tenant"
        )
        .order_by(
            "-is_primary",
            "joined_at",
        )
    )

    tenants = []

    for lease_tenant in lease_tenants:

        tenant = (
            lease_tenant.tenant
        )

        tenants.append(
            {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "email":
                    tenant.email,

                "phone_number":
                    tenant.phone_number,

                "tenant_role":
                    lease_tenant.tenant_role,

                "is_primary":
                    lease_tenant.is_primary,

                "joined_at": (
                    str(
                        lease_tenant.joined_at
                    )
                    if lease_tenant.joined_at
                    else None
                ),

                "left_at": (
                    str(
                        lease_tenant.left_at
                    )
                    if lease_tenant.left_at
                    else None
                ),
            }
        )

    primary_tenant = (
        next(
            (
                item
                for item in tenants
                if item[
                    "is_primary"
                ]
            ),
            tenants[0]
            if tenants
            else None,
        )
    )

    # =====================================================
    # CHARGES
    # =====================================================

    charges_queryset = (
        LeaseCharge.objects
        .filter(
            lease=lease
        )
        .order_by(
            "-is_active",
            "charge_type",
        )
    )

    charges = []

    for charge in charges_queryset:

        charges.append(
            {
                "id":
                    charge.id,

                "charge_type":
                    charge.charge_type,

                "description":
                    charge.description,

                "amount":
                    str(
                        charge.amount
                    ),

                "frequency":
                    charge.frequency,

                "start_date": (
                    str(
                        charge.start_date
                    )
                    if charge.start_date
                    else None
                ),

                "end_date": (
                    str(
                        charge.end_date
                    )
                    if charge.end_date
                    else None
                ),

                "is_active":
                    charge.is_active,
            }
        )

    # =====================================================
    # DEPOSITS
    # =====================================================

    deposits_queryset = (
        LeaseDeposit.objects
        .filter(
            lease=lease
        )
        .order_by(
            "deposit_type"
        )
    )

    deposits = []

    total_deposit_required = (
        Decimal(
            "0.00"
        )
    )

    total_deposit_paid = (
        Decimal(
            "0.00"
        )
    )

    for deposit in deposits_queryset:

        required_amount = (
            deposit.required_amount
            or Decimal(
                "0.00"
            )
        )

        paid_amount = (
            deposit.paid_amount
            or Decimal(
                "0.00"
            )
        )

        total_deposit_required += (
            required_amount
        )

        total_deposit_paid += (
            paid_amount
        )

        deposits.append(
            {
                "id":
                    deposit.id,

                "deposit_type":
                    deposit.deposit_type,

                "required_amount":
                    str(
                        required_amount
                    ),

                "paid_amount":
                    str(
                        paid_amount
                    ),

                "balance":
                    str(
                        required_amount
                        - paid_amount
                    ),

                "status":
                    deposit.status,

                "notes":
                    deposit.notes,
            }
        )

    # =====================================================
    # INVOICES
    # =====================================================

    invoice_queryset = (
        Invoice.objects
        .filter(
            lease=lease,
            organization=organization,
        )
        .order_by(
            "-created_at"
        )[:5]
    )

    invoices = []

    outstanding_balance = (
        Decimal(
            "0.00"
        )
    )

    for invoice in invoice_queryset:

        balance = (
            invoice.balance
            or Decimal(
                "0.00"
            )
        )

        outstanding_balance += (
            balance
        )

        invoices.append(
            {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "total_amount":
                    str(
                        invoice.total_amount
                    ),

                "paid_amount":
                    str(
                        invoice.paid_amount
                    ),

                "balance":
                    str(
                        invoice.balance
                    ),

                "status":
                    invoice.status,

                "due_date": (
                    str(
                        invoice.due_date
                    )
                    if getattr(
                        invoice,
                        "due_date",
                        None,
                    )
                    else None
                ),
            }
        )

    # =====================================================
    # LEASE DURATION
    # =====================================================

    duration_days = (
        (
            lease.end_date
            - lease.start_date
        ).days
        if (
            lease.start_date
            and lease.end_date
        )
        else None
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "lease": {
                "id":
                    lease.id,

                "lease_number":
                    lease.lease_number,

                "status":
                    lease.status,

                "start_date":
                    str(
                        lease.start_date
                    ),

                "end_date":
                    str(
                        lease.end_date
                    ),

                "duration_days":
                    duration_days,

                "monthly_rent":
                    str(
                        lease.monthly_rent
                    ),

                "deposit_amount":
                    str(
                        lease.deposit_amount
                    ),

                "billing_day":
                    lease.billing_day,

                "payment_frequency":
                    lease.payment_frequency,

                "grace_period_days":
                    lease.grace_period_days,

                "created_at": (
                    lease.created_at.isoformat()
                    if getattr(
                        lease,
                        "created_at",
                        None,
                    )
                    else None
                ),

                "updated_at": (
                    lease.updated_at.isoformat()
                    if getattr(
                        lease,
                        "updated_at",
                        None,
                    )
                    else None
                ),

                "created_by": (
                    {
                        "id":
                            lease.created_by.id,

                        "name": (
                            getattr(
                                lease.created_by,
                                "full_name",
                                None
                            )
                            or
                            lease.created_by.email
                        ),
                    }
                    if lease.created_by
                    else None
                ),

                "approved_by": (
                    {
                        "id":
                            lease.approved_by.id,

                        "name": (
                            getattr(
                                lease.approved_by,
                                "full_name",
                                None
                            )
                            or
                            lease.approved_by.email
                        ),
                    }
                    if lease.approved_by
                    else None
                ),
            },

            "property": (
                {
                    "id":
                        property_obj.id,

                    "name":
                        property_obj.name,

                    "property_code": (
                        getattr(
                            property_obj,
                            "property_code",
                            None
                        )
                        or getattr(
                            property_obj,
                            "code",
                            None
                        )
                    ),

                    "address":
                        property_obj.address,

                    "city":
                        property_obj.city,

                    "county":
                        property_obj.county,
                }
                if property_obj
                else None
            ),

            "unit": (
                {
                    "id":
                        unit.id,

                    "name":
                        unit.name,

                    "unit_code":
                        unit.unit_code,

                    "unit_type":
                        unit.unit_type,

                    "monthly_rent":
                        str(
                            unit.monthly_rent
                        ),

                    "status":
                        unit.status,

                    "building": (
                        {
                            "id":
                                unit.building.id,

                            "name":
                                unit.building.name,
                        }
                        if unit.building
                        else None
                    ),

                    "floor": (
                        {
                            "id":
                                unit.floor.id,

                            "name":
                                unit.floor.name,
                        }
                        if unit.floor
                        else None
                    ),
                }
                if unit
                else None
            ),

            "primary_tenant":
                primary_tenant,

            "tenants":
                tenants,

            "charges":
                charges,

            "deposits":
                deposits,

            "deposit_summary": {
                "required":
                    str(
                        total_deposit_required
                    ),

                "paid":
                    str(
                        total_deposit_paid
                    ),

                "balance":
                    str(
                        total_deposit_required
                        - total_deposit_paid
                    ),
            },

            "invoices":
                invoices,

            "financial_summary": {
                "monthly_rent":
                    str(
                        lease.monthly_rent
                    ),

                "outstanding":
                    str(
                        outstanding_balance
                    ),
            },
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_payment_leases(
    request,
    tenant_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # TENANT
    # =====================================================

    try:
        tenant = (
            Tenant.objects.get(
                id=tenant_id,
                organization=organization,
            )
        )

    except Tenant.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Tenant not found."
            },
            status=404,
        )

    # =====================================================
    # LEASES
    # =====================================================

    lease_links = (
        LeaseTenant.objects
        .filter(
            tenant=
                tenant,

            left_at__isnull=
                True,

            lease__status__in=[
                "draft",
                "pending_approval",
                "pending_signature",
                "active",
            ],
        )
        .select_related(
            "lease",
            "lease__unit",
            "lease__unit__property",
            "lease__unit__building",
            "lease__unit__floor",
        )
        .order_by(
            "-lease__created_at"
        )
    )

    leases = []

    for link in lease_links:
        lease = (
            link.lease
        )

        outstanding = (
            Invoice.objects
            .filter(
                organization=
                    organization,

                lease=
                    lease,

                tenant=
                    tenant,

                status__in=[
                    "unpaid",
                    "partially_paid",
                    "overdue",
                ],
            )
            .aggregate(
                total=
                    Sum(
                        "balance"
                    )
            )[
                "total"
            ]
            or Decimal(
                "0.00"
            )
        )

        leases.append(
            {
                "id":
                    lease.id,

                "lease_number":
                    lease.lease_number,

                "status":
                    lease.status,

                "monthly_rent":
                    str(
                        lease.monthly_rent
                    ),

                "outstanding_balance":
                    str(
                        outstanding
                    ),

                "start_date":
                    str(
                        lease.start_date
                    ),

                "end_date":
                    str(
                        lease.end_date
                    ),

                "property": {
                    "id":
                        lease.unit.property.id,

                    "name":
                        lease.unit.property.name,
                },

                "unit": {
                    "id":
                        lease.unit.id,

                    "name":
                        lease.unit.name,

                    "unit_code":
                        lease.unit.unit_code,

                    "building": (
                        lease.unit.building.name
                        if lease.unit.building
                        else None
                    ),

                    "floor": (
                        lease.unit.floor.name
                        if lease.unit.floor
                        else None
                    ),
                },
            }
        )

    return JsonResponse(
        {
            "tenant": {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "phone_number":
                    tenant.phone_number,

                "email":
                    tenant.email,
            },

            "count":
                len(
                    leases
                ),

            "leases":
                leases,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lease_payment_invoices(
    request,
    lease_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # LEASE
    # =====================================================

    try:
        lease = (
            Lease.objects
            .select_related(
                "unit",
                "unit__property",
            )
            .get(
                id=lease_id,
                organization=organization,
            )
        )

    except Lease.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Lease not found."
            },
            status=404,
        )

    # =====================================================
    # PRIMARY TENANT
    # =====================================================

    primary_link = (
        LeaseTenant.objects
        .filter(
            lease=lease,
            left_at__isnull=True,
        )
        .select_related(
            "tenant"
        )
        .order_by(
            "-is_primary"
        )
        .first()
    )

    if not primary_link:
        return JsonResponse(
            {
                "message":
                    "No tenant is linked to this lease."
            },
            status=400,
        )

    tenant = (
        primary_link.tenant
    )

    # =====================================================
    # PAYABLE INVOICES
    # =====================================================

    invoices_queryset = (
        Invoice.objects
        .filter(
            organization=organization,
            lease=lease,
            tenant=tenant,
            balance__gt=0,
        )
        .exclude(
            status__in=[
                "paid",
                "cancelled",
                "void",
            ]
        )
        .order_by(
            "due_date",
            "-created_at",
        )
    )

    invoices = []

    for invoice in invoices_queryset:

        invoices.append(
            {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "invoice_type_display": (
                    invoice.get_invoice_type_display()
                    if hasattr(
                        invoice,
                        "get_invoice_type_display"
                    )
                    else invoice.invoice_type
                ),

                "is_rent_invoice": (
                    invoice.invoice_type
                    == "rent"
                ),

                "total_amount":
                    str(
                        invoice.total_amount
                    ),

                "paid_amount":
                    str(
                        invoice.paid_amount
                    ),

                "balance":
                    str(
                        invoice.balance
                    ),

                "status":
                    invoice.status,

                "due_date": (
                    str(
                        invoice.due_date
                    )
                    if invoice.due_date
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "lease": {
                "id":
                    lease.id,

                "lease_number":
                    lease.lease_number,

                "monthly_rent":
                    str(
                        lease.monthly_rent
                    ),

                "property_name":
                    lease.unit.property.name,

                "unit_name":
                    lease.unit.name,

                "unit_code":
                    lease.unit.unit_code,
            },

            "tenant": {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,
            },

            "count":
                len(
                    invoices
                ),

            "invoices":
                invoices,
        },
        status=200,
    )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_details(
    request,
    payment_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

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

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .exists()
    )

    if not membership_exists:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # PAYMENT
    # =====================================================

    try:
        payment = (
            Payment.objects
            .select_related(
                "organization",
                "tenant",
                "received_by",
            )
            .get(
                id=
                    payment_id,

                organization=
                    organization,
            )
        )

    except Payment.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Payment not found."
            },
            status=404,
        )

    # =====================================================
    # METADATA
    # =====================================================

    metadata = (
        payment.metadata
        or {}
    )

    lease_id = (
        metadata.get(
            "lease_id"
        )
    )

    property_id = (
        metadata.get(
            "property_id"
        )
    )

    unit_id = (
        metadata.get(
            "unit_id"
        )
    )

    # =====================================================
    # LEASE
    # =====================================================

    lease = None

    if lease_id:
        lease = (
            Lease.objects
            .select_related(
                "unit",
                "unit__property",
                "unit__building",
                "unit__floor",
            )
            .filter(
                id=
                    lease_id,

                organization=
                    organization,
            )
            .first()
        )

    # =====================================================
    # ALLOCATION
    # =====================================================

    allocation = (
        PaymentAllocation.objects
        .select_related(
            "invoice"
        )
        .filter(
            payment=
                payment
        )
        .first()
    )

    # =====================================================
    # INVOICE
    # =====================================================

    invoice = (
        allocation.invoice
        if allocation
        else None
    )

    # =====================================================
    # RECEIPT
    # =====================================================

    receipt = (
        Receipt.objects
        .filter(
            payment=
                payment,

            organization=
                organization,
        )
        .first()
    )

    # =====================================================
    # PROPERTY / UNIT
    # =====================================================

    property_obj = None
    unit = None

    if lease:
        unit = (
            lease.unit
        )

        property_obj = (
            unit.property
            if unit
            else None
        )

    else:
        if unit_id:
            unit = (
                Unit.objects
                .select_related(
                    "property",
                    "building",
                    "floor",
                )
                .filter(
                    id=
                        unit_id
                )
                .first()
            )

        if unit:
            property_obj = (
                unit.property
            )

        elif property_id:
            property_obj = (
                Property.objects
                .filter(
                    id=
                        property_id,

                    organization=
                        organization,
                )
                .first()
            )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "payment": {
                "id":
                    payment.id,

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "provider":
                    payment.provider,

                "provider_display":
                    payment.get_provider_display(),

                "payment_method":
                    payment.payment_method,

                "payment_method_display":
                    payment.get_payment_method_display(),

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "status":
                    payment.status,

                "status_display":
                    payment.get_status_display(),

                "paid_at": (
                    payment.paid_at.isoformat()
                    if payment.paid_at
                    else None
                ),

                "created_at": (
                    payment.created_at.isoformat()
                    if payment.created_at
                    else None
                ),

                "updated_at": (
                    payment.updated_at.isoformat()
                    if payment.updated_at
                    else None
                ),

                "notes":
                    metadata.get(
                        "notes",
                        ""
                    ),

                "source":
                    metadata.get(
                        "source",
                        ""
                    ),
            },

            "tenant": (
                {
                    "id":
                        payment.tenant.id,

                    "full_name":
                        payment.tenant.full_name,

                    "email":
                        payment.tenant.email,

                    "phone_number":
                        payment.tenant.phone_number,
                }
                if payment.tenant
                else None
            ),

            "lease": (
                {
                    "id":
                        lease.id,

                    "lease_number":
                        lease.lease_number,

                    "status":
                        lease.status,

                    "start_date":
                        str(
                            lease.start_date
                        ),

                    "end_date":
                        str(
                            lease.end_date
                        ),

                    "monthly_rent":
                        str(
                            lease.monthly_rent
                        ),
                }
                if lease
                else None
            ),

            "property": (
                {
                    "id":
                        property_obj.id,

                    "name":
                        property_obj.name,

                    "address":
                        property_obj.address,

                    "city":
                        property_obj.city,

                    "county":
                        property_obj.county,
                }
                if property_obj
                else None
            ),

            "unit": (
                {
                    "id":
                        unit.id,

                    "name":
                        unit.name,

                    "unit_code":
                        unit.unit_code,

                    "status":
                        unit.status,

                    "building": (
                        unit.building.name
                        if unit.building
                        else None
                    ),

                    "floor": (
                        unit.floor.name
                        if unit.floor
                        else None
                    ),
                }
                if unit
                else None
            ),

            "invoice": (
                {
                    "id":
                        invoice.id,

                    "invoice_number":
                        invoice.invoice_number,

                    "invoice_type":
                        invoice.invoice_type,

                    "total_amount":
                        str(
                            invoice.total_amount
                        ),

                    "paid_amount":
                        str(
                            invoice.paid_amount
                        ),

                    "balance":
                        str(
                            invoice.balance
                        ),

                    "status":
                        invoice.status,

                    "due_date": (
                        str(
                            invoice.due_date
                        )
                        if invoice.due_date
                        else None
                    ),
                }
                if invoice
                else None
            ),

            "allocation": (
                {
                    "id":
                        allocation.id,

                    "allocated_amount":
                        str(
                            allocation
                            .allocated_amount
                        ),
                }
                if allocation
                else None
            ),

            "receipt": (
                {
                    "id":
                        receipt.id,

                    "receipt_number":
                        receipt.receipt_number,

                    "issued_at": (
                        receipt.issued_at.isoformat()
                        if receipt.issued_at
                        else None
                    ),

                    "file_url":
                        receipt.file_url,
                }
                if receipt
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
                        or payment.received_by.email
                    ),
                }
                if payment.received_by
                else None
            ),
        },
        status=200,
    )


