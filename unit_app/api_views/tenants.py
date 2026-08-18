from django.contrib.auth.password_validation import (
    validate_password,
)

from django.core.exceptions import (
    ValidationError,
)

from django.shortcuts import render

from .common_imports import *
from .helper import *
User = get_user_model()


def can_manage_tenants(
    user,
    organization,
):
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
        return False

    codes = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    return bool(
        codes.intersection({
            "organization_owner",
            "organization_admin",
            "property_manager",
            "leasing_agent",
        })
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_properties(request):
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

    if not can_manage_tenants(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
            },
            status=403,
        )

    properties = (
        Property.objects
        .filter(
            organization=organization,
            status="active",
        )
        .order_by(
            "name"
        )
    )

    results = []

    for property_obj in properties:

        available_units = (
            Unit.objects
            .filter(
                property=property_obj,
                status="available",
            )
            .count()
        )

        results.append(
            {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,

                "property_type":
                    property_obj.property_type,

                "address":
                    property_obj.address,

                "city":
                    property_obj.city,

                "county":
                    property_obj.county,

                "location": (
                    f"{property_obj.address}, "
                    f"{property_obj.city}"
                ),

                "available_units":
                    available_units,
            }
        )

    return JsonResponse(
        {
            "properties":
                results,

            "count":
                len(results),
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_property_units(request):
    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    property_id = (
        request.GET.get(
            "property_id"
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

    if not property_id:
        return JsonResponse(
            {
                "message":
                    "property_id is required."
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

    if not can_manage_tenants(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
            },
            status=403,
        )

    try:
        property_obj = (
            Property.objects.get(
                id=property_id,
                organization=organization,
                status="active",
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

    units = (
        Unit.objects
        .filter(
            property=property_obj,
            status="available",
        )
        .select_related(
            "building",
            "floor",
        )
        .order_by(
            "building__name",
            "floor__floor_number",
            "unit_code",
        )
    )

    return JsonResponse(
        {
            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,
            },

            "units": [
                {
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

                    "bedrooms":
                        unit.bedrooms,

                    "bathrooms":
                        unit.bathrooms,

                    "monthly_rent":
                        str(
                            unit.monthly_rent
                        ),

                    "deposit_amount":
                        str(
                            unit.deposit_amount
                        ),

                    "service_charge": (
                        str(
                            unit.service_charge
                        )
                        if unit.service_charge
                        is not None
                        else None
                    ),

                    "status":
                        unit.status,
                }
                for unit
                in units
            ],
        },
        status=200,
    )




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_and_assign_tenant(request):
    data = request.data
    manager = request.user

    # =====================================================
    # INPUT
    # =====================================================

    organization_id = (
        data.get(
            "organization_id"
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

    tenant_type = str(
        data.get(
            "tenant_type",
            "individual"
        )
    ).strip()

    full_name = str(
        data.get(
            "full_name",
            ""
        )
    ).strip()

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip().lower()

    phone_number = str(
        data.get(
            "phone_number",
            ""
        )
    ).strip()

    national_id = str(
        data.get(
            "national_id_number",
            ""
        )
        or ""
    ).strip()

    kra_pin = str(
        data.get(
            "kra_pin",
            ""
        )
        or ""
    ).strip().upper()

    occupation = str(
        data.get(
            "occupation",
            ""
        )
        or ""
    ).strip()

    employer = str(
        data.get(
            "employer",
            ""
        )
        or ""
    ).strip()

    move_in_date_raw = (
        data.get(
            "move_in_date"
        )
    )

    notes = str(
        data.get(
            "notes",
            ""
        )
        or ""
    ).strip()

    emergency_contact = (
        data.get(
            "emergency_contact"
        )
    )

    # =====================================================
    # REQUIRED
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "Organization is required."
            },
            status=400,
        )

    if not property_id:
        return JsonResponse(
            {
                "message":
                    "Property is required."
            },
            status=400,
        )

    if not unit_id:
        return JsonResponse(
            {
                "message":
                    "Unit is required."
            },
            status=400,
        )

    if not full_name:
        return JsonResponse(
            {
                "message":
                    "Tenant name is required."
            },
            status=400,
        )

    if not email:
        return JsonResponse(
            {
                "message":
                    "Tenant email is required."
            },
            status=400,
        )

    if not phone_number:
        return JsonResponse(
            {
                "message":
                    "Tenant phone number is required."
            },
            status=400,
        )

    if tenant_type not in {
        "individual",
        "company",
        "group",
    }:
        return JsonResponse(
            {
                "message":
                    "Invalid tenant type."
            },
            status=400,
        )

    # =====================================================
    # MOVE IN DATE
    # =====================================================

    move_in_date = None

    if move_in_date_raw:
        move_in_date = parse_date(
            str(
                move_in_date_raw
            )
        )

        if not move_in_date:
            return JsonResponse(
                {
                    "message":
                        "Move-in date must use YYYY-MM-DD."
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

    if not can_manage_tenants(
        manager,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to add tenants."
            },
            status=403,
        )

    # =====================================================
    # PROPERTY
    # =====================================================

    try:
        property_obj = (
            Property.objects.get(
                id=property_id,
                organization=organization,
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
    # EXISTING EMAIL
    # =====================================================

    existing_tenant = (
        Tenant.objects
        .filter(
            organization=organization,
            email__iexact=email,
        )
        .first()
    )

    if existing_tenant:
        return JsonResponse(
            {
                "message":
                    "A tenant with this email already exists in this organization."
            },
            status=400,
        )

    # =====================================================
    # NAMES
    # =====================================================

    name_parts = (
        full_name.split()
    )

    first_name = (
        name_parts[0]
        if name_parts
        else ""
    )

    last_name = (
        name_parts[-1]
        if len(name_parts) > 1
        else ""
    )

    middle_name = (
        " ".join(
            name_parts[1:-1]
        )
        if len(name_parts) > 2
        else ""
    )

    # =====================================================
    # CREATE
    # =====================================================

    try:
        with transaction.atomic():

            # =================================================
            # LOCK UNIT
            # =================================================

            try:
                unit = (
                    Unit.objects
                    .select_for_update()
                    .select_related(
                        "building",
                        "floor",
                    )
                    .get(
                        id=unit_id,
                        property=property_obj,
                    )
                )

            except Unit.DoesNotExist:
                return JsonResponse(
                    {
                        "message":
                            "Unit does not belong to this property."
                    },
                    status=404,
                )

            if unit.status != "available":
                return JsonResponse(
                    {
                        "message":
                            "This unit is no longer available."
                    },
                    status=400,
                )

            if (
                TenantUnitAssignment.objects
                .filter(
                    unit=unit,
                    is_active=True,
                )
                .exists()
            ):
                return JsonResponse(
                    {
                        "message":
                            "This unit is already assigned."
                    },
                    status=400,
                )

            # =================================================
            # USER
            # =================================================

            user_account = (
                User.objects
                .filter(
                    email__iexact=email
                )
                .first()
            )

            created_user = False

            if not user_account:

                # username is unique in your User model,
                # therefore email works well here.

                user_account = User(
                    username=email,
                    email=email,
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    phone_number=phone_number,

                    email_verified=False,
                    phone_verified=False,

                    is_verified=False,
                    status="pending",

                    is_active=False,
                )

                # No password until tenant activates account.
                user_account.set_unusable_password()

                user_account.save()

                created_user = True

            # =================================================
            # TENANT ROLE
            # =================================================

            tenant_role, _ = (
                Role.objects
                .get_or_create(
                    organization=
                        organization,

                    code=
                        "tenant",

                    defaults={
                        "name":
                            "tenant",

                        "description":
                            "Tenant access to UNIT.",

                        "scope":
                            "tenant",

                        "is_system_role":
                            True,

                        "is_active":
                            True,
                    },
                )
            )

            # =================================================
            # MEMBERSHIP
            # =================================================

            membership = (
                OrganizationMembership.objects
                .filter(
                    user=
                        user_account,

                    organization=
                        organization,
                )
                .first()
            )

            if not membership:

                employee_number = (
                    f"TEN-"
                    f"{organization.id}-"
                    f"{uuid.uuid4().hex[:8].upper()}"
                )

                membership = (
                    OrganizationMembership.objects.create(
                        user=
                            user_account,

                        organization=
                            organization,

                        employee_number=
                            employee_number,

                        job_title=
                            "Tenant",

                        invited_by=
                            manager,

                        is_active=
                            True,
                    )
                )

            membership.roles.add(
                tenant_role
            )

            # =================================================
            # TENANT PROFILE
            # =================================================

            tenant = (
                Tenant.objects.create(
                    organization=
                        organization,

                    user=
                        user_account,

                    tenant_type=
                        tenant_type,

                    full_name=
                        full_name,

                    email=
                        email,

                    phone_number=
                        phone_number,

                    national_id_number=(
                        national_id
                        or None
                    ),

                    kra_pin=(
                        kra_pin
                        or None
                    ),

                    occupation=(
                        occupation
                        or None
                    ),

                    employer=(
                        employer
                        or None
                    ),

                    status=
                        "active",
                )
            )

            # =================================================
            # EMERGENCY CONTACT
            # =================================================

            if emergency_contact:

                contact_name = str(
                    emergency_contact.get(
                        "name",
                        ""
                    )
                ).strip()

                relationship = str(
                    emergency_contact.get(
                        "relationship",
                        ""
                    )
                ).strip()

                contact_phone = str(
                    emergency_contact.get(
                        "phone_number",
                        ""
                    )
                ).strip()

                contact_email = str(
                    emergency_contact.get(
                        "email",
                        ""
                    )
                    or ""
                ).strip().lower()

                if (
                    contact_name
                    and relationship
                    and contact_phone
                ):
                    TenantEmergencyContact.objects.create(
                        tenant=
                            tenant,

                        name=
                            contact_name,

                        relationship=
                            relationship,

                        phone_number=
                            contact_phone,

                        email=(
                            contact_email
                            or None
                        ),
                    )

            # =================================================
            # ASSIGN UNIT
            # =================================================

            assignment = (
                TenantUnitAssignment.objects.create(
                    organization=
                        organization,

                    tenant=
                        tenant,

                    property=
                        property_obj,

                    unit=
                        unit,

                    assigned_by=
                        manager,

                    move_in_date=
                        move_in_date,

                    notes=
                        notes,

                    is_active=
                        True,
                )
            )

            # =================================================
            # OCCUPIED
            # =================================================

            unit.status = (
                "occupied"
            )

            unit.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            # =================================================
            # ACTIVATION TOKEN
            # =================================================

            activation_token = (
                uuid.uuid4().hex
            )

            user_account.reset_token = (
                activation_token
            )

            user_account.save(
                update_fields=[
                    "reset_token"
                ]
            )

        # =====================================================
        # EMAIL AFTER DB COMMIT
        # =====================================================

        activation_link = (
            "http://192.168.100.12:8000"
            "/tenant/activate/"
            f"?token={activation_token}"
        )

        try:
            send_email(
                email,

                f"Activate your UNIT account - {organization.name}",

                f"""
                <div style="
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: auto;
                    padding: 24px;
                ">

                    <h2>
                        Welcome to UNIT
                    </h2>

                    <p>
                        Hello {first_name},
                    </p>

                    <p>
                        You have been added as a tenant
                        at
                        <strong>
                            {organization.name}
                        </strong>.
                    </p>

                    <p>
                        Property:
                        <strong>
                            {property_obj.name}
                        </strong>
                    </p>

                    <p>
                        Unit:
                        <strong>
                            {unit.name}
                        </strong>
                    </p>

                    <p>
                        Click below to create your
                        password and activate your
                        UNIT account.
                    </p>

                    <a
                        href="{activation_link}"
                        style="
                            background: #0B6B36;
                            color: #ffffff;
                            padding: 12px 22px;
                            border-radius: 8px;
                            text-decoration: none;
                            display: inline-block;
                        "
                    >
                        Activate Account
                    </a>

                    <p style="
                        color: #64748b;
                        margin-top: 24px;
                    ">
                        After activation, open the
                        UNIT mobile app and sign in
                        using {email}.
                    </p>

                </div>
                """,
            )

        except Exception as email_error:
            print(
                "TENANT INVITATION EMAIL ERROR:",
                str(email_error),
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        return JsonResponse(
            {
                "message":
                    "Tenant created, assigned and invited successfully.",

                "tenant": {
                    "id":
                        tenant.id,

                    "full_name":
                        tenant.full_name,

                    "email":
                        tenant.email,

                    "phone_number":
                        tenant.phone_number,

                    "tenant_type":
                        tenant.tenant_type,
                },

                "user": {
                    "id":
                        user_account.id,

                    "email":
                        user_account.email,

                    "account_active":
                        user_account.is_active,

                    "invitation_sent":
                        created_user,
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

                    "building":
                        unit.building.name,

                    "floor":
                        unit.floor.name,

                    "status":
                        unit.status,
                },

                "assignment": {
                    "id":
                        assignment.id,

                    "move_in_date": (
                        str(
                            assignment.move_in_date
                        )
                        if assignment.move_in_date
                        else None
                    ),
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE TENANT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create tenant.",

                "error":
                    str(error),
            },
            status=500,
        )





def activate_tenant_web(request):
    token = str(
        request.GET.get(
            "token",
            ""
        )
        or
        request.POST.get(
            "token",
            ""
        )
    ).strip()

    if not token:
        return render(
            request,
            "tenants/invalid_activation.html",
        )

    user = (
        User.objects
        .filter(
            reset_token=token
        )
        .first()
    )

    if not user:
        return render(
            request,
            "tenants/invalid_activation.html",
        )

    tenant = (
        Tenant.objects
        .filter(
            user=user
        )
        .select_related(
            "organization"
        )
        .first()
    )

    if not tenant:
        return render(
            request,
            "tenants/invalid_activation.html",
        )

    assignment = (
        TenantUnitAssignment.objects
        .filter(
            tenant=tenant,
            is_active=True,
        )
        .select_related(
            "property",
            "unit",
        )
        .first()
    )

    if request.method == "GET":
        return render(
            request,
            "tenants/activate.html",
            {
                "token":
                    token,

                "tenant":
                    tenant,

                "assignment":
                    assignment,
            },
        )

    password = (
        request.POST.get(
            "password"
        )
    )

    confirm_password = (
        request.POST.get(
            "confirm_password"
        )
    )

    if not password:
        return render(
            request,
            "tenants/activate.html",
            {
                "token":
                    token,

                "tenant":
                    tenant,

                "assignment":
                    assignment,

                "error":
                    "Password is required.",
            },
        )

    if password != confirm_password:
        return render(
            request,
            "tenants/activate.html",
            {
                "token":
                    token,

                "tenant":
                    tenant,

                "assignment":
                    assignment,

                "error":
                    "Passwords do not match.",
            },
        )

    try:
        validate_password(
            password,
            user=user,
        )

    except ValidationError as error:
        return render(
            request,
            "tenants/activate.html",
            {
                "token":
                    token,

                "tenant":
                    tenant,

                "assignment":
                    assignment,

                "error":
                    " ".join(
                        error.messages
                    ),
            },
        )

    user.set_password(
        password
    )

    user.is_active = True
    user.status = "active"
    user.email_verified = True
    user.is_verified = True

    # Token cannot be reused.
    user.reset_token = None

    user.save()

    return render(
        request,
        "tenants/activation_success.html",
        {
            "tenant":
                tenant,

            "assignment":
                assignment,
        },
    )




# APIS FOR TENANTS SCREENS
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_dashboard(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # ORGANIZATION REQUIRED
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
                    "You do not belong to this organization."
            },
            status=403,
        )

    # =====================================================
    # CHECK TENANT ROLE
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

    if (
        "tenant"
        not in role_codes
    ):
        return JsonResponse(
            {
                "message":
                    "Tenant access is required."
            },
            status=403,
        )

    # =====================================================
    # TENANT PROFILE
    # =====================================================

    try:
        tenant = (
            Tenant.objects.get(
                user=user,
                organization=organization,
                status="active",
            )
        )

    except Tenant.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Tenant profile not found."
            },
            status=404,
        )

    # =====================================================
    # CURRENT UNIT ASSIGNMENT
    # =====================================================

    assignment = (
        TenantUnitAssignment.objects
        .filter(
            tenant=tenant,
            organization=organization,
            is_active=True,
        )
        .select_related(
            "property",
            "unit",
            "unit__building",
            "unit__floor",
        )
        .order_by(
            "-assigned_at"
        )
        .first()
    )

    # =====================================================
    # ASSIGNMENT RESPONSE
    # =====================================================

    assignment_data = None

    if assignment:
        property_obj = (
            assignment.property
        )

        unit = (
            assignment.unit
        )

        location_parts = [
            property_obj.address,
            property_obj.city,
            property_obj.county,
        ]

        location = ", ".join(
            [
                str(item)
                for item
                in location_parts
                if item
            ]
        )

        assignment_data = {
            "id":
                assignment.id,

            "move_in_date": (
                str(
                    assignment.move_in_date
                )
                if assignment.move_in_date
                else None
            ),

            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,

                "location":
                    location,
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

                "bedrooms":
                    unit.bedrooms,

                "bathrooms":
                    unit.bathrooms,

                "monthly_rent":
                    str(
                        unit.monthly_rent
                    ),

                "deposit_amount":
                    str(
                        unit.deposit_amount
                    ),

                "service_charge": (
                    str(
                        unit.service_charge
                    )
                    if unit.service_charge
                    is not None
                    else None
                ),

                "status":
                    unit.status,
            },
        }

    # =====================================================
    # INVOICES
    # =====================================================

    invoices = (
        Invoice.objects
        .filter(
            organization=organization,
            tenant=tenant,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
    )

    # =====================================================
    # TOTAL OUTSTANDING
    # =====================================================

    outstanding_balance = (
        invoices
        .filter(
            status__in=[
                "issued",
                "partially_paid",
                "overdue",
            ]
        )
        .aggregate(
            total=Sum(
                "balance"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # NEXT BILL
    # =====================================================

    today = (
        timezone.now().date()
    )

    next_invoice = (
        invoices
        .filter(
            status__in=[
                "issued",
                "partially_paid",
                "overdue",
            ],

            balance__gt=0,
        )
        .order_by(
            "due_date"
        )
        .first()
    )

    next_due_date = (
        next_invoice.due_date
        if next_invoice
        else None
    )

    next_due_amount = (
        next_invoice.balance
        if next_invoice
        else Decimal("0.00")
    )

    # =====================================================
    # THIS MONTH PAID
    # =====================================================

    current_month = (
        timezone.now()
    )

    paid_this_month = (
        Payment.objects
        .filter(
            organization=organization,
            tenant=tenant,
            status="completed",
            paid_at__year=
                current_month.year,
            paid_at__month=
                current_month.month,
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # RECENT INVOICES
    # =====================================================

    recent_invoice_objects = (
        invoices
        .order_by(
            "-issue_date",
            "-created_at",
        )[:5]
    )

    recent_invoices = []

    for invoice in (
        recent_invoice_objects
    ):
        title = (
            invoice
            .get_invoice_type_display()
        )

        recent_invoices.append(
            {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "title":
                    title,

                "issue_date":
                    str(
                        invoice.issue_date
                    ),

                "due_date":
                    str(
                        invoice.due_date
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
            }
        )

    # =====================================================
    # PAYMENTS
    # =====================================================

    payments = (
        Payment.objects
        .filter(
            organization=organization,
            tenant=tenant,
            status="completed",
        )
        .order_by(
            "-paid_at",
            "-created_at",
        )[:5]
    )

    recent_payments = [
        {
            "id":
                payment.id,

            "reference":
                payment.payment_reference,

            "provider":
                payment.get_provider_display(),

            "payment_method":
                payment.get_payment_method_display(),

            "amount":
                str(
                    payment.amount
                ),

            "currency":
                payment.currency,

            "status":
                payment.status,

            "paid_at": (
                payment.paid_at
                .isoformat()
                if payment.paid_at
                else None
            ),
        }

        for payment
        in payments
    ]

    # =====================================================
    # CURRENT LEASE
    #
    # A tenant may have a unit assignment before a formal
    # lease has been created. Therefore lease can be null.
    # =====================================================

    lease_tenant = (
        LeaseTenant.objects
        .filter(
            tenant=tenant,

            lease__organization=
                organization,

            lease__status__in=[
                "pending_approval",
                "pending_signature",
                "active",
            ],
        )
        .select_related(
            "lease",
            "lease__unit",
        )
        .order_by(
            "-lease__created_at"
        )
        .first()
    )

    lease_data = None

    if lease_tenant:
        lease = (
            lease_tenant.lease
        )

        lease_data = {
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

            "status":
                lease.status,

            "signed_at": (
                lease.signed_at
                .isoformat()
                if lease.signed_at
                else None
            ),
        }

    # =====================================================
    # MAINTENANCE
    #
    # Only tickets submitted by this logged-in tenant
    # should appear as "your requests".
    # =====================================================

    maintenance_tickets = (
        MaintenanceTicket.objects
        .filter(
            organization=organization,
            reported_by=user,
            source="tenant",
        )
    )

    if assignment:
        maintenance_tickets = (
            maintenance_tickets
            .filter(
                unit=assignment.unit
            )
        )

    open_maintenance = (
        maintenance_tickets
        .exclude(
            status__in=[
                "completed",
                "closed",
                "cancelled",
            ]
        )
        .count()
    )

    completed_maintenance = (
        maintenance_tickets
        .filter(
            status__in=[
                "completed",
                "closed",
            ]
        )
        .count()
    )

    latest_maintenance = (
        maintenance_tickets
        .order_by(
            "-created_at"
        )[:3]
    )

    maintenance_data = [
        {
            "id":
                ticket.id,

            "ticket_number":
                ticket.ticket_number,

            "title":
                ticket.title,

            "category":
                ticket.category,

            "priority":
                ticket.priority,

            "status":
                ticket.status,

            "created_at":
                ticket.created_at
                .isoformat(),
        }
        for ticket
        in latest_maintenance
    ]

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
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "user": {
                "id":
                    user.id,

                "email":
                    user.email,

                "first_name":
                    user.first_name,
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
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

                "tenant_type":
                    tenant.tenant_type,

                "status":
                    tenant.status,
            },

            "assignment":
                assignment_data,

            "rent": {
                "outstanding_balance":
                    str(
                        outstanding_balance
                    ),

                "next_due_date": (
                    str(
                        next_due_date
                    )
                    if next_due_date
                    else None
                ),

                "next_due_amount":
                    str(
                        next_due_amount
                    ),

                "paid_this_month":
                    str(
                        paid_this_month
                    ),
            },

            "lease":
                lease_data,

            "maintenance": {
                "open":
                    open_maintenance,

                "completed":
                    completed_maintenance,

                "recent":
                    maintenance_data,
            },

            "recent_invoices":
                recent_invoices,

            "recent_payments":
                recent_payments,

            "unread_notifications":
                unread_notifications,
        },
        status=200,
    )


# helper
def get_tenant_context(
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

    if "tenant" not in role_codes:
        return (
            None,
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

                user=user,

                status="active",
            )
        )

    except Tenant.DoesNotExist:
        return (
            None,
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

    assignment = (
        TenantUnitAssignment.objects
        .filter(
            organization=
                organization,

            tenant=
                tenant,

            is_active=True,
        )
        .select_related(
            "property",
            "unit",
            "unit__building",
            "unit__floor",
        )
        .order_by(
            "-assigned_at"
        )
        .first()
    )

    return (
        organization,
        tenant,
        assignment,
        None,
    )
# end of helper

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_maintenance_list(request):
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
        assignment,
        error_response,
    ) = get_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    tickets = (
        MaintenanceTicket.objects
        .filter(
            organization=
                organization,

            reported_by=
                request.user,

            source=
                "tenant",
        )
        .select_related(
            "property",
            "unit",
            "building",
            "assigned_to",
        )
        .order_by(
            "-created_at"
        )
    )

    # If the tenant has a current assignment,
    # restrict requests to that current unit.
    if assignment:
        tickets = (
            tickets.filter(
                unit=
                    assignment.unit
            )
        )

    open_count = (
        tickets
        .filter(
            status="open"
        )
        .count()
    )

    in_progress_count = (
        tickets
        .filter(
            status__in=[
                "under_review",
                "approved",
                "published_to_kaskazi",
                "assigned",
                "in_progress",
                "awaiting_approval",
            ]
        )
        .count()
    )

    completed_count = (
        tickets
        .filter(
            status__in=[
                "completed",
                "closed",
            ]
        )
        .count()
    )

    results = []

    for ticket in tickets:
        results.append(
            {
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

                "category_label":
                    ticket.get_category_display(),

                "priority":
                    ticket.priority,

                "priority_label":
                    ticket.get_priority_display(),

                "status":
                    ticket.status,

                "status_label":
                    ticket.get_status_display(),

                "property_id":
                    ticket.property_id,

                "property_name":
                    (
                        ticket.property.name
                        if ticket.property
                        else None
                    ),

                "building_id":
                    ticket.building_id,

                "building_name":
                    (
                        ticket.building.name
                        if ticket.building
                        else None
                    ),

                "unit_id":
                    ticket.unit_id,

                "unit_name":
                    (
                        ticket.unit.name
                        if ticket.unit
                        else None
                    ),

                "unit_code":
                    (
                        ticket.unit.unit_code
                        if ticket.unit
                        else None
                    ),

                "assigned_to": (
                    {
                        "id":
                            ticket.assigned_to.id,

                        "name":
                            ticket.assigned_to
                            .get_full_name(),
                    }
                    if ticket.assigned_to
                    else None
                ),

                "preferred_date": (
                    str(
                        ticket.preferred_date
                    )
                    if ticket.preferred_date
                    else None
                ),

                "scheduled_at": (
                    ticket.scheduled_at
                    .isoformat()
                    if ticket.scheduled_at
                    else None
                ),

                "completed_at": (
                    ticket.completed_at
                    .isoformat()
                    if ticket.completed_at
                    else None
                ),

                "created_at":
                    ticket.created_at
                    .isoformat(),

                "updated_at":
                    ticket.updated_at
                    .isoformat(),
            }
        )

    return JsonResponse(
        {
            "summary": {
                "total":
                    tickets.count(),

                "open":
                    open_count,

                "in_progress":
                    in_progress_count,

                "completed":
                    completed_count,
            },

            "assignment": (
                {
                    "property": {
                        "id":
                            assignment.property.id,

                        "name":
                            assignment.property.name,
                    },

                    "unit": {
                        "id":
                            assignment.unit.id,

                        "name":
                            assignment.unit.name,

                        "unit_code":
                            assignment.unit.unit_code,
                    },
                }
                if assignment
                else None
            ),

            "tickets":
                results,
        },
        status=200,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_maintenance_detail(
    request,
    ticket_id,
):
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
        assignment,
        error_response,
    ) = get_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        ticket = (
            MaintenanceTicket.objects
            .select_related(
                "property",
                "building",
                "unit",
                "lease",
                "assigned_to",
            )
            .prefetch_related(
                "media",
                "comments",
                "comments__user",
                "status_history",
            )
            .get(
                id=ticket_id,

                organization=
                    organization,

                reported_by=
                    request.user,

                source=
                    "tenant",
            )
        )

    except MaintenanceTicket.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Maintenance request not found."
            },
            status=404,
        )

    # Current assignment protection
    if (
        assignment
        and ticket.unit_id
        and ticket.unit_id
        != assignment.unit_id
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have access to this request."
            },
            status=403,
        )

    media = [
        {
            "id":
                item.id,

            "file_url":
                item.file_url,

            "file_type":
                item.file_type,

            "media_stage":
                item.media_stage,

            "caption":
                item.caption,

            "created_at":
                item.created_at
                .isoformat(),
        }
        for item
        in ticket.media.all()
    ]

    # Only tenant-visible comments.
    comments = [
        {
            "id":
                comment.id,

            "comment":
                comment.comment,

            "user": (
                comment.user
                .get_full_name()
                or comment.user.email
            ),

            "created_at":
                comment.created_at
                .isoformat(),
        }
        for comment
        in ticket.comments
        .filter(
            is_internal=False
        )
        .order_by(
            "created_at"
        )
    ]

    history = [
        {
            "id":
                item.id,

            "previous_status":
                item.previous_status,

            "new_status":
                item.new_status,

            "notes":
                item.notes,

            "created_at":
                item.created_at
                .isoformat(),
        }
        for item
        in ticket.status_history
        .order_by(
            "created_at"
        )
    ]

    return JsonResponse(
        {
            "ticket": {
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

                "category_label":
                    ticket.get_category_display(),

                "priority":
                    ticket.priority,

                "priority_label":
                    ticket.get_priority_display(),

                "status":
                    ticket.status,

                "status_label":
                    ticket.get_status_display(),

                "preferred_date": (
                    str(
                        ticket.preferred_date
                    )
                    if ticket.preferred_date
                    else None
                ),

                "scheduled_at": (
                    ticket.scheduled_at
                    .isoformat()
                    if ticket.scheduled_at
                    else None
                ),

                "completed_at": (
                    ticket.completed_at
                    .isoformat()
                    if ticket.completed_at
                    else None
                ),

                "property": {
                    "id":
                        ticket.property.id,

                    "name":
                        ticket.property.name,
                },

                "building": (
                    {
                        "id":
                            ticket.building.id,

                        "name":
                            ticket.building.name,
                    }
                    if ticket.building
                    else None
                ),

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

                "assigned_to": (
                    {
                        "id":
                            ticket.assigned_to.id,

                        "name":
                            ticket.assigned_to
                            .get_full_name(),
                    }
                    if ticket.assigned_to
                    else None
                ),

                "created_at":
                    ticket.created_at
                    .isoformat(),

                "updated_at":
                    ticket.updated_at
                    .isoformat(),
            },

            "media":
                media,

            "comments":
                comments,

            "status_history":
                history,
        },
        status=200,
    )



# END OF APIS FOR TENANTS SCREENS




