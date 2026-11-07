
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    SubscriptionPackage,
    OrganizationSubscription,
    SubscriptionPayment,
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


class AdminPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def has_field(model, name):
    return any(
        field.name == name
        for field in model._meta.concrete_fields
    )


def value(obj, name, default=None):
    return getattr(obj, name, default)


def money(obj, name):
    amount = value(obj, name)
    return str(amount) if amount is not None else "0"


def iso(obj, name):
    date = value(obj, name)
    return date.isoformat() if date else None


def get_choices(model, name):
    if not has_field(model, name):
        return []

    field = model._meta.get_field(name)

    return [
        {"value": str(key), "label": str(label)}
        for key, label in field.flatchoices
        if key not in ("", None)
    ]


def organization_data(subscription):
    organization = subscription.organization

    return {
        "id": organization.id,
        "name": organization.name,
        "email": value(organization, "email"),
        "phone_number": value(
            organization, "phone_number"
        ),
    }


def serialize_package(package):
    return {
        "id": package.pk,
        "code": value(package, "code"),
        "name": value(package, "name"),
        "description": value(package, "description"),
        "monthly_price": money(package, "monthly_price"),
        "yearly_price": money(package, "yearly_price"),
        "is_active": value(package, "is_active"),
        "trial_days": value(package, "trial_days"),
        "max_properties": value(package, "max_properties"),
        "max_units": value(package, "max_units"),
        "max_users": value(package, "max_users"),
        "max_projects": value(package, "max_projects"),
        "created_at": iso(package, "created_at"),
        "updated_at": iso(package, "updated_at"),
    }


def serialize_subscription(subscription):
    package = subscription.package

    return {
        "id": subscription.pk,
        "organization": organization_data(subscription),
        "package": (
            serialize_package(package) if package else None
        ),
        "status": subscription.status,
        "billing_cycle": value(
            subscription, "billing_cycle"
        ),
        "trial_end": iso(subscription, "trial_end"),
        "current_period_start": iso(
            subscription, "current_period_start"
        ),
        "current_period_end": iso(
            subscription, "current_period_end"
        ),
        "cancel_at_period_end": value(
            subscription, "cancel_at_period_end"
        ),
        "created_at": iso(subscription, "created_at"),
        "updated_at": iso(subscription, "updated_at"),
        "is_active_subscription": (
            subscription.is_active_subscription
            if isinstance(
                getattr(
                    type(subscription),
                    "is_active_subscription",
                    None,
                ),
                property,
            )
            else None
        ),
    }


def serialize_payment(payment):
    subscription = value(payment, "subscription")
    organization = value(payment, "organization")
    package = value(payment, "package")

    return {
        "id": payment.pk,
        "organization": (
            {
                "id": organization.pk,
                "name": organization.name,
            }
            if organization else None
        ),
        "subscription_id": (
            subscription.pk if subscription else None
        ),
        "package": (
            {
                "id": package.pk,
                "name": package.name,
            }
            if package else None
        ),
        "amount": money(payment, "amount"),
        "currency": value(payment, "currency", "KES"),
        "status": value(payment, "status"),
        "reference": (
            value(payment, "reference")
            or value(payment, "transaction_reference")
            or value(payment, "payment_reference")
        ),
        "paid_at": iso(payment, "paid_at"),
        "created_at": iso(payment, "created_at"),
    }


def subscription_queryset():
    return OrganizationSubscription.objects.select_related(
        "organization",
        "package",
    )


def payment_queryset():
    queryset = SubscriptionPayment.objects.all()

    relations = [
        name
        for name in (
            "organization",
            "subscription",
            "package",
        )
        if has_field(SubscriptionPayment, name)
    ]

    if relations:
        queryset = queryset.select_related(*relations)

    return queryset


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_subscriptions(request):
    queryset = subscription_queryset()

    search = request.query_params.get(
        "search", ""
    ).strip()
    status_filter = request.query_params.get(
        "status", ""
    ).strip()
    package_id = request.query_params.get(
        "package_id", ""
    ).strip()
    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    if search:
        queryset = queryset.filter(
            Q(organization__name__icontains=search)
            | Q(package__name__icontains=search)
        )

    if status_filter:
        valid = {
            item["value"]
            for item in get_choices(
                OrganizationSubscription, "status"
            )
        }

        if valid and status_filter not in valid:
            return Response(
                {"message": "Invalid subscription status."},
                status=400,
            )

        queryset = queryset.filter(status=status_filter)

    if package_id:
        if not package_id.isdigit():
            return Response(
                {"message": "Invalid package ID."},
                status=400,
            )
        queryset = queryset.filter(
            package_id=int(package_id)
        )

    if organization_id:
        if not organization_id.isdigit():
            return Response(
                {"message": "Invalid organization ID."},
                status=400,
            )
        queryset = queryset.filter(
            organization_id=int(organization_id)
        )

    queryset = queryset.order_by("-pk")

    paginator = AdminPagination()
    page = paginator.paginate_queryset(
        queryset, request
    )

    return paginator.get_paginated_response([
        serialize_subscription(item) for item in page
    ])


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_stats(request):
    subscriptions = OrganizationSubscription.objects.all()
    payments = SubscriptionPayment.objects.all()

    completed = payments.filter(status="completed")

    revenue = completed.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    today = timezone.localdate()

    period_field = OrganizationSubscription._meta.get_field(
        "current_period_end"
    )

    is_datetime = period_field.get_internal_type() == (
        "DateTimeField"
    )

    expiry_lookup = (
        "current_period_end__date__gte"
        if is_datetime else "current_period_end__gte"
    )

    expiry_end_lookup = (
        "current_period_end__date__lte"
        if is_datetime else "current_period_end__lte"
    )

    from datetime import timedelta
    upcoming = subscriptions.filter(
        status__in=["active", "trial"],
        **{
            expiry_lookup: today,
            expiry_end_lookup: today + timedelta(days=30),
        }
    ).count()

    return Response({
        "total_subscriptions": subscriptions.count(),
        "active_subscriptions": subscriptions.filter(
            status="active"
        ).count(),
        "trial_subscriptions": subscriptions.filter(
            status="trial"
        ).count(),
        "past_due_subscriptions": subscriptions.filter(
            status="past_due"
        ).count(),
        "expired_subscriptions": subscriptions.filter(
            status="expired"
        ).count(),
        "cancelled_subscriptions": subscriptions.filter(
            status="cancelled"
        ).count(),
        "suspended_subscriptions": subscriptions.filter(
            status="suspended"
        ).count(),
        "expiring_within_30_days": upcoming,
        "total_packages": SubscriptionPackage.objects.count(),
        "total_payments": payments.count(),
        "completed_payments": completed.count(),
        "total_revenue": str(revenue),
        "currency": "KES",
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_detail(request, subscription_id):
    subscription = get_object_or_404(
        subscription_queryset(),
        pk=subscription_id,
    )

    payments = payment_queryset()

    if has_field(SubscriptionPayment, "subscription"):
        payments = payments.filter(
            subscription_id=subscription.pk
        )
    elif has_field(SubscriptionPayment, "organization"):
        payments = payments.filter(
            organization_id=subscription.organization_id
        )
    else:
        payments = payments.none()

    payments = payments.order_by("-pk")[:30]

    return Response({
        "subscription": serialize_subscription(subscription),
        "payments": [
            serialize_payment(payment)
            for payment in payments
        ],
    })


@api_view(["GET", "POST"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_packages(request):
    if request.method == "GET":
        packages = SubscriptionPackage.objects.all().order_by(
            "monthly_price", "pk"
        )

        return Response({
            "results": [
                serialize_package(item)
                for item in packages
            ],
            "count": packages.count(),
        })

    return save_package(request)


EDITABLE_PACKAGE_FIELDS = {
    "code",
    "name",
    "description",
    "monthly_price",
    "yearly_price",
    "is_active",
    "trial_days",
    "max_properties",
    "max_units",
    "max_users",
    "max_projects",
}


def save_package(request, package=None):
    creating = package is None

    if not isinstance(request.data, dict):
        return Response(
            {"message": "Expected a JSON object."},
            status=400,
        )

    data = request.data

    unknown = set(data) - EDITABLE_PACKAGE_FIELDS

    if unknown:
        return Response(
            {
                "message": (
                    "Unsupported package fields: "
                    + ", ".join(sorted(unknown))
                )
            },
            status=400,
        )

    if creating:
        package = SubscriptionPackage()

    errors = {}

    for field_name in EDITABLE_PACKAGE_FIELDS:
        if field_name not in data:
            continue

        if not has_field(SubscriptionPackage, field_name):
            errors[field_name] = (
                "This field is not supported by the model."
            )
            continue

        field = SubscriptionPackage._meta.get_field(
            field_name
        )

        raw = data[field_name]
        kind = field.get_internal_type()

        try:
            if raw is None:
                if not field.null:
                    raise ValueError("This field cannot be null.")
                parsed = None

            elif kind == "BooleanField":
                if not isinstance(raw, bool):
                    raise ValueError("Expected true or false.")
                parsed = raw

            elif kind == "DecimalField":
                if isinstance(raw, bool):
                    raise ValueError("Invalid decimal value.")
                parsed = Decimal(str(raw))
                if not parsed.is_finite():
                    raise ValueError("Invalid decimal value.")
                if parsed < 0:
                    raise ValueError("Cannot be negative.")

            elif kind in (
                "IntegerField",
                "PositiveIntegerField",
                "PositiveSmallIntegerField",
                "SmallIntegerField",
            ):
                if isinstance(raw, bool):
                    raise ValueError("Invalid integer value.")
                parsed = int(raw)
                if str(parsed) != str(raw):
                    raise ValueError("Expected an integer.")
                if parsed < 0:
                    raise ValueError("Cannot be negative.")

            elif kind in ("CharField", "TextField"):
                if not isinstance(raw, str):
                    raise ValueError("Expected text.")
                parsed = raw.strip()
                if not parsed and not field.blank:
                    raise ValueError("This field is required.")

            else:
                raise ValueError("Unsupported field type.")

            setattr(package, field_name, parsed)

        except (
            ValueError,
            TypeError,
            InvalidOperation,
        ) as exc:
            errors[field_name] = str(exc)

    if errors:
        return Response(
            {"errors": errors},
            status=400,
        )

    try:
        package.full_clean()
    except Exception as exc:
        if hasattr(exc, "message_dict"):
            return Response(
                {"errors": exc.message_dict},
                status=400,
            )
        return Response(
            {"message": str(exc)},
            status=400,
        )

    with transaction.atomic():
        package.save()

    return Response(
        {"package": serialize_package(package)},
        status=201 if creating else 200,
    )


@api_view(["PATCH"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_package_detail(request, package_id):
    package = get_object_or_404(
        SubscriptionPackage,
        pk=package_id,
    )

    return save_package(request, package)


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_payments(request):
    queryset = payment_queryset()

    status_filter = request.query_params.get(
        "status", ""
    ).strip()

    search = request.query_params.get(
        "search", ""
    ).strip()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if search:
        filters = Q()

        if has_field(SubscriptionPayment, "organization"):
            filters |= Q(
                organization__name__icontains=search
            )

        for field_name in (
            "reference",
            "transaction_reference",
            "payment_reference",
        ):
            if has_field(SubscriptionPayment, field_name):
                filters |= Q(
                    **{f"{field_name}__icontains": search}
                )

        queryset = (
            queryset.filter(filters)
            if filters.children
            else queryset.none()
        )

    queryset = queryset.order_by("-pk")

    paginator = AdminPagination()
    page = paginator.paginate_queryset(
        queryset, request
    )

    return paginator.get_paginated_response([
        serialize_payment(payment)
        for payment in page
    ])
