from .common_imports import *



def user_can_manage_roles(
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

    return bool(
        role_codes.intersection({
            "organization_owner",
            "organization_admin",
        })
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_role_options(request):
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

    if not user_can_manage_roles(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to manage roles."
            },
            status=403,
        )

    # Prevent normal creation of the
    # organization_owner role.
    excluded_roles = {
        "organization_owner",
    }

    roles = []

    for value, label in (
        Role.ROLES_NAMES
    ):
        if value in excluded_roles:
            continue

        roles.append(
            {
                "value":
                    value,

                "label":
                    label,
            }
        )

    return JsonResponse(
        {
            "roles":
                roles
        },
        status=200,
    )




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_role(request):
    user = request.user
    data = request.data

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    code = str(
        data.get(
            "code",
            ""
        )
    ).strip().lower()

    description = str(
        data.get(
            "description",
            ""
        )
        or ""
    ).strip()

    scope = str(
        data.get(
            "scope",
            ""
        )
        or ""
    ).strip()

    is_active = data.get(
        "is_active",
        True,
    )

    # =====================================================
    # REQUIRED
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    if not name:
        return JsonResponse(
            {
                "message":
                    "Role name is required."
            },
            status=400,
        )

    if not code:
        return JsonResponse(
            {
                "message":
                    "Role code is required."
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
    # PERMISSION
    # =====================================================

    if not user_can_manage_roles(
        user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to create roles."
            },
            status=403,
        )

    # =====================================================
    # VALID ROLE NAME
    # =====================================================

    allowed_names = dict(
        Role.ROLES_NAMES
    )

    if name not in allowed_names:
        return JsonResponse(
            {
                "message":
                    "Invalid role name."
            },
            status=400,
        )

    # =====================================================
    # PROTECT OWNER ROLE
    # =====================================================

    if (
        name ==
        "organization_owner"
    ):
        return JsonResponse(
            {
                "message":
                    "Organization Owner cannot be created manually."
            },
            status=403,
        )

    # =====================================================
    # DUPLICATE CODE
    # =====================================================

    if (
        Role.objects
        .filter(
            organization=
                organization,

            code__iexact=
                code,
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "A role with this code already exists in this organization."
            },
            status=400,
        )

    # =====================================================
    # DUPLICATE ROLE NAME
    # =====================================================

    if (
        Role.objects
        .filter(
            organization=
                organization,

            name=name,
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "This role already exists in this organization."
            },
            status=400,
        )

    # =====================================================
    # CREATE
    # =====================================================

    try:
        role = (
            Role.objects.create(
                organization=
                    organization,

                code=
                    code,

                name=
                    name,

                description=
                    description,

                scope=
                    scope,

                is_system_role=
                    False,

                is_active=
                    bool(
                        is_active
                    ),
            )
        )

        return JsonResponse(
            {
                "message":
                    "Role created successfully.",

                "role": {
                    "id":
                        role.id,

                    "organization_id":
                        organization.id,

                    "code":
                        role.code,

                    "name":
                        role.name,

                    "name_display":
                        role
                        .get_name_display(),

                    "description":
                        role.description,

                    "scope":
                        role.scope,

                    "is_system_role":
                        role
                        .is_system_role,

                    "is_active":
                        role.is_active,
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE ROLE ERROR:",
            str(error)
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create role.",

                "error":
                    str(error),
            },
            status=500,
        )






@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_organization_roles(request):
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

    user_role_codes = set(
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
    }

    if not user_role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to manage roles."
            },
            status=403,
        )

    roles = (
        Role.objects
        .filter(
            organization=
                organization
        )
        .annotate(
            members_count=Count(
                "memberships",
                filter=Q(
                    memberships__is_active=True
                ),
                distinct=True,
            ),
        )
        .order_by(
            "name"
        )
    )

    role_data = []

    for role in roles:
        primary_members_count = (
            OrganizationMembership.objects
            .filter(
                organization=
                    organization,

                primary_role=
                    role,

                is_active=True,
            )
            .count()
        )

        role_data.append(
            {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.name,

                "name_display":
                    role
                    .get_name_display(),

                "description":
                    role.description,

                "scope":
                    role.scope,

                "is_system_role":
                    role
                    .is_system_role,

                "is_active":
                    role.is_active,

                "members_count":
                    role.members_count,

                "primary_members_count":
                    primary_members_count,

                "created_at":
                    role.created_at
                    .isoformat(),
            }
        )

    return JsonResponse(
        {
            "summary": {
                "total_roles":
                    roles.count(),

                "active_roles":
                    roles.filter(
                        is_active=True
                    ).count(),

                "inactive_roles":
                    roles.filter(
                        is_active=False
                    ).count(),

                "system_roles":
                    roles.filter(
                        is_system_role=True
                    ).count(),
            },

            "roles":
                role_data,

            "count":
                len(
                    role_data
                ),
        },
        status=200,
    )






def can_manage_roles(
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
        })
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_role_details(
    request,
    role_id,
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

    if not can_manage_roles(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to manage roles."
            },
            status=403,
        )

    try:
        role = (
            Role.objects.get(
                id=role_id,
                organization=organization,
            )
        )

    except Role.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Role not found."
            },
            status=404,
        )

    memberships = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            roles=role,
            is_active=True,
        )
        .select_related(
            "user",
            "primary_role",
        )
        .distinct()
    )

    members = []

    for membership in memberships:
        member = membership.user

        full_name = " ".join(
            filter(
                None,
                [
                    member.first_name,
                    member.middle_name,
                    member.last_name,
                ],
            )
        )

        members.append(
            {
                "membership_id":
                    membership.id,

                "user_id":
                    member.id,

                "full_name":
                    full_name,

                "email":
                    member.email,

                "phone_number":
                    member.phone_number,

                "profile_image":
                    member.profile_image,

                "is_primary": (
                    membership
                    .primary_role_id
                    == role.id
                ),
            }
        )

    primary_members_count = (
        memberships.filter(
            primary_role=role
        ).count()
    )

    return JsonResponse(
        {
            "role": {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.name,

                "name_display":
                    role
                    .get_name_display(),

                "description":
                    role.description,

                "scope":
                    role.scope,

                "is_system_role":
                    role.is_system_role,

                "is_active":
                    role.is_active,

                "members_count":
                    memberships.count(),

                "primary_members_count":
                    primary_members_count,

                "created_at":
                    role.created_at
                    .isoformat(),

                "updated_at":
                    role.updated_at
                    .isoformat(),
            },

            "members":
                members,
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_role(
    request,
    role_id,
):
    data = request.data

    organization_id = (
        data.get(
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

    if not can_manage_roles(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to update roles."
            },
            status=403,
        )

    try:
        role = (
            Role.objects.get(
                id=role_id,
                organization=organization,
            )
        )

    except Role.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Role not found."
            },
            status=404,
        )

    if role.is_system_role:
        return JsonResponse(
            {
                "message":
                    "System roles cannot be edited."
            },
            status=403,
        )

    if "description" in data:
        role.description = str(
            data.get(
                "description",
                ""
            )
            or ""
        ).strip()

    if "scope" in data:
        role.scope = str(
            data.get(
                "scope",
                ""
            )
            or ""
        ).strip()

    role.save()

    return JsonResponse(
        {
            "message":
                "Role updated successfully.",

            "role": {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.name,

                "name_display":
                    role
                    .get_name_display(),

                "description":
                    role.description,

                "scope":
                    role.scope,

                "is_system_role":
                    role.is_system_role,

                "is_active":
                    role.is_active,
            },
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_role_status(
    request,
    role_id,
):
    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    is_active = (
        request.data.get(
            "is_active"
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

    if not isinstance(
        is_active,
        bool,
    ):
        return JsonResponse(
            {
                "message":
                    "is_active must be true or false."
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

    if not can_manage_roles(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to manage roles."
            },
            status=403,
        )

    try:
        role = (
            Role.objects.get(
                id=role_id,
                organization=organization,
            )
        )

    except Role.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Role not found."
            },
            status=404,
        )

    if role.is_system_role:
        return JsonResponse(
            {
                "message":
                    "System roles cannot be deactivated."
            },
            status=403,
        )

    role.is_active = (
        is_active
    )

    role.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "message":
                "Role status updated.",

            "role": {
                "id":
                    role.id,

                "code":
                    role.code,

                "name":
                    role.name,

                "name_display":
                    role
                    .get_name_display(),

                "description":
                    role.description,

                "scope":
                    role.scope,

                "is_active":
                    role.is_active,

                "is_system_role":
                    role.is_system_role,
            },
        },
        status=200,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_role(
    request,
    role_id,
):
    organization_id = (
        request.data.get(
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

    if not can_manage_roles(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to delete roles."
            },
            status=403,
        )

    try:
        role = (
            Role.objects.get(
                id=role_id,
                organization=organization,
            )
        )

    except Role.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Role not found."
            },
            status=404,
        )

    if role.is_system_role:
        return JsonResponse(
            {
                "message":
                    "System roles cannot be deleted."
            },
            status=403,
        )

    members_count = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            roles=role,
            is_active=True,
        )
        .distinct()
        .count()
    )

    if members_count > 0:
        return JsonResponse(
            {
                "message": (
                    f"This role is assigned to "
                    f"{members_count} member(s). "
                    "Remove the role from them before deleting it."
                )
            },
            status=400,
        )

    role_name = (
        role.get_name_display()
    )

    role.delete()

    return JsonResponse(
        {
            "message":
                f"{role_name} deleted successfully."
        },
        status=200,
    )