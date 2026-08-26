from .common_imports import *
from .helper import *

from decimal import Decimal
from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)


# ============================================================
# INVOICE CREATE OPTIONS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_create_options(
    request
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not organization_id:
        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "organization_id is required."
            },
            status=400,
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
        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Organization not found."
            },
            status=404,
        )

    # ========================================================
    # MEMBERSHIP
    # ========================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
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
    # TENANTS
    # ========================================================

    tenants_queryset = (
        Tenant.objects
        .filter(
            organization=organization
        )
        .order_by(
            "full_name"
        )
    )

    tenants = []

    for tenant in tenants_queryset:

        lease_links = (
            LeaseTenant.objects
            .filter(
                tenant=tenant,
                left_at__isnull=True,
                lease__organization=
                    organization,
            )
            .exclude(
                lease__status__in=[
                    "cancelled",
                    "terminated",
                    "expired",
                ]
            )
            .select_related(
                "lease",
                "lease__unit",
                "lease__unit__property",
                "lease__unit__building",
                "lease__unit__floor",
            )
            .order_by(
                "-lease__created_at"
            )
        )

        leases = []

        for link in lease_links:

            lease = (
                link.lease
            )

            unit = (
                lease.unit
            )

            property_obj = (
                unit.property
                if unit
                else None
            )

            leases.append(
                {
                    "id":
                        lease.id,

                    "lease_number":
                        lease.lease_number,

                    "status":
                        lease.status,

                    "monthly_rent":
                        str(
                            lease.monthly_rent
                        ),

                    "billing_day":
                        lease.billing_day,

                    "payment_frequency":
                        lease.payment_frequency,

                    "start_date":
                        str(
                            lease.start_date
                        ),

                    "end_date":
                        str(
                            lease.end_date
                        ),

                    "property": (
                        {
                            "id":
                                property_obj.id,

                            "name":
                                property_obj.name,
                        }
                        if property_obj
                        else None
                    ),

                    "unit": (
                        {
                            "id":
                                unit.id,

                            "name":
                                unit.name,

                            "unit_code":
                                unit.unit_code,

                            "building": (
                                unit.building.name
                                if unit.building
                                else None
                            ),

                            "floor": (
                                unit.floor.name
                                if unit.floor
                                else None
                            ),
                        }
                        if unit
                        else None
                    ),
                }
            )

        tenants.append(
            {
                "id":
                    tenant.id,

                "full_name":
                    tenant.full_name,

                "email":
                    tenant.email,

                "phone_number":
                    tenant.phone_number,

                "leases":
                    leases,
            }
        )

    # ========================================================
    # INVOICE TYPES
    # ========================================================

    invoice_types = [
        {
            "value":
                value,

            "label":
                label,
        }
        for value, label
        in Invoice.INVOICE_TYPES
    ]

    charge_types = [
        {
            "value":
                value,

            "label":
                label,
        }
        for value, label
        in InvoiceItem.CHARGE_TYPES
    ]

    return JsonResponse(
        {
            "success":
                True,

            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "tenants":
                tenants,

            "invoice_types":
                invoice_types,

            "charge_types":
                charge_types,
        },
        status=200,
    )



from .common_imports import *
from .helper import *

import uuid

from decimal import (
    Decimal,
    InvalidOperation,
)

from django.db import (
    transaction,
)

from django.http import (
    JsonResponse,
)

from django.utils import (
    timezone,
)

from django.utils.dateparse import (
    parse_date,
)

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)


# ============================================================
# CREATE INVOICE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice(
    request
):
    user = request.user
    data = request.data

    # ========================================================
    # DATA
    # ========================================================

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    tenant_id = (
        data.get(
            "tenant_id"
        )
    )

    lease_id = (
        data.get(
            "lease_id"
        )
    )

    invoice_type = str(
        data.get(
            "invoice_type",
            "rent"
        )
        or "rent"
    ).strip().lower()

    issue_date_raw = str(
        data.get(
            "issue_date",
            ""
        )
        or ""
    ).strip()

    due_date_raw = str(
        data.get(
            "due_date",
            ""
        )
        or ""
    ).strip()

    discount_raw = (
        data.get(
            "discount_amount",
            0
        )
    )

    status = str(
        data.get(
            "status",
            "issued"
        )
        or "issued"
    ).strip().lower()

    items_raw = (
        data.get(
            "items"
        )
        or []
    )

    # ========================================================
    # DEBUG
    # ========================================================

    print(
        "========================================"
    )

    print(
        "CREATE INVOICE REQUEST"
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

    if not issue_date_raw:
        missing_fields.append(
            "issue_date"
        )

    if not due_date_raw:
        missing_fields.append(
            "due_date"
        )

    if not items_raw:
        missing_fields.append(
            "items"
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
    # IDS
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

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid organization, tenant, or lease ID."
            },
            status=400,
        )

    # ========================================================
    # DATES
    # ========================================================

    issue_date = (
        parse_date(
            issue_date_raw
        )
    )

    due_date = (
        parse_date(
            due_date_raw
        )
    )

    if not issue_date:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "issue_date must use YYYY-MM-DD format."
            },
            status=400,
        )

    if not due_date:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "due_date must use YYYY-MM-DD format."
            },
            status=400,
        )

    if due_date < issue_date:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Due date cannot be before issue date."
            },
            status=400,
        )

    # ========================================================
    # INVOICE TYPE
    # ========================================================

    valid_invoice_types = {
        value
        for value, label
        in Invoice.INVOICE_TYPES
    }

    if invoice_type not in valid_invoice_types:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid invoice type."
            },
            status=400,
        )

    # ========================================================
    # STATUS
    # ========================================================

    valid_statuses = {
        value
        for value, label
        in Invoice.STATUS_CHOICES
    }

    if status not in valid_statuses:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid invoice status."
            },
            status=400,
        )

    if status not in {
        "draft",
        "issued",
    }:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "New invoices can only be created as draft or issued."
            },
            status=400,
        )

    # ========================================================
    # DISCOUNT
    # ========================================================

    try:

        discount_amount = Decimal(
            str(
                discount_raw
                or 0
            )
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invalid discount amount."
            },
            status=400,
        )

    if discount_amount < 0:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Discount cannot be negative."
            },
            status=400,
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

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Organization not found."
            },
            status=404,
        )

    # ========================================================
    # MEMBERSHIP
    # ========================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
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
    # PERMISSION
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
                    "You do not have permission to create invoices."
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

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Tenant not found in this organization."
            },
            status=404,
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

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Lease not found."
            },
            status=404,
        )

    if not lease.unit:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Lease does not have a unit."
            },
            status=400,
        )

    if not lease.unit.property:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Lease unit does not belong to a property."
            },
            status=400,
        )

    property_obj = (
        lease.unit.property
    )

    # ========================================================
    # TENANT MUST BELONG TO LEASE
    # ========================================================

    tenant_on_lease = (
        LeaseTenant.objects
        .filter(
            lease=lease,
            tenant=tenant,
            left_at__isnull=True,
        )
        .exists()
    )

    if not tenant_on_lease:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "The selected tenant is not linked to this lease."
            },
            status=400,
        )

    # ========================================================
    # VALIDATE ITEMS
    # ========================================================

    if not isinstance(
        items_raw,
        list
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "items must be an array."
            },
            status=400,
        )

    valid_charge_types = {
        value
        for value, label
        in InvoiceItem.CHARGE_TYPES
    }

    processed_items = []

    subtotal = Decimal(
        "0.00"
    )

    total_tax = Decimal(
        "0.00"
    )

    for index, item in enumerate(
        items_raw
    ):

        charge_type = str(
            item.get(
                "charge_type",
                "other"
            )
            or "other"
        ).strip().lower()

        description = str(
            item.get(
                "description",
                ""
            )
            or ""
        ).strip()

        quantity_raw = (
            item.get(
                "quantity",
                1
            )
        )

        unit_price_raw = (
            item.get(
                "unit_price"
            )
        )

        tax_rate_raw = (
            item.get(
                "tax_rate",
                0
            )
        )

        if (
            charge_type
            not in valid_charge_types
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Invalid charge type for item {index + 1}."
                },
                status=400,
            )

        if not description:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Description is required for item {index + 1}."
                },
                status=400,
            )

        try:

            quantity = Decimal(
                str(
                    quantity_raw
                )
            )

            unit_price = Decimal(
                str(
                    unit_price_raw
                )
            )

            tax_rate = Decimal(
                str(
                    tax_rate_raw
                    or 0
                )
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Invalid values in invoice item {index + 1}."
                },
                status=400,
            )

        if quantity <= 0:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Quantity must be greater than zero for item {index + 1}."
                },
                status=400,
            )

        if unit_price < 0:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Unit price cannot be negative for item {index + 1}."
                },
                status=400,
            )

        if tax_rate < 0:

            return JsonResponse(
                {
                    "success":
                        False,

                    "message":
                        f"Tax rate cannot be negative for item {index + 1}."
                },
                status=400,
            )

        base_amount = (
            quantity
            * unit_price
        )

        item_tax = (
            base_amount
            * tax_rate
            / Decimal(
                "100"
            )
        )

        line_total = (
            base_amount
            + item_tax
        )

        subtotal += (
            base_amount
        )

        total_tax += (
            item_tax
        )

        processed_items.append(
            {
                "charge_type":
                    charge_type,

                "description":
                    description,

                "quantity":
                    quantity,

                "unit_price":
                    unit_price,

                "tax_rate":
                    tax_rate,

                "line_total":
                    line_total,
            }
        )

    # ========================================================
    # TOTAL
    # ========================================================

    total_amount = (
        subtotal
        + total_tax
        - discount_amount
    )

    if total_amount <= 0:

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Invoice total must be greater than zero."
            },
            status=400,
        )

    # ========================================================
    # CREATE
    # ========================================================

    try:

        with transaction.atomic():

            invoice_number = (
                "INV-"
                f"{organization.id}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

            while (
                Invoice.objects
                .filter(
                    invoice_number=
                        invoice_number
                )
                .exists()
            ):

                invoice_number = (
                    "INV-"
                    f"{organization.id}-"
                    f"{uuid.uuid4().hex[:10].upper()}"
                )

            invoice = (
                Invoice.objects.create(
                    organization=
                        organization,

                    lease=
                        lease,

                    tenant=
                        tenant,

                    property=
                        property_obj,

                    invoice_number=
                        invoice_number,

                    invoice_type=
                        invoice_type,

                    issue_date=
                        issue_date,

                    due_date=
                        due_date,

                    subtotal=
                        subtotal,

                    tax_amount=
                        total_tax,

                    discount_amount=
                        discount_amount,

                    total_amount=
                        total_amount,

                    paid_amount=
                        Decimal(
                            "0.00"
                        ),

                    balance=
                        total_amount,

                    status=
                        status,
                )
            )

            invoice_items = []

            for item in processed_items:

                invoice_item = (
                    InvoiceItem.objects
                    .create(
                        invoice=
                            invoice,

                        charge_type=
                            item[
                                "charge_type"
                            ],

                        description=
                            item[
                                "description"
                            ],

                        quantity=
                            item[
                                "quantity"
                            ],

                        unit_price=
                            item[
                                "unit_price"
                            ],

                        tax_rate=
                            item[
                                "tax_rate"
                            ],

                        line_total=
                            item[
                                "line_total"
                            ],
                    )
                )

                invoice_items.append(
                    {
                        "id":
                            invoice_item.id,

                        "charge_type":
                            invoice_item.charge_type,

                        "description":
                            invoice_item.description,

                        "quantity":
                            str(
                                invoice_item.quantity
                            ),

                        "unit_price":
                            str(
                                invoice_item.unit_price
                            ),

                        "tax_rate":
                            str(
                                invoice_item.tax_rate
                            ),

                        "line_total":
                            str(
                                invoice_item.line_total
                            ),
                    }
                )

            print(
                "INVOICE CREATED:",
                invoice.id,
                invoice.invoice_number
            )

            return JsonResponse(
                {
                    "success":
                        True,

                    "message":
                        "Invoice created successfully.",

                    "invoice": {
                        "id":
                            invoice.id,

                        "invoice_number":
                            invoice.invoice_number,

                        "invoice_type":
                            invoice.invoice_type,

                        "status":
                            invoice.status,

                        "issue_date":
                            str(
                                invoice.issue_date
                            ),

                        "due_date":
                            str(
                                invoice.due_date
                            ),

                        "subtotal":
                            str(
                                invoice.subtotal
                            ),

                        "tax_amount":
                            str(
                                invoice.tax_amount
                            ),

                        "discount_amount":
                            str(
                                invoice.discount_amount
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

                        "tenant": {
                            "id":
                                tenant.id,

                            "full_name":
                                tenant.full_name,
                        },

                        "lease": {
                            "id":
                                lease.id,

                            "lease_number":
                                lease.lease_number,
                        },

                        "property": {
                            "id":
                                property_obj.id,

                            "name":
                                property_obj.name,
                        },

                        "unit": {
                            "id":
                                lease.unit.id,

                            "name":
                                lease.unit.name,

                            "unit_code":
                                lease.unit.unit_code,
                        },

                        "items":
                            invoice_items,
                    },
                },
                status=201,
            )

    except Exception as error:

        print(
            "CREATE INVOICE ERROR:",
            repr(
                error
            )
        )

        return JsonResponse(
            {
                "success":
                    False,

                "message":
                    "Unable to create invoice.",

                "error":
                    str(
                        error
                    ),
            },
            status=500,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_invoices(
    request
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    tenant_id = (
        request.GET.get(
            "tenant_id"
        )
    )

    lease_id = (
        request.GET.get(
            "lease_id"
        )
    )

    status_filter = (
        request.GET.get(
            "status"
        )
    )

    invoice_type = (
        request.GET.get(
            "invoice_type"
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

    organization = (
        Organization.objects
        .filter(
            id=organization_id
        )
        .first()
    )

    if not organization:

        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    membership_exists = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
        )
        .exists()
    )

    if not membership_exists:

        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    invoices = (
        Invoice.objects
        .filter(
            organization=organization
        )
        .select_related(
            "tenant",
            "lease",
            "property",
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-issue_date",
            "-created_at",
        )
    )

    if tenant_id:

        invoices = (
            invoices.filter(
                tenant_id=tenant_id
            )
        )

    if lease_id:

        invoices = (
            invoices.filter(
                lease_id=lease_id
            )
        )

    if status_filter:

        invoices = (
            invoices.filter(
                status=status_filter
            )
        )

    if invoice_type:

        invoices = (
            invoices.filter(
                invoice_type=invoice_type
            )
        )

    invoice_data = []

    for invoice in invoices:

        invoice_data.append(
            {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "invoice_type_display":
                    invoice.get_invoice_type_display(),

                "status":
                    invoice.status,

                "status_display":
                    invoice.get_status_display(),

                "issue_date":
                    str(
                        invoice.issue_date
                    ),

                "due_date":
                    str(
                        invoice.due_date
                    ),

                "subtotal":
                    str(
                        invoice.subtotal
                    ),

                "tax_amount":
                    str(
                        invoice.tax_amount
                    ),

                "discount_amount":
                    str(
                        invoice.discount_amount
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

                "tenant": (
                    {
                        "id":
                            invoice.tenant.id,

                        "full_name":
                            invoice.tenant.full_name,
                    }
                    if invoice.tenant
                    else None
                ),

                "lease": (
                    {
                        "id":
                            invoice.lease.id,

                        "lease_number":
                            invoice.lease.lease_number,
                    }
                    if invoice.lease
                    else None
                ),

                "property": (
                    {
                        "id":
                            invoice.property.id,

                        "name":
                            invoice.property.name,
                    }
                    if invoice.property
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "success":
                True,

            "count":
                len(
                    invoice_data
                ),

            "invoices":
                invoice_data,
        },
        status=200,
    )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_details(
    request,
    invoice_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "organization_id is required.",
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    organization = (
        Organization.objects
        .filter(
            id=organization_id
        )
        .first()
    )

    if not organization:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "Organization not found.",
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    membership = (
        OrganizationMembership.objects
        .filter(
            organization=organization,
            user=user,
            is_active=True,
        )
        .first()
    )

    if not membership:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "You do not have access to this organization.",
            },
            status=403,
        )

    # =====================================================
    # INVOICE
    # =====================================================

    invoice = (
        Invoice.objects
        .select_related(
            "organization",
            "tenant",
            "lease",
            "property",
            "lease__unit",
            "lease__unit__property",
            "lease__unit__building",
            "lease__unit__floor",
        )
        .prefetch_related(
            "items"
        )
        .filter(
            id=invoice_id,
            organization=organization,
        )
        .first()
    )

    if not invoice:
        return JsonResponse(
            {
                "success": False,
                "message":
                    "Invoice not found.",
            },
            status=404,
        )

    # =====================================================
    # PROPERTY / UNIT
    # =====================================================

    lease = (
        invoice.lease
    )

    tenant = (
        invoice.tenant
    )

    property_obj = (
        invoice.property
    )

    unit = None

    if lease:
        unit = (
            lease.unit
        )

        if (
            not property_obj
            and unit
        ):
            property_obj = (
                unit.property
            )

    # =====================================================
    # ITEMS
    # =====================================================

    items = []

    for item in invoice.items.all():

        items.append(
            {
                "id":
                    item.id,

                "charge_type":
                    item.charge_type,

                "charge_type_display": (
                    item.get_charge_type_display()
                    if hasattr(
                        item,
                        "get_charge_type_display"
                    )
                    else item.charge_type
                ),

                "description":
                    item.description,

                "quantity":
                    str(
                        item.quantity
                    ),

                "unit_price":
                    str(
                        item.unit_price
                    ),

                "tax_rate":
                    str(
                        item.tax_rate
                    ),

                "line_total":
                    str(
                        item.line_total
                    ),
            }
        )

    # =====================================================
    # PAYMENT ALLOCATIONS
    # =====================================================

    allocations_queryset = (
        PaymentAllocation.objects
        .filter(
            invoice=invoice
        )
        .select_related(
            "payment",
            "payment__received_by",
        )
        .order_by(
            "-payment__paid_at",
            "-payment__created_at",
        )
    )

    allocations = []

    total_allocated = (
        Decimal(
            "0.00"
        )
    )

    for allocation in allocations_queryset:

        payment = (
            allocation.payment
        )

        allocated_amount = (
            allocation.allocated_amount
            or Decimal(
                "0.00"
            )
        )

        total_allocated += (
            allocated_amount
        )

        allocations.append(
            {
                "id":
                    allocation.id,

                "allocated_amount":
                    str(
                        allocated_amount
                    ),

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
                        payment.paid_at.isoformat()
                        if payment.paid_at
                        else None
                    ),

                    "received_by": (
                        (
                            getattr(
                                payment.received_by,
                                "full_name",
                                None
                            )
                            or
                            payment.received_by.email
                        )
                        if payment.received_by
                        else None
                    ),
                },
            }
        )

    # =====================================================
    # RECEIPTS
    # =====================================================

    payment_ids = [
        allocation[
            "payment"
        ][
            "id"
        ]
        for allocation in allocations
    ]

    receipts_queryset = (
        Receipt.objects
        .filter(
            organization=organization,
            payment_id__in=payment_ids,
        )
        .order_by(
            "-issued_at"
        )
        if payment_ids
        else Receipt.objects.none()
    )

    receipts = []

    for receipt in receipts_queryset:

        receipts.append(
            {
                "id":
                    receipt.id,

                "receipt_number":
                    receipt.receipt_number,

                "payment_id":
                    receipt.payment_id,

                "issued_at": (
                    receipt.issued_at.isoformat()
                    if receipt.issued_at
                    else None
                ),

                "file_url":
                    receipt.file_url,
            }
        )

    # =====================================================
    # PAYMENT PROGRESS
    # =====================================================

    total_amount = (
        invoice.total_amount
        or Decimal(
            "0.00"
        )
    )

    paid_amount = (
        invoice.paid_amount
        or Decimal(
            "0.00"
        )
    )

    balance = (
        invoice.balance
        or Decimal(
            "0.00"
        )
    )

    payment_percentage = 0

    if total_amount > 0:

        payment_percentage = (
            float(
                (
                    paid_amount
                    / total_amount
                )
                * Decimal(
                    "100"
                )
            )
        )

        payment_percentage = (
            round(
                min(
                    payment_percentage,
                    100
                ),
                2,
            )
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "success": True,

            "invoice": {
                "id":
                    invoice.id,

                "invoice_number":
                    invoice.invoice_number,

                "invoice_type":
                    invoice.invoice_type,

                "invoice_type_display":
                    invoice.get_invoice_type_display(),

                "status":
                    invoice.status,

                "status_display":
                    invoice.get_status_display(),

                "issue_date":
                    str(
                        invoice.issue_date
                    ),

                "due_date":
                    str(
                        invoice.due_date
                    ),

                "subtotal":
                    str(
                        invoice.subtotal
                    ),

                "tax_amount":
                    str(
                        invoice.tax_amount
                    ),

                "discount_amount":
                    str(
                        invoice.discount_amount
                    ),

                "total_amount":
                    str(
                        total_amount
                    ),

                "paid_amount":
                    str(
                        paid_amount
                    ),

                "balance":
                    str(
                        balance
                    ),

                "payment_percentage":
                    payment_percentage,

                "created_at": (
                    invoice.created_at.isoformat()
                    if invoice.created_at
                    else None
                ),

                "updated_at": (
                    invoice.updated_at.isoformat()
                    if invoice.updated_at
                    else None
                ),
            },

            "tenant": (
                {
                    "id":
                        tenant.id,

                    "full_name":
                        tenant.full_name,

                    "email":
                        tenant.email,

                    "phone_number":
                        tenant.phone_number,

                    "tenant_type":
                        getattr(
                            tenant,
                            "tenant_type",
                            None,
                        ),
                }
                if tenant
                else None
            ),

            "lease": (
                {
                    "id":
                        lease.id,

                    "lease_number":
                        lease.lease_number,

                    "status":
                        lease.status,

                    "start_date":
                        str(
                            lease.start_date
                        ),

                    "end_date":
                        str(
                            lease.end_date
                        ),

                    "monthly_rent":
                        str(
                            lease.monthly_rent
                        ),
                }
                if lease
                else None
            ),

            "property": (
                {
                    "id":
                        property_obj.id,

                    "name":
                        property_obj.name,

                    "address":
                        property_obj.address,

                    "city":
                        property_obj.city,

                    "county":
                        property_obj.county,
                }
                if property_obj
                else None
            ),

            "unit": (
                {
                    "id":
                        unit.id,

                    "name":
                        unit.name,

                    "unit_code":
                        unit.unit_code,

                    "status":
                        unit.status,

                    "building": (
                        unit.building.name
                        if unit.building
                        else None
                    ),

                    "floor": (
                        unit.floor.name
                        if unit.floor
                        else None
                    ),
                }
                if unit
                else None
            ),

            "items":
                items,

            "payments": {
                "count":
                    len(
                        allocations
                    ),

                "total_allocated":
                    str(
                        total_allocated
                    ),

                "allocations":
                    allocations,
            },

            "receipts":
                receipts,

            "can_record_payment": (
                invoice.status
                not in [
                    "paid",
                    "cancelled",
                    "void",
                ]
                and
                balance > 0
            ),
        },
        status=200,
    )