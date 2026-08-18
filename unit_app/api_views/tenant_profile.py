from .common_imports import *

def get_tenant_profile_context(
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

    roles = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    if "tenant" not in roles:
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
                organization=organization,
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

    return (
        organization,
        membership,
        tenant,
        None,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_profile(request):
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
        membership,
        tenant,
        error_response,
    ) = get_tenant_profile_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    assignment = (
        TenantUnitAssignment.objects
        .filter(
            organization=organization,
            tenant=tenant,
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

                "monthly_rent":
                    str(
                        unit.monthly_rent
                    ),

                "status":
                    unit.status,
            },
        }

    user = request.user

    return JsonResponse(
        {
            "user": {
                "id":
                    user.id,

                "first_name":
                    user.first_name,

                "middle_name":
                    getattr(
                        user,
                        "middle_name",
                        "",
                    ),

                "last_name":
                    user.last_name,

                "email":
                    user.email,

                "phone_number":
                    getattr(
                        user,
                        "phone_number",
                        None,
                    ),

                "email_verified":
                    getattr(
                        user,
                        "email_verified",
                        False,
                    ),

                "phone_verified":
                    getattr(
                        user,
                        "phone_verified",
                        False,
                    ),

                "is_verified":
                    getattr(
                        user,
                        "is_verified",
                        False,
                    ),

                "status":
                    getattr(
                        user,
                        "status",
                        "active",
                    ),
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

                "tenant_type_label":
                    tenant.get_tenant_type_display(),

                "national_id_number":
                    tenant.national_id_number,

                "kra_pin":
                    tenant.kra_pin,

                "occupation":
                    tenant.occupation,

                "employer":
                    tenant.employer,

                "status":
                    tenant.status,
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

                "roles": list(
                    membership.roles
                    .filter(
                        is_active=True
                    )
                    .values_list(
                        "code",
                        flat=True,
                    )
                ),
            },

            "assignment":
                assignment_data,
        },
        status=200,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_tenant_profile(request):
    organization_id = (
        request.data.get(
            "organization_id"
        )
        or
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
        membership,
        tenant,
        error_response,
    ) = get_tenant_profile_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    data = request.data
    user = request.user

    full_name = str(
        data.get(
            "full_name",
            tenant.full_name,
        )
        or ""
    ).strip()

    phone_number = str(
        data.get(
            "phone_number",
            tenant.phone_number,
        )
        or ""
    ).strip()

    national_id = str(
        data.get(
            "national_id_number",
            tenant.national_id_number
            or "",
        )
        or ""
    ).strip()

    kra_pin = str(
        data.get(
            "kra_pin",
            tenant.kra_pin
            or "",
        )
        or ""
    ).strip().upper()

    occupation = str(
        data.get(
            "occupation",
            tenant.occupation
            or "",
        )
        or ""
    ).strip()

    employer = str(
        data.get(
            "employer",
            tenant.employer
            or "",
        )
        or ""
    ).strip()

    if not full_name:
        return JsonResponse(
            {
                "message":
                    "Full name is required."
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

    tenant.full_name = (
        full_name
    )

    tenant.phone_number = (
        phone_number
    )

    tenant.national_id_number = (
        national_id
        or None
    )

    tenant.kra_pin = (
        kra_pin
        or None
    )

    tenant.occupation = (
        occupation
        or None
    )

    tenant.employer = (
        employer
        or None
    )

    tenant.save(
        update_fields=[
            "full_name",
            "phone_number",
            "national_id_number",
            "kra_pin",
            "occupation",
            "employer",
            "updated_at",
        ]
    )

    # Keep login User profile in sync.

    user.first_name = (
        first_name
    )

    user.last_name = (
        last_name
    )

    if hasattr(
        user,
        "middle_name"
    ):
        user.middle_name = (
            middle_name
        )

    if hasattr(
        user,
        "phone_number"
    ):
        user.phone_number = (
            phone_number
        )

    user_fields = [
        "first_name",
        "last_name",
    ]

    if hasattr(
        user,
        "middle_name"
    ):
        user_fields.append(
            "middle_name"
        )

    if hasattr(
        user,
        "phone_number"
    ):
        user_fields.append(
            "phone_number"
        )

    user.save(
        update_fields=
            user_fields
    )

    return JsonResponse(
        {
            "message":
                "Profile updated successfully.",

            "tenant": {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "email":
                    tenant.email,

                "phone_number":
                    tenant.phone_number,

                "national_id_number":
                    tenant.national_id_number,

                "kra_pin":
                    tenant.kra_pin,

                "occupation":
                    tenant.occupation,

                "employer":
                    tenant.employer,
            },
        },
        status=200,
    )



from django.contrib.auth import (
    authenticate,
)

from django.contrib.auth.password_validation import (
    validate_password,
)

from django.core.exceptions import (
    ValidationError,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_change_password(
    request
):
    user = request.user

    current_password = (
        request.data.get(
            "current_password"
        )
    )

    new_password = (
        request.data.get(
            "new_password"
        )
    )

    confirm_password = (
        request.data.get(
            "confirm_password"
        )
    )

    if not current_password:
        return JsonResponse(
            {
                "message":
                    "Current password is required."
            },
            status=400,
        )

    if not new_password:
        return JsonResponse(
            {
                "message":
                    "New password is required."
            },
            status=400,
        )

    if (
        new_password !=
        confirm_password
    ):
        return JsonResponse(
            {
                "message":
                    "New passwords do not match."
            },
            status=400,
        )

    if not user.check_password(
        current_password
    ):
        return JsonResponse(
            {
                "message":
                    "Current password is incorrect."
            },
            status=400,
        )

    try:
        validate_password(
            new_password,
            user=user,
        )

    except ValidationError as error:
        return JsonResponse(
            {
                "message":
                    " ".join(
                        error.messages
                    )
            },
            status=400,
        )

    if user.check_password(
        new_password
    ):
        return JsonResponse(
            {
                "message":
                    "New password must be different from your current password."
            },
            status=400,
        )

    user.set_password(
        new_password
    )

    user.save(
        update_fields=[
            "password"
        ]
    )

    return JsonResponse(
        {
            "message":
                "Password changed successfully."
        },
        status=200,
    )