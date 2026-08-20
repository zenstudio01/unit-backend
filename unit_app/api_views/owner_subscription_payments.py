from .common_imports import *


def get_subscription_manager(
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
                organization=organization,
                user=user,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return (
            None,
            JsonResponse(
                {
                    "message":
                        "You do not belong to this organization."
                },
                status=403,
            ),
        )

    role_codes = set(
        membership.roles
        .filter(
            is_active=True
        )
        .values_list(
            "code",
            flat=True,
        )
    )

    allowed_roles = {
        "organization_owner",
        "organization_admin",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return (
            None,
            JsonResponse(
                {
                    "message":
                        "Only organization owners or administrators can manage subscriptions."
                },
                status=403,
            ),
        )

    return (
        organization,
        None,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initialize_subscription_payment(
    request
):
    user = request.user

    organization_id = (
        request.data.get(
            "organization_id"
        )
    )

    package_id = (
        request.data.get(
            "package_id"
        )
    )

    billing_cycle = str(
        request.data.get(
            "billing_cycle",
            "monthly"
        )
        or "monthly"
    ).strip()

    # =====================================================
    # VALIDATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    if not package_id:
        return JsonResponse(
            {
                "message":
                    "package_id is required."
            },
            status=400,
        )

    if billing_cycle not in [
        "monthly",
        "yearly",
    ]:
        return JsonResponse(
            {
                "message":
                    "Invalid billing cycle."
            },
            status=400,
        )

    if not user.email:
        return JsonResponse(
            {
                "message":
                    "Your account does not have an email address."
            },
            status=400,
        )

    (
        organization,
        error_response,
    ) = get_subscription_manager(
        user,
        organization_id,
    )

    if error_response:
        return error_response

    # =====================================================
    # PACKAGE
    # =====================================================

    try:
        package = (
            SubscriptionPackage.objects.get(
                id=package_id,
                is_active=True,
            )
        )

    except SubscriptionPackage.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Subscription package not found."
            },
            status=404,
        )

    if package.code == "enterprise":
        return JsonResponse(
            {
                "message":
                    "Enterprise pricing is handled by UNIT sales.",

                "code":
                    "contact_sales",
            },
            status=400,
        )

    # =====================================================
    # SUBSCRIPTION
    # =====================================================

    try:
        subscription = (
            OrganizationSubscription.objects.get(
                organization=organization
            )
        )

    except OrganizationSubscription.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization subscription record not found."
            },
            status=404,
        )

    # =====================================================
    # PRICE
    # =====================================================

    if billing_cycle == "monthly":
        amount = (
            package.monthly_price
        )

    else:
        amount = (
            package.yearly_price
        )

    if amount <= 0:
        return JsonResponse(
            {
                "message":
                    "This package cannot be purchased online."
            },
            status=400,
        )

    # Paystack expects amount in
    # the lowest currency unit.
    #
    # KES 5,000 = 500000

    paystack_amount = int(
        amount * 100
    )

    payment_reference = (
        "UNIT-SUB-"
        f"{organization.id}-"
        f"{uuid.uuid4().hex[:12].upper()}"
    )

    # =====================================================
    # CREATE LOCAL PENDING PAYMENT FIRST
    # =====================================================

    payment = (
        SubscriptionPayment.objects.create(
            organization=
                organization,

            subscription=
                subscription,

            package=
                package,

            amount=
                amount,

            currency=
                "KES",

            billing_cycle=
                billing_cycle,

            payment_method=
                "paystack",

            payment_reference=
                payment_reference,

            status=
                "pending",

            metadata={
                "user_id":
                    user.id,

                "package_code":
                    package.code,

                "organization_id":
                    organization.id,
            },
        )
    )

    # =====================================================
    # PAYSTACK
    # =====================================================

    headers = {
        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}",

        "Content-Type":
            "application/json",
    }

    callback_url = (
        f"{settings.UNIT_BACKEND_URL}"
        f"/api/v1/subscription/paystack/callback/"
    )

    payload = {
        "email":
            user.email,

        "amount":
            paystack_amount,

        "currency":
            "KES",

        "reference":
            payment_reference,

        "callback_url":
            callback_url,

        "metadata": {
            "organization_id":
                organization.id,

            "organization_name":
                organization.name,

            "user_id":
                user.id,

            "package_id":
                package.id,

            "package_code":
                package.code,

            "billing_cycle":
                billing_cycle,

            "subscription_payment_id":
                payment.id,
        },
    }

    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=30,
        )

        data = response.json()

    except Exception as error:
        payment.status = (
            "failed"
        )

        payment.metadata = {
            **payment.metadata,

            "initialization_error":
                str(error),
        }

        payment.save(
            update_fields=[
                "status",
                "metadata",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "Unable to connect to Paystack."
            },
            status=502,
        )

    # =====================================================
    # INITIALIZATION FAILED
    # =====================================================

    if not data.get(
        "status"
    ):
        payment.status = (
            "failed"
        )

        payment.metadata = {
            **payment.metadata,

            "paystack_initialization":
                data,
        }

        payment.save(
            update_fields=[
                "status",
                "metadata",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "Unable to initialize Paystack payment.",

                "paystack_response":
                    data,
            },
            status=400,
        )

    # =====================================================
    # SAVE PAYSTACK REFERENCE
    # =====================================================

    paystack_data = (
        data.get(
            "data",
            {}
        )
    )

    authorization_url = (
        paystack_data.get(
            "authorization_url"
        )
    )

    reference = (
        paystack_data.get(
            "reference"
        )
    )

    payment.external_reference = (
        reference
    )

    payment.metadata = {
        **payment.metadata,

        "authorization_url":
            authorization_url,

        "paystack_access_code":
            paystack_data.get(
                "access_code"
            ),
    }

    payment.save(
        update_fields=[
            "external_reference",
            "metadata",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "message":
                "Payment initialized successfully.",

            "authorization_url":
                authorization_url,

            "reference":
                reference,

            "payment": {
                "id":
                    payment.id,

                "payment_reference":
                    payment.payment_reference,

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "billing_cycle":
                    payment.billing_cycle,

                "package": {
                    "id":
                        package.id,

                    "code":
                        package.code,

                    "name":
                        package.name,
                },
            },
        },
        status=200,
    )


def activate_paid_subscription(
    payment,
    paystack_data,
):
    now = timezone.now()

    subscription = (
        payment.subscription
    )

    # =====================================================
    # DON'T ACTIVATE TWICE
    # =====================================================

    if payment.status == "completed":
        return subscription

    # =====================================================
    # PERIOD
    # =====================================================

    period_start = (
        now
    )

    if payment.billing_cycle == "yearly":
        period_end = (
            period_start +
            relativedelta(
                years=1
            )
        )

    else:
        period_end = (
            period_start +
            relativedelta(
                months=1
            )
        )

    # =====================================================
    # PAYMENT
    # =====================================================

    payment.status = (
        "completed"
    )

    payment.paid_at = (
        now
    )

    payment.period_start = (
        period_start
    )

    payment.period_end = (
        period_end
    )

    payment.external_reference = (
        paystack_data.get(
            "reference"
        )
        or payment.external_reference
    )

    payment.metadata = {
        **(
            payment.metadata
            or {}
        ),

        "paystack_transaction_id":
            paystack_data.get(
                "id"
            ),

        "paystack_channel":
            paystack_data.get(
                "channel"
            ),

        "paystack_gateway_response":
            paystack_data.get(
                "gateway_response"
            ),
    }

    payment.save()

    # =====================================================
    # ORGANIZATION SUBSCRIPTION
    # =====================================================

    subscription.package = (
        payment.package
    )

    subscription.billing_cycle = (
        payment.billing_cycle
    )

    subscription.status = (
        "active"
    )

    subscription.current_period_start = (
        period_start
    )

    subscription.current_period_end = (
        period_end
    )

    subscription.cancelled_at = (
        None
    )

    subscription.auto_renew = (
        True
    )

    subscription.save()

    return subscription



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_subscription_payment(
    request,
    reference,
):
    try:
        payment = (
            SubscriptionPayment.objects
            .select_related(
                "organization",
                "subscription",
                "package",
            )
            .get(
                payment_reference=
                    reference
            )
        )

    except SubscriptionPayment.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Subscription payment not found."
            },
            status=404,
        )

    # Ensure logged-in user can manage
    # this organization.

    (
        organization,
        error_response,
    ) = get_subscription_manager(
        request.user,
        payment.organization_id,
    )

    if error_response:
        return error_response

    # Already completed

    if payment.status == "completed":
        return JsonResponse(
            {
                "success": True,

                "message":
                    "Payment already verified.",

                "status":
                    "completed",
            },
            status=200,
        )

    headers = {
        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers,
            timeout=30,
        )

        data = response.json()

    except Exception as error:
        return JsonResponse(
            {
                "message":
                    "Unable to verify payment with Paystack."
            },
            status=502,
        )

    if not data.get(
        "status"
    ):
        return JsonResponse(
            {
                "message":
                    "Paystack verification failed."
            },
            status=400,
        )

    payment_data = (
        data.get(
            "data",
            {}
        )
    )

    if (
        payment_data.get(
            "status"
        ) !=
        "success"
    ):
        return JsonResponse(
            {
                "success": False,

                "message":
                    "Payment has not been completed.",

                "status":
                    payment_data.get(
                        "status"
                    ),
            },
            status=400,
        )

    # =====================================================
    # VERIFY AMOUNT
    # =====================================================

    expected_amount = int(
        payment.amount *
        100
    )

    received_amount = int(
        payment_data.get(
            "amount",
            0
        )
    )

    if (
        received_amount !=
        expected_amount
    ):
        return JsonResponse(
            {
                "message":
                    "Payment amount does not match the subscription amount."
            },
            status=400,
        )

    with transaction.atomic():

        payment = (
            SubscriptionPayment.objects
            .select_for_update()
            .get(
                id=payment.id
            )
        )

        subscription = (
            activate_paid_subscription(
                payment,
                payment_data,
            )
        )

    return JsonResponse(
        {
            "success": True,

            "message":
                "Subscription payment verified successfully.",

            "subscription": {
                "id":
                    subscription.id,

                "status":
                    subscription.status,

                "package":
                    subscription.package.name,

                "billing_cycle":
                    subscription.billing_cycle,

                "current_period_start":
                    subscription
                    .current_period_start
                    .isoformat(),

                "current_period_end":
                    subscription
                    .current_period_end
                    .isoformat(),
            },
        },
        status=200,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def subscription_paystack_callback(
    request
):
    reference = (
        request.GET.get(
            "reference"
        )
        or
        request.GET.get(
            "trxref"
        )
    )

    if not reference:
        return JsonResponse(
            {
                "message":
                    "Payment reference was not provided."
            },
            status=400,
        )

    try:
        payment = (
            SubscriptionPayment.objects
            .select_related(
                "subscription",
                "package",
                "organization",
            )
            .get(
                payment_reference=
                    reference
            )
        )

    except SubscriptionPayment.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Payment record not found."
            },
            status=404,
        )

    # Already processed

    if payment.status == "completed":
        return JsonResponse(
            {
                "success": True,

                "message":
                    "Subscription is already active.",

                "reference":
                    reference,
            },
            status=200,
        )

    headers = {
        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers,
            timeout=30,
        )

        data = response.json()

    except Exception:
        return JsonResponse(
            {
                "message":
                    "Unable to verify payment."
            },
            status=502,
        )

    if not data.get(
        "status"
    ):
        return JsonResponse(
            {
                "message":
                    "Paystack verification failed."
            },
            status=400,
        )

    payment_data = (
        data.get(
            "data",
            {}
        )
    )

    if (
        payment_data.get(
            "status"
        ) !=
        "success"
    ):
        return JsonResponse(
            {
                "success": False,

                "message":
                    "Payment was not successful."
            },
            status=400,
        )

    # =====================================================
    # CHECK AMOUNT
    # =====================================================

    expected_amount = int(
        payment.amount *
        100
    )

    if (
        int(
            payment_data.get(
                "amount",
                0
            )
        )
        !=
        expected_amount
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid payment amount."
            },
            status=400,
        )

    # =====================================================
    # ACTIVATE
    # =====================================================

    with transaction.atomic():

        payment = (
            SubscriptionPayment.objects
            .select_for_update()
            .get(
                id=payment.id
            )
        )

        subscription = (
            activate_paid_subscription(
                payment,
                payment_data,
            )
        )

    return JsonResponse(
        {
            "success": True,

            "message":
                "Subscription activated successfully.",

            "reference":
                reference,

            "package":
                subscription.package.name,

            "billing_cycle":
                subscription.billing_cycle,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_payment_history(
    request
):
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
        error_response,
    ) = get_subscription_manager(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    payments = (
        SubscriptionPayment.objects
        .filter(
            organization=
                organization
        )
        .select_related(
            "package"
        )
        .order_by(
            "-created_at"
        )
    )

    results = []

    for payment in payments:
        results.append(
            {
                "id":
                    payment.id,

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "package": {
                    "id":
                        payment.package.id,

                    "code":
                        payment.package.code,

                    "name":
                        payment.package.name,
                },

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "billing_cycle":
                    payment.billing_cycle,

                "payment_method":
                    payment.payment_method,

                "status":
                    payment.status,

                "paid_at": (
                    payment.paid_at
                    .isoformat()
                    if payment.paid_at
                    else None
                ),

                "period_start": (
                    payment.period_start
                    .isoformat()
                    if payment.period_start
                    else None
                ),

                "period_end": (
                    payment.period_end
                    .isoformat()
                    if payment.period_end
                    else None
                ),

                "created_at":
                    payment.created_at
                    .isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "payments": results,
        },
        status=200,
    )
