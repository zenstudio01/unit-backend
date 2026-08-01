from .common_imports import *

import os
import uuid
import requests

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone


# ============================================================
# CONFIGURATION
# ============================================================

PAYSTACK_SECRET_KEY = getattr(
    settings,
    "PAYSTACK_SECRET_KEY",
    os.environ.get("PAYSTACK_SECRET_KEY"),
)

PAYSTACK_CALLBACK_URL = getattr(
    settings,
    "PAYSTACK_SUBSCRIPTION_CALLBACK_URL",
    os.environ.get(
        "PAYSTACK_SUBSCRIPTION_CALLBACK_URL",
        "https://yourdomain.com/api/subscriptions/callback/",
    ),
)

PAYSTACK_INITIALIZE_URL = (
    "https://api.paystack.co/transaction/initialize"
)

PAYSTACK_VERIFY_URL = (
    "https://api.paystack.co/transaction/verify"
)

VALID_BILLING_CYCLES = {
    "monthly",
    "yearly",
}

SUBSCRIPTION_MANAGEMENT_ROLES = {
    "owner",
    "admin",
    "property_manager",
}


# ============================================================
# HELPERS
# ============================================================

def get_company_membership(user, company_id):
    """
    Return the user's active membership in a company.
    """

    return (
        CompanyStaff.objects
        .select_related(
            "company",
            "user",
        )
        .filter(
            user=user,
            company_id=company_id,
            is_active=True,
        )
        .first()
    )


def can_manage_company_subscription(membership):
    return (
        membership is not None
        and membership.role
        in SUBSCRIPTION_MANAGEMENT_ROLES
    )


def serialize_package(package):
    return {
        "id": package.id,
        "name": package.name,
        "description": package.description,
        "monthly_price": float(
            package.monthly_price
        ),
        "yearly_price": float(
            package.yearly_price
        ),
        "month_days": package.month_days,
        "year_days": package.year_days,
        "number_of_units": (
            package.number_of_units
        ),
        "mpesa_daraja": (
            package.mpesa_daraja
        ),
        "email_notifications": (
            package.email_notifications
        ),
        "logs_duration": (
            package.logs_duration
        ),
        "created_at": (
            package.created_at.isoformat()
            if package.created_at
            else None
        ),
        "updated_at": (
            package.updated_at.isoformat()
            if package.updated_at
            else None
        ),
    }


def serialize_subscription(subscription):
    return {
        "id": subscription.id,
        "company": {
            "id": subscription.company_id,
            "name": subscription.company.name,
        },
        "package": serialize_package(
            subscription.package
        ),
        "billing_cycle": (
            subscription.billing_cycle
        ),
        "start_date": (
            subscription.start_date.isoformat()
            if subscription.start_date
            else None
        ),
        "end_date": (
            subscription.end_date.isoformat()
            if subscription.end_date
            else None
        ),
        "is_active": subscription.is_active,
        "is_expired": (
            subscription.end_date
            < timezone.now()
            if subscription.end_date
            else True
        ),
    }


def get_package_amount(
    package,
    billing_cycle,
):
    if billing_cycle == "monthly":
        return package.monthly_price

    if billing_cycle == "yearly":
        return package.yearly_price

    return None


def get_subscription_expiry(
    package,
    billing_cycle,
    start_date=None,
):
    start_date = (
        start_date or timezone.now()
    )

    if billing_cycle == "monthly":
        return start_date + timedelta(
            days=package.month_days
        )

    return start_date + timedelta(
        days=package.year_days
    )


def get_paystack_headers():
    return {
        "Authorization": (
            f"Bearer {PAYSTACK_SECRET_KEY}"
        ),
        "Content-Type": "application/json",
    }


def safe_send_push_notification(
    user,
    title,
    body,
    data=None,
):
    expo_token = getattr(
        user,
        "expo_token",
        None,
    )

    if not expo_token:
        return False

    try:
        send_push_notification(
            expo_token,
            title=title,
            body=body,
            data=data or {},
        )

        return True

    except Exception as error:
        print(
            "SUBSCRIPTION PUSH ERROR:",
            str(error),
        )

        return False


def verify_paystack_transaction(reference):
    """
    Verify a transaction with Paystack.

    Returns:
        tuple:
            transaction_data, error_message
    """

    if not PAYSTACK_SECRET_KEY:
        return (
            None,
            "Paystack secret key is not configured.",
        )

    try:
        response = requests.get(
            f"{PAYSTACK_VERIFY_URL}/{reference}",
            headers=get_paystack_headers(),
            timeout=30,
        )

    except requests.RequestException as error:
        return (
            None,
            f"Unable to connect to Paystack: {error}",
        )

    try:
        result = response.json()

    except ValueError:
        return (
            None,
            "Paystack returned an invalid response.",
        )

    if response.status_code != 200:
        return (
            None,
            result.get(
                "message",
                "Paystack verification failed.",
            ),
        )

    if not result.get("status"):
        return (
            None,
            result.get(
                "message",
                "Transaction verification failed.",
            ),
        )

    transaction_data = result.get("data")

    if not transaction_data:
        return (
            None,
            "Paystack transaction data is missing.",
        )

    return transaction_data, None


def activate_company_subscription(
    payment,
    transaction,
):
    """
    Safely mark a payment as successful and activate
    the company's subscription.

    This function must be called inside transaction.atomic().
    """

    package = payment.package
    company = payment.company

    billing_cycle = payment.billing_cycle

    start_date = timezone.now()

    # When extending the same package and billing cycle,
    # start from the current subscription's expiry date.
    current_subscription = (
        Subscription.objects
        .select_for_update()
        .filter(company=company)
        .first()
    )

    if (
        current_subscription
        and current_subscription.is_active
        and current_subscription.end_date
        and current_subscription.end_date
        > timezone.now()
        and current_subscription.package_id
        == package.id
        and current_subscription.billing_cycle
        == billing_cycle
    ):
        start_date = (
            current_subscription.end_date
        )

    expiry_date = get_subscription_expiry(
        package,
        billing_cycle,
        start_date,
    )

    subscription, created = (
        Subscription.objects.update_or_create(
            company=company,
            defaults={
                "package": package,
                "billing_cycle": billing_cycle,
                "start_date": start_date,
                "end_date": expiry_date,
                "is_active": True,
            },
        )
    )

    payment.status = "success"
    payment.paid_at = timezone.now()
    payment.gateway_response = (
        transaction.get(
            "gateway_response"
        )
    )
    payment.channel = transaction.get(
        "channel"
    )
    payment.currency = transaction.get(
        "currency",
        payment.currency,
    )
    payment.paystack_transaction_id = (
        transaction.get("id")
    )

    payment.save(
        update_fields=[
            "status",
            "paid_at",
            "gateway_response",
            "channel",
            "currency",
            "paystack_transaction_id",
            "updated_at",
        ]
    )

    return subscription, created


# ============================================================
# GET PACKAGES
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_packages(request):
    try:
        packages = (
            Package.objects
            .filter(is_active=True)
            .order_by("monthly_price")
        )

        data = [
            serialize_package(package)
            for package in packages
        ]

        return Response(
            {
                "success": True,
                "count": len(data),
                "packages": data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET PACKAGES ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "subscription packages."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# GET COMPANY SUBSCRIPTION
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_subscription(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not membership:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have access to "
                        "this company."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        subscription = (
            Subscription.objects
            .select_related(
                "company",
                "package",
            )
            .filter(
                company_id=company_id
            )
            .first()
        )

        if not subscription:
            return Response(
                {
                    "success": True,
                    "has_subscription": False,
                    "subscription": None,
                },
                status=status.HTTP_200_OK,
            )

        if (
            subscription.end_date
            and subscription.end_date
            <= timezone.now()
            and subscription.is_active
        ):
            subscription.is_active = False

            subscription.save(
                update_fields=[
                    "is_active",
                ]
            )

        return Response(
            {
                "success": True,
                "has_subscription": True,
                "subscription": (
                    serialize_subscription(
                        subscription
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET COMPANY SUBSCRIPTION ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the company subscription."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# INITIALIZE PAYSTACK SUBSCRIPTION PAYMENT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def property_manager_subscribe_plan(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        package_id = request.data.get(
            "package_id"
        )

        billing_cycle = str(
            request.data.get(
                "billing_cycle",
                "monthly",
            )
        ).strip().lower()

        email = str(
            request.data.get(
                "email",
                request.user.email,
            )
        ).strip().lower()

        if not PAYSTACK_SECRET_KEY:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Paystack has not been configured."
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not package_id:
            return Response(
                {
                    "success": False,
                    "message": "Package is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A payment email is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            billing_cycle
            not in VALID_BILLING_CYCLES
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Billing cycle must be monthly "
                        "or yearly."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_company_subscription(
            membership
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "manage this company's subscription."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        package = (
            Package.objects
            .filter(
                id=package_id,
                is_active=True,
            )
            .first()
        )

        if not package:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Package was not found or "
                        "is not active."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        amount = get_package_amount(
            package,
            billing_cycle,
        )

        if (
            amount is None
            or amount <= Decimal("0.00")
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "The selected package has an "
                        "invalid price."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        internal_reference = (
            f"SUB-{company_id}-"
            f"{uuid.uuid4().hex[:16].upper()}"
        )

        payload = {
            "email": email,
            "amount": int(
                amount * Decimal("100")
            ),
            "currency": "KES",
            "reference": internal_reference,
            "callback_url": (
                PAYSTACK_CALLBACK_URL
            ),
            "metadata": {
                "payment_type": (
                    "company_subscription"
                ),
                "user_id": request.user.id,
                "company_id": int(company_id),
                "package_id": package.id,
                "billing_cycle": billing_cycle,
                "custom_fields": [
                    {
                        "display_name": "Company",
                        "variable_name": (
                            "company_name"
                        ),
                        "value": (
                            membership.company.name
                        ),
                    },
                    {
                        "display_name": "Package",
                        "variable_name": (
                            "package_name"
                        ),
                        "value": package.name,
                    },
                    {
                        "display_name": (
                            "Billing cycle"
                        ),
                        "variable_name": (
                            "billing_cycle"
                        ),
                        "value": billing_cycle,
                    },
                ],
            },
        }

        try:
            paystack_response = requests.post(
                PAYSTACK_INITIALIZE_URL,
                json=payload,
                headers=get_paystack_headers(),
                timeout=30,
            )

        except requests.RequestException as error:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to connect to Paystack."
                    ),
                    "error": str(error),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            paystack_data = (
                paystack_response.json()
            )

        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Paystack returned an invalid "
                        "response."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if (
            paystack_response.status_code != 200
            or not paystack_data.get("status")
        ):
            return Response(
                {
                    "success": False,
                    "message": paystack_data.get(
                        "message",
                        "Unable to initialize payment.",
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_data = paystack_data.get(
            "data",
            {},
        )

        reference = transaction_data.get(
            "reference"
        )

        authorization_url = (
            transaction_data.get(
                "authorization_url"
            )
        )

        access_code = transaction_data.get(
            "access_code"
        )

        if (
            not reference
            or not authorization_url
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Paystack did not return complete "
                        "payment information."
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment = (
            SubscriptionPayment.objects.create(
                user=request.user,
                company=membership.company,
                package=package,
                billing_cycle=billing_cycle,
                email=email,
                amount=amount,
                currency="KES",
                reference=reference,
                access_code=access_code,
                payment_method="paystack",
                status="pending",
            )
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Subscription payment initialized."
                ),
                "payment": {
                    "id": payment.id,
                    "company_id": (
                        payment.company_id
                    ),
                    "package_id": (
                        payment.package_id
                    ),
                    "billing_cycle": (
                        payment.billing_cycle
                    ),
                    "amount": float(
                        payment.amount
                    ),
                    "currency": (
                        payment.currency
                    ),
                    "reference": (
                        payment.reference
                    ),
                    "authorization_url": (
                        authorization_url
                    ),
                    "access_code": access_code,
                    "status": payment.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as error:
        print(
            "INITIALIZE SUBSCRIPTION ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while initializing "
                    "the subscription payment."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# VERIFY SUBSCRIPTION PAYMENT
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_verify_subscription(
    request,
    reference,
):
    try:
        payment = (
            SubscriptionPayment.objects
            .select_related(
                "company",
                "package",
                "user",
            )
            .filter(
                reference=reference,
            )
            .first()
        )

        if not payment:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Subscription payment record "
                        "was not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = get_company_membership(
            request.user,
            payment.company_id,
        )

        if not membership:
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have access to "
                        "this payment."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if payment.status == "success":
            subscription = (
                Subscription.objects
                .select_related(
                    "company",
                    "package",
                )
                .filter(
                    company=payment.company
                )
                .first()
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Payment was already processed."
                    ),
                    "payment_status": (
                        payment.status
                    ),
                    "subscription": (
                        serialize_subscription(
                            subscription
                        )
                        if subscription
                        else None
                    ),
                },
                status=status.HTTP_200_OK,
            )

        transaction_data, error = (
            verify_paystack_transaction(
                reference
            )
        )

        if error:
            return Response(
                {
                    "success": False,
                    "message": error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            transaction_data.get("status")
            != "success"
        ):
            payment.status = "failed"

            payment.gateway_response = (
                transaction_data.get(
                    "gateway_response"
                )
            )

            payment.save(
                update_fields=[
                    "status",
                    "gateway_response",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "The payment was not successful."
                    ),
                    "payment_status": (
                        transaction_data.get(
                            "status"
                        )
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_amount = int(
            payment.amount
            * Decimal("100")
        )

        paid_amount = transaction_data.get(
            "amount"
        )

        if paid_amount != expected_amount:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The amount received does not match "
                        "the subscription payment."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            transaction_data.get("currency")
            != payment.currency
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "The payment currency does not "
                        "match the expected currency."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        metadata = (
            transaction_data.get(
                "metadata"
            )
            or {}
        )

        try:
            metadata_company_id = int(
                metadata.get("company_id")
            )

            metadata_package_id = int(
                metadata.get("package_id")
            )

        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Payment metadata is invalid."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            metadata_company_id
            != payment.company_id
            or metadata_package_id
            != payment.package_id
            or metadata.get("billing_cycle")
            != payment.billing_cycle
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Payment metadata does not match "
                        "the subscription request."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            locked_payment = (
                SubscriptionPayment.objects
                .select_for_update()
                .select_related(
                    "company",
                    "package",
                    "user",
                )
                .get(id=payment.id)
            )

            if (
                locked_payment.status
                == "success"
            ):
                subscription = (
                    Subscription.objects
                    .select_related(
                        "company",
                        "package",
                    )
                    .get(
                        company=
                        locked_payment.company
                    )
                )

            else:
                subscription, _ = (
                    activate_company_subscription(
                        locked_payment,
                        transaction_data,
                    )
                )

                Notification.objects.create(
                    user=locked_payment.user,
                    company=(
                        locked_payment.company
                    ),
                    title=(
                        "Subscription Activated"
                    ),
                    message=(
                        f"The {locked_payment.package.name} "
                        f"subscription for "
                        f"{locked_payment.company.name} "
                        f"has been activated successfully."
                    ),
                    notification_type=(
                        "subscription"
                    ),
                    data={
                        "company_id": (
                            locked_payment.company_id
                        ),
                        "subscription_id": (
                            subscription.id
                        ),
                        "package_id": (
                            locked_payment.package_id
                        ),
                    },
                )

        notification_sent = (
            safe_send_push_notification(
                payment.user,
                title="Subscription Activated",
                body=(
                    f"The {payment.package.name} "
                    f"subscription for "
                    f"{payment.company.name} "
                    f"is now active."
                ),
                data={
                    "screen": "Subscription",
                    "company_id": str(
                        payment.company_id
                    ),
                    "subscription_id": str(
                        subscription.id
                    ),
                },
            )
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Payment verified and subscription "
                    "activated successfully."
                ),
                "notification_sent": (
                    notification_sent
                ),
                "subscription": (
                    serialize_subscription(
                        subscription
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "VERIFY SUBSCRIPTION ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while verifying "
                    "the subscription payment."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PAYSTACK CALLBACK
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def property_manager_subscription_callback(
    request,
):
    reference = request.GET.get(
        "reference"
    )

    if not reference:
        return render(
            request,
            "subscription/payment_failed.html",
            {
                "message": (
                    "Payment reference is missing."
                ),
            },
            status=400,
        )

    try:
        payment = (
            SubscriptionPayment.objects
            .select_related(
                "company",
                "package",
                "user",
            )
            .filter(
                reference=reference
            )
            .first()
        )

        if not payment:
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "Payment record was not found."
                    ),
                    "reference": reference,
                },
                status=404,
            )

        transaction_data, error = (
            verify_paystack_transaction(
                reference
            )
        )

        if error:
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": error,
                    "reference": reference,
                },
                status=400,
            )

        if (
            transaction_data.get("status")
            != "success"
        ):
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "The payment was not successful."
                    ),
                    "reference": reference,
                },
                status=400,
            )

        expected_amount = int(
            payment.amount
            * Decimal("100")
        )

        if (
            transaction_data.get("amount")
            != expected_amount
        ):
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "The paid amount does not match "
                        "the expected subscription amount."
                    ),
                    "reference": reference,
                },
                status=400,
            )

        if (
            transaction_data.get("currency")
            != payment.currency
        ):
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "The payment currency does not "
                        "match."
                    ),
                    "reference": reference,
                },
                status=400,
            )

        metadata = (
            transaction_data.get(
                "metadata"
            )
            or {}
        )

        try:
            metadata_company_id = int(
                metadata.get("company_id")
            )

            metadata_package_id = int(
                metadata.get("package_id")
            )

        except (
            TypeError,
            ValueError,
        ):
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "The transaction metadata "
                        "is invalid."
                    ),
                    "reference": reference,
                },
                status=400,
            )

        if (
            metadata_company_id
            != payment.company_id
            or metadata_package_id
            != payment.package_id
            or metadata.get("billing_cycle")
            != payment.billing_cycle
        ):
            return render(
                request,
                "subscription/payment_failed.html",
                {
                    "message": (
                        "The transaction details do not "
                        "match the subscription request."
                    ),
                    "reference": reference,
                },
                status=400,
            )

        created_subscription = False

        with transaction.atomic():
            locked_payment = (
                SubscriptionPayment.objects
                .select_for_update()
                .select_related(
                    "company",
                    "package",
                    "user",
                )
                .get(id=payment.id)
            )

            if (
                locked_payment.status
                == "success"
            ):
                subscription = (
                    Subscription.objects
                    .select_related(
                        "company",
                        "package",
                    )
                    .filter(
                        company=
                        locked_payment.company
                    )
                    .first()
                )

            else:
                subscription, created_subscription = (
                    activate_company_subscription(
                        locked_payment,
                        transaction_data,
                    )
                )

                Notification.objects.create(
                    user=locked_payment.user,
                    company=(
                        locked_payment.company
                    ),
                    title=(
                        "Subscription Activated"
                    ),
                    message=(
                        f"The "
                        f"{locked_payment.package.name} "
                        f"subscription for "
                        f"{locked_payment.company.name} "
                        f"has been activated successfully."
                    ),
                    notification_type=(
                        "subscription"
                    ),
                    data={
                        "company_id": (
                            locked_payment.company_id
                        ),
                        "subscription_id": (
                            subscription.id
                        ),
                        "package_id": (
                            locked_payment.package_id
                        ),
                    },
                )

        if created_subscription:
            safe_send_push_notification(
                payment.user,
                title="Subscription Activated",
                body=(
                    f"The {payment.package.name} "
                    f"subscription for "
                    f"{payment.company.name} "
                    f"is now active."
                ),
                data={
                    "screen": "Subscription",
                    "company_id": str(
                        payment.company_id
                    ),
                    "subscription_id": str(
                        subscription.id
                    ),
                },
            )

        return render(
            request,
            "subscription/payment_success.html",
            {
                "reference": reference,
                "company_name": (
                    payment.company.name
                ),
                "package_name": (
                    payment.package.name
                ),
                "billing_cycle": (
                    payment.billing_cycle.title()
                ),
                "amount": payment.amount,
                "currency": payment.currency,
                "end_date": (
                    subscription.end_date
                    if subscription
                    else None
                ),
            },
        )

    except Exception as error:
        print(
            "SUBSCRIPTION CALLBACK ERROR:",
            str(error),
        )

        return render(
            request,
            "subscription/payment_failed.html",
            {
                "message": (
                    "An unexpected error occurred while "
                    "processing the payment."
                ),
                "reference": reference,
            },
            status=500,
        )