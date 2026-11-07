
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import OrganizationMembership


User = get_user_model()


class IsPlatformAdmin(BasePermission):
    message = "Only UNIT platform administrators can access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def user_fields():
    return {
        field.name
        for field in User._meta.get_fields()
    }


def user_created_field():
    fields = user_fields()

    if "created_at" in fields:
        return "created_at"

    if "date_joined" in fields:
        return "date_joined"

    return None


def user_display_name(user):
    name = user.get_full_name().strip()
    return name or user.get_username()


def user_queryset():
    return User.objects.all()


def memberships_for_user(user):
    qs = (
        OrganizationMembership.objects
        .filter(user=user)
        .select_related("organization", "primary_role")
        .prefetch_related("roles")
    )

    results = []

    for membership in qs:
        role_names = [
            role.name
            for role in membership.roles.all()
        ]

        primary_role = (
            membership.primary_role.name
            if membership.primary_role_id
            else None
        )

        if primary_role and primary_role not in role_names:
            role_names.insert(0, primary_role)

        results.append({
            "id": membership.id,
            "organization_id": membership.organization_id,
            "organization_name": membership.organization.name,
            "primary_role": primary_role,
            "roles": role_names,
            "is_active": membership.is_active,
        })

    return results


def serialize_user(user, include_memberships=False):
    created_field = user_created_field()
    created_at = (
        getattr(user, created_field, None)
        if created_field else None
    )

    result = {
        "id": user.pk,
        "username": user.get_username(),
        "full_name": user_display_name(user),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "last_login": user.last_login,
        "created_at": created_at,
        "organization_count": (
            OrganizationMembership.objects
            .filter(user=user)
            .values("organization_id")
            .distinct()
            .count()
        ),
    }

    if include_memberships:
        result["memberships"] = memberships_for_user(user)

    return result


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_users(request):
    queryset = user_queryset()

    search = request.query_params.get(
        "search", ""
    ).strip()

    status_filter = request.query_params.get(
        "status", ""
    ).strip().lower()

    role_filter = request.query_params.get(
        "role", ""
    ).strip().lower()

    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    if search:
        query = (
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

        username_field = User.USERNAME_FIELD

        query |= Q(**{
            f"{username_field}__icontains": search
        })

        queryset = queryset.filter(query)

    if status_filter == "active":
        queryset = queryset.filter(is_active=True)

    elif status_filter == "inactive":
        queryset = queryset.filter(is_active=False)

    elif status_filter not in ("", "all"):
        return Response(
            {"message": "Invalid status filter."},
            status=400,
        )

    if role_filter == "superadmin":
        queryset = queryset.filter(is_superuser=True)

    elif role_filter == "admin":
        queryset = queryset.filter(
            is_staff=True,
            is_superuser=False,
        )

    elif role_filter == "user":
        queryset = queryset.filter(
            is_staff=False,
            is_superuser=False,
        )

    elif role_filter not in ("", "all"):
        return Response(
            {"message": "Invalid role filter."},
            status=400,
        )

    if organization_id:
        if not organization_id.isdigit():
            return Response(
                {"message": "Invalid organization ID."},
                status=400,
            )

        member_ids = (
            OrganizationMembership.objects
            .filter(organization_id=int(organization_id))
            .values("user_id")
        )

        queryset = queryset.filter(pk__in=member_ids)

    created_field = user_created_field()

    if created_field:
        queryset = queryset.order_by(
            f"-{created_field}", "-pk"
        )
    else:
        queryset = queryset.order_by("-pk")

    paginator = UserPagination()
    page = paginator.paginate_queryset(queryset, request)

    return paginator.get_paginated_response([
        serialize_user(user)
        for user in page
    ])


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_user_stats(request):
    queryset = User.objects.all()
    created_field = user_created_field()

    month_start = timezone.now().replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    new_this_month = None

    if created_field:
        new_this_month = queryset.filter(**{
            f"{created_field}__gte": month_start
        }).count()

    return Response({
        "total_users": queryset.count(),
        "active_users": queryset.filter(
            is_active=True
        ).count(),
        "inactive_users": queryset.filter(
            is_active=False
        ).count(),
        "platform_admins": queryset.filter(
            is_staff=True
        ).count(),
        "superusers": queryset.filter(
            is_superuser=True
        ).count(),
        "new_users_this_month": new_this_month,
        "users_with_organizations": (
            OrganizationMembership.objects
            .values("user_id")
            .distinct()
            .count()
        ),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_user_detail(request, user_id):
    user = get_object_or_404(
        user_queryset(),
        pk=user_id,
    )

    return Response({
        "user": serialize_user(
            user,
            include_memberships=True,
        ),
    })


@api_view(["PATCH"])
@permission_classes([IsPlatformAdmin])
def admin_user_status(request, user_id):
    value = request.data.get("is_active")

    if type(value) is not bool:
        return Response(
            {
                "message": (
                    "is_active must be true or false."
                )
            },
            status=400,
        )

    with transaction.atomic():
        user = get_object_or_404(
            User.objects.select_for_update(),
            pk=user_id,
        )

        # Prevent self-deactivation
        if user.pk == request.user.pk and not value:
            return Response(
                {
                    "message": (
                        "You cannot deactivate your own account."
                    )
                },
                status=403,
            )

        # Protect superuser accounts
        if user.is_superuser:
            return Response(
                {
                    "message": (
                        "Superuser account status cannot be "
                        "changed from this page."
                    )
                },
                status=403,
            )

        # Only superusers may change staff accounts
        if user.is_staff and not request.user.is_superuser:
            return Response(
                {
                    "message": (
                        "Only a superuser can change "
                        "another administrator's account status."
                    )
                },
                status=403,
            )

        user.is_active = value
        user.save(update_fields=["is_active"])

    return Response({
        "message": (
            "User account activated successfully."
            if value
            else "User account deactivated successfully."
        ),
        "user": serialize_user(user),
    })
