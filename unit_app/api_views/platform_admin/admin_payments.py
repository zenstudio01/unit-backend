
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    Payment,
    PaymentAllocation,
    Receipt,
    PaymentReconciliation,
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


class AdminPaymentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def date_value(value):
    return value.isoformat() if value else None


def user_name(user):
    if not user:
        return None
    return user.get_full_name() or user.get_username()


def payment_queryset():
    return Payment.objects.select_related(
        "organization", "tenant", "received_by"
    )


def serialize_payment(payment):
    return {
        "id": payment.pk,
        "payment_reference": payment.payment_reference,
        "external_reference": payment.external_reference,
        "organization": {
            "id": payment.organization_id,
            "name": payment.organization.name,
        },
        "tenant": (
            {
                "id": payment.tenant_id,
                "name": payment.tenant.full_name,
            }
            if payment.tenant_id else None
        ),
        "provider": payment.provider,
        "payment_method": payment.payment_method,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "paid_at": date_value(payment.paid_at),
        "created_at": date_value(payment.created_at),
        "received_by": user_name(payment.received_by),
    }


def serialize_subscription_payment(payment):
    return {
        "id": payment.pk,
        "payment_reference": payment.payment_reference,
        "external_reference": payment.external_reference,
        "organization": {
            "id": payment.organization_id,
            "name": payment.organization.name,
        },
        "package": {
            "id": payment.package_id,
            "name": payment.package.name,
        },
        "subscription_id": payment.subscription_id,
        "billing_cycle": payment.billing_cycle,
        "payment_method": payment.payment_method,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "paid_at": date_value(payment.paid_at),
        "created_at": date_value(payment.created_at),
    }


def serialize_reconciliation(record):
    return {
        "id": record.pk,
        "statement_reference": record.statement_reference,
        "organization": {
            "id": record.organization_id,
            "name": record.organization.name,
        },
        "provider": record.provider,
        "period_start": date_value(record.period_start),
        "period_end": date_value(record.period_end),
        "expected_amount": str(record.expected_amount),
        "received_amount": str(record.received_amount),
        "difference": str(record.difference),
        "status": record.status,
        "reviewed_by": user_name(record.reviewed_by),
        "created_at": date_value(record.created_at),
    }


def validate_choice(request, model, field_name, param_name=None):
    param_name = param_name or field_name
    selected = request.query_params.get(param_name, "").strip()

    if not selected:
        return None, None

    allowed = {
        str(key)
        for key, _ in model._meta.get_field(
            field_name
        ).flatchoices
    }

    if selected not in allowed:
        return None, Response(
            {"message": f"Invalid {param_name}."},
            status=400,
        )

    return selected, None


def organization_filter(request, queryset):
    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    if not organization_id:
        return queryset, None

    if not organization_id.isdigit():
        return None, Response(
            {"message": "Invalid organization ID."},
            status=400,
        )

    return queryset.filter(
        organization_id=int(organization_id)
    ), None


def paginate(request, queryset, serializer):
    paginator = AdminPaymentPagination()
    page = paginator.paginate_queryset(queryset, request)

    return paginator.get_paginated_response([
        serializer(item) for item in page
    ])


def totals_by_currency(queryset):
    return list(
        queryset.values("currency")
        .annotate(
            total=Sum("amount"),
            count=Count("id"),
        )
        .order_by("currency")
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_payments(request):
    queryset = payment_queryset()

    search = request.query_params.get("search", "").strip()

    if search:
        queryset = queryset.filter(
            Q(payment_reference__icontains=search)
            | Q(external_reference__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(tenant__full_name__icontains=search)
        )

    for field in ("status", "provider", "payment_method"):
        selected, error = validate_choice(
            request, Payment, field
        )
        if error:
            return error
        if selected:
            queryset = queryset.filter(**{field: selected})

    queryset, error = organization_filter(
        request, queryset
    )
    if error:
        return error

    currency = request.query_params.get(
        "currency", ""
    ).strip().upper()

    if currency:
        if len(currency) != 3 or not currency.isalpha():
            return Response(
                {"message": "Invalid currency."},
                status=400,
            )
        queryset = queryset.filter(currency=currency)

    return paginate(
        request,
        queryset.order_by("-created_at", "-pk"),
        serialize_payment,
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_payment_stats(request):
    payments = Payment.objects.all()
    subscriptions = SubscriptionPayment.objects.all()
    reconciliations = PaymentReconciliation.objects.all()

    return Response({
        "property_payments": {
            "total": payments.count(),
            "completed": payments.filter(
                status="completed"
            ).count(),
            "pending": payments.filter(
                status__in=["pending", "processing"]
            ).count(),
            "failed": payments.filter(
                status="failed"
            ).count(),
            "refunded": payments.filter(
                status__in=[
                    "refunded",
                    "partially_refunded",
                ]
            ).count(),
            "completed_amounts": totals_by_currency(
                payments.filter(status="completed")
            ),
            "refunded_amounts": totals_by_currency(
                payments.filter(status="refunded")
            ),
        },
        "subscription_payments": {
            "total": subscriptions.count(),
            "completed": subscriptions.filter(
                status="completed"
            ).count(),
            "pending": subscriptions.filter(
                status="pending"
            ).count(),
            "failed": subscriptions.filter(
                status="failed"
            ).count(),
            "refunded": subscriptions.filter(
                status="refunded"
            ).count(),
            "completed_amounts": totals_by_currency(
                subscriptions.filter(status="completed")
            ),
        },
        "reconciliations": {
            "total": reconciliations.count(),
            "needs_attention": reconciliations.filter(
                status__in=[
                    "pending",
                    "partially_matched",
                    "mismatch",
                ]
            ).count(),
        },
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_subscription_transactions(request):
    queryset = SubscriptionPayment.objects.select_related(
        "organization", "subscription", "package"
    )

    search = request.query_params.get("search", "").strip()

    if search:
        queryset = queryset.filter(
            Q(payment_reference__icontains=search)
            | Q(external_reference__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(package__name__icontains=search)
        )

    for field in ("status", "payment_method"):
        selected, error = validate_choice(
            request, SubscriptionPayment, field
        )
        if error:
            return error
        if selected:
            queryset = queryset.filter(**{field: selected})

    queryset, error = organization_filter(
        request, queryset
    )
    if error:
        return error

    return paginate(
        request,
        queryset.order_by("-created_at", "-pk"),
        serialize_subscription_payment,
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_payment_reconciliations(request):
    queryset = PaymentReconciliation.objects.select_related(
        "organization", "reviewed_by"
    )

    search = request.query_params.get("search", "").strip()

    if search:
        queryset = queryset.filter(
            Q(statement_reference__icontains=search)
            | Q(organization__name__icontains=search)
        )

    for field in ("status", "provider"):
        selected, error = validate_choice(
            request, PaymentReconciliation, field
        )
        if error:
            return error
        if selected:
            queryset = queryset.filter(**{field: selected})

    queryset, error = organization_filter(
        request, queryset
    )
    if error:
        return error

    return paginate(
        request,
        queryset.order_by("-created_at", "-pk"),
        serialize_reconciliation,
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_payment_detail(request, payment_id):
    payment = get_object_or_404(
        payment_queryset(),
        pk=payment_id,
    )

    allocations = (
        PaymentAllocation.objects
        .filter(payment_id=payment_id)
        .select_related("invoice")
        .order_by("-allocated_at")
    )

    receipts = (
        Receipt.objects
        .filter(payment_id=payment_id)
        .order_by("-issued_at")
    )

    return Response({
        "payment": serialize_payment(payment),
        "allocations": [
            {
                "id": allocation.pk,
                "invoice_id": allocation.invoice_id,
                "invoice_number": (
                    allocation.invoice.invoice_number
                ),
                "invoice_type": (
                    allocation.invoice.invoice_type
                ),
                "allocated_amount": str(
                    allocation.allocated_amount
                ),
                "allocated_at": date_value(
                    allocation.allocated_at
                ),
            }
            for allocation in allocations
        ],
        "receipts": [
            {
                "id": receipt.pk,
                "receipt_number": receipt.receipt_number,
                "issued_at": date_value(receipt.issued_at),
                "file_url": receipt.file_url,
            }
            for receipt in receipts
        ],
    })
