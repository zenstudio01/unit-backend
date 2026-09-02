from .common_imports import *
from .helper import *



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_organization(request):

    user = request.user
    data = request.data

    # =====================================================
    # READ DATA
    # =====================================================

    name = str(
        data.get(
            "name",
            ""
        )
        or ""
    ).strip()

    organization_type = str(
        data.get(
            "organization_type",
            ""
        )
        or ""
    ).strip()

    requested_role = str(
        data.get(
            "requested_role",
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

    email = str(
        data.get(
            "email",
            ""
        )
        or ""
    ).strip().lower()

    phone_number = str(
        data.get(
            "phone_number",
            ""
        )
        or ""
    ).strip()

    website = str(
        data.get(
            "website",
            ""
        )
        or ""
    ).strip()

    country = str(
        data.get(
            "country",
            "Kenya"
        )
        or "Kenya"
    ).strip()

    county = str(
        data.get(
            "county",
            ""
        )
        or ""
    ).strip()

    city = str(
        data.get(
            "city",
            ""
        )
        or ""
    ).strip()

    address = str(
        data.get(
            "address",
            ""
        )
        or ""
    ).strip()

    logo = str(
        data.get(
            "logo",
            ""
        )
        or ""
    ).strip()

    print(
        "========================================"
    )

    print(
        "CREATE ORGANIZATION"
    )

    print(
        "NAME:",
        name
    )

    print(
        "ORGANIZATION TYPE:",
        organization_type
    )

    print(
        "REQUESTED ROLE:",
        requested_role
    )

    print(
        "========================================"
    )

    # =====================================================
    # REQUIRED FIELDS
    # =====================================================

    missing_fields = []

    if not name:
        missing_fields.append(
            "name"
        )

    if not organization_type:
        missing_fields.append(
            "organization_type"
        )

    if not email:
        missing_fields.append(
            "email"
        )

    if not phone_number:
        missing_fields.append(
            "phone_number"
        )

    if not country:
        missing_fields.append(
            "country"
        )

    if not county:
        missing_fields.append(
            "county"
        )

    if not city:
        missing_fields.append(
            "city"
        )

    if not address:
        missing_fields.append(
            "address"
        )

    if missing_fields:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Missing required organization fields.",

                "fields":
                    missing_fields,
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION TYPE
    # =====================================================

    valid_organization_types = {
        "property_manager",
        "landlord",
        "developer",
        "contractor",
        "consultancy",
        "investor",
        "corporate_client",
        "other",
    }

    if (
        organization_type
        not in valid_organization_types
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid organization type."
            },
            status=400,
        )

    # =====================================================
    # REQUESTED ROLE
    # =====================================================

    valid_requested_roles = {
        "property_manager",
        "project_manager",
        "investor",
        "service_provider",
        "landlord",
        "organization_owner",
    }

    if (
        requested_role
        and
        requested_role
        not in valid_requested_roles
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid requested role."
            },
            status=400,
        )

    # =====================================================
    # DUPLICATES
    # =====================================================

    if (
        Organization.objects
        .filter(
            name__iexact=
                name
        )
        .exists()
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "An organization with this name already exists."
            },
            status=400,
        )

    if kra_pin:

        kra_exists = (
            Organization.objects
            .filter(
                kra_pin__iexact=
                    kra_pin
            )
            .exists()
        )

        if kra_exists:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "An organization with this KRA PIN already exists."
                },
                status=400,
            )

    # =====================================================
    # SLUG
    # =====================================================

    base_slug = (
        slugify(
            name
        )
        or
        "organization"
    )

    slug = (
        base_slug
    )

    counter = 1

    while (
        Organization.objects
        .filter(
            slug=slug
        )
        .exists()
    ):

        slug = (
            f"{base_slug}-{counter}"
        )

        counter += 1

    # =====================================================
    # CREATE
    # =====================================================

    try:

        with transaction.atomic():

            # =================================================
            # ORGANIZATION
            # =================================================

            organization = (
                Organization.objects
                .create(
                    created_by=
                        user,

                    name=
                        name,

                    slug=
                        slug,

                    organization_type=
                        organization_type,

                    kra_pin=
                        kra_pin
                        or None,

                    email=
                        email,

                    phone_number=
                        phone_number,

                    website=
                        website
                        or None,

                    country=
                        country,

                    county=
                        county,

                    city=
                        city,

                    address=
                        address,

                    logo=(
                        logo
                        if logo
                        else
                        (
                            "https://res.cloudinary.com/"
                            "dc68huvjj/image/upload/"
                            "v1748102584/"
                            "kwwwa0avlfoeybpi3key.png"
                        )
                    ),

                    is_verified=
                        False,
                )
            )

            # =================================================
            # TRIAL SUBSCRIPTION
            # =================================================

            create_trial_subscription(
                organization
            )

            # =================================================
            # ORGANIZATION OWNER ROLE
            # =================================================

            owner_role, _ = (
                Role.objects
                .get_or_create(
                    organization=
                        organization,

                    code=
                        "organization_owner",

                    defaults={
                        "name":
                            "organization_owner",

                        "description":
                            (
                                "Owner of the organization "
                                "with full administrative access."
                            ),

                        "scope":
                            "organization",

                        "is_system_role":
                            True,

                        "is_active":
                            True,
                    },
                )
            )

            # =================================================
            # DETERMINE DEFAULT WORKING ROLE
            # =================================================

            primary_role = (
                owner_role
            )

            job_title = (
                "Organization Owner"
            )

            additional_role = (
                None
            )

            # =================================================
            # PROJECT MANAGER
            # =================================================

            if (
                requested_role
                ==
                "project_manager"
            ):

                additional_role, _ = (
                    Role.objects
                    .get_or_create(
                        organization=
                            organization,

                        code=
                            "project_manager",

                        defaults={
                            "name":
                                "project_manager",

                            "description":
                                (
                                    "Manages construction projects, "
                                    "tasks, milestones, budgets, "
                                    "contractors and site activities."
                                ),

                            "scope":
                                "project_management",

                            "is_system_role":
                                True,

                            "is_active":
                                True,
                        },
                    )
                )

                primary_role = (
                    additional_role
                )

                job_title = (
                    "Project Manager"
                )

            # =================================================
            # PROPERTY MANAGER
            # =================================================

            elif (
                requested_role
                ==
                "property_manager"
            ):

                additional_role, _ = (
                    Role.objects
                    .get_or_create(
                        organization=
                            organization,

                        code=
                            "property_manager",

                        defaults={
                            "name":
                                "property_manager",

                            "description":
                                (
                                    "Manages properties, tenants, "
                                    "leases, payments and maintenance."
                                ),

                            "scope":
                                "property_management",

                            "is_system_role":
                                True,

                            "is_active":
                                True,
                        },
                    )
                )

                primary_role = (
                    additional_role
                )

                job_title = (
                    "Property Manager"
                )

            # =================================================
            # INVESTOR
            # =================================================

            elif (
                requested_role
                ==
                "investor"
            ):

                additional_role, _ = (
                    Role.objects
                    .get_or_create(
                        organization=
                            organization,

                        code=
                            "investor",

                        defaults={
                            "name":
                                "investor",

                            "description":
                                (
                                    "Views investments, property "
                                    "performance and financial reports."
                                ),

                            "scope":
                                "investment",

                            "is_system_role":
                                True,

                            "is_active":
                                True,
                        },
                    )
                )

                primary_role = (
                    additional_role
                )

                job_title = (
                    "Investor"
                )

            # =================================================
            # LANDLORD
            # =================================================

            elif (
                requested_role
                ==
                "landlord"
            ):

                additional_role, _ = (
                    Role.objects
                    .get_or_create(
                        organization=
                            organization,

                        code=
                            "landlord",

                        defaults={
                            "name":
                                "landlord",

                            "description":
                                "Property owner or landlord.",

                            "scope":
                                "property",

                            "is_system_role":
                                True,

                            "is_active":
                                True,
                        },
                    )
                )

                primary_role = (
                    additional_role
                )

                job_title = (
                    "Landlord"
                )

            # =================================================
            # MEMBER NUMBER
            # =================================================

            employee_number = (
                "UNIT-"
                +
                uuid.uuid4()
                .hex[:10]
                .upper()
            )

            # =================================================
            # MEMBERSHIP
            # =================================================

            membership = (
                OrganizationMembership.objects
                .create(
                    user=
                        user,

                    organization=
                        organization,

                    primary_role=
                        primary_role,

                    employee_number=
                        employee_number,

                    job_title=
                        job_title,

                    is_primary_contact=
                        True,

                    is_active=
                        True,
                )
            )

            # =================================================
            # ALWAYS ADD OWNER ROLE
            # =================================================

            membership.roles.add(
                owner_role
            )

            # =================================================
            # ADD WORKING ROLE
            # =================================================

            if (
                additional_role
                and
                additional_role.id
                !=
                owner_role.id
            ):

                membership.roles.add(
                    additional_role
                )

            # =================================================
            # OPTIONAL:
            # SAVE REQUESTED ROLE ON USER
            # =================================================

            if hasattr(
                user,
                "requested_role"
            ):

                user.requested_role = (
                    requested_role
                )

                user.save(
                    update_fields=[
                        "requested_role"
                    ]
                )

        # =====================================================
        # RESPONSE
        # =====================================================

        return JsonResponse(
            {
                "success":
                    True,

                "message":
                    "Organization created successfully.",

                "next_step":
                    "select_organization",

                "role":
                    primary_role.code,

                "organization": {
                    "id":
                        organization.id,

                    "name":
                        organization.name,

                    "slug":
                        organization.slug,

                    "organization_type":
                        organization.organization_type,

                    "kra_pin":
                        organization.kra_pin,

                    "email":
                        organization.email,

                    "phone_number":
                        organization.phone_number,

                    "website":
                        organization.website,

                    "country":
                        organization.country,

                    "county":
                        organization.county,

                    "city":
                        organization.city,

                    "address":
                        organization.address,

                    "logo":
                        organization.logo,

                    "is_verified":
                        organization.is_verified,
                },

                "membership": {
                    "id":
                        membership.id,

                    "employee_number":
                        membership.employee_number,

                    "job_title":
                        membership.job_title,

                    "primary_role": {
                        "id":
                            primary_role.id,

                        "code":
                            primary_role.code,

                        "name":
                            primary_role
                            .get_name_display(),
                    },

                    "roles": [
                        {
                            "id":
                                role.id,

                            "code":
                                role.code,

                            "name":
                                role
                                .get_name_display(),
                        }

                        for role
                        in membership
                        .roles
                        .all()
                    ],

                    "is_primary_contact":
                        membership.is_primary_contact,
                },
            },
            status=201,
        )

    except Exception as error:

        print(
            "========================================"
        )

        print(
            "CREATE ORGANIZATION ERROR:"
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
                    "Unable to create organization.",

                "error":
                    str(
                        error
                    ),
            },
            status=500,
        )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_organizations(request):
    user = request.user

    try:
        memberships = (
            OrganizationMembership.objects
            .filter(
                user=user,
                is_active=True,
            )
            .select_related(
                "organization",
            )
            .prefetch_related(
                "roles",
                "organization__properties",
                "organization__memberships",
            )
            .order_by(
                "organization__name"
            )
        )

        organizations = []

        for membership in memberships:
            organization = membership.organization

            roles = membership.roles.filter(
                is_active=True
            )

            organizations.append(
                {
                    "id":
                        organization.id,

                    "name":
                        organization.name,

                    "slug":
                        organization.slug,

                    "organization_type":
                        organization.organization_type,

                    "organization_type_display":
                        get_organization_type_display(
                            organization.organization_type
                        ),

                    "roles": [
                        {
                            "id": role.id,
                            "code": role.code,
                            "name":
                                role.get_name_display(),
                        }
                        for role in roles
                    ],

                    "properties_count":
                        organization.properties
                        .filter(status="active")
                        .count(),

                    "members_count":
                        organization.memberships
                        .filter(is_active=True)
                        .count(),

                    "is_verified":
                        organization.is_verified,

                    "membership": {
                        "id":
                            membership.id,

                        "employee_number":
                            membership.employee_number,

                        "job_title":
                            membership.job_title,

                        "is_primary_contact":
                            membership.is_primary_contact,
                    },

                    "location": {
                        "country":
                            organization.country,

                        "county":
                            organization.county,

                        "city":
                            organization.city,

                        "address":
                            organization.address,
                    },
                }
            )

        return JsonResponse(
            {
                "organizations":
                    organizations,
                "count":
                    len(organizations),
            },
            status=200,
        )

    except Exception as error:
        print(
            "MY ORGANIZATIONS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to load organizations."
            },
            status=500,
        )


def get_organization_type_display(
    organization_type
):
    organization_types = {
        "property_manager":
            "Property Management Company",

        "landlord":
            "Landlord Organization",

        "developer":
            "Property Developer",

        "contractor":
            "Contractor",

        "consultancy":
            "Consultancy",

        "investor":
            "Investor Organization",

        "corporate_client":
            "Corporate Client",

        "other":
            "Other",
    }

    return organization_types.get(
        organization_type,
        organization_type
            .replace("_", " ")
            .title(),
    )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_organization_roles(request, organization_id):
    user = request.user

    try:
        organization = Organization.objects.get(
            id=organization_id
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related("roles")
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
                    "You do not belong to this organization."
            },
            status=403,
        )

    roles = (
        membership.roles
        .filter(is_active=True)
        .order_by("name")
    )

    response_roles = [
        {
            "id": role.id,
            "code": role.code,
            "name": role.get_name_display(),
            "description":
                role.description or "",
            "scope":
                role.scope,
        }
        for role in roles
    ]

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,

                "organization_type":
                    organization.organization_type,

                "is_verified":
                    organization.is_verified,
            },

            "membership": {
                "id":
                    membership.id,

                "employee_number":
                    membership.employee_number,

                "job_title":
                    membership.job_title,

                "is_primary_contact":
                    membership.is_primary_contact,
            },

            "roles":
                response_roles,

            "count":
                len(response_roles),
        },
        status=200,
    )