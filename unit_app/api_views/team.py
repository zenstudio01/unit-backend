from .common_imports import *



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_team_roles(request):
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
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization_id=
                    organization_id,

                user=user,

                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access."
            },
            status=403,
        )

    codes = set(
        membership.roles
        .values_list(
            "code",
            flat=True,
        )
    )

    if not codes.intersection({
        "organization_owner",
        "organization_admin",
        "property_manager",
    }):
        return JsonResponse(
            {
                "message":
                    "You cannot manage team members."
            },
            status=403,
        )

    # Do not allow an ordinary owner/admin
    # to assign system-level roles.

    roles = (
        Role.objects
        .filter(
            is_active=True
        )
        .exclude(
            code__in=[
                "organization_owner",
            ]
        )
        .order_by(
            "name"
        )
    )

    return JsonResponse(
        {
            "roles": [
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
                for role in roles
            ]
        },
        status=200,
    )







@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_team_member(request):
    user = request.user
    data = request.data

    organization_id = data.get(
        "organization_id"
    )

    first_name = str(
        data.get(
            "first_name",
            ""
        )
    ).strip()

    middle_name = str(
        data.get(
            "middle_name",
            ""
        )
        or ""
    ).strip()

    last_name = str(
        data.get(
            "last_name",
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
        or ""
    ).strip()

    role_ids = data.get(
        "role_ids",
        []
    )

    primary_role_id = (
        data.get(
            "primary_role_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if (
        not organization_id
        or
        not first_name
        or
        not last_name
        or
        not email
    ):
        return JsonResponse(
            {
                "message":
                    "Organization, first name, last name and email are required."
            },
            status=400,
        )

    if not role_ids:
        return JsonResponse(
            {
                "message":
                    "At least one role is required."
            },
            status=400,
        )

    if not primary_role_id:
        return JsonResponse(
            {
                "message":
                    "Primary role is required."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
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
    # CURRENT USER PERMISSION
    # =====================================================

    try:
        requester_membership = (
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

    requester_roles = set(
        requester_membership.roles
        .values_list(
            "code",
            flat=True,
        )
    )

    if not requester_roles.intersection({
        "organization_owner",
        "organization_admin",
        "property_manager",
    }):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to add team members."
            },
            status=403,
        )

    # =====================================================
    # ROLES
    # =====================================================

    roles = list(
        Role.objects
        .filter(
            id__in=
                role_ids,

            is_active=True,
        )
    )

    if len(roles) != len(
        set(role_ids)
    ):
        return JsonResponse(
            {
                "message":
                    "One or more roles are invalid."
            },
            status=400,
        )

    try:
        primary_role = (
            Role.objects.get(
                id=
                    primary_role_id,

                is_active=True,
            )
        )

    except Role.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Primary role is invalid."
            },
            status=400,
        )

    if primary_role.id not in [
        role.id
        for role in roles
    ]:
        return JsonResponse(
            {
                "message":
                    "Primary role must be one of the assigned roles."
            },
            status=400,
        )

    # Prevent unauthorized creation
    # of organization_owner.

    assigning_owner = any(
        role.code ==
        "organization_owner"
        for role in roles
    )

    if (
        assigning_owner
        and
        "organization_owner"
        not in requester_roles
    ):
        return JsonResponse(
            {
                "message":
                    "Only the organization owner can assign the owner role."
            },
            status=403,
        )

    # =====================================================
    # EXISTING USER?
    # =====================================================

    existing_user = (
        User.objects
        .filter(
            email__iexact=email
        )
        .first()
    )

    # =====================================================
    # EXISTING USER
    # =====================================================

    if existing_user:

        existing_membership = (
            OrganizationMembership.objects
            .filter(
                organization=
                    organization,

                user=
                    existing_user,
            )
            .first()
        )

        if existing_membership:
            return JsonResponse(
                {
                    "message":
                        "This user already belongs to this organization."
                },
                status=400,
            )

        try:
            with transaction.atomic():

                membership = (
                    OrganizationMembership.objects.create(
                        organization=
                            organization,

                        user=
                            existing_user,

                        primary_role=
                            primary_role,

                        is_active=True,
                    )
                )

                membership.roles.set(
                    roles
                )

            Notification.objects.create(
                user=
                    existing_user,

                organization=
                    organization,

                notification_type=
                    "organization",

                title=
                    "Added to Organization",

                message=(
                    f"You have been added to "
                    f"{organization.name}."
                ),
            )

            return JsonResponse(
                {
                    "message":
                        f"{existing_user.first_name or email} has been added successfully.",

                    "status":
                        "added",

                    "membership_id":
                        membership.id,
                },
                status=201,
            )

        except Exception as error:
            return JsonResponse(
                {
                    "message":
                        "Unable to add team member.",

                    "error":
                        str(error),
                },
                status=500,
            )

    # =====================================================
    # NEW USER → INVITATION
    # =====================================================

    existing_invitation = (
        OrganizationInvitation.objects
        .filter(
            organization=
                organization,

            email__iexact=
                email,

            status=
                "pending",
        )
        .first()
    )

    if existing_invitation:
        return JsonResponse(
            {
                "message":
                    "An invitation has already been sent to this email."
            },
            status=400,
        )

    try:
        with transaction.atomic():

            invitation = (
                OrganizationInvitation.objects.create(
                    organization=
                        organization,

                    first_name=
                        first_name,

                    middle_name=
                        middle_name,

                    last_name=
                        last_name,

                    email=
                        email,

                    phone_number=
                        phone_number,

                    primary_role=
                        primary_role,

                    invited_by=
                        user,

                    expires_at=(
                        timezone.now()
                        +
                        timedelta(
                            days=7
                        )
                    ),
                )
            )

            invitation.roles.set(
                roles
            )

        # -------------------------------------------------
        # Send your email here.
        #
        # Use the send_email() helper you already use in
        # your signup flow.
        # -------------------------------------------------

        activation_link = (
            "https://unit-backend-lof1.onrender.com/api/v1/"
            f"invitations/accept_invitation/?token="
            f"{invitation.token}"
        )

        try:
            send_email(
                email,
                f"You're invited to {organization.name}",
                f"""
                <div style="
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: auto;
                    padding: 24px;
                ">
                    <h2>
                        You've been invited to UNIT
                    </h2>

                    <p>
                        Hello {first_name},
                    </p>

                    <p>
                        {user.first_name} has invited
                        you to join
                        <strong>
                            {organization.name}
                        </strong>
                        on UNIT.
                    </p>

                    <p>
                        Use the button below to activate
                        your account and create your
                        password.
                    </p>

                    <a
                        href="{activation_link}"
                        style="
                            background: #0B6B36;
                            color: white;
                            padding: 12px 20px;
                            border-radius: 8px;
                            text-decoration: none;
                            display: inline-block;
                        "
                    >
                        Activate Account
                    </a>

                    <p>
                        This invitation expires in 7 days.
                    </p>
                </div>
                """,
            )

        except Exception as email_error:
            print(
                "INVITATION EMAIL ERROR:",
                email_error,
            )

        return JsonResponse(
            {
                "message":
                    f"Invitation sent to {email}.",

                "status":
                    "invited",

                "invitation_id":
                    invitation.id,
            },
            status=201,
        )

    except Exception as error:
        return JsonResponse(
            {
                "message":
                    "Unable to create invitation.",

                "error":
                    str(error),
            },
            status=500,
        )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_team_members(request):
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
                id=
                    organization_id
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

    if not (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=user,

            is_active=True,
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have access."
            },
            status=403,
        )

    memberships = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            is_active=True,
        )
        .select_related(
            "user",
            "primary_role",
        )
        .prefetch_related(
            "roles"
        )
        .order_by(
            "user__first_name"
        )
    )

    members = []

    for membership in memberships:

        member = (
            membership.user
        )

        members.append(
            {
                "membership_id":
                    membership.id,

                "user_id":
                    member.id,

                "full_name":
                    " ".join(
                        filter(
                            None,
                            [
                                member.first_name,
                                member.middle_name,
                                member.last_name,
                            ],
                        )
                    ),

                "email":
                    member.email,

                "phone_number":
                    member.phone_number,

                "profile_image":
                    member.profile_image,

                "is_active":
                    membership.is_active,

                "primary_role": (
                    {
                        "id":
                            membership
                            .primary_role.id,

                        "code":
                            membership
                            .primary_role.code,

                        "name":
                            membership
                            .primary_role.name,
                    }

                    if membership
                    .primary_role

                    else None
                ),

                "roles": [
                    {
                        "id":
                            role.id,

                        "code":
                            role.code,

                        "name":
                            role.name,
                    }
                    for role
                    in membership.roles.all()
                ],
            }
        )

    invitations = (
        OrganizationInvitation.objects
        .filter(
            organization=
                organization,

            status="pending",
        )
        .prefetch_related(
            "roles"
        )
        .order_by(
            "-created_at"
        )
    )

    invitation_data = []

    for invitation in invitations:

        invitation_data.append(
            {
                "id":
                    invitation.id,

                "full_name":
                    " ".join(
                        filter(
                            None,
                            [
                                invitation.first_name,
                                invitation.middle_name,
                                invitation.last_name,
                            ],
                        )
                    ),

                "email":
                    invitation.email,

                "phone_number":
                    invitation.phone_number,

                "status":
                    invitation.status,

                "expires_at":
                    invitation.expires_at
                    .isoformat(),

                "roles": [
                    {
                        "id":
                            role.id,

                        "code":
                            role.code,

                        "name":
                            role.name,
                    }
                    for role
                    in invitation.roles.all()
                ],
            }
        )

    return JsonResponse(
        {
            "summary": {
                "active_members":
                    len(members),

                "pending_invitations":
                    len(
                        invitation_data
                    ),

                "total":
                    len(members)
                    +
                    len(
                        invitation_data
                    ),
            },

            "members":
                members,

            "invitations":
                invitation_data,
        },
        status=200,
    )