from .common_imports import *
from .helper import *

import uuid

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)


# ============================================================
# RECORD MANUAL PAYMENT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def record_manual_payment(request):

    user = request.user
    data = request.data

    # ========================================================
    # REQUEST DATA
    # ========================================================

    organization_id = data.get(
        "organization_id"
    )

    tenant_id = data.get(
        "tenant_id"
    )

    lease_id = data.get(
        "lease_id"
    )

    invoice_id = data.get(
        "invoice_id"
    )

    amount_raw = data.get(
        "amount"
    )

    frontend_payment_method = str(
        data.get(
            "payment_method",
            ""
        )
        or ""
    ).strip().lower()

    external_reference = str(
        data.get(
            "external_reference"
        )
        or
        data.get(
            "reference"
        )
        or ""
    ).strip()

    payment_date_raw = str(
        data.get(
            "payment_date",
            ""
        )
        or ""
    ).strip()

    notes = str(
        data.get(
            "notes",
            ""
        )
        or ""
    ).strip()

    currency = str(
        data.get(
            "currency",
            "KES"
        )
        or "KES"
    ).strip().upper()

    # ========================================================
    # DEBUG REQUEST
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "RECORD MANUAL PAYMENT REQUEST"
    )

    print(
        "DATA:",
        data
    )

    print(
        "========================================"
    )

    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    missing_fields = []

    if not organization_id:
        missing_fields.append(
            "organization_id"
        )

    if not tenant_id:
        missing_fields.append(
            "tenant_id"
        )

    if not lease_id:
        missing_fields.append(
            "lease_id"
        )

    if amount_raw in [
        None,
        "",
    ]:
        missing_fields.append(
            "amount"
        )

    if not frontend_payment_method:
        missing_fields.append(
            "payment_method"
        )

    if missing_fields:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Missing required fields.",

                "fields":
                    missing_fields,
            },
            status=400,
        )

    # ========================================================
    # NORMALIZE IDs
    # ========================================================

    try:
        organization_id = int(
            organization_id
        )

        tenant_id = int(
            tenant_id
        )

        lease_id = int(
            lease_id
        )

        if invoice_id not in [
            None,
            "",
            "null",
            "undefined",
        ]:
            invoice_id = int(
                invoice_id
            )

        else:
            invoice_id = None

    except (
        ValueError,
        TypeError,
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid organization, tenant, lease, or invoice ID."
            },
            status=400,
        )

    # ========================================================
    # AMOUNT
    # ========================================================

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
                "success":
                    False,

                "message":
                    "Enter a valid payment amount."
            },
            status=400,
        )

    if amount <= 0:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Payment amount must be greater than zero."
            },
            status=400,
        )

    # ========================================================
    # CURRENCY
    # ========================================================

    if len(
        currency
    ) != 3:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Currency must use a valid 3-letter ISO code."
            },
            status=400,
        )

    # ========================================================
    # PAYMENT METHOD MAPPING
    # ========================================================

    PAYMENT_MAPPING = {

        "mpesa": {
            "provider":
                "mpesa",

            "payment_method":
                "mobile_money",
        },

        "mobile_money": {
            "provider":
                "mpesa",

            "payment_method":
                "mobile_money",
        },

        "paystack": {
            "provider":
                "paystack",

            "payment_method":
                "card",
        },

        "card": {
            "provider":
                "paystack",

            "payment_method":
                "card",
        },

        "stripe": {
            "provider":
                "stripe",

            "payment_method":
                "card",
        },

        "bank": {
            "provider":
                "bank",

            "payment_method":
                "bank_transfer",
        },

        "bank_transfer": {
            "provider":
                "bank",

            "payment_method":
                "bank_transfer",
        },

        "cash": {
            "provider":
                "cash",

            "payment_method":
                "cash",
        },

        "cheque": {
            "provider":
                "bank",

            "payment_method":
                "cheque",
        },

        "other": {
            "provider":
                "other",

            "payment_method":
                "other",
        },
    }

    payment_config = (
        PAYMENT_MAPPING.get(
            frontend_payment_method
        )
    )

    if not payment_config:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid payment method.",

                "received":
                    frontend_payment_method,

                "allowed_methods":
                    list(
                        PAYMENT_MAPPING.keys()
                    ),
            },
            status=400,
        )

    provider = (
        payment_config[
            "provider"
        ]
    )

    payment_method = (
        payment_config[
            "payment_method"
        ]
    )

    print(
        "PAYMENT PROVIDER:",
        provider
    )

    print(
        "PAYMENT METHOD:",
        payment_method
    )

    # ========================================================
    # PAYMENT DATE
    # ========================================================

    paid_at = timezone.now()

    if payment_date_raw:

        payment_date = parse_date(
            payment_date_raw
        )

        if not payment_date:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "payment_date must use YYYY-MM-DD format."
                },
                status=400,
            )

        local_now = (
            timezone.localtime()
        )

        naive_datetime = (
            datetime.combine(
                payment_date,
                local_now.time().replace(
                    microsecond=0
                ),
            )
        )

        paid_at = (
            timezone.make_aware(
                naive_datetime,
                timezone.get_current_timezone(),
            )
        )

    # ========================================================
    # ORGANIZATION
    # ========================================================

    organization = (
        Organization.objects
        .filter(
            id=organization_id
        )
        .first()
    )

    if not organization:

        print(
            "ORGANIZATION NOT FOUND:",
            organization_id
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Organization not found.",

                "organization_id":
                    organization_id,
            },
            status=400,
        )

    print(
        "ORGANIZATION FOUND:",
        organization.id
    )

    # ========================================================
    # ORGANIZATION MEMBERSHIP
    # ========================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=
                organization,

            user=
                user,

            is_active=
                True,
        )
        .prefetch_related(
            "roles"
        )
        .first()
    )

    if not membership:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # ========================================================
    # PERMISSIONS
    # ========================================================

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
        "property_manager",
        "accountant",
        "owner",
        "landlord",
    }

    if not role_codes.intersection(
        allowed_roles
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "You do not have permission to record payments."
            },
            status=403,
        )

    # ========================================================
    # TENANT
    # ========================================================

    tenant = (
        Tenant.objects
        .filter(
            id=tenant_id,
            organization=organization,
        )
        .first()
    )

    if not tenant:

        print(
            "TENANT NOT FOUND:",
            tenant_id
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Tenant not found in this organization.",

                "tenant_id":
                    tenant_id,
            },
            status=400,
        )

    print(
        "TENANT FOUND:",
        tenant.id
    )

    # ========================================================
    # LEASE
    # ========================================================

    lease = (
        Lease.objects
        .select_related(
            "unit",
            "unit__property",
            "unit__building",
            "unit__floor",
        )
        .filter(
            id=lease_id,
            organization=organization,
        )
        .first()
    )

    if not lease:

        print(
            "LEASE NOT FOUND:",
            lease_id
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Lease not found in this organization.",

                "lease_id":
                    lease_id,
            },
            status=400,
        )

    print(
        "LEASE FOUND:",
        lease.id
    )

    if not lease.unit:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "The selected lease does not have a unit."
            },
            status=400,
        )

    if not lease.unit.property:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "The lease unit is not linked to a property."
            },
            status=400,
        )

    property_obj = (
        lease.unit.property
    )

    # ========================================================
    # TENANT MUST BELONG TO LEASE
    # ========================================================

    lease_tenant = (
        LeaseTenant.objects
        .filter(
            lease=
                lease,

            tenant=
                tenant,

            left_at__isnull=
                True,
        )
        .first()
    )

    if not lease_tenant:

        print(
            "TENANT NOT LINKED TO LEASE"
        )

        print(
            "TENANT:",
            tenant.id
        )

        print(
            "LEASE:",
            lease.id
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "The selected tenant is not linked to the selected lease.",

                "tenant_id":
                    tenant.id,

                "lease_id":
                    lease.id,
            },
            status=400,
        )

    # ========================================================
    # EXTERNAL REFERENCE DUPLICATE
    # ========================================================

    if external_reference:

        duplicate_payment = (
            Payment.objects
            .filter(
                organization=
                    organization,

                external_reference__iexact=
                    external_reference,
            )
            .first()
        )

        if duplicate_payment:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "A payment with this transaction reference already exists.",

                    "existing_payment": {
                        "id":
                            duplicate_payment.id,

                        "payment_reference":
                            duplicate_payment.payment_reference,
                    },
                },
                status=400,
            )

    # ========================================================
    # INVOICE PRE-CHECK
    # ========================================================

    invoice = None

    if invoice_id:

        print(
            "SEARCHING INVOICE:",
            invoice_id
        )

        invoice = (
            Invoice.objects
            .select_related(
                "organization",
                "tenant",
                "lease",
                "property",
            )
            .filter(
                id=invoice_id
            )
            .first()
        )

        # ----------------------------------------------------
        # INVOICE DOES NOT EXIST AT ALL
        # ----------------------------------------------------

        if not invoice:

            print(
                "INVOICE DOES NOT EXIST:",
                invoice_id
            )

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "The selected invoice does not exist.",

                    "invoice_id":
                        invoice_id,
                },
                status=400,
            )

        print(
            "INVOICE FOUND:",
            invoice.id
        )

        print(
            "INVOICE ORGANIZATION:",
            invoice.organization_id
        )

        print(
            "INVOICE TENANT:",
            invoice.tenant_id
        )

        print(
            "INVOICE LEASE:",
            invoice.lease_id
        )

        # ----------------------------------------------------
        # ORGANIZATION
        # ----------------------------------------------------

        if (
            invoice.organization_id
            != organization.id
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "The selected invoice belongs to another organization.",

                    "invoice_id":
                        invoice.id,

                    "invoice_organization_id":
                        invoice.organization_id,

                    "selected_organization_id":
                        organization.id,
                },
                status=400,
            )

        # ----------------------------------------------------
        # TENANT
        # ----------------------------------------------------

        if (
            invoice.tenant_id
            != tenant.id
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "The selected invoice does not belong to this tenant.",

                    "invoice_id":
                        invoice.id,

                    "invoice_tenant_id":
                        invoice.tenant_id,

                    "selected_tenant_id":
                        tenant.id,
                },
                status=400,
            )

        # ----------------------------------------------------
        # LEASE
        # ----------------------------------------------------

        if (
            invoice.lease_id
            != lease.id
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "The selected invoice does not belong to this lease.",

                    "invoice_id":
                        invoice.id,

                    "invoice_lease_id":
                        invoice.lease_id,

                    "selected_lease_id":
                        lease.id,
                },
                status=400,
            )

        # ----------------------------------------------------
        # PROPERTY
        # ----------------------------------------------------

        if (
            invoice.property_id
            and
            invoice.property_id
            != property_obj.id
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "The invoice belongs to a different property.",

                    "invoice_property_id":
                        invoice.property_id,

                    "lease_property_id":
                        property_obj.id,
                },
                status=400,
            )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if invoice.status in [
            "cancelled",
            "void",
        ]:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "Payments cannot be recorded against this invoice.",

                    "invoice_status":
                        invoice.status,
                },
                status=400,
            )

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        invoice_balance = (
            invoice.balance
            or Decimal(
                "0.00"
            )
        )

        if invoice_balance <= 0:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "This invoice has already been fully paid."
                },
                status=400,
            )

        # ----------------------------------------------------
        # OVERPAYMENT
        # ----------------------------------------------------

        if amount > invoice_balance:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        "Payment amount exceeds the invoice balance.",

                    "payment_amount":
                        str(
                            amount
                        ),

                    "invoice_balance":
                        str(
                            invoice_balance
                        ),
                },
                status=400,
            )

    # ========================================================
    # CREATE PAYMENT
    # ========================================================

    try:

        with transaction.atomic():

            # =================================================
            # LOCK INVOICE AGAIN
            # =================================================

            if invoice:

                invoice = (
                    Invoice.objects
                    .select_for_update()
                    .get(
                        id=
                            invoice.id
                    )
                )

                # Re-check balance after database lock

                invoice_balance = (
                    invoice.balance
                    or Decimal(
                        "0.00"
                    )
                )

                if invoice_balance <= 0:

                    return JsonResponse(
                        {
                            "success":
                                False,

                            "message":
                                "This invoice has already been fully paid."
                        },
                        status=400,
                    )

                if amount > invoice_balance:

                    return JsonResponse(
                        {
                            "success":
                                False,

                            "message":
                                "Payment amount exceeds the current invoice balance.",

                            "payment_amount":
                                str(
                                    amount
                                ),

                            "invoice_balance":
                                str(
                                    invoice_balance
                                ),
                        },
                        status=400,
                    )

            # =================================================
            # PAYMENT REFERENCE
            # =================================================

            payment_reference = (
                "PAY-"
                f"{organization.id}-"
                f"{uuid.uuid4().hex[:12].upper()}"
            )

            # =================================================
            # PAYMENT METADATA
            # =================================================

            metadata = {
                "source":
                    "manual",

                "organization_id":
                    organization.id,

                "tenant_id":
                    tenant.id,

                "lease_id":
                    lease.id,

                "property_id":
                    property_obj.id,

                "unit_id":
                    lease.unit.id,

                "invoice_id": (
                    invoice.id
                    if invoice
                    else None
                ),

                "notes":
                    notes,

                "frontend_payment_method":
                    frontend_payment_method,

                "recorded_by_user_id":
                    user.id,
            }

            # =================================================
            # PAYMENT
            # =================================================

            payment = (
                Payment.objects.create(
                    organization=
                        organization,

                    tenant=
                        tenant,

                    payment_reference=
                        payment_reference,

                    external_reference=(
                        external_reference
                        or None
                    ),

                    provider=
                        provider,

                    payment_method=
                        payment_method,

                    amount=
                        amount,

                    currency=
                        currency,

                    status=
                        "completed",

                    paid_at=
                        paid_at,

                    received_by=
                        user,

                    metadata=
                        metadata,
                )
            )

            print(
                "PAYMENT CREATED:",
                payment.id,
                payment.payment_reference
            )

            # =================================================
            # PAYMENT ALLOCATION
            # =================================================

            allocation = None

            if invoice:

                allocation = (
                    PaymentAllocation.objects
                    .create(
                        payment=
                            payment,

                        invoice=
                            invoice,

                        allocated_amount=
                            amount,
                    )
                )

                # =============================================
                # UPDATE INVOICE
                # =============================================

                current_paid_amount = (
                    invoice.paid_amount
                    or Decimal(
                        "0.00"
                    )
                )

                invoice.paid_amount = (
                    current_paid_amount
                    + amount
                )

                invoice.balance = (
                    invoice.total_amount
                    - invoice.paid_amount
                )

                if invoice.balance <= 0:

                    invoice.balance = (
                        Decimal(
                            "0.00"
                        )
                    )

                    invoice.status = (
                        "paid"
                    )

                else:

                    invoice.status = (
                        "partially_paid"
                    )

                invoice.save(
                    update_fields=[
                        "paid_amount",
                        "balance",
                        "status",
                        "updated_at",
                    ]
                )

                print(
                    "INVOICE UPDATED:"
                )

                print(
                    "INVOICE:",
                    invoice.id
                )

                print(
                    "PAID:",
                    invoice.paid_amount
                )

                print(
                    "BALANCE:",
                    invoice.balance
                )

                print(
                    "STATUS:",
                    invoice.status
                )

            # =================================================
            # RECEIPT
            # =================================================

            receipt_number = (
                "RCT-"
                f"{organization.id}-"
                f"{uuid.uuid4().hex[:12].upper()}"
            )

            receipt = (
                Receipt.objects.create(
                    organization=
                        organization,

                    payment=
                        payment,

                    receipt_number=
                        receipt_number,

                    issued_by=
                        user,
                )
            )

            print(
                "RECEIPT CREATED:",
                receipt.receipt_number
            )

            # =================================================
            # RESPONSE
            # =================================================

            response_data = {

                "success":
                    True,

                "message":
                    "Payment recorded successfully.",

                "payment": {
                    "id":
                        payment.id,

                    "payment_reference":
                        payment.payment_reference,

                    "external_reference":
                        payment.external_reference,

                    "provider":
                        payment.provider,

                    "payment_method":
                        payment.payment_method,

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

                "lease": {
                    "id":
                        lease.id,

                    "lease_number":
                        lease.lease_number,

                    "status":
                        lease.status,

                    "property_id":
                        property_obj.id,

                    "property_name":
                        property_obj.name,

                    "unit_id":
                        lease.unit.id,

                    "unit_name":
                        lease.unit.name,

                    "unit_code":
                        lease.unit.unit_code,

                    "building": (
                        lease.unit
                        .building
                        .name
                        if lease.unit.building
                        else None
                    ),

                    "floor": (
                        lease.unit
                        .floor
                        .name
                        if lease.unit.floor
                        else None
                    ),
                },

                "receipt": {
                    "id":
                        receipt.id,

                    "receipt_number":
                        receipt.receipt_number,

                    "issued_at": (
                        receipt.issued_at
                        .isoformat()
                        if receipt.issued_at
                        else None
                    ),

                    "file_url":
                        receipt.file_url,
                },
            }

            # =================================================
            # INVOICE RESPONSE
            # =================================================

            if invoice:

                response_data[
                    "invoice"
                ] = {

                    "id":
                        invoice.id,

                    "invoice_number":
                        invoice.invoice_number,

                    "invoice_type":
                        invoice.invoice_type,

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

            else:

                response_data[
                    "invoice"
                ] = None

            # =================================================
            # ALLOCATION
            # =================================================

            if allocation:

                response_data[
                    "allocation"
                ] = {

                    "id":
                        allocation.id,

                    "allocated_amount":
                        str(
                            allocation
                            .allocated_amount
                        ),
                }

            else:

                response_data[
                    "allocation"
                ] = None

            print(
                "========================================"
            )

            print(
                "PAYMENT COMPLETED SUCCESSFULLY"
            )

            print(
                "PAYMENT:",
                payment.payment_reference
            )

            print(
                "========================================\n"
            )

            return JsonResponse(
                response_data,
                status=201,
            )

    # ========================================================
    # FINAL ERROR
    # ========================================================

    except Exception as error:

        print(
            "========================================"
        )

        print(
            "RECORD PAYMENT FAILED"
        )

        print(
            "ERROR:",
            repr(
                error
            )
        )

        print(
            "========================================"
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Unable to record payment.",

                "error":
                    str(
                        error
                    ),
            },
            status=500,
        )