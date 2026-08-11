from .common_imports import *



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_organization(request):
    user = request.user
    data = request.data

    # --------------------------------------------------
    # Read fields
    # --------------------------------------------------

    name = str(
        data.get("name", "")
    ).strip()

    organization_type = str(
        data.get("organization_type", "")
    ).strip()

    kra_pin = str(
        data.get("kra_pin", "")
    ).strip().upper()

    email = str(
        data.get("email", "")
    ).strip().lower()

    phone_number = str(
        data.get("phone_number", "")
    ).strip()

    website = str(
        data.get("website", "")
    ).strip()

    country = str(
        data.get("country", "Kenya")
    ).strip()

    county = str(
        data.get("county", "")
    ).strip()

    city = str(
        data.get("city", "")
    ).strip()

    address = str(
        data.get("address", "")
    ).strip()

    logo = str(
        data.get("logo", "")
    ).strip()

    # --------------------------------------------------
    # Required fields
    # --------------------------------------------------

    missing_fields = []

    if not name:
        missing_fields.append("name")

    if not organization_type:
        missing_fields.append(
            "organization_type"
        )

    if not email:
        missing_fields.append("email")

    if not phone_number:
        missing_fields.append(
            "phone_number"
        )

    if not country:
        missing_fields.append("country")

    if not county:
        missing_fields.append("county")

    if not city:
        missing_fields.append("city")

    if not address:
        missing_fields.append("address")

    if missing_fields:
        return JsonResponse(
            {
                "message":
                    "Missing required organization fields.",
                "fields": missing_fields,
            },
            status=400,
        )

    # --------------------------------------------------
    # Validate organization type
    # --------------------------------------------------

    valid_organization_types = [
        "property_manager",
        "landlord",
        "developer",
        "contractor",
        "consultancy",
        "investor",
        "corporate_client",
        "other",
    ]

    if (
        organization_type
        not in valid_organization_types
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid organization type."
            },
            status=400,
        )

    # --------------------------------------------------
    # Duplicate checks
    # --------------------------------------------------

    if Organization.objects.filter(
        name__iexact=name
    ).exists():
        return JsonResponse(
            {
                "message":
                    "An organization with this name already exists."
            },
            status=400,
        )

    if (
        kra_pin
        and Organization.objects.filter(
            kra_pin__iexact=kra_pin
        ).exists()
    ):
        return JsonResponse(
            {
                "message":
                    "An organization with this KRA PIN already exists."
            },
            status=400,
        )

    # --------------------------------------------------
    # Generate unique slug
    # --------------------------------------------------

    base_slug = slugify(name)

    if not base_slug:
        base_slug = "organization"

    slug = base_slug

    counter = 1

    while Organization.objects.filter(
        slug=slug
    ).exists():

        slug = f"{base_slug}-{counter}"

        counter += 1

    try:
        with transaction.atomic():

            # ------------------------------------------
            # Create organization
            # ------------------------------------------

            organization = (
                Organization.objects.create(
                    created_by=user,

                    name=name,

                    slug=slug,

                    organization_type=
                        organization_type,

                    kra_pin=
                        kra_pin or None,

                    email=email,

                    phone_number=
                        phone_number,

                    website=
                        website or None,

                    country=country,

                    county=county,

                    city=city,

                    address=address,

                    logo=(
                        logo
                        if logo
                        else (
                            "https://res.cloudinary.com/"
                            "dc68huvjj/image/upload/"
                            "v1748102584/"
                            "kwwwa0avlfoeybpi3key.png"
                        )
                    ),

                    is_verified=False,
                )
            )

            # ------------------------------------------
            # Create organization owner role
            # ------------------------------------------

            owner_role, _ = (
                Role.objects.get_or_create(
                    organization=organization,

                    code="organization_owner",

                    defaults={
                        "name":
                            "organization_owner",

                        "description":
                            (
                                "Owner of the organization "
                                "with full administrative "
                                "access."
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

            # ------------------------------------------
            # Generate employee/member number
            # ------------------------------------------

            employee_number = (
                "UNIT-"
                + uuid.uuid4().hex[
                    :10
                ].upper()
            )

            # ------------------------------------------
            # Create membership
            # ------------------------------------------

            membership = (
                OrganizationMembership.objects.create(
                    user=user,

                    organization=organization,

                    # role=owner_role,

                    employee_number=
                        employee_number,

                    job_title=
                        "Organization Owner",

                    is_primary_contact=
                        True,

                    is_active=True,
                )
            )
            membership.roles.add(owner_role)

        # --------------------------------------------------
        # Response
        # --------------------------------------------------

        return JsonResponse(
            {
                "message":
                    "Organization created successfully.",

                "next_step":
                    "select_organization",

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

                    "roles": [
                        {
                            "id": role.id,
                            "code": role.code,
                            "name": role.get_name_display(),
                        }
                        for role in membership.roles.all()
                    ],

                    "is_primary_contact":
                        membership.is_primary_contact,
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE ORGANIZATION ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create organization."
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