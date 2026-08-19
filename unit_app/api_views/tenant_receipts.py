from .common_imports import *



def get_receipt_tenant_context(
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
                organization=
                    organization,

                user=
                    user,

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

    if "tenant" not in role_codes:
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
                organization=
                    organization,

                user=
                    user,

                status=
                    "active",
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
def tenant_receipts(request):
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
    ) = get_receipt_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    payments = (
        Payment.objects
        .filter(
            organization=
                organization,

            tenant=
                tenant,

            status=
                "completed",
        )
        .order_by(
            "-paid_at",
            "-created_at",
        )
    )

    total_paid = (
        payments
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    results = []

    for payment in payments:
        allocation = (
            PaymentAllocation.objects
            .filter(
                payment=payment
            )
            .select_related(
                "invoice"
            )
            .order_by(
                "id"
            )
            .first()
        )

        invoice = (
            allocation.invoice
            if allocation
            else None
        )

        metadata = (
            payment.metadata
            or {}
        )

        mpesa_receipt_number = (
            metadata.get(
                "mpesa_receipt_number"
            )
        )

        receipt_number = (
            f"RCT-{payment.id:06d}"
        )

        results.append(
            {
                "id":
                    payment.id,

                "receipt_number":
                    receipt_number,

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "mpesa_receipt_number":
                    mpesa_receipt_number,

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "provider":
                    payment.provider,

                "provider_label":
                    payment
                    .get_provider_display(),

                "payment_method":
                    payment.payment_method,

                "payment_method_label":
                    payment
                    .get_payment_method_display(),

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

                "invoice_id": (
                    invoice.id
                    if invoice
                    else None
                ),

                "invoice_number": (
                    invoice.invoice_number
                    if invoice
                    else None
                ),

                "invoice_type": (
                    invoice.invoice_type
                    if invoice
                    else None
                ),

                "allocated_amount": (
                    str(
                        allocation
                        .allocated_amount
                    )
                    if allocation
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "summary": {
                "count":
                    payments.count(),

                "total_paid":
                    str(
                        total_paid
                    ),
            },

            "receipts":
                results,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_receipt_detail(
    request,
    payment_id,
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
        tenant,
        error_response,
    ) = get_receipt_tenant_context(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        payment = (
            Payment.objects.get(
                id=payment_id,

                organization=
                    organization,

                tenant=
                    tenant,

                status=
                    "completed",
            )
        )

    except Payment.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Receipt not found."
            },
            status=404,
        )

    allocations = (
        PaymentAllocation.objects
        .filter(
            payment=payment
        )
        .select_related(
            "invoice"
        )
        .order_by(
            "id"
        )
    )

    allocation_data = []

    for allocation in allocations:
        invoice = (
            allocation.invoice
        )

        allocation_data.append(
            {
                "id":
                    allocation.id,

                "allocated_amount":
                    str(
                        allocation
                        .allocated_amount
                    ),

                "invoice": {
                    "id":
                        invoice.id,

                    "invoice_number":
                        invoice.invoice_number,

                    "invoice_type":
                        invoice.invoice_type,

                    "invoice_type_label":
                        invoice
                        .get_invoice_type_display(),

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

                    "due_date":
                        str(
                            invoice.due_date
                        ),
                },
            }
        )

    metadata = (
        payment.metadata
        or {}
    )

    return JsonResponse(
        {
            "receipt": {
                "id":
                    payment.id,

                "receipt_number":
                    f"RCT-{payment.id:06d}",

                "payment_reference":
                    payment.payment_reference,

                "external_reference":
                    payment.external_reference,

                "mpesa_receipt_number":
                    metadata.get(
                        "mpesa_receipt_number"
                    ),

                "amount":
                    str(
                        payment.amount
                    ),

                "currency":
                    payment.currency,

                "provider":
                    payment.provider,

                "provider_label":
                    payment
                    .get_provider_display(),

                "payment_method":
                    payment.payment_method,

                "payment_method_label":
                    payment
                    .get_payment_method_display(),

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
            },

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "allocations":
                allocation_data,
        },
        status=200,
    )