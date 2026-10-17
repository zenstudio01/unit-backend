from unit_app.api_views.common_imports import *


User = get_user_model()


def profile_error(message, status=400):
    return JsonResponse(
        {"success": False, "message": message},
        status=status,
    )


def serialize_profile(user, organization_id=None):
    data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name or "",
        "middle_name": getattr(user, "middle_name", "") or "",
        "last_name": user.last_name or "",
        "full_name": user.get_full_name().strip() or user.username,
        "email": user.email or "",
        "phone_number": getattr(user, "phone_number", "") or "",
        "profile_image": getattr(user, "profile_image", "") or "",
        "email_verified": getattr(user, "email_verified", False),
        "phone_verified": getattr(user, "phone_verified", False),
        "status": getattr(user, "status", ""),
        "date_joined": (
            user.date_joined.isoformat()
            if getattr(user, "date_joined", None)
            else None
        ),
        "organization": None,
        "roles": [],
        "membership_id": None,
    }

    if organization_id:
        membership = (
            OrganizationMembership.objects
            .filter(
                user=user,
                organization_id=organization_id,
                is_active=True,
            )
            .select_related("organization", "primary_role")
            .prefetch_related("roles")
            .first()
        )

        if membership:
            data["membership_id"] = membership.id
            data["organization"] = {
                "id": membership.organization_id,
                "name": membership.organization.name,
                "slug": getattr(
                    membership.organization, "slug", ""
                ),
            }

            roles = list(
                membership.roles.values_list("name", flat=True)
            )

            if (
                membership.primary_role
                and membership.primary_role.name not in roles
            ):
                roles.append(membership.primary_role.name)

            data["roles"] = roles

    return data


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def project_manager_profile(request):
    """
    GET:
        /api/v1/project-manager/profile/?organization_id=1

    PATCH:
        /api/v1/project-manager/profile/
        {
            "first_name": "Gideon",
            "middle_name": "Ngige",
            "last_name": "Ushindi",
            "email": "user@example.com",
            "phone_number": "0712345678",
            "profile_image": "https://example.com/profile.jpg"
        }
    """

    user = request.user

    organization_id = (
        request.query_params.get("organization_id")
        or request.data.get("organization_id")
    )

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "profile": serialize_profile(user, organization_id),
        })

    allowed_fields = {
        "first_name",
        "middle_name",
        "last_name",
        "email",
        "phone_number",
        "profile_image",
    }

    supplied_fields = allowed_fields.intersection(request.data.keys())

    if not supplied_fields:
        return profile_error(
            "Provide at least one profile field to update."
        )

    for field in supplied_fields:
        value = request.data.get(field)

        if value is None:
            value = ""

        if not isinstance(value, str):
            return profile_error(f"{field} must be text.")

        value = value.strip()

        if field == "email" and value:
            from django.core.validators import validate_email

            try:
                validate_email(value)
            except ValidationError:
                return profile_error("Enter a valid email address.")

            if User.objects.filter(email__iexact=value).exclude(
                pk=user.pk
            ).exists():
                return profile_error(
                    "This email address is already in use."
                )

        if field == "phone_number" and value:
            if User.objects.filter(
                phone_number=value
            ).exclude(pk=user.pk).exists():
                return profile_error(
                    "This phone number is already in use."
                )

        setattr(user, field, value)

    # Verification must be repeated if the corresponding contact changes.
    if "email" in supplied_fields:
        old_email = user.email
        new_email = request.data.get("email", "").strip()
        if old_email != new_email:
            if hasattr(user, "email_verified"):
                user.email_verified = False

    if "phone_number" in supplied_fields:
        old_phone = getattr(user, "_original_phone_number", None)
        # Do not mark the phone verified from a profile edit.
        if hasattr(user, "phone_verified"):
            user.phone_verified = False

    try:
        user.save()
    except Exception:
        return profile_error(
            "Could not update the profile. Check the supplied details."
        )

    return JsonResponse({
        "success": True,
        "message": "Profile updated successfully.",
        "profile": serialize_profile(user, organization_id),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def project_manager_change_password(request):
    """
    POST /api/v1/project-manager/profile/change-password/

    {
        "current_password": "...",
        "new_password": "...",
        "confirm_password": "..."
    }
    """

    current_password = request.data.get("current_password", "")
    new_password = request.data.get("new_password", "")
    confirm_password = request.data.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        return profile_error(
            "Current password, new password, and confirmation are required."
        )

    user = request.user

    if not user.check_password(current_password):
        return profile_error("Your current password is incorrect.", 400)

    if new_password != confirm_password:
        return profile_error("The new passwords do not match.")

    if current_password == new_password:
        return profile_error(
            "Your new password must differ from your current password."
        )

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        return JsonResponse({
            "success": False,
            "message": "The new password does not meet the requirements.",
            "errors": list(exc.messages),
        }, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Keeps Django session authentication valid if sessions are used.
    update_session_auth_hash(request, user)

    return JsonResponse({
        "success": True,
        "message": "Password changed successfully.",
    })
