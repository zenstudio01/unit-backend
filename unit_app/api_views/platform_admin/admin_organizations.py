
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Organization,
    OrganizationMembership,
    OrganizationSubscription,
    Property,
    Unit,
    ConstructionProject,
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


class OrganizationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def subscription_data(organization):
    try:
        subscription = organization.subscription
    except OrganizationSubscription.DoesNotExist:
        return {
            "plan": "No Plan",
            "status": "none",
            "billing_cycle": None,
            "trial_end": None,
            "current_period_end": None,
        }

    return {
        "plan": subscription.package.name,
        "status": subscription.status,
        "billing_cycle": subscription.billing_cycle,
        "trial_end": subscription.trial_end,
        "current_period_end": subscription.current_period_end,
    }


def serialize_organization(org):
    owner = org.created_by
    subscription = subscription_data(org)

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "organization_type": org.organization_type,
        "logo": org.logo,
        "email": org.email,
        "phone_number": org.phone_number,
        "country": org.country,
        "county": org.county,
        "city": org.city,
        "address": org.address,
        "website": org.website,
        "is_verified": org.is_verified,
        "created_at": org.created_at,
        "owner": {
            "id": owner.id,
            "name": owner.get_full_name() or owner.get_username(),
            "username": owner.get_username(),
            "email": owner.email,
        },
        "properties": org.property_count,
        "units": org.unit_count,
        "projects": org.project_count,
        "members": org.member_count,
        "subscription": subscription,
    }


def organization_queryset():
    return (
        Organization.objects
        .select_related("created_by", "subscription__package")
        .annotate(
            property_count=Count("properties", distinct=True),
            unit_count=Count(
                "properties__units",
                distinct=True,
            ),
            project_count=Count(
                "construction_projects",
                distinct=True,
            ),
            member_count=Count(
                "memberships",
                distinct=True,
            ),
        )
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_organizations(request):
    queryset = organization_queryset()

    search = request.query_params.get("search", "").strip()
    verified = request.query_params.get("verified", "").strip()
    org_type = request.query_params.get("type", "").strip()
    plan_status = request.query_params.get("plan_status", "").strip()

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(slug__icontains=search)
            | Q(email__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(created_by__username__icontains=search)
            | Q(created_by__email__icontains=search)
            | Q(created_by__first_name__icontains=search)
            | Q(created_by__last_name__icontains=search)
        )

    if verified == "true":
        queryset = queryset.filter(is_verified=True)
    elif verified == "false":
        queryset = queryset.filter(is_verified=False)

    if org_type:
        queryset = queryset.filter(organization_type=org_type)

    if plan_status == "none":
        queryset = queryset.filter(subscription__isnull=True)
    elif plan_status:
        queryset = queryset.filter(
            subscription__status=plan_status
        )

    queryset = queryset.order_by("-created_at", "-id")

    paginator = OrganizationPagination()
    page = paginator.paginate_queryset(queryset, request)

    return paginator.get_paginated_response(
        [serialize_organization(org) for org in page]
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_organization_stats(request):
    organizations = Organization.objects.all()

    return Response({
        "total": organizations.count(),
        "verified": organizations.filter(
            is_verified=True
        ).count(),
        "unverified": organizations.filter(
            is_verified=False
        ).count(),
        "active_subscriptions": OrganizationSubscription.objects.filter(
            status="active",
            current_period_end__gt=timezone.now(),
        ).count(),
        "trial_subscriptions": OrganizationSubscription.objects.filter(
            status="trial",
            trial_end__gt=timezone.now(),
        ).count(),
        "total_properties": Property.objects.count(),
        "total_units": Unit.objects.count(),
        "total_projects": ConstructionProject.objects.count(),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_organization_detail(request, organization_id):
    org = get_object_or_404(
        organization_queryset(),
        pk=organization_id,
    )

    properties = Property.objects.filter(
        organization=org
    ).order_by("-created_at")[:20]

    projects = ConstructionProject.objects.filter(
        organization=org
    ).order_by("-created_at")[:20]

    memberships = (
        OrganizationMembership.objects
        .filter(organization=org)
        .select_related("user", "primary_role")
        .prefetch_related("roles")
        .order_by("-joined_at")[:20]
    )

    return Response({
        "organization": serialize_organization(org),
        "properties": [
            {
                "id": item.id,
                "name": item.name,
                "property_code": item.property_code,
                "property_type": item.property_type,
                "status": item.status,
                "city": item.city,
                "units": item.units.count(),
            }
            for item in properties
        ],
        "projects": [
            {
                "id": item.id,
                "name": item.name,
                "project_code": item.project_code,
                "project_type": item.project_type,
                "status": item.status,
            }
            for item in projects
        ],
        "members": [
            {
                "id": member.id,
                "name": (
                    member.user.get_full_name()
                    or member.user.get_username()
                ),
                "email": member.user.email,
                "role": (
                    member.primary_role.name
                    if member.primary_role else None
                ),
                "roles": [
                    role.name for role in member.roles.all()
                ],
                "is_active": member.is_active,
            }
            for member in memberships
        ],
    })


@api_view(["PATCH"])
@permission_classes([IsPlatformAdmin])
def admin_organization_verification(request, organization_id):
    org = get_object_or_404(
        Organization,
        pk=organization_id,
    )

    verified = request.data.get("is_verified")

    if type(verified) is not bool:
        return Response(
            {"message": "is_verified must be a boolean."},
            status=400,
        )

    org.is_verified = verified
    org.save(update_fields=["is_verified", "updated_at"])

    return Response({
        "message": (
            "Organization verified successfully."
            if verified else
            "Organization verification removed."
        ),
        "id": org.id,
        "is_verified": org.is_verified,
    })
