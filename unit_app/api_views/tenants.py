from .common_imports import *

import secrets
import string

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date


# ============================================================
# CONFIGURATION
# ============================================================

TENANT_MANAGEMENT_ROLES = {
    "admin",
    "property_manager",
    "leasing_officer",
    "accountant",
}

TENANT_CREATION_ROLES = {
    "admin",
    "property_manager",
    "leasing_officer",
}

RENT_MANAGEMENT_ROLES = {
    "admin",
    "property_manager",
    "leasing_officer",
    "accountant",
}

VALID_MAINTENANCE_PRIORITIES = {
    "low",
    "medium",
    "high",
    "urgent",
}

VALID_MAINTENANCE_CATEGORIES = {
    "plumbing",
    "electrical",
    "appliance",
    "security",
    "cleaning",
    "structural",
    "other",
}


# ============================================================
# HELPERS
# ============================================================

def get_company_membership(user, company_id):
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


def can_manage_tenants(membership):
    return (
        membership is not None
        and membership.role in TENANT_MANAGEMENT_ROLES
    )


def can_create_tenants(membership):
    return (
        membership is not None
        and membership.role in TENANT_CREATION_ROLES
    )


def can_manage_rent(membership):
    return (
        membership is not None
        and membership.role in RENT_MANAGEMENT_ROLES
    )


def generate_temporary_password(length=12):
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

        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
            and any(
                character in "!@#$%&*"
                for character in password
            )
        ):
            return password


def get_unit_name(unit):
    return (
        getattr(unit, "unit_number", None)
        or getattr(unit, "name", None)
    )


def get_unit_rent(unit):
    return (
        getattr(unit, "rent", None)
        or getattr(unit, "price_per_month", None)
        or Decimal("0.00")
    )


def get_active_lease_for_tenant(
    tenant,
    company_id=None,
):
    today = timezone.localdate()

    leases = (
        Lease.objects
        .select_related(
            "tenant__user",
            "unit",
            "unit__property",
            "unit__property__company",
        )
        .filter(
            tenant=tenant,
            status="active",
            lease_start__lte=today,
            lease_end__gte=today,
        )
        .order_by("-lease_start")
    )

    if company_id:
        leases = leases.filter(
            unit__property__company_id=company_id
        )

    return leases.first()


def get_tenant_profile(user):
    return (
        Tenant.objects
        .select_related("user")
        .filter(user=user)
        .first()
    )


def get_invoice_outstanding(invoice):
    amount = invoice.amount or Decimal("0.00")
    amount_paid = (
        invoice.amount_paid
        or Decimal("0.00")
    )

    return max(
        amount - amount_paid,
        Decimal("0.00"),
    )


def serialize_tenant(
    tenant,
    lease=None,
):
    user = tenant.user

    if lease is None:
        lease = get_active_lease_for_tenant(
            tenant
        )

    unit = lease.unit if lease else None
    property_instance = (
        unit.property
        if unit
        else None
    )

    latest_invoice = None

    if lease:
        latest_invoice = (
            RentInvoice.objects
            .filter(lease=lease)
            .order_by("-due_date")
            .first()
        )

    payment_status = "No Invoice"

    if latest_invoice:
        if latest_invoice.status == "paid":
            payment_status = "Paid"

        elif (
            latest_invoice.status == "overdue"
            or (
                latest_invoice.due_date
                and latest_invoice.due_date
                < timezone.localdate()
                and latest_invoice.status
                not in {
                    "paid",
                    "cancelled",
                }
            )
        ):
            payment_status = "Overdue"

        else:
            payment_status = "Pending"

    outstanding_balance = (
        get_invoice_outstanding(
            latest_invoice
        )
        if latest_invoice
        else Decimal("0.00")
    )

    return {
        "id": tenant.id,
        "tenant_id": f"TNT-{tenant.id:05d}",
        "user_id": user.id,
        "name": user.full_name,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_image": user.profile_image,
        "is_active": tenant.is_active,
        "status": (
            "active"
            if tenant.is_active
            else "inactive"
        ),
        "property": (
            {
                "id": property_instance.id,
                "name": property_instance.name,
                "company_id": (
                    property_instance.company_id
                ),
            }
            if property_instance
            else None
        ),
        "property_name": (
            property_instance.name
            if property_instance
            else None
        ),
        "unit": (
            {
                "id": unit.id,
                "name": get_unit_name(unit),
                "rent": float(
                    get_unit_rent(unit)
                ),
            }
            if unit
            else None
        ),
        "unit_number": (
            get_unit_name(unit)
            if unit
            else None
        ),
        "rent_amount": (
            float(get_unit_rent(unit))
            if unit
            else 0
        ),
        "lease": (
            {
                "id": lease.id,
                "start_date": (
                    lease.lease_start.isoformat()
                ),
                "end_date": (
                    lease.lease_end.isoformat()
                ),
                "status": lease.status,
            }
            if lease
            else None
        ),
        "rent_status": payment_status,
        "outstanding_balance": float(
            outstanding_balance
        ),
        "created_at": (
            tenant.created_at.isoformat()
            if getattr(
                tenant,
                "created_at",
                None,
            )
            else None
        ),
    }


def serialize_maintenance_request(
    maintenance,
):
    return {
        "id": maintenance.id,
        "title": maintenance.title,
        "description": maintenance.description,
        "priority": maintenance.priority,
        "category": maintenance.category,
        "status": maintenance.status,
        "property": {
            "id": maintenance.property_id,
            "name": maintenance.property.name,
        },
        "unit": {
            "id": maintenance.unit_id,
            "name": get_unit_name(
                maintenance.unit
            ),
        },
        "images": (
            maintenance.images or []
        ),
        "assigned_professional": (
            {
                "id": (
                    maintenance
                    .assigned_professional_id
                ),
                "name": (
                    maintenance
                    .assigned_professional
                    .user
                    .full_name
                ),
            }
            if maintenance.assigned_professional
            else None
        ),
        "created_at": (
            maintenance.created_at.isoformat()
        ),
        "updated_at": (
            maintenance.updated_at.isoformat()
            if getattr(
                maintenance,
                "updated_at",
                None,
            )
            else None
        ),
    }


# ============================================================
# GET COMPANY TENANTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_tenants(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        search_query = str(
            request.GET.get("search", "")
        ).strip()

        property_id = request.GET.get(
            "property_id"
        )

        unit_id = request.GET.get(
            "unit_id"
        )

        status_filter = str(
            request.GET.get("status", "")
        ).strip().lower()

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

        if not can_manage_tenants(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's tenants."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        leases = (
            Lease.objects
            .select_related(
                "tenant__user",
                "unit",
                "unit__property",
                "unit__property__company",
            )
            .filter(
                unit__property__company_id=
                company_id,
            )
            .order_by(
                "-lease_start"
            )
        )

        if property_id:
            leases = leases.filter(
                unit__property_id=property_id
            )

        if unit_id:
            leases = leases.filter(
                unit_id=unit_id
            )

        if status_filter:
            leases = leases.filter(
                status=status_filter
            )

        if search_query:
            leases = leases.filter(
                Q(
                    tenant__user__full_name__icontains=
                    search_query
                )
                | Q(
                    tenant__user__email__icontains=
                    search_query
                )
                | Q(
                    tenant__user__phone_number__icontains=
                    search_query
                )
                | Q(
                    unit__unit_number__icontains=
                    search_query
                )
                | Q(
                    unit__name__icontains=
                    search_query
                )
                | Q(
                    unit__property__name__icontains=
                    search_query
                )
            )

        seen_tenant_ids = set()
        data = []

        for lease in leases:
            if lease.tenant_id in seen_tenant_ids:
                continue

            seen_tenant_ids.add(
                lease.tenant_id
            )

            data.append(
                serialize_tenant(
                    lease.tenant,
                    lease,
                )
            )

        return Response(
            {
                "success": True,
                "count": len(data),
                "tenants": data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "GET TENANTS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "tenants."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# ADD TENANT AND CREATE LEASE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_tenant(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        full_name = str(
            request.data.get(
                "full_name",
                "",
            )
        ).strip()

        email = str(
            request.data.get(
                "email",
                "",
            )
        ).strip().lower()

        phone_number = str(
            request.data.get(
                "phone_number",
                "",
            )
        ).strip()

        unit_id = request.data.get(
            "unit_id"
        )

        lease_start_value = request.data.get(
            "lease_start"
        )

        lease_end_value = request.data.get(
            "lease_end"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not full_name:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Tenant full name is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Tenant email is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not unit_id:
            return Response(
                {
                    "success": False,
                    "message": "Unit is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_create_tenants(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to add "
                        "tenants to this company."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        unit = (
            Unit.objects
            .select_related(
                "property",
                "property__company",
            )
            .filter(
                id=unit_id,
                property__company_id=company_id,
            )
            .first()
        )

        if not unit:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Unit was not found in this company."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        active_lease_exists = (
            Lease.objects
            .filter(
                unit=unit,
                status="active",
                lease_end__gte=
                timezone.localdate(),
            )
            .exists()
        )

        if active_lease_exists:
            return Response(
                {
                    "success": False,
                    "message": (
                        "This unit already has an active lease."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        lease_start = (
            parse_date(
                str(lease_start_value)
            )
            if lease_start_value
            else timezone.localdate()
        )

        lease_end = (
            parse_date(
                str(lease_end_value)
            )
            if lease_end_value
            else lease_start
            + timedelta(days=365)
        )

        if not lease_start:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid lease start date. "
                        "Use YYYY-MM-DD."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not lease_end:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid lease end date. "
                        "Use YYYY-MM-DD."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lease_end <= lease_start:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Lease end date must be after "
                        "the lease start date."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        temporary_password = None
        user_created = False
        tenant_created = False

        with transaction.atomic():
            tenant_user = (
                User.objects
                .filter(
                    email__iexact=email
                )
                .first()
            )

            if tenant_user:
                changed_fields = []

                if (
                    full_name
                    and tenant_user.full_name
                    != full_name
                ):
                    tenant_user.full_name = (
                        full_name
                    )

                    changed_fields.append(
                        "full_name"
                    )

                if (
                    phone_number
                    and not tenant_user.phone_number
                ):
                    tenant_user.phone_number = (
                        phone_number
                    )

                    changed_fields.append(
                        "phone_number"
                    )

                if changed_fields:
                    tenant_user.save(
                        update_fields=changed_fields
                    )

            else:
                temporary_password = (
                    generate_temporary_password()
                )

                tenant_user = (
                    User.objects.create_user(
                        username=email,
                        email=email,
                        full_name=full_name,
                        phone_number=(
                            phone_number or None
                        ),
                        role="user",
                        is_verified=True,
                        password=temporary_password,
                    )
                )

                user_created = True

            tenant, tenant_created = (
                Tenant.objects.get_or_create(
                    user=tenant_user,
                    defaults={
                        "is_active": True,
                    },
                )
            )

            if not tenant.is_active:
                tenant.is_active = True

                tenant.save(
                    update_fields=[
                        "is_active"
                    ]
                )

            lease = Lease.objects.create(
                tenant=tenant,
                unit=unit,
                lease_start=lease_start,
                lease_end=lease_end,
                status="active",
            )

            unit.status = "occupied"

            unit.save(
                update_fields=["status"]
            )

        response_data = {
            "success": True,
            "message": (
                "Tenant added and lease created "
                "successfully."
            ),
            "user_created": user_created,
            "tenant_created": tenant_created,
            "tenant": serialize_tenant(
                tenant,
                lease,
            ),
        }

        if temporary_password:
            response_data[
                "temporary_password"
            ] = temporary_password

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )

    except Exception as error:
        print(
            "ADD TENANT ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while adding "
                    "the tenant."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# REQUEST RENT PAYMENT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_rent(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        tenant_id = request.data.get(
            "tenant_id"
        )

        invoice_id = request.data.get(
            "invoice_id"
        )

        if not company_id:
            return Response(
                {
                    "success": False,
                    "message": "Company is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tenant_id:
            return Response(
                {
                    "success": False,
                    "message": "Tenant is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_rent(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to "
                        "request rent payments."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        lease = (
            Lease.objects
            .select_related(
                "tenant__user",
                "unit",
                "unit__property",
            )
            .filter(
                tenant_id=tenant_id,
                unit__property__company_id=
                company_id,
                status="active",
            )
            .order_by("-lease_start")
            .first()
        )

        if not lease:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No active tenant lease was found "
                        "in this company."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        invoice_query = (
            RentInvoice.objects
            .filter(
                lease=lease,
            )
            .exclude(
                status__in=[
                    "paid",
                    "cancelled",
                ]
            )
        )

        if invoice_id:
            invoice_query = (
                invoice_query.filter(
                    id=invoice_id
                )
            )

        invoice = (
            invoice_query
            .order_by("due_date")
            .first()
        )

        if not invoice:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No pending rent invoice was found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        outstanding_amount = (
            get_invoice_outstanding(invoice)
        )

        if outstanding_amount <= 0:
            return Response(
                {
                    "success": False,
                    "message": (
                        "This invoice has no outstanding "
                        "balance."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = lease.tenant.user.phone_number

        if not phone:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The tenant does not have a phone "
                        "number configured."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add your Daraja STK Push integration here.
        #
        # response = initiate_stk_push(
        #     phone=phone,
        #     amount=outstanding_amount,
        #     reference=f"RENT-{invoice.id}",
        # )
        #
        # RentPayment.objects.create(
        #     invoice=invoice,
        #     tenant=lease.tenant,
        #     amount=outstanding_amount,
        #     payment_method="mpesa",
        #     status="pending",
        #     transaction_id=response.checkout_request_id,
        # )

        return Response(
            {
                "success": True,
                "message": (
                    "Rent payment request validated. "
                    "Connect Daraja to send the STK Push."
                ),
                "payment_request": {
                    "tenant_id": lease.tenant_id,
                    "tenant_name": (
                        lease.tenant.user.full_name
                    ),
                    "phone": phone,
                    "invoice_id": invoice.id,
                    "amount": float(
                        outstanding_amount
                    ),
                    "currency": "KES",
                    "status": "not_initiated",
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "REQUEST RENT ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while preparing "
                    "the rent payment request."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# TENANT DASHBOARD
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_dashboard(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        lease = get_active_lease_for_tenant(
            tenant,
            company_id,
        )

        if not lease:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "No active lease was found."
                    ),
                },
                status=404,
            )

        unit = lease.unit
        property_instance = unit.property

        unpaid_invoice = (
            RentInvoice.objects
            .filter(
                lease=lease,
            )
            .exclude(
                status__in=[
                    "paid",
                    "cancelled",
                ]
            )
            .order_by("due_date")
            .first()
        )

        current_rent = (
            get_invoice_outstanding(
                unpaid_invoice
            )
            if unpaid_invoice
            else Decimal("0.00")
        )

        next_due_date = (
            unpaid_invoice.due_date.strftime(
                "%d %b %Y"
            )
            if unpaid_invoice
            and unpaid_invoice.due_date
            else "No pending rent"
        )

        pending_invoices = (
            RentInvoice.objects
            .filter(
                lease=lease,
            )
            .exclude(
                status__in=[
                    "paid",
                    "cancelled",
                ]
            )
        )

        balance = sum(
            (
                get_invoice_outstanding(
                    invoice
                )
                for invoice
                in pending_invoices
            ),
            Decimal("0.00"),
        )

        pending_requests = (
            MaintenanceRequest.objects
            .filter(
                tenant=tenant,
                unit=unit,
                status__in=[
                    "pending",
                    "assigned",
                    "in_progress",
                ],
            )
            .count()
        )

        announcements = (
            Announcement.objects
            .filter(
                is_active=True,
                property__company_id=
                property_instance.company_id,
            )
            .filter(
                Q(target="all")
                | Q(
                    target="property",
                    property=property_instance,
                )
                | Q(
                    target="unit",
                    unit=unit,
                )
            )
            .select_related(
                "created_by"
            )
            .order_by("-created_at")[:5]
        )

        announcement_data = [
            {
                "id": item.id,
                "title": item.title,
                "message": item.message,
                "target": item.target,
                "date": (
                    item.created_at.strftime(
                        "%d %b %Y"
                    )
                ),
                "created_by": (
                    item.created_by.full_name
                    if item.created_by
                    else None
                ),
            }
            for item in announcements
        ]

        recent_payments = (
            RentPayment.objects
            .filter(
                invoice__lease=lease,
                tenant=tenant,
                status="success",
            )
            .order_by("-paid_at")[:5]
        )

        payment_data = [
            {
                "id": payment.id,
                "amount": float(
                    payment.amount
                ),
                "status": payment.status,
                "payment_method": (
                    payment.payment_method
                ),
                "transaction_id": getattr(
                    payment,
                    "transaction_id",
                    None,
                ),
                "paid_at": (
                    payment.paid_at.isoformat()
                    if payment.paid_at
                    else None
                ),
            }
            for payment in recent_payments
        ]

        return JsonResponse(
            {
                "success": True,
                "dashboard": {
                    "tenant": serialize_tenant(
                        tenant,
                        lease,
                    ),
                    "tenant_name": (
                        tenant.user.full_name
                    ),
                    "property_name": (
                        property_instance.name
                    ),
                    "unit_name": (
                        get_unit_name(unit)
                    ),
                    "current_rent": float(
                        current_rent
                    ),
                    "balance": float(balance),
                    "next_due_date": (
                        next_due_date
                    ),
                    "pending_requests": (
                        pending_requests
                    ),
                    "announcements": (
                        announcement_data
                    ),
                    "recent_payments": (
                        payment_data
                    ),
                },
            },
            status=200,
        )

    except Exception as error:
        print(
            "TENANT DASHBOARD ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the tenant dashboard."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# TENANT ANNOUNCEMENTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_announcements(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        lease = get_active_lease_for_tenant(
            tenant,
            company_id,
        )

        if not lease:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "No active lease was found."
                    ),
                },
                status=404,
            )

        unit = lease.unit
        property_instance = unit.property

        announcements = (
            Announcement.objects
            .filter(
                is_active=True,
                property__company_id=
                property_instance.company_id,
            )
            .filter(
                Q(target="all")
                | Q(
                    target="property",
                    property=property_instance,
                )
                | Q(
                    target="unit",
                    unit=unit,
                )
            )
            .select_related(
                "created_by",
                "property",
                "unit",
            )
            .order_by("-created_at")
        )

        data = []

        for announcement in announcements:
            data.append({
                "id": announcement.id,
                "title": announcement.title,
                "message": announcement.message,
                "target": announcement.target,
                "property": (
                    announcement.property.name
                    if announcement.property
                    else None
                ),
                "unit": (
                    get_unit_name(
                        announcement.unit
                    )
                    if announcement.unit
                    else None
                ),
                "date": (
                    announcement.created_at
                    .strftime("%d %b %Y")
                ),
                "created_at": (
                    announcement.created_at
                    .isoformat()
                ),
                "created_by": (
                    announcement
                    .created_by
                    .full_name
                    if announcement.created_by
                    else None
                ),
            })

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "announcements": data,
            },
            status=200,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "announcements."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# CREATE TENANT MAINTENANCE REQUEST
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_maintenance_request(request):
    try:
        company_id = request.data.get(
            "company_id"
        )

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        lease = get_active_lease_for_tenant(
            tenant,
            company_id,
        )

        if not lease:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "No active lease was found."
                    ),
                },
                status=404,
            )

        title = str(
            request.data.get(
                "title",
                "",
            )
        ).strip()

        description = str(
            request.data.get(
                "description",
                "",
            )
        ).strip()

        priority = str(
            request.data.get(
                "priority",
                "medium",
            )
        ).strip().lower()

        category = str(
            request.data.get(
                "category",
                "other",
            )
        ).strip().lower()

        if not title:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Title is required.",
                },
                status=400,
            )

        if not description:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Description is required."
                    ),
                },
                status=400,
            )

        if (
            priority
            not in VALID_MAINTENANCE_PRIORITIES
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Invalid maintenance priority."
                    ),
                    "allowed_priorities": sorted(
                        VALID_MAINTENANCE_PRIORITIES
                    ),
                },
                status=400,
            )

        if (
            category
            not in VALID_MAINTENANCE_CATEGORIES
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Invalid maintenance category."
                    ),
                    "allowed_categories": sorted(
                        VALID_MAINTENANCE_CATEGORIES
                    ),
                },
                status=400,
            )

        uploaded_images = []

        for image in request.FILES.getlist(
            "images"
        ):
            upload = (
                cloudinary.uploader.upload(
                    image,
                    folder=(
                        f"companies/"
                        f"{lease.unit.property.company_id}/"
                        f"maintenance_requests/"
                        f"tenant_{tenant.id}"
                    ),
                    resource_type="image",
                )
            )

            uploaded_images.append(
                upload["secure_url"]
            )

        maintenance = (
            MaintenanceRequest.objects.create(
                tenant=tenant,
                property=lease.unit.property,
                unit=lease.unit,
                title=title,
                description=description,
                priority=priority,
                category=category,
                status="pending",
                images=uploaded_images,
            )
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Maintenance request submitted "
                    "successfully."
                ),
                "request": (
                    serialize_maintenance_request(
                        maintenance
                    )
                ),
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE MAINTENANCE REQUEST ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while submitting "
                    "the maintenance request."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# GET TENANT MAINTENANCE REQUESTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_maintenance_requests(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        status_filter = str(
            request.GET.get(
                "status",
                "",
            )
        ).strip().lower()

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        maintenance_requests = (
            MaintenanceRequest.objects
            .select_related(
                "property",
                "unit",
                "assigned_professional__user",
            )
            .filter(
                tenant=tenant
            )
            .order_by("-created_at")
        )

        if company_id:
            maintenance_requests = (
                maintenance_requests.filter(
                    property__company_id=
                    company_id
                )
            )

        if status_filter:
            maintenance_requests = (
                maintenance_requests.filter(
                    status=status_filter
                )
            )

        data = [
            serialize_maintenance_request(
                item
            )
            for item in maintenance_requests
        ]

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "requests": data,
            },
            status=200,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "maintenance requests."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# TENANT RENT PAYMENTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_rent_payments(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        payments = (
            RentPayment.objects
            .select_related(
                "tenant__user",
                "invoice",
                "invoice__lease__unit",
                "invoice__lease__unit__property",
            )
            .filter(
                tenant=tenant
            )
            .order_by("-paid_at")
        )

        if company_id:
            payments = payments.filter(
                invoice__lease__unit__property__company_id=
                company_id
            )

        data = []

        for payment in payments:
            lease = payment.invoice.lease
            unit = lease.unit
            property_instance = unit.property

            data.append({
                "id": payment.id,
                "invoice_id": payment.invoice_id,
                "amount": float(
                    payment.amount
                ),
                "status": payment.status,
                "is_paid": (
                    payment.status == "success"
                ),
                "payment_date": (
                    payment.paid_at.strftime(
                        "%d %b %Y"
                    )
                    if payment.paid_at
                    else None
                ),
                "paid_at": (
                    payment.paid_at.isoformat()
                    if payment.paid_at
                    else None
                ),
                "transaction_id": getattr(
                    payment,
                    "transaction_id",
                    None,
                ),
                "reference": getattr(
                    payment,
                    "reference",
                    None,
                ),
                "payment_method": (
                    payment.payment_method
                ),
                "tenant": (
                    payment
                    .tenant
                    .user
                    .full_name
                ),
                "property": (
                    property_instance.name
                ),
                "unit": get_unit_name(unit),
            })

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "payments": data,
            },
            status=200,
        )

    except Exception as error:
        print(
            "TENANT RENT PAYMENTS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "rent payments."
                ),
                "error": str(error),
            },
            status=500,
        )


# ============================================================
# TENANT PROFILE
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_profile(request):
    try:
        company_id = request.GET.get(
            "company_id"
        )

        tenant = get_tenant_profile(
            request.user
        )

        if not tenant:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Tenant profile not found."
                    ),
                },
                status=404,
            )

        lease = get_active_lease_for_tenant(
            tenant,
            company_id,
        )

        if not lease:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "No active lease was found."
                    ),
                },
                status=404,
            )

        unit = lease.unit
        property_instance = unit.property
        user = tenant.user

        pending_invoices = (
            RentInvoice.objects
            .filter(
                lease=lease
            )
            .exclude(
                status__in=[
                    "paid",
                    "cancelled",
                ]
            )
        )

        outstanding_balance = sum(
            (
                get_invoice_outstanding(
                    invoice
                )
                for invoice
                in pending_invoices
            ),
            Decimal("0.00"),
        )

        return JsonResponse(
            {
                "success": True,
                "profile": {
                    "id": tenant.id,
                    "tenant_id": (
                        f"TNT-{tenant.id:05d}"
                    ),
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone_number": (
                        user.phone_number
                    ),
                    "profile_image": (
                        user.profile_image
                    ),
                    "company": {
                        "id": (
                            property_instance
                            .company_id
                        ),
                        "name": (
                            property_instance
                            .company
                            .name
                        ),
                    },
                    "property": {
                        "id": property_instance.id,
                        "name": (
                            property_instance.name
                        ),
                    },
                    "unit": {
                        "id": unit.id,
                        "name": get_unit_name(unit),
                    },
                    "rent_amount": float(
                        get_unit_rent(unit)
                    ),
                    "outstanding_balance": float(
                        outstanding_balance
                    ),
                    "lease_start": (
                        lease.lease_start
                        .isoformat()
                    ),
                    "lease_end": (
                        lease.lease_end
                        .isoformat()
                    ),
                    "move_in_date": (
                        lease.lease_start
                        .strftime("%d %b %Y")
                    ),
                    "lease_status": lease.status,
                    "status": (
                        "Active"
                        if tenant.is_active
                        else "Inactive"
                    ),
                },
            },
            status=200,
        )

    except Exception as error:
        print(
            "TENANT PROFILE ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the tenant profile."
                ),
                "error": str(error),
            },
            status=500,
        )