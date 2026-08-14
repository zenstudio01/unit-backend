from .common_imports import *


@api_view(["GET"])
@permission_classes([AllowAny])
def get_invitation_details(request):
    token = str(
        request.GET.get(
            "token",
            ""
        )
    ).strip()

    if not token:
        return JsonResponse(
            {
                "message":
                    "Invitation token is required."
            },
            status=400,
        )

    try:
        invitation = (
            OrganizationInvitation.objects
            .select_related(
                "organization",
                "primary_role",
                "invited_by",
            )
            .prefetch_related(
                "roles"
            )
            .get(
                token=token
            )
        )

    except OrganizationInvitation.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Invalid invitation link."
            },
            status=404,
        )

    if invitation.status == "accepted":
        return JsonResponse(
            {
                "message":
                    "This invitation has already been accepted.",
                "status":
                    "accepted",
            },
            status=400,
        )

    if invitation.status == "cancelled":
        return JsonResponse(
            {
                "message":
                    "This invitation has been cancelled.",
                "status":
                    "cancelled",
            },
            status=400,
        )

    if invitation.status == "expired":
        return JsonResponse(
            {
                "message":
                    "This invitation has expired.",
                "status":
                    "expired",
            },
            status=400,
        )

    if invitation.expires_at < timezone.now():
        invitation.status = "expired"

        invitation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "This invitation has expired.",
                "status":
                    "expired",
            },
            status=400,
        )

    roles = [
        {
            "id":
                role.id,

            "code":
                role.code,

            "name":
                role.get_name_display()
                if hasattr(
                    role,
                    "get_name_display"
                )
                else role.name,
        }
        for role
        in invitation.roles.all()
    ]

    return JsonResponse(
        {
            "message":
                "Invitation is valid.",

            "invitation": {
                "id":
                    invitation.id,

                "first_name":
                    invitation.first_name,

                "middle_name":
                    invitation.middle_name,

                "last_name":
                    invitation.last_name,

                "email":
                    invitation.email,

                "phone_number":
                    invitation.phone_number,

                "status":
                    invitation.status,

                "organization": {
                    "id":
                        invitation.organization.id,

                    "name":
                        invitation.organization.name,

                    "logo":
                        invitation.organization.logo,

                    "city":
                        invitation.organization.city,

                    "county":
                        invitation.organization.county,
                },

                "roles":
                    roles,

                "primary_role": (
                    {
                        "id":
                            invitation.primary_role.id,

                        "code":
                            invitation.primary_role.code,

                        "name":
                            invitation.primary_role
                            .get_name_display()
                            if hasattr(
                                invitation.primary_role,
                                "get_name_display",
                            )
                            else invitation.primary_role.name,
                    }
                    if invitation.primary_role
                    else None
                ),

                "invited_by": {
                    "id":
                        invitation.invited_by.id,

                    "name":
                        " ".join(
                            filter(
                                None,
                                [
                                    invitation.invited_by.first_name,
                                    invitation.invited_by.middle_name,
                                    invitation.invited_by.last_name,
                                ],
                            )
                        ),
                }
                if invitation.invited_by
                else None,

                "expires_at":
                    invitation.expires_at.isoformat(),
            },
        },
        status=200,
    )





User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def accept_invitation(request):
    data = request.data

    token = str(
        data.get(
            "token",
            ""
        )
    ).strip()

    password = data.get(
        "password"
    )

    confirm_password = data.get(
        "confirm_password"
    )

    if not token:
        return JsonResponse(
            {
                "message":
                    "Invitation token is required."
            },
            status=400,
        )

    if not password:
        return JsonResponse(
            {
                "message":
                    "Password is required."
            },
            status=400,
        )

    if not confirm_password:
        return JsonResponse(
            {
                "message":
                    "Confirm password is required."
            },
            status=400,
        )

    if password != confirm_password:
        return JsonResponse(
            {
                "message":
                    "Passwords do not match."
            },
            status=400,
        )

    try:
        validate_password(
            password
        )

    except ValidationError as error:
        return JsonResponse(
            {
                "message":
                    "Password does not meet requirements.",

                "errors":
                    list(
                        error.messages
                    ),
            },
            status=400,
        )

    try:
        invitation = (
            OrganizationInvitation.objects
            .select_related(
                "organization",
                "primary_role",
            )
            .prefetch_related(
                "roles"
            )
            .get(
                token=token
            )
        )

    except OrganizationInvitation.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Invalid invitation link."
            },
            status=404,
        )

    if invitation.status != "pending":
        return JsonResponse(
            {
                "message":
                    f"This invitation is {invitation.status}.",
                "status":
                    invitation.status,
            },
            status=400,
        )

    if invitation.expires_at < timezone.now():
        invitation.status = "expired"

        invitation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "This invitation has expired."
            },
            status=400,
        )

    organization = (
        invitation.organization
    )

    invited_roles = list(
        invitation.roles.all()
    )

    try:
        with transaction.atomic():

            # =============================================
            # USER
            # =============================================

            user = (
                User.objects
                .filter(
                    email__iexact=
                        invitation.email
                )
                .first()
            )

            if not user:

                username = (
                    invitation.email.lower()
                )

                user = (
                    User.objects.create_user(
                        username=
                            username,

                        email=
                            invitation.email.lower(),

                        password=
                            password,

                        first_name=
                            invitation.first_name,

                        middle_name=
                            invitation.middle_name,

                        last_name=
                            invitation.last_name,

                        phone_number=
                            invitation.phone_number,

                        email_verified=
                            True,

                        is_verified=
                            True,

                        status=
                            "active",
                    )
                )

            else:
                # Existing user should not have their
                # current password overwritten automatically.
                #
                # If they came through this invitation
                # activation flow and do not have a usable
                # password, set one.

                if not user.has_usable_password():
                    user.set_password(
                        password
                    )

                    user.save(
                        update_fields=[
                            "password"
                        ]
                    )

            # =============================================
            # MEMBERSHIP
            # =============================================

            membership = (
                OrganizationMembership.objects
                .filter(
                    organization=
                        organization,

                    user=user,
                )
                .first()
            )

            if membership:
                if membership.is_active:
                    return JsonResponse(
                        {
                            "message":
                                "You already belong to this organization."
                        },
                        status=400,
                    )

                membership.is_active = True

                if invitation.primary_role:
                    membership.primary_role = (
                        invitation.primary_role
                    )

                membership.save()

            else:
                membership = (
                    OrganizationMembership.objects.create(
                        organization=
                            organization,

                        user=user,

                        primary_role=
                            invitation.primary_role,

                        is_active=True,
                    )
                )

            # =============================================
            # ASSIGN ROLES
            # =============================================

            membership.roles.set(
                invited_roles
            )

            # =============================================
            # ACCEPT INVITATION
            # =============================================

            invitation.status = (
                "accepted"
            )

            invitation.accepted_at = (
                timezone.now()
            )

            invitation.save(
                update_fields=[
                    "status",
                    "accepted_at",
                    "updated_at",
                ]
            )

            # =============================================
            # NOTIFICATION
            # =============================================

            Notification.objects.create(
                user=user,

                organization=
                    organization,

                notification_type=
                    "organization",

                title=
                    "Organization Access Activated",

                message=(
                    f"You now have access to "
                    f"{organization.name}."
                ),
            )

        return JsonResponse(
            {
                "message":
                    "Invitation accepted successfully. You can now sign in.",

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
                },

                "organization": {
                    "id":
                        organization.id,

                    "name":
                        organization.name,
                },

                "membership": {
                    "id":
                        membership.id,

                    "primary_role": (
                        {
                            "id":
                                membership.primary_role.id,

                            "code":
                                membership.primary_role.code,

                            "name":
                                membership.primary_role
                                .get_name_display()
                                if hasattr(
                                    membership.primary_role,
                                    "get_name_display",
                                )
                                else membership.primary_role.name,
                        }

                        if membership.primary_role

                        else None
                    ),

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
                        }

                        for role
                        in membership.roles.all()
                    ],
                },
            },
            status=200,
        )

    except Exception as error:
        print(
            "ACCEPT INVITATION ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to activate account.",

                "error":
                    str(error),
            },
            status=500,
        )






User = get_user_model()


def accept_invitation_web(request):
    token = str(
        request.GET.get("token", "")
        or request.POST.get("token", "")
    ).strip()

    # =====================================================
    # TOKEN REQUIRED
    # =====================================================

    if not token:
        return render(
            request,
            "invitations/invalid_invitation.html",
            {
                "message":
                    "The invitation link is invalid."
            },
        )

    # =====================================================
    # INVITATION
    # =====================================================

    try:
        invitation = (
            OrganizationInvitation.objects
            .select_related(
                "organization",
                "primary_role",
                "invited_by",
            )
            .prefetch_related(
                "roles"
            )
            .get(
                token=token
            )
        )

    except OrganizationInvitation.DoesNotExist:
        return render(
            request,
            "invitations/invalid_invitation.html",
            {
                "message":
                    "This invitation does not exist."
            },
        )

    # =====================================================
    # ALREADY ACCEPTED
    # =====================================================

    if invitation.status == "accepted":
        return render(
            request,
            "invitations/already_accepted.html",
            {
                "invitation":
                    invitation,
            },
        )

    # =====================================================
    # CANCELLED
    # =====================================================

    if invitation.status == "cancelled":
        return render(
            request,
            "invitations/invalid_invitation.html",
            {
                "message":
                    "This invitation has been cancelled."
            },
        )

    # =====================================================
    # EXPIRED
    # =====================================================

    if (
        invitation.status == "expired"
        or invitation.expires_at < timezone.now()
    ):
        if invitation.status != "expired":
            invitation.status = "expired"

            invitation.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return render(
            request,
            "invitations/expired_invitation.html",
            {
                "invitation":
                    invitation,
            },
        )

    # =====================================================
    # ROLE DATA
    # =====================================================

    roles = (
        invitation.roles.all()
    )

    # =====================================================
    # GET
    #
    # Show invitation information + password form.
    # =====================================================

    if request.method == "GET":
        return render(
            request,
            "invitations/accept_invitation.html",
            {
                "invitation":
                    invitation,

                "organization":
                    invitation.organization,

                "roles":
                    roles,

                "token":
                    token,
            },
        )

    # =====================================================
    # POST
    # =====================================================

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

    # =====================================================
    # PASSWORD REQUIRED
    # =====================================================

    if not password:
        return render(
            request,
            "invitations/accept_invitation.html",
            {
                "invitation":
                    invitation,

                "organization":
                    invitation.organization,

                "roles":
                    roles,

                "token":
                    token,

                "error":
                    "Password is required.",
            },
        )

    # =====================================================
    # PASSWORD MATCH
    # =====================================================

    if password != confirm_password:
        return render(
            request,
            "invitations/accept_invitation.html",
            {
                "invitation":
                    invitation,

                "organization":
                    invitation.organization,

                "roles":
                    roles,

                "token":
                    token,

                "error":
                    "Passwords do not match.",
            },
        )

    # =====================================================
    # DJANGO PASSWORD VALIDATION
    # =====================================================

    try:
        validate_password(
            password
        )

    except ValidationError as error:
        return render(
            request,
            "invitations/accept_invitation.html",
            {
                "invitation":
                    invitation,

                "organization":
                    invitation.organization,

                "roles":
                    roles,

                "token":
                    token,

                "error":
                    " ".join(
                        error.messages
                    ),
            },
        )

    # =====================================================
    # ACTIVATE
    # =====================================================

    try:
        with transaction.atomic():

            organization = (
                invitation.organization
            )

            # ---------------------------------------------
            # USER
            # ---------------------------------------------

            user = (
                User.objects
                .filter(
                    email__iexact=
                        invitation.email
                )
                .first()
            )

            if not user:
                user = (
                    User.objects
                    .create_user(
                        username=
                            invitation.email.lower(),

                        email=
                            invitation.email.lower(),

                        password=
                            password,

                        first_name=
                            invitation.first_name,

                        middle_name=
                            invitation.middle_name,

                        last_name=
                            invitation.last_name,

                        phone_number=
                            invitation.phone_number,

                        email_verified=True,

                        is_verified=True,

                        status="active",
                    )
                )

            else:
                # Existing account:
                # do not overwrite an existing password.

                if not user.has_usable_password():
                    user.set_password(
                        password
                    )

                    user.save(
                        update_fields=[
                            "password"
                        ]
                    )

            # ---------------------------------------------
            # MEMBERSHIP
            # ---------------------------------------------

            membership = (
                OrganizationMembership.objects
                .filter(
                    user=user,

                    organization=
                        organization,
                )
                .first()
            )

            if not membership:
                membership = (
                    OrganizationMembership.objects
                    .create(
                        user=user,

                        organization=
                            organization,

                        primary_role=
                            invitation.primary_role,

                        is_active=True,
                    )
                )

            else:
                membership.is_active = True

                membership.primary_role = (
                    invitation.primary_role
                )

                membership.save()

            # ---------------------------------------------
            # ROLES
            # ---------------------------------------------

            membership.roles.set(
                roles
            )

            # ---------------------------------------------
            # INVITATION
            # ---------------------------------------------

            invitation.status = (
                "accepted"
            )

            invitation.accepted_at = (
                timezone.now()
            )

            invitation.save(
                update_fields=[
                    "status",
                    "accepted_at",
                    "updated_at",
                ]
            )

            # ---------------------------------------------
            # NOTIFICATION
            # ---------------------------------------------

            Notification.objects.create(
                user=user,

                organization=
                    organization,

                notification_type=
                    "organization",

                title=
                    "Organization Access Activated",

                message=(
                    f"Your access to "
                    f"{organization.name} "
                    f"has been activated."
                ),
            )

        # =================================================
        # SUCCESS PAGE
        # =================================================

        return render(
            request,
            "invitations/invitation_success.html",
            {
                "user":
                    user,

                "organization":
                    invitation.organization,

                "roles":
                    roles,
            },
        )

    except Exception as error:
        print(
            "WEB INVITATION ERROR:",
            str(error),
        )

        return render(
            request,
            "invitations/accept_invitation.html",
            {
                "invitation":
                    invitation,

                "organization":
                    invitation.organization,

                "roles":
                    roles,

                "token":
                    token,

                "error":
                    "Unable to activate your account. Please try again.",
            },
        )