from .common_imports import *

import math
import secrets
import string

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


# ============================================================
# ADMIN HELPERS
# ============================================================

def is_platform_admin(user):
    """
    Only platform administrators and Django superusers
    can access the platform administration APIs.
    """

    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_superuser
            or user.role == "platform_admin"
        )
    )


def platform_admin_required(view_function):
    """
    Simple custom decorator for function-based DRF views.
    """

    def wrapped_view(request, *args, **kwargs):
        if not is_platform_admin(request.user):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to perform "
                        "this platform administration action."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return view_function(request, *args, **kwargs)

    return wrapped_view


def normalize_boolean(value, default=None):
    """
    Convert JSON and form-data values to boolean.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized_value = value.strip().lower()

        if normalized_value in {
            "true",
            "1",
            "yes",
            "on",
        }:
            return True

        if normalized_value in {
            "false",
            "0",
            "no",
            "off",
        }:
            return False

    return bool(value)


def get_user_operational_roles(user):
    """
    Return every operational role connected to a user.

    A user may belong to multiple companies and may have
    more than one operational role.
    """

    roles = []

    staff_memberships = (
        CompanyStaff.objects
        .filter(user=user, is_active=True)
        .select_related("company")
    )

    for membership in staff_memberships:
        roles.append({
            "type": "company_staff",
            "role": membership.role,
            "company_id": membership.company_id,
            "company_name": membership.company.name,
            "membership_id": membership.id,
        })

    landlord_profiles = (
        Landlord.objects
        .filter(user=user)
        .select_related("company")
    )

    for landlord in landlord_profiles:
        roles.append({
            "type": "landlord",
            "role": "landlord",
            "company_id": landlord.company_id,
            "company_name": landlord.company.name,
            "profile_id": landlord.id,
        })

    tenant_profiles = (
        Tenant.objects
        .filter(user=user)
        .select_related("company")
    )

    for tenant in tenant_profiles:
        roles.append({
            "type": "tenant",
            "role": "tenant",
            "company_id": tenant.company_id,
            "company_name": tenant.company.name,
            "profile_id": tenant.id,
        })

    service_provider = (
        ServiceProvider.objects
        .filter(user=user)
        .first()
    )

    if service_provider:
        roles.append({
            "type": "service_provider",
            "role": "service_provider",
            "profile_id": service_provider.id,
        })

    professional_memberships = (
        Professional.objects
        .filter(user=user)
        .select_related("company")
    )

    for professional in professional_memberships:
        roles.append({
            "type": "professional",
            "role": "professional",
            "company_id": professional.company_id,
            "company_name": professional.company.name,
            "profile_id": professional.id,
            "professional_title": (
                professional.professional_title
            ),
        })

    return roles


def get_user_assets_summary(user):
    """
    Calculate assets and memberships associated with a user.
    """

    company_ids = list(
        CompanyStaff.objects
        .filter(
            user=user,
            is_active=True,
            role__in=["admin", "property_manager"],
        )
        .values_list("company_id", flat=True)
    )

    managed_property_count = (
        Property.objects
        .filter(manager__user=user)
        .distinct()
        .count()
    )

    company_property_count = (
        Property.objects
        .filter(company_id__in=company_ids)
        .distinct()
        .count()
    )

    landlord_property_count = (
        Property.objects
        .filter(landlord__user=user)
        .distinct()
        .count()
    )

    tenant_profile_count = (
        Tenant.objects
        .filter(user=user)
        .count()
    )

    company_count = (
        CompanyStaff.objects
        .filter(user=user, is_active=True)
        .values("company_id")
        .distinct()
        .count()
    )

    return {
        "companies": company_count,
        "managed_properties": managed_property_count,
        "company_properties": company_property_count,
        "landlord_properties": landlord_property_count,
        "tenant_profiles": tenant_profile_count,
        "total": (
            managed_property_count
            + landlord_property_count
            + tenant_profile_count
        ),
    }


def serialize_admin_user(user):
    operational_roles = get_user_operational_roles(user)
    assets = get_user_assets_summary(user)

    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "platform_role": user.role,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "profile_image": user.profile_image,
        "operational_roles": operational_roles,
        "assets": assets,
        "created_at": user.created_at.isoformat(),
        "last_login": (
            user.last_login.isoformat()
            if user.last_login
            else None
        ),
    }


def generate_temporary_password(length=12):
    """
    Generate a temporary password with mixed character types.
    """

    alphabet = (
        string.ascii_letters
        + string.digits
        + "!@#$%&*"
    )

    while True:
        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        has_lowercase = any(
            character.islower()
            for character in password
        )

        has_uppercase = any(
            character.isupper()
            for character in password
        )

        has_number = any(
            character.isdigit()
            for character in password
        )

        has_symbol = any(
            character in "!@#$%&*"
            for character in password
        )

        if all([
            has_lowercase,
            has_uppercase,
            has_number,
            has_symbol,
        ]):
            return password


def humanize_time(timestamp):
    """
    Convert a datetime into a readable relative time.
    """

    if not timestamp:
        return "Unknown"

    difference = timezone.now() - timestamp

    if difference.total_seconds() < 60:
        return "Just now"

    if difference.total_seconds() < 3600:
        minutes = int(
            difference.total_seconds() // 60
        )

        return f"{minutes}m ago"

    if difference.total_seconds() < 86400:
        hours = int(
            difference.total_seconds() // 3600
        )

        return f"{hours}h ago"

    days = difference.days

    if days == 1:
        return "Yesterday"

    if days < 30:
        return f"{days} days ago"

    return timestamp.strftime("%d %b %Y")


# ============================================================
# ADMIN USERS LIST
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_users_list(request):
    """
    Return a searchable and paginated list of all platform users.

    Supported filters:

    search:
        Search by name, email, username or phone number.

    role:
        platform_admin
        user
        company_admin
        property_manager
        accountant
        leasing_officer
        maintenance_officer
        landlord
        tenant
        service_provider
        professional

    status:
        active
        inactive
        verified
        unverified
        email_verified
        email_unverified
    """

    try:
        queryset = (
            User.objects
            .all()
            .order_by("-created_at")
        )

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        role_filter = str(
            request.GET.get("role", "")
        ).strip().lower()

        status_filter = str(
            request.GET.get("status", "")
        ).strip().lower()

        # ----------------------------------------------------
        # Search filter
        # ----------------------------------------------------

        if search_query:
            queryset = queryset.filter(
                Q(
                    full_name__icontains=search_query
                )
                | Q(
                    email__icontains=search_query
                )
                | Q(
                    phone_number__icontains=search_query
                )
                | Q(
                    username__icontains=search_query
                )
                | Q(
                    company_memberships__company__name__icontains=
                    search_query
                )
            ).distinct()

        # ----------------------------------------------------
        # Role filter
        # ----------------------------------------------------

        platform_roles = {
            "platform_admin",
            "user",
        }

        company_roles = {
            "admin",
            "company_admin",
            "property_manager",
            "accountant",
            "leasing_officer",
            "maintenance_officer",
        }

        if role_filter in platform_roles:
            queryset = queryset.filter(
                role=role_filter
            )

        elif role_filter in company_roles:
            company_role = role_filter

            if role_filter == "company_admin":
                company_role = "admin"

            queryset = queryset.filter(
                company_memberships__role=company_role,
                company_memberships__is_active=True,
            ).distinct()

        elif role_filter == "landlord":
            queryset = queryset.filter(
                landlord_profiles__isnull=False
            ).distinct()

        elif role_filter == "tenant":
            queryset = queryset.filter(
                tenant_profiles__isnull=False
            ).distinct()

        elif role_filter == "service_provider":
            queryset = queryset.filter(
                service_provider_profile__isnull=False
            ).distinct()

        elif role_filter == "professional":
            queryset = queryset.filter(
                professional_profile__isnull=False
            ).distinct()

        # ----------------------------------------------------
        # Status filter
        # ----------------------------------------------------

        if status_filter == "verified":
            queryset = queryset.filter(
                is_verified=True
            )

        elif status_filter == "unverified":
            queryset = queryset.filter(
                is_verified=False
            )

        elif status_filter == "active":
            queryset = queryset.filter(
                is_active=True
            )

        elif status_filter == "inactive":
            queryset = queryset.filter(
                is_active=False
            )

        elif status_filter == "email_verified":
            queryset = queryset.filter(
                email_verified=True
            )

        elif status_filter == "email_unverified":
            queryset = queryset.filter(
                email_verified=False
            )

        # ----------------------------------------------------
        # Summary metrics
        # ----------------------------------------------------

        summary_data = {
            "total_users": User.objects.count(),

            "platform_admins": User.objects.filter(
                Q(role="platform_admin")
                | Q(is_superuser=True)
            ).distinct().count(),

            "company_admins": CompanyStaff.objects.filter(
                role="admin",
                is_active=True,
            ).values(
                "user_id"
            ).distinct().count(),

            "property_managers": CompanyStaff.objects.filter(
                role="property_manager",
                is_active=True,
            ).values(
                "user_id"
            ).distinct().count(),

            "accountants": CompanyStaff.objects.filter(
                role="accountant",
                is_active=True,
            ).values(
                "user_id"
            ).distinct().count(),

            "leasing_officers": CompanyStaff.objects.filter(
                role="leasing_officer",
                is_active=True,
            ).values(
                "user_id"
            ).distinct().count(),

            "maintenance_officers": CompanyStaff.objects.filter(
                role="maintenance_officer",
                is_active=True,
            ).values(
                "user_id"
            ).distinct().count(),

            "landlords": Landlord.objects.values(
                "user_id"
            ).distinct().count(),

            "tenants": Tenant.objects.values(
                "user_id"
            ).distinct().count(),

            "service_providers": ServiceProvider.objects.values(
                "user_id"
            ).distinct().count(),

            "professionals": Professional.objects.values(
                "user_id"
            ).distinct().count(),

            "active_users": User.objects.filter(
                is_active=True
            ).count(),

            "inactive_users": User.objects.filter(
                is_active=False
            ).count(),

            "verified_users": User.objects.filter(
                is_verified=True
            ).count(),

            "unverified_users": User.objects.filter(
                is_verified=False
            ).count(),
        }

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------

        try:
            page = int(
                request.GET.get("page", 1)
            )

            limit = int(
                request.GET.get("limit", 10)
            )

        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Page and limit must be valid integers."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        total_count = queryset.count()
        total_pages = math.ceil(
            total_count / limit
        ) if total_count else 0

        start = (page - 1) * limit
        end = start + limit

        paginated_users = queryset[start:end]

        results = [
            serialize_admin_user(user)
            for user in paginated_users
        ]

        return Response(
            {
                "success": True,
                "count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "summary": summary_data,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "ADMIN USERS LIST ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving users."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# TOGGLE USER ACTIVE STATUS
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_toggle_active(request, pk):
    try:
        user_node = User.objects.get(pk=pk)

        if user_node.pk == request.user.pk:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You cannot deactivate your own account."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_node.is_superuser:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A superuser account cannot be deactivated "
                        "through this endpoint."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        requested_state = normalize_boolean(
            request.data.get("is_active"),
            default=None,
        )

        if requested_state is None:
            user_node.is_active = not user_node.is_active
        else:
            user_node.is_active = requested_state

        user_node.save(
            update_fields=["is_active"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "User account status updated successfully."
                ),
                "user_id": user_node.id,
                "is_active": user_node.is_active,
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User record was not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "Failed to update the user status."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# VERIFY USER
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_verify_user(request, pk):
    try:
        user_node = User.objects.get(pk=pk)

        is_verified = normalize_boolean(
            request.data.get(
                "is_verified",
                True,
            ),
            default=True,
        )

        user_node.is_verified = is_verified

        user_node.save(
            update_fields=["is_verified"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "User verification status updated successfully."
                ),
                "user_id": user_node.id,
                "is_verified": user_node.is_verified,
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User record was not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "Failed to update verification status."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# ADMIN RESET USER PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_reset_password(request, pk):
    """
    Generate a secure temporary password.

    The temporary password is returned only once in this response.
    The frontend should require the administrator to copy it
    immediately and deliver it through a secure channel.
    """

    try:
        user_node = User.objects.get(pk=pk)

        if user_node.is_superuser:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A superuser password cannot be reset "
                        "through this endpoint."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        temporary_password = generate_temporary_password()

        user_node.set_password(
            temporary_password
        )

        user_node.save(
            update_fields=["password"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "A temporary password was generated successfully."
                ),
                "user_id": user_node.id,
                "temporary_password": temporary_password,
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User record was not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "Failed to reset the user password."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# UPDATE PLATFORM USER PROFILE
# ============================================================

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_update_profile(request, pk):
    """
    Update platform-level user properties.

    CompanyStaff roles must not be changed using this endpoint.
    Use a company staff-management endpoint for company roles.
    """

    try:
        user_node = User.objects.get(pk=pk)

        allowed_platform_roles = {
            "user",
            "platform_admin",
        }

        platform_role = request.data.get(
            "platform_role",
            request.data.get("role"),
        )

        if platform_role is not None:
            platform_role = str(
                platform_role
            ).strip().lower()

            if platform_role not in allowed_platform_roles:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Invalid platform role. Company roles "
                            "must be updated through CompanyStaff."
                        ),
                        "allowed_roles": list(
                            allowed_platform_roles
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                user_node.pk == request.user.pk
                and platform_role != "platform_admin"
            ):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "You cannot remove your own platform "
                            "administrator role."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_node.role = platform_role

        if "is_active" in request.data:
            is_active = normalize_boolean(
                request.data.get("is_active"),
                default=user_node.is_active,
            )

            if (
                user_node.pk == request.user.pk
                and not is_active
            ):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "You cannot deactivate your own account."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_node.is_active = is_active

        if "is_verified" in request.data:
            user_node.is_verified = normalize_boolean(
                request.data.get("is_verified"),
                default=user_node.is_verified,
            )

        if "email_verified" in request.data:
            user_node.email_verified = normalize_boolean(
                request.data.get("email_verified"),
                default=user_node.email_verified,
            )

        user_node.save()

        return Response(
            {
                "success": True,
                "message": (
                    "User profile updated successfully."
                ),
                "user": serialize_admin_user(user_node),
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User record was not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "Failed to update the user profile."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# DELETE PLATFORM USER
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_delete_user(request, pk):
    try:
        user_node = User.objects.get(pk=pk)

        if user_node.pk == request.user.pk:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You cannot delete your own account."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_node.is_superuser:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A superuser account cannot be deleted "
                        "through this endpoint."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user_details = {
            "id": user_node.id,
            "email": user_node.email,
            "full_name": user_node.full_name,
        }

        with transaction.atomic():
            user_node.delete()

        return Response(
            {
                "success": True,
                "message": (
                    "User account deleted successfully."
                ),
                "deleted_user": user_details,
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User record was not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception as error:
        print(
            "ADMIN DELETE USER ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "The user could not be deleted. The account "
                    "may be connected to protected leases, payments, "
                    "companies or financial records."
                ),
                "error": str(error),
            },
            status=status.HTTP_409_CONFLICT,
        )


# ============================================================
# PLATFORM DASHBOARD METRICS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@platform_admin_required
def admin_dashboard_metrics(request):
    """
    Return platform-wide company, user, unit, lease,
    maintenance and financial metrics.
    """

    try:
        timeframe = str(
            request.GET.get(
                "timeframe",
                "last_6_months",
            )
        ).strip().lower()

        now = timezone.now()

        # ----------------------------------------------------
        # Date range
        # ----------------------------------------------------

        if timeframe == "today":
            start_date = now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        elif timeframe == "this_week":
            start_date = (
                now
                - timedelta(days=now.weekday())
            ).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        elif timeframe == "this_month":
            start_date = now.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        elif timeframe == "this_year":
            start_date = now.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        else:
            # Approximately six months including current month.
            start_date = (
                now - timedelta(days=180)
            ).replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        # ----------------------------------------------------
        # Global metrics
        # ----------------------------------------------------

        total_users_count = User.objects.count()
        active_users_count = User.objects.filter(
            is_active=True
        ).count()

        total_companies_count = Company.objects.count()

        verified_companies_count = Company.objects.filter(
            is_verified=True
        ).count()

        total_properties_count = Property.objects.count()
        total_units_count = Unit.objects.count()

        # Prefer active leases instead of manually trusting unit status.
        occupied_units_count = (
            Lease.objects
            .filter(
                status="active",
                lease_start__lte=now.date(),
                lease_end__gte=now.date(),
            )
            .values("unit_id")
            .distinct()
            .count()
        )

        available_units_count = max(
            total_units_count - occupied_units_count,
            0,
        )

        occupancy_rate = (
            occupied_units_count
            / total_units_count
            * 100
        ) if total_units_count else 0

        open_tickets_count = (
            MaintenanceRequest.objects
            .exclude(
                status__in=[
                    "completed",
                    "cancelled",
                ]
            )
            .count()
        )

        overdue_invoices_count = (
            RentInvoice.objects
            .filter(
                due_date__lt=now.date(),
            )
            .exclude(
                status__in=[
                    "paid",
                    "cancelled",
                ]
            )
            .count()
        )

        active_subscriptions_count = (
            Subscription.objects
            .filter(
                status="active",
                start_date__lte=now,
                end_date__gte=now,
            )
            .count()
        )

        # ----------------------------------------------------
        # Financial metrics
        # ----------------------------------------------------

        successful_payments = RentPayment.objects.filter(
            status="success"
        )

        gmv_volume_total = (
            successful_payments
            .aggregate(
                total=Sum("amount")
            )
            .get("total")
            or 0
        )

        timeframe_revenue = (
            successful_payments
            .filter(
                paid_at__gte=start_date,
                paid_at__lte=now,
            )
            .aggregate(
                total=Sum("amount")
            )
            .get("total")
            or 0
        )

        # ----------------------------------------------------
        # Actual monthly revenue chart
        # ----------------------------------------------------

        revenue_queryset = (
            successful_payments
            .filter(
                paid_at__gte=start_date,
                paid_at__lte=now,
            )
            .annotate(
                month=TruncMonth("paid_at")
            )
            .values("month")
            .annotate(
                volume=Sum("amount"),
                transactions=Count("id"),
            )
            .order_by("month")
        )

        revenue_chart_history = []

        for entry in revenue_queryset:
            revenue_chart_history.append({
                "name": entry[
                    "month"
                ].strftime("%b %Y"),
                "volume": float(
                    entry["volume"] or 0
                ),
                "transactions": entry[
                    "transactions"
                ],
            })

        # ----------------------------------------------------
        # Operational demographic chart
        # ----------------------------------------------------

        demographics_chart_data = [
            {
                "role": "Platform Admins",
                "count": User.objects.filter(
                    Q(role="platform_admin")
                    | Q(is_superuser=True)
                ).distinct().count(),
            },
            {
                "role": "Company Admins",
                "count": CompanyStaff.objects.filter(
                    role="admin",
                    is_active=True,
                ).values(
                    "user_id"
                ).distinct().count(),
            },
            {
                "role": "Property Managers",
                "count": CompanyStaff.objects.filter(
                    role="property_manager",
                    is_active=True,
                ).values(
                    "user_id"
                ).distinct().count(),
            },
            {
                "role": "Accountants",
                "count": CompanyStaff.objects.filter(
                    role="accountant",
                    is_active=True,
                ).values(
                    "user_id"
                ).distinct().count(),
            },
            {
                "role": "Landlords",
                "count": Landlord.objects.values(
                    "user_id"
                ).distinct().count(),
            },
            {
                "role": "Tenants",
                "count": Tenant.objects.values(
                    "user_id"
                ).distinct().count(),
            },
            {
                "role": "Providers",
                "count": ServiceProvider.objects.values(
                    "user_id"
                ).distinct().count(),
            },
        ]

        # ----------------------------------------------------
        # Recent activity timeline
        # ----------------------------------------------------

        activities = []

        recent_users = (
            User.objects
            .all()
            .order_by("-created_at")[:3]
        )

        for user in recent_users:
            activities.append({
                "message": (
                    f"New user registration: "
                    f"{user.full_name}."
                ),
                "timestamp": humanize_time(
                    user.created_at
                ),
                "created_at": (
                    user.created_at.isoformat()
                ),
                "module": "Identity",
                "type": "user_registration",
            })

        recent_companies = (
            Company.objects
            .select_related("owner")
            .order_by("-created_at")[:3]
        )

        for company in recent_companies:
            activities.append({
                "message": (
                    f"Company registered: "
                    f"{company.name} by "
                    f"{company.owner.full_name}."
                ),
                "timestamp": humanize_time(
                    company.created_at
                ),
                "created_at": (
                    company.created_at.isoformat()
                ),
                "module": "Companies",
                "type": "company_registration",
            })

        recent_payments = (
            successful_payments
            .select_related(
                "tenant__user",
                "invoice",
            )
            .order_by("-paid_at")[:3]
        )

        for payment in recent_payments:
            activities.append({
                "message": (
                    f"Rent payment of KES "
                    f"{payment.amount:,.2f} received from "
                    f"{payment.tenant.user.full_name}."
                ),
                "timestamp": humanize_time(
                    payment.paid_at
                ),
                "created_at": (
                    payment.paid_at.isoformat()
                ),
                "module": "Payments",
                "type": "rent_payment",
            })

        recent_tickets = (
            MaintenanceRequest.objects
            .select_related("unit")
            .order_by("-created_at")[:3]
        )

        for ticket in recent_tickets:
            activities.append({
                "message": (
                    f"Maintenance request created for "
                    f"unit {ticket.unit.unit_number}: "
                    f"{ticket.title}."
                ),
                "timestamp": humanize_time(
                    ticket.created_at
                ),
                "created_at": (
                    ticket.created_at.isoformat()
                ),
                "module": "Maintenance",
                "type": "maintenance_request",
            })

        # Sort all different activity types together.
        activities.sort(
            key=lambda item: item["created_at"],
            reverse=True,
        )

        activities = activities[:10]

        if not activities:
            activities = [{
                "message": (
                    "No recent platform activity is available."
                ),
                "timestamp": "Active",
                "created_at": now.isoformat(),
                "module": "Core",
                "type": "system",
            }]

        return Response(
            {
                "success": True,
                "timeframe": {
                    "value": timeframe,
                    "start_date": start_date.isoformat(),
                    "end_date": now.isoformat(),
                },
                "cards": {
                    "gmv": {
                        "value": float(gmv_volume_total),
                        "formatted": (
                            f"KES {gmv_volume_total:,.2f}"
                        ),
                    },
                    "timeframe_revenue": {
                        "value": float(timeframe_revenue),
                        "formatted": (
                            f"KES {timeframe_revenue:,.2f}"
                        ),
                    },
                    "total_users": total_users_count,
                    "active_users": active_users_count,
                    "total_companies": total_companies_count,
                    "verified_companies": (
                        verified_companies_count
                    ),
                    "active_subscriptions": (
                        active_subscriptions_count
                    ),
                    "total_properties": (
                        total_properties_count
                    ),
                    "total_units": total_units_count,
                    "occupied_units": (
                        occupied_units_count
                    ),
                    "available_units": (
                        available_units_count
                    ),
                    "occupancy_rate": {
                        "value": round(
                            occupancy_rate,
                            2,
                        ),
                        "formatted": (
                            f"{occupancy_rate:.1f}%"
                        ),
                    },
                    "open_tickets": open_tickets_count,
                    "overdue_invoices": (
                        overdue_invoices_count
                    ),
                },
                "charts": {
                    "revenue_history": (
                        revenue_chart_history
                    ),
                    "demographics": (
                        demographics_chart_data
                    ),
                    "unit_occupancy": [
                        {
                            "status": "Occupied",
                            "count": occupied_units_count,
                        },
                        {
                            "status": "Available",
                            "count": available_units_count,
                        },
                    ],
                },
                "activities": activities,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "ADMIN DASHBOARD ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "platform dashboard metrics."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )