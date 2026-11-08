
from copy import deepcopy

from django.db import transaction
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status

from unit_app.models import PlatformSetting

from .admin_settings_serializers import (
    DEFAULT_SETTINGS,
    SECTION_SERIALIZERS,
    AdminProfileSerializer,
    ChangePasswordSerializer,
)


class IsPlatformAdmin(BasePermission):
    message = "Platform administrator access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


def get_settings_instance():
    obj, _ = PlatformSetting.objects.get_or_create(pk=1)
    return obj


def serialize_settings(obj):
    return {
        section: {
            **deepcopy(defaults),
            **(getattr(obj, section) or {}),
        }
        for section, defaults in DEFAULT_SETTINGS.items()
    }


def serialize_profile(user):
    return {
        "id": user.pk,
        "username": user.get_username(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsPlatformAdmin])
def admin_platform_settings(request):
    if request.method == "GET":
        obj = get_settings_instance()
        return Response({
            "settings": serialize_settings(obj),
            "updated_at": obj.updated_at,
        })

    if not isinstance(request.data, dict):
        return Response(
            {"message": "Expected a JSON object."},
            status=400,
        )

    if not request.data:
        return Response(
            {"message": "No settings supplied."},
            status=400,
        )

    unknown_sections = (
        set(request.data) - set(SECTION_SERIALIZERS)
    )

    if unknown_sections:
        return Response(
            {
                "message": "Unknown settings sections.",
                "sections": sorted(unknown_sections),
            },
            status=400,
        )

    validated = {}
    errors = {}

    for section, incoming in request.data.items():
        if not isinstance(incoming, dict):
            errors[section] = "Expected an object."
            continue

        if not incoming:
            errors[section] = "No fields supplied."
            continue

        serializer_class = SECTION_SERIALIZERS[section]

        # Reject unknown fields explicitly.
        allowed = set(serializer_class().fields)
        unknown = set(incoming) - allowed

        if unknown:
            errors[section] = {
                field: ["Unknown field."]
                for field in unknown
            }
            continue

        serializer = serializer_class(
            data=incoming,
            partial=True,
        )

        if not serializer.is_valid():
            errors[section] = serializer.errors
        else:
            validated[section] = serializer.validated_data

    if errors:
        return Response(
            {"message": "Validation failed.", "errors": errors},
            status=400,
        )

    with transaction.atomic():
        obj = get_settings_instance()

        for section, updates in validated.items():
            current = {
                **deepcopy(DEFAULT_SETTINGS[section]),
                **(getattr(obj, section) or {}),
            }

            current.update(updates)

            # Revalidate the entire merged section.
            serializer = SECTION_SERIALIZERS[section](
                data=current
            )
            serializer.is_valid(raise_exception=True)

            setattr(
                obj,
                section,
                serializer.validated_data,
            )

        obj.save()

    return Response({
        "message": "Platform settings updated successfully.",
        "settings": serialize_settings(obj),
        "updated_at": obj.updated_at,
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsPlatformAdmin])
def admin_settings_profile(request):
    user = request.user

    if request.method == "GET":
        return Response(serialize_profile(user))

    serializer = AdminProfileSerializer(
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)

    for field, value in serializer.validated_data.items():
        setattr(user, field, value)

    if serializer.validated_data:
        user.save(
            update_fields=list(serializer.validated_data)
        )

    return Response({
        "message": "Profile updated successfully.",
        "user": serialize_profile(user),
    })


@api_view(["POST"])
@permission_classes([IsPlatformAdmin])
def admin_settings_change_password(request):
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    user = request.user
    user.set_password(
        serializer.validated_data["new_password"]
    )
    user.save(update_fields=["password"])

    # The frontend should clear existing JWTs and
    # require a new login after password changes.
    return Response({
        "message": (
            "Password changed successfully. "
            "Please sign in again."
        ),
        "requires_reauthentication": True,
    })
