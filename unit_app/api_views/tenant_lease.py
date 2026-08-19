from .common_imports import *



def get_lease_tenant_context(
    user,
    organization_id,
):
    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Organization not found."
                },
                status=404,
            ),
        )

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
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "You do not belong to this organization."
                },
                status=403,
            ),
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

    if (
        "tenant"
        not in role_codes
    ):
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Tenant access is required."
                },
                status=403,
            ),
        )

    try:
        tenant = (
            Tenant.objects.get(
                organization=
                    organization,

                user=
                    user,

                status=
                    "active",
            )
        )

    except Tenant.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Tenant profile not found."
                },
                status=404,
            ),
        )

    return (
        organization,
        tenant,
        None,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_lease(request):
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

    (
        organization,
        tenant,
        error_response,
    ) = get_lease_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    # =====================================================
    # CURRENT LEASE
    # =====================================================

    lease_tenant = (
        LeaseTenant.objects
        .filter(
            tenant=tenant,

            lease__organization=
                organization,

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
        .first()
    )

    if not lease_tenant:
        return JsonResponse(
            {
                "lease":
                    None,

                "tenant": {
                    "id":
                        tenant.id,

                    "full_name":
                        tenant.full_name,
                },
            },
            status=200,
        )

    lease = (
        lease_tenant.lease
    )

    unit = (
        lease.unit
    )

    property_obj = (
        unit.property
    )

    # =====================================================
    # CHARGES
    # =====================================================

    charges = []

    try:
        for charge in (
            lease.charges
            .all()
            .order_by(
                "id"
            )
        ):
            charges.append(
                {
                    "id":
                        charge.id,

                    "name": (
                        getattr(
                            charge,
                            "name",
                            None
                        )
                        or
                        getattr(
                            charge,
                            "charge_name",
                            None
                        )
                        or
                        getattr(
                            charge,
                            "charge_type",
                            "Charge"
                        )
                    ),

                    "amount":
                        str(
                            charge.amount
                        ),

                    "frequency":
                        getattr(
                            charge,
                            "frequency",
                            "one_time",
                        ),
                }
            )

    except Exception:
        charges = []

    # =====================================================
    # DEPOSITS
    # =====================================================

    deposits = []

    try:
        for deposit in (
            lease.deposits
            .all()
            .order_by(
                "-id"
            )
        ):
            deposits.append(
                {
                    "id":
                        deposit.id,

                    "deposit_type":
                        getattr(
                            deposit,
                            "deposit_type",
                            "security",
                        ),

                    "deposit_type_label": (
                        deposit
                        .get_deposit_type_display()
                        if hasattr(
                            deposit,
                            "get_deposit_type_display"
                        )
                        else getattr(
                            deposit,
                            "deposit_type",
                            "Deposit",
                        )
                    ),

                    "amount":
                        str(
                            deposit.amount
                        ),

                    "status":
                        getattr(
                            deposit,
                            "status",
                            "held",
                        ),
                }
            )

    except Exception:
        deposits = []

    # =====================================================
    # RENEWAL
    # =====================================================

    renewal_data = None

    try:
        renewal = (
            lease.renewals
            .order_by(
                "-created_at"
            )
            .first()
        )

        if renewal:
            renewal_data = {
                "id":
                    renewal.id,

                "new_start_date": (
                    str(
                        renewal.new_start_date
                    )
                    if getattr(
                        renewal,
                        "new_start_date",
                        None,
                    )
                    else None
                ),

                "new_end_date": (
                    str(
                        renewal.new_end_date
                    )
                    if getattr(
                        renewal,
                        "new_end_date",
                        None,
                    )
                    else None
                ),

                "new_monthly_rent": (
                    str(
                        renewal.new_monthly_rent
                    )
                    if getattr(
                        renewal,
                        "new_monthly_rent",
                        None,
                    )
                    is not None
                    else None
                ),

                "status":
                    getattr(
                        renewal,
                        "status",
                        None,
                    ),
            }

    except Exception:
        renewal_data = None

    # =====================================================
    # TERMINATION
    # =====================================================

    termination_data = None

    try:
        termination = (
            lease.terminations
            .order_by(
                "-created_at"
            )
            .first()
        )

        if termination:
            termination_data = {
                "id":
                    termination.id,

                "termination_date": (
                    str(
                        termination
                        .termination_date
                    )
                    if getattr(
                        termination,
                        "termination_date",
                        None,
                    )
                    else None
                ),

                "reason":
                    getattr(
                        termination,
                        "reason",
                        None,
                    ),
            }

    except Exception:
        termination_data = None

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "tenant": {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "tenant_role":
                    lease_tenant.tenant_role,

                "tenant_role_label": (
                    lease_tenant
                    .get_tenant_role_display()
                    if hasattr(
                        lease_tenant,
                        "get_tenant_role_display",
                    )
                    else lease_tenant
                    .tenant_role
                ),

                "is_primary":
                    lease_tenant.is_primary,
            },

            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,
            },

            "unit": {
                "id":
                    unit.id,

                "name":
                    unit.name,

                "unit_code":
                    unit.unit_code,

                "unit_type":
                    unit.unit_type,

                "building_name":
                    unit.building.name,

                "floor_name":
                    unit.floor.name,
            },

            "lease": {
                "id":
                    lease.id,

                "lease_number":
                    lease.lease_number,

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

                "payment_frequency_label": (
                    lease
                    .get_payment_frequency_display()
                    if hasattr(
                        lease,
                        "get_payment_frequency_display",
                    )
                    else lease
                    .payment_frequency
                ),

                "grace_period_days":
                    lease.grace_period_days,

                "status":
                    lease.status,

                "signed_at": (
                    lease.signed_at
                    .isoformat()
                    if lease.signed_at
                    else None
                ),

                "terminated_at": (
                    lease.terminated_at
                    .isoformat()
                    if lease.terminated_at
                    else None
                ),

                "created_at":
                    lease.created_at
                    .isoformat(),

                "updated_at":
                    lease.updated_at
                    .isoformat(),
            },

            "charges":
                charges,

            "deposits":
                deposits,

            "renewal":
                renewal_data,

            "termination":
                termination_data,
        },
        status=200,
    )