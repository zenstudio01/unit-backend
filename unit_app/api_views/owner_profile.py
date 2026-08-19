from .common_imports import *




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_owner_profile(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
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

    # =====================================================
    # ROLE ACCESS
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
        "landlord",
        "investor",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to access the owner profile."
            },
            status=403,
        )

    # =====================================================
    # USER PROFILE
    # =====================================================

    user_profile, _ = (
        UserProfile.objects
        .get_or_create(
            user=user
        )
    )

    # =====================================================
    # OWNER
    # =====================================================

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

    owner_data = None

    owned_property_count = 0

    if owner:

        ownerships = (
            PropertyOwnership.objects
            .filter(
                owner=owner,
                is_active=True,
            )
        )

        owned_property_count = (
            ownerships.count()
        )

        average_ownership = (
            ownerships
            .aggregate(
                value=Avg(
                    "ownership_percentage"
                )
            )["value"]
            or Decimal("0")
        )

        owner_data = {
            "id":
                owner.id,

            "owner_type":
                owner.owner_type,

            "name":
                owner.name,

            "email":
                owner.email,

            "phone_number":
                owner.phone_number,

            "national_id_number":
                owner
                .national_id_number,

            "registration_number":
                owner
                .registration_number,

            "kra_pin":
                owner.kra_pin,

            "status":
                owner.status,

            "properties_count":
                owned_property_count,

            "average_ownership_percentage":
                float(
                    average_ownership
                ),
        }

    # =====================================================
    # PORTFOLIOS
    # =====================================================

    portfolio_count = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            status="active",
        )
        .count()
    )

    # =====================================================
    # ROLES
    # =====================================================

    roles_data = []

    for role in (
        membership.roles
        .filter(
            is_active=True
        )
        .order_by(
            "name"
        )
    ):
        roles_data.append(
            {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.get_name_display()
                    if hasattr(
                        role,
                        "get_name_display",
                    )
                    else role.name,

                "description":
                    role.description,
            }
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
                    user.middle_name,

                "last_name":
                    user.last_name,

                "email":
                    user.email,

                "phone_number":
                    user.phone_number,

                "profile_image":
                    user.profile_image,

                "phone_verified":
                    user.phone_verified,

                "email_verified":
                    user.email_verified,

                "is_verified":
                    user.is_verified,

                "status":
                    user.status,

                "created_at":
                    user.created_at
                    .isoformat(),
            },

            "profile": {
                "national_id_number":
                    user_profile
                    .national_id_number,

                "kra_pin":
                    user_profile
                    .kra_pin,

                "gender":
                    user_profile.gender,

                "date_of_birth": (
                    user_profile
                    .date_of_birth
                    .isoformat()

                    if user_profile
                    .date_of_birth

                    else None
                ),

                "county":
                    user_profile.county,

                "city":
                    user_profile.city,

                "address":
                    user_profile.address,

                "latitude": (
                    str(
                        user_profile
                        .latitude
                    )
                    if user_profile
                    .latitude is not None
                    else None
                ),

                "longitude": (
                    str(
                        user_profile
                        .longitude
                    )
                    if user_profile
                    .longitude is not None
                    else None
                ),
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,

                "slug":
                    organization.slug,

                "organization_type":
                    organization
                    .organization_type,

                "logo":
                    organization.logo,

                "email":
                    organization.email,

                "phone_number":
                    organization
                    .phone_number,

                "country":
                    organization.country,

                "county":
                    organization.county,

                "city":
                    organization.city,

                "address":
                    organization.address,

                "is_verified":
                    organization
                    .is_verified,
            },

            "membership": {
                "id":
                    membership.id,

                "employee_number":
                    membership
                    .employee_number,

                "job_title":
                    membership.job_title,

                "is_primary_contact":
                    membership
                    .is_primary_contact,

                "is_active":
                    membership.is_active,

                "joined_at":
                    membership
                    .joined_at
                    .isoformat(),

                "roles":
                    roles_data,
            },

            "owner":
                owner_data,

            "statistics": {
                "properties":
                    owned_property_count,

                "portfolios":
                    portfolio_count,
            },
        },
        status=200,
    )





@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_owner_profile(request):
    user = request.user
    data = request.data

    # =====================================================
    # VALUES
    # =====================================================

    first_name = str(
        data.get(
            "first_name",
            user.first_name,
        )
        or ""
    ).strip()

    middle_name = str(
        data.get(
            "middle_name",
            user.middle_name,
        )
        or ""
    ).strip()

    last_name = str(
        data.get(
            "last_name",
            user.last_name,
        )
        or ""
    ).strip()

    phone_number = str(
        data.get(
            "phone_number",
            user.phone_number,
        )
        or ""
    ).strip()

    profile_image = str(
        data.get(
            "profile_image",
            user.profile_image,
        )
        or ""
    ).strip()

    # =====================================================
    # REQUIRED
    # =====================================================

    if not first_name:
        return JsonResponse(
            {
                "message":
                    "First name is required."
            },
            status=400,
        )

    if not last_name:
        return JsonResponse(
            {
                "message":
                    "Last name is required."
            },
            status=400,
        )

    if not phone_number:
        return JsonResponse(
            {
                "message":
                    "Phone number is required."
            },
            status=400,
        )

    # =====================================================
    # PHONE UNIQUE
    # =====================================================

    if (
        User.objects
        .exclude(
            id=user.id
        )
        .filter(
            phone_number=
                phone_number
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "This phone number is already being used by another account."
            },
            status=400,
        )

    # =====================================================
    # PROFILE FIELDS
    # =====================================================

    profile, _ = (
        UserProfile.objects
        .get_or_create(
            user=user
        )
    )

    national_id_number = (
        data.get(
            "national_id_number",
            profile
            .national_id_number,
        )
    )

    kra_pin = (
        data.get(
            "kra_pin",
            profile.kra_pin,
        )
    )

    gender = (
        data.get(
            "gender",
            profile.gender,
        )
    )

    date_of_birth = (
        data.get(
            "date_of_birth"
        )
    )

    county = (
        data.get(
            "county",
            profile.county,
        )
    )

    city = (
        data.get(
            "city",
            profile.city,
        )
    )

    address = (
        data.get(
            "address",
            profile.address,
        )
    )

    latitude = (
        data.get(
            "latitude",
            profile.latitude,
        )
    )

    longitude = (
        data.get(
            "longitude",
            profile.longitude,
        )
    )

    # =====================================================
    # UPDATE
    # =====================================================

    try:
        with transaction.atomic():

            user.first_name = (
                first_name
            )

            user.middle_name = (
                middle_name
            )

            user.last_name = (
                last_name
            )

            user.phone_number = (
                phone_number
            )

            if profile_image:
                user.profile_image = (
                    profile_image
                )

            user.save(
                update_fields=[
                    "first_name",
                    "middle_name",
                    "last_name",
                    "phone_number",
                    "profile_image",
                ]
            )

            profile.national_id_number = (
                national_id_number
                or None
            )

            profile.kra_pin = (
                kra_pin or None
            )

            profile.gender = (
                gender or None
            )

            profile.county = (
                county or None
            )

            profile.city = (
                city or None
            )

            profile.address = (
                address or None
            )

            profile.latitude = (
                latitude or None
            )

            profile.longitude = (
                longitude or None
            )

            # Only modify DOB when
            # explicitly sent.
            if (
                "date_of_birth"
                in data
            ):
                profile.date_of_birth = (
                    date_of_birth
                    or None
                )

            profile.save()

        return JsonResponse(
            {
                "message":
                    "Profile updated successfully.",

                "user": {
                    "id":
                        user.id,

                    "first_name":
                        user.first_name,

                    "middle_name":
                        user.middle_name,

                    "last_name":
                        user.last_name,

                    "email":
                        user.email,

                    "phone_number":
                        user.phone_number,

                    "profile_image":
                        user.profile_image,
                },

                "profile": {
                    "national_id_number":
                        profile
                        .national_id_number,

                    "kra_pin":
                        profile.kra_pin,

                    "gender":
                        profile.gender,

                    "date_of_birth": (
                        profile
                        .date_of_birth

                        if profile
                        .date_of_birth

                        else None
                    ),

                    "county":
                        profile.county,

                    "city":
                        profile.city,

                    "address":
                        profile.address,

                    "latitude": (
                        str(
                            profile
                            .latitude
                        )
                        if profile
                        .latitude
                        is not None
                        else None
                    ),

                    "longitude": (
                        str(
                            profile
                            .longitude
                        )
                        if profile
                        .longitude
                        is not None
                        else None
                    ),
                },
            },
            status=200,
        )

    except Exception as error:
        print(
            "UPDATE OWNER PROFILE ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to update profile.",

                "error":
                    str(error),
            },
            status=500,
        )