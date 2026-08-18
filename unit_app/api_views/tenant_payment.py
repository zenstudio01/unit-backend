from .common_imports import *

def get_payment_tenant(
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
                user=user,
                organization=organization,
                status="active",
            )
        )

    except Tenant.DoesNotExist:
        return (
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
        tenant,
        None,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_payments(request):
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
        tenant,
        error_response,
    ) = get_payment_tenant(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    # =====================================================
    # INVOICES
    # =====================================================

    invoice_queryset = (
        Invoice.objects
        .filter(
            organization=organization,
            tenant=tenant,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
        .order_by(
            "-issue_date",
            "-created_at",
        )
    )

    outstanding_balance = (
        invoice_queryset
        .filter(
            balance__gt=0
        )
        .aggregate(
            total=Sum(
                "balance"
            )
        )["total"]
        or Decimal("0.00")
    )

    next_invoice = (
        invoice_queryset
        .filter(
            balance__gt=0
        )
        .order_by(
            "due_date"
        )
        .first()
    )

    invoices = []

    for invoice in (
        invoice_queryset[:30]
    ):
        invoices.append(
            {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "title":
                    invoice
                    .get_invoice_type_display(),

                "issue_date":
                    str(
                        invoice.issue_date
                    ),

                "due_date":
                    str(
                        invoice.due_date
                    ),

                "total_amount":
                    str(
                        invoice.total_amount
                    ),

                "paid_amount":
                    str(
                        invoice.paid_amount
                    ),

                "balance":
                    str(
                        invoice.balance
                    ),

                "status":
                    invoice.status,
            }
        )

    # =====================================================
    # PAYMENTS
    # =====================================================

    payment_queryset = (
        Payment.objects
        .filter(
            organization=organization,
            tenant=tenant,
        )
        .order_by(
            "-created_at"
        )
    )

    now = timezone.now()

    paid_this_month = (
        payment_queryset
        .filter(
            status="completed",
            paid_at__year=
                now.year,
            paid_at__month=
                now.month,
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    total_paid = (
        payment_queryset
        .filter(
            status="completed"
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    payments = []

    for payment in (
        payment_queryset[:30]
    ):
        payments.append(
            {
                "id":
                    payment.id,

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "provider":
                    payment.provider,

                "provider_label":
                    payment.get_provider_display(),

                "payment_method":
                    payment.payment_method,

                "payment_method_label":
                    payment.get_payment_method_display(),

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "status":
                    payment.status,

                "paid_at": (
                    payment.paid_at
                    .isoformat()
                    if payment.paid_at
                    else None
                ),

                "created_at":
                    payment.created_at
                    .isoformat(),
            }
        )

    return JsonResponse(
        {
            "tenant": {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "phone_number":
                    tenant.phone_number,

                "email":
                    tenant.email,
            },

            "summary": {
                "outstanding_balance":
                    str(
                        outstanding_balance
                    ),

                "paid_this_month":
                    str(
                        paid_this_month
                    ),

                "total_paid":
                    str(
                        total_paid
                    ),

                "next_due_date": (
                    str(
                        next_invoice.due_date
                    )
                    if next_invoice
                    else None
                ),

                "next_due_amount": (
                    str(
                        next_invoice.balance
                    )
                    if next_invoice
                    else "0.00"
                ),
            },

            "invoices":
                invoices,

            "payments":
                payments,
        },
        status=200,
    )




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_tenant_payment(request):
    data = request.data

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    invoice_id = (
        data.get(
            "invoice_id"
        )
    )

    phone_number = str(
        data.get(
            "phone_number",
            ""
        )
    ).strip()

    amount_raw = (
        data.get(
            "amount"
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

    if not invoice_id:
        return JsonResponse(
            {
                "message":
                    "invoice_id is required."
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

    try:
        amount = Decimal(
            str(
                amount_raw
            )
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid payment amount."
            },
            status=400,
        )

    if amount <= 0:
        return JsonResponse(
            {
                "message":
                    "Amount must be greater than zero."
            },
            status=400,
        )

    (
        organization,
        tenant,
        error_response,
    ) = get_payment_tenant(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        invoice = (
            Invoice.objects.get(
                id=invoice_id,
                organization=organization,
                tenant=tenant,
            )
        )

    except Invoice.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Invoice not found."
            },
            status=404,
        )

    if invoice.status in [
        "paid",
        "cancelled",
        "void",
    ]:
        return JsonResponse(
            {
                "message":
                    "This invoice cannot be paid."
            },
            status=400,
        )

    if invoice.balance <= 0:
        return JsonResponse(
            {
                "message":
                    "This invoice has no outstanding balance."
            },
            status=400,
        )

    if amount > invoice.balance:
        return JsonResponse(
            {
                "message":
                    "Payment cannot exceed the invoice balance."
            },
            status=400,
        )

    # =====================================================
    # INTERNAL PAYMENT REFERENCE
    # =====================================================

    payment_reference = (
        "PAY-"
        f"{organization.id}-"
        f"{uuid.uuid4().hex[:10].upper()}"
    )

    # =====================================================
    # CREATE PENDING PAYMENT FIRST
    # =====================================================

    payment = (
        Payment.objects.create(
            organization=
                organization,

            tenant=
                tenant,

            amount=
                amount,

            currency=
                "KES",

            provider=
                "mpesa",

            payment_method=
                "mobile_money",

            payment_reference=
                payment_reference,

            status=
                "pending",

            metadata={
                "invoice_id":
                    invoice.id,

                "phone_number":
                    phone_number,
            },
        )
    )

    try:
        mpesa_response = (
            initiate_stk_push(
                phone_number=
                    phone_number,

                amount=
                    amount,

                account_reference=
                    invoice.invoice_number,

                description=
                    f"UNIT Rent {invoice.invoice_number}",
            )
        )

        checkout_request_id = (
            mpesa_response.get(
                "CheckoutRequestID"
            )
        )

        merchant_request_id = (
            mpesa_response.get(
                "MerchantRequestID"
            )
        )

        response_code = str(
            mpesa_response.get(
                "ResponseCode",
                ""
            )
        )

        if response_code != "0":
            payment.status = (
                "failed"
            )

            payment.metadata = {
                **(
                    payment.metadata
                    or {}
                ),

                "mpesa_response":
                    mpesa_response,
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
                        mpesa_response.get(
                            "ResponseDescription",
                            "Unable to initiate M-Pesa payment.",
                        )
                },
                status=400,
            )

        payment.external_reference = (
            checkout_request_id
        )

        payment.metadata = {
            **(
                payment.metadata
                or {}
            ),

            "checkout_request_id":
                checkout_request_id,

            "merchant_request_id":
                merchant_request_id,
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
                    "M-Pesa payment request sent successfully.",

                "payment": {
                    "id":
                        payment.id,

                    "payment_reference":
                        payment.payment_reference,

                    "amount":
                        str(
                            payment.amount
                        ),

                    "status":
                        payment.status,
                },

                "checkout_request_id":
                    checkout_request_id,
            },
            status=201,
        )

    except Exception as error:
        print(
            "MPESA INITIATION ERROR:",
            str(error),
        )

        payment.status = (
            "failed"
        )

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return JsonResponse(
            {
                "message":
                    "Unable to initiate M-Pesa payment."
            },
            status=500,
        )




@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_payment_callback(request):
    data = request.data

    try:
        callback = (
            data["Body"][
                "stkCallback"
            ]
        )

    except (
        KeyError,
        TypeError,
    ):
        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc":
                    "Accepted",
            }
        )

    checkout_request_id = (
        callback.get(
            "CheckoutRequestID"
        )
    )

    result_code = (
        callback.get(
            "ResultCode"
        )
    )

    try:
        payment = (
            Payment.objects
            .select_for_update()
            .get(
                external_reference=
                    checkout_request_id
            )
        )

    except Payment.DoesNotExist:
        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc":
                    "Accepted",
            }
        )

    # Already processed callback
    if (
        payment.status ==
        "completed"
    ):
        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc":
                    "Already processed",
            }
        )

    # =====================================================
    # FAILED / CANCELLED
    # =====================================================

    if result_code != 0:
        payment.status = (
            "failed"
        )

        payment.metadata = {
            **(
                payment.metadata
                or {}
            ),

            "mpesa_callback":
                callback,
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
                "ResultCode": 0,
                "ResultDesc":
                    "Accepted",
            }
        )

    # =====================================================
    # CALLBACK ITEMS
    # =====================================================

    callback_items = (
        callback
        .get(
            "CallbackMetadata",
            {}
        )
        .get(
            "Item",
            []
        )
    )

    metadata = {}

    for item in callback_items:
        name = (
            item.get(
                "Name"
            )
        )

        value = (
            item.get(
                "Value"
            )
        )

        metadata[name] = (
            value
        )

    receipt_number = (
        metadata.get(
            "MpesaReceiptNumber"
        )
    )

    actual_amount = Decimal(
        str(
            metadata.get(
                "Amount",
                payment.amount,
            )
        )
    )

    invoice_id = (
        payment.metadata
        .get(
            "invoice_id"
        )
    )

    try:
        with transaction.atomic():

            invoice = (
                Invoice.objects
                .select_for_update()
                .get(
                    id=invoice_id,
                    tenant=
                        payment.tenant,

                    organization=
                        payment.organization,
                )
            )

            # Prevent double allocation
            if (
                PaymentAllocation.objects
                .filter(
                    payment=payment,
                    invoice=invoice,
                )
                .exists()
            ):
                return JsonResponse(
                    {
                        "ResultCode":
                            0,

                        "ResultDesc":
                            "Already allocated",
                    }
                )

            amount_to_allocate = min(
                actual_amount,
                invoice.balance,
            )

            # ---------------------------------------------
            # PAYMENT
            # ---------------------------------------------

            payment.amount = (
                actual_amount
            )

            payment.status = (
                "completed"
            )

            payment.paid_at = (
                timezone.now()
            )

            payment.external_reference = (
                receipt_number
                or
                checkout_request_id
            )

            payment.metadata = {
                **(
                    payment.metadata
                    or {}
                ),

                "checkout_request_id":
                    checkout_request_id,

                "mpesa_receipt_number":
                    receipt_number,

                "mpesa_callback":
                    callback,
            }

            payment.save()

            # ---------------------------------------------
            # ALLOCATION
            # ---------------------------------------------

            PaymentAllocation.objects.create(
                payment=
                    payment,

                invoice=
                    invoice,

                allocated_amount=
                    amount_to_allocate,
            )

            # ---------------------------------------------
            # INVOICE
            # ---------------------------------------------

            invoice.paid_amount = (
                invoice.paid_amount +
                amount_to_allocate
            )

            invoice.balance = max(
                Decimal("0.00"),
                invoice.total_amount -
                invoice.paid_amount,
            )

            if invoice.balance <= 0:
                invoice.status = (
                    "paid"
                )

            elif invoice.paid_amount > 0:
                invoice.status = (
                    "partially_paid"
                )

            invoice.save()

    except Invoice.DoesNotExist:
        print(
            "PAYMENT INVOICE NOT FOUND:",
            invoice_id
        )

    return JsonResponse(
        {
            "ResultCode": 0,
            "ResultDesc":
                "Accepted",
        }
    )



