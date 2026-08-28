from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def new_property_manager_profile(request):

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
                "success": False,
                "message":
                    "organization_id is required.",
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    try:
        organization = (
            Organization.objects
            .get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "Organization not found.",
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            user=user,
            organization=organization,
            is_active=True,
        )
        .prefetch_related(
            "roles"
        )
        .select_related(
            "primary_role"
        )
        .first()
    )

    if not membership:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "You do not have access to this organization.",
            },
            status=403,
        )

    # =====================================================
    # ROLE CHECK
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
        "property_manager",
        "organization_admin",
        "organization_owner",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "success": False,
                "message":
                    "You do not have permission to access this profile.",
            },
            status=403,
        )

    # =====================================================
    # USER PROFILE
    # =====================================================

    profile, _ = (
        UserProfile.objects
        .get_or_create(
            user=user
        )
    )

    # =====================================================
    # FULL NAME
    # =====================================================

    full_name = " ".join(
        [
            part.strip()
            for part in [
                user.first_name,
                user.middle_name,
                user.last_name,
            ]
            if part
            and part.strip()
        ]
    )

    # =====================================================
    # ROLES
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
                "id": role.id,
                "code": role.code,
                "name":
                    role.get_name_display(),
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "success": True,

            "user": {
                "id":
                    user.id,

                "full_name":
                    full_name,

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

                "status":
                    user.status,
            },

            "profile": {
                "national_id_number":
                    profile.national_id_number,

                "kra_pin":
                    profile.kra_pin,

                "gender":
                    profile.gender,

                "date_of_birth": (
                    profile.date_of_birth.isoformat()
                    if profile.date_of_birth
                    else None
                ),

                "county":
                    profile.county,

                "city":
                    profile.city,

                "address":
                    profile.address,
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

                "primary_role": (
                    {
                        "id":
                            membership.primary_role.id,

                        "code":
                            membership.primary_role.code,

                        "name":
                            membership.primary_role.get_name_display(),
                    }
                    if membership.primary_role
                    else None
                ),

                "roles":
                    roles,

                "joined_at":
                    membership.joined_at.isoformat(),
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,

                "organization_type":
                    organization.organization_type,

                "email":
                    organization.email,

                "phone_number":
                    organization.phone_number,

                "logo":
                    organization.logo,

                "address":
                    organization.address,

                "city":
                    organization.city,

                "county":
                    organization.county,

                "country":
                    organization.country,
            },
        },
        status=200,
    )




@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_property_manager_profile(request):

    user = request.user

    organization_id = (
        request.data.get(
            "organization_id"
        )
        or
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
                "success":
                    False,

                "message":
                    "organization_id is required."
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
            user=
                user,

            organization=
                organization,

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
    # ROLE CHECK
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
        "property_manager",
        "organization_admin",
        "organization_owner",
    }

    if not role_codes.intersection(
        allowed_roles
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "You do not have permission to update this profile."
            },
            status=403,
        )

    # =====================================================
    # PROFILE
    # =====================================================

    profile, created = (
        UserProfile.objects
        .get_or_create(
            user=
                user
        )
    )

    data = request.data

    # =====================================================
    # DATA
    # =====================================================

    full_name = str(
        data.get(
            "full_name",
            ""
        )
        or ""
    ).strip()

    phone_number = str(
        data.get(
            "phone_number",
            user.phone_number
        )
        or ""
    ).strip()

    national_id_number = str(
        data.get(
            "national_id_number",
            profile.national_id_number
            or ""
        )
        or ""
    ).strip()

    kra_pin = str(
        data.get(
            "kra_pin",
            profile.kra_pin
            or ""
        )
        or ""
    ).strip().upper()

    county = str(
        data.get(
            "county",
            profile.county
            or ""
        )
        or ""
    ).strip()

    city = str(
        data.get(
            "city",
            profile.city
            or ""
        )
        or ""
    ).strip()

    address = str(
        data.get(
            "address",
            profile.address
            or ""
        )
        or ""
    ).strip()

    job_title = str(
        data.get(
            "job_title",
            membership.job_title
            or ""
        )
        or ""
    ).strip()

    # =====================================================
    # REQUIRED
    # =====================================================

    if not full_name:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Full name is required."
            },
            status=400,
        )

    if not phone_number:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Phone number is required."
            },
            status=400,
        )

    # =====================================================
    # UNIQUE PHONE CHECK
    # =====================================================

    phone_exists = (
        User.objects
        .filter(
            phone_number=
                phone_number
        )
        .exclude(
            id=
                user.id
        )
        .exists()
    )

    if phone_exists:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "This phone number is already in use."
            },
            status=400,
        )

    # =====================================================
    # NAME
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
    # USER UPDATE
    # =====================================================

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

    user.save(
        update_fields=[
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
        ]
    )

    # =====================================================
    # USER PROFILE UPDATE
    # =====================================================

    profile.national_id_number = (
        national_id_number
        or None
    )

    profile.kra_pin = (
        kra_pin
        or None
    )

    profile.county = (
        county
        or None
    )

    profile.city = (
        city
        or None
    )

    profile.address = (
        address
        or None
    )

    profile.save(
        update_fields=[
            "national_id_number",
            "kra_pin",
            "county",
            "city",
            "address",
            "updated_at",
        ]
    )

    # =====================================================
    # MEMBERSHIP UPDATE
    # =====================================================

    membership.job_title = (
        job_title
        or None
    )

    membership.save(
        update_fields=[
            "job_title",
            "updated_at",
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
                "Profile updated successfully.",

            "user": {
                "id":
                    user.id,

                "full_name":
                    full_name,

                "email":
                    user.email,

                "phone_number":
                    user.phone_number,

                "profile_image":
                    user.profile_image,
            },

            "profile": {
                "national_id_number":
                    profile.national_id_number,

                "kra_pin":
                    profile.kra_pin,

                "county":
                    profile.county,

                "city":
                    profile.city,

                "address":
                    profile.address,
            },

            "membership": {
                "id":
                    membership.id,

                "employee_number":
                    membership.employee_number,

                "job_title":
                    membership.job_title,
            },
        },
        status=200,
    )