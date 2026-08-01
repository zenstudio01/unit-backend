from .common_imports import *

import secrets
import string

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


# ============================================================
# LANDLORD HELPERS
# ============================================================

LANDLORD_MANAGEMENT_ROLES = {
    "admin",
    "property_manager",
    "accountant",
}


def get_company_membership(user, company_id):
    """
    Return an active company membership for the authenticated user.
    """

    return (
        CompanyStaff.objects
        .select_related("company", "user")
        .filter(
            user=user,
            company_id=company_id,
            is_active=True,
        )
        .first()
    )


def can_manage_landlords(membership):
    """
    Determine whether a company staff member can manage landlords.
    """

    return (
        membership is not None
        and membership.role in LANDLORD_MANAGEMENT_ROLES
    )


def normalize_decimal(value, default="0.00"):
    """
    Safely convert input into a Decimal.
    """

    if value in [None, ""]:
        return Decimal(default)

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def generate_temporary_password(length=12):
    """
    Generate a secure temporary password.
    """

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


def get_landlord_profile_for_user(user, company_id=None):
    """
    Resolve the authenticated user's landlord profile.

    A company_id is required when the user has landlord profiles
    under more than one company.
    """

    queryset = (
        Landlord.objects
        .select_related("user", "company")
        .filter(user=user)
    )

    if company_id:
        return queryset.filter(
            company_id=company_id
        ).first()

    profiles = list(queryset[:2])

    if len(profiles) == 1:
        return profiles[0]

    return None


def get_landlord_paid_payments(landlord):
    """
    Return successful rent payments for properties assigned
    to the landlord.
    """

    return RentPayment.objects.filter(
        invoice__lease__unit__property__landlord=landlord,
        status="success",
    )


def get_landlord_pending_invoices(landlord):
    """
    Return rent invoices that still have an outstanding balance.
    """

    return (
        RentInvoice.objects
        .filter(
            lease__unit__property__landlord=landlord,
        )
        .exclude(
            status__in=[
                "paid",
                "cancelled",
            ]
        )
    )


def get_invoice_outstanding_expression(invoice):
    """
    Calculate the outstanding balance for one invoice.
    """

    amount = invoice.amount or Decimal("0.00")
    amount_paid = invoice.amount_paid or Decimal("0.00")

    return max(
        amount - amount_paid,
        Decimal("0.00"),
    )


def serialize_landlord(landlord):
    properties = landlord.properties.all()

    properties_count = properties.count()

    total_units = (
        Unit.objects
        .filter(property__landlord=landlord)
        .count()
    )

    total_collected = (
        get_landlord_paid_payments(landlord)
        .aggregate(total=Sum("amount"))
        .get("total")
        or Decimal("0.00")
    )

    pending_invoices = (
        get_landlord_pending_invoices(landlord)
        .only("amount", "amount_paid")
    )

    outstanding_balance = sum(
        (
            get_invoice_outstanding_expression(invoice)
            for invoice in pending_invoices
        ),
        Decimal("0.00"),
    )

    return {
        "id": landlord.id,
        "user_id": landlord.user_id,
        "company": {
            "id": landlord.company_id,
            "name": landlord.company.name,
        },
        "name": landlord.user.full_name,
        "email": landlord.user.email,
        "phone_number": (
            landlord.user.phone_number or None
        ),
        "profile_image": (
            landlord.user.profile_image
        ),
        "commission_rate": float(
            landlord.commission_rate
            or Decimal("0.00")
        ),
        "properties_count": properties_count,
        "total_units": total_units,
        "total_rent_collected": float(
            total_collected
        ),
        "formatted_total_rent_collected": (
            f"KES {total_collected:,.2f}"
        ),
        "outstanding_rent": float(
            outstanding_balance
        ),
        "formatted_outstanding_rent": (
            f"KES {outstanding_balance:,.2f}"
        ),
        "created_at": landlord.created_at.isoformat(),
    }


# ============================================================
# 1. FETCH COMPANY LANDLORDS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def landlord_list(request):
    try:
        company_id = request.GET.get("company_id")

        search_query = str(
            request.GET.get("search", "")
        ).strip()

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

        if not can_manage_landlords(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to view "
                        "this company's landlords."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        landlords = (
            Landlord.objects
            .select_related(
                "user",
                "company",
            )
            .prefetch_related("properties")
            .filter(company_id=company_id)
            .order_by("-created_at")
        )

        if search_query:
            landlords = landlords.filter(
                Q(
                    user__full_name__icontains=
                    search_query
                )
                | Q(
                    user__email__icontains=
                    search_query
                )
                | Q(
                    user__phone_number__icontains=
                    search_query
                )
            )

        data = [
            serialize_landlord(landlord)
            for landlord in landlords
        ]

        return Response(
            {
                "success": True,
                "count": len(data),
                "landlords": data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "LANDLORD LIST ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "landlords."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 2. CREATE OR LINK LANDLORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_landlord(request):
    try:
        company_id = request.data.get("company_id")
        property_id = request.data.get("property_id")

        full_name = str(
            request.data.get("name", "")
        ).strip()

        email = str(
            request.data.get("email", "")
        ).strip().lower()

        phone_number = str(
            request.data.get("phone_number", "")
        ).strip()

        commission_rate = normalize_decimal(
            request.data.get("commission_rate"),
            default="0.00",
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
                    "message": "Landlord name is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email:
            return Response(
                {
                    "success": False,
                    "message": "Landlord email is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if commission_rate is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Commission rate must be a valid number."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            commission_rate < Decimal("0.00")
            or commission_rate > Decimal("100.00")
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Commission rate must be between "
                        "0 and 100."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = get_company_membership(
            request.user,
            company_id,
        )

        if not can_manage_landlords(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to add "
                        "landlords to this company."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        selected_property = None

        if property_id:
            selected_property = (
                Property.objects
                .filter(
                    id=property_id,
                    company_id=company_id,
                )
                .first()
            )

            if not selected_property:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "Property was not found in "
                            "this company."
                        ),
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                selected_property.landlord_id
                and selected_property.landlord.company_id
                != int(company_id)
            ):
                return Response(
                    {
                        "success": False,
                        "message": (
                            "The property has an invalid landlord "
                            "assignment from another company."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        temporary_password = None
        user_created = False
        landlord_created = False

        with transaction.atomic():
            landlord_user = (
                User.objects
                .filter(email__iexact=email)
                .first()
            )

            if landlord_user:
                changed_fields = []

                if (
                    full_name
                    and landlord_user.full_name != full_name
                ):
                    landlord_user.full_name = full_name
                    changed_fields.append("full_name")

                if (
                    phone_number
                    and not landlord_user.phone_number
                ):
                    landlord_user.phone_number = phone_number
                    changed_fields.append("phone_number")

                if changed_fields:
                    landlord_user.save(
                        update_fields=changed_fields
                    )

            else:
                temporary_password = (
                    generate_temporary_password()
                )

                landlord_user = User.objects.create_user(
                    username=email,
                    email=email,
                    full_name=full_name,
                    phone_number=phone_number or None,
                    role="user",
                    password=temporary_password,
                )

                user_created = True

            landlord, landlord_created = (
                Landlord.objects.get_or_create(
                    user=landlord_user,
                    company_id=company_id,
                    defaults={
                        "commission_rate": commission_rate,
                    },
                )
            )

            if not landlord_created:
                landlord.commission_rate = commission_rate

                landlord.save(
                    update_fields=["commission_rate"]
                )

            if selected_property:
                selected_property.landlord = landlord

                selected_property.save(
                    update_fields=["landlord"]
                )

        landlord = (
            Landlord.objects
            .select_related(
                "user",
                "company",
            )
            .prefetch_related("properties")
            .get(id=landlord.id)
        )

        response_data = {
            "success": True,
            "message": (
                "Landlord added successfully."
                if landlord_created
                else "Existing landlord profile updated successfully."
            ),
            "user_created": user_created,
            "landlord_created": landlord_created,
            "landlord": serialize_landlord(
                landlord
            ),
        }

        # Return only once. Deliver it securely to the landlord.
        if temporary_password:
            response_data["temporary_password"] = (
                temporary_password
            )

        return Response(
            response_data,
            status=(
                status.HTTP_201_CREATED
                if landlord_created
                else status.HTTP_200_OK
            ),
        )

    except Exception as error:
        print(
            "ADD LANDLORD ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while adding "
                    "the landlord."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 3. ASSIGN PROPERTY TO LANDLORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_property_to_landlord(
    request,
    landlord_id,
):
    try:
        property_id = request.data.get("property_id")

        if not property_id:
            return Response(
                {
                    "success": False,
                    "message": "Property is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        landlord = (
            Landlord.objects
            .select_related("company", "user")
            .filter(id=landlord_id)
            .first()
        )

        if not landlord:
            return Response(
                {
                    "success": False,
                    "message": "Landlord not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = get_company_membership(
            request.user,
            landlord.company_id,
        )

        if not can_manage_landlords(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to manage "
                        "this landlord."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        selected_property = (
            Property.objects
            .filter(
                id=property_id,
                company_id=landlord.company_id,
            )
            .first()
        )

        if not selected_property:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Property was not found in the "
                        "landlord's company."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        selected_property.landlord = landlord

        selected_property.save(
            update_fields=["landlord"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Property assigned to landlord successfully."
                ),
                "property": {
                    "id": selected_property.id,
                    "name": selected_property.name,
                },
                "landlord": {
                    "id": landlord.id,
                    "name": landlord.user.full_name,
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while assigning "
                    "the property."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 4. REMOVE PROPERTY FROM LANDLORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_property_from_landlord(
    request,
    landlord_id,
):
    try:
        property_id = request.data.get("property_id")

        landlord = (
            Landlord.objects
            .select_related("company", "user")
            .filter(id=landlord_id)
            .first()
        )

        if not landlord:
            return Response(
                {
                    "success": False,
                    "message": "Landlord not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = get_company_membership(
            request.user,
            landlord.company_id,
        )

        if not can_manage_landlords(membership):
            return Response(
                {
                    "success": False,
                    "message": (
                        "You do not have permission to manage "
                        "this landlord."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        selected_property = (
            Property.objects
            .filter(
                id=property_id,
                company_id=landlord.company_id,
                landlord=landlord,
            )
            .first()
        )

        if not selected_property:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The selected property is not assigned "
                        "to this landlord."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        selected_property.landlord = None

        selected_property.save(
            update_fields=["landlord"]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Property removed from landlord successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while removing "
                    "the property."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 5. PROCESS LANDLORD PAYOUT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def landlord_process_payout(request, pk):
    """
    Validate a landlord payout request.

    This endpoint does not claim that money has been transferred.
    Integrate the actual B2C payment provider before marking a
    payout as completed.
    """

    try:
        landlord = (
            Landlord.objects
            .select_related(
                "user",
                "company",
            )
            .filter(pk=pk)
            .first()
        )

        if not landlord:
            return Response(
                {
                    "success": False,
                    "message": "Landlord not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = get_company_membership(
            request.user,
            landlord.company_id,
        )

        if (
            not membership
            or membership.role not in {
                "admin",
                "accountant",
            }
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only a company administrator or "
                        "accountant can process payouts."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        amount = normalize_decimal(
            request.data.get("amount")
        )

        if amount is None or amount <= Decimal("0.00"):
            return Response(
                {
                    "success": False,
                    "message": (
                        "A valid payout amount greater than "
                        "zero is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not landlord.user.phone_number:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The landlord does not have a phone "
                        "number configured for payout."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        available_rent = (
            get_landlord_paid_payments(landlord)
            .aggregate(total=Sum("amount"))
            .get("total")
            or Decimal("0.00")
        )

        if amount > available_rent:
            return Response(
                {
                    "success": False,
                    "message": (
                        "The requested payout exceeds the "
                        "landlord's recorded rent collections."
                    ),
                    "available_amount": float(
                        available_rent
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Do not return a success transfer message until the
        # actual payout provider confirms the transaction.
        #
        # Recommended:
        # payout = LandlordPayout.objects.create(
        #     landlord=landlord,
        #     company=landlord.company,
        #     initiated_by=request.user,
        #     amount=amount,
        #     phone_number=landlord.user.phone_number,
        #     status="pending",
        # )
        #
        # provider_response = initiate_mpesa_b2c(...)
        # payout.reference = provider_response.reference
        # payout.save(...)

        return Response(
            {
                "success": True,
                "message": (
                    "Payout request validated. Connect the "
                    "payment provider to initiate transfer."
                ),
                "payout": {
                    "landlord_id": landlord.id,
                    "landlord_name": (
                        landlord.user.full_name
                    ),
                    "phone_number": (
                        landlord.user.phone_number
                    ),
                    "amount": float(amount),
                    "status": "not_initiated",
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "LANDLORD PAYOUT ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while validating "
                    "the landlord payout."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 6. LANDLORD DASHBOARD
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def landlord_dashboard(request):
    try:
        company_id = request.GET.get("company_id")

        landlord = get_landlord_profile_for_user(
            request.user,
            company_id,
        )

        if not landlord:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Landlord profile not found. Supply "
                        "company_id when you belong to more "
                        "than one company."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        properties = (
            Property.objects
            .filter(
                landlord=landlord,
                company=landlord.company,
            )
            .prefetch_related("units")
        )

        property_count = properties.count()

        units = Unit.objects.filter(
            property__landlord=landlord,
            property__company=landlord.company,
        )

        unit_count = units.count()

        today = timezone.localdate()

        active_leases = (
            Lease.objects
            .filter(
                unit__property__landlord=landlord,
                unit__property__company=landlord.company,
                status="active",
                lease_start__lte=today,
                lease_end__gte=today,
            )
        )

        occupied_units = (
            active_leases
            .values("unit_id")
            .distinct()
            .count()
        )

        available_units = max(
            unit_count - occupied_units,
            0,
        )

        maintenance_units = units.filter(
            status="under_maintenance"
        ).count()

        tenant_count = (
            active_leases
            .values("tenant_id")
            .distinct()
            .count()
        )

        now = timezone.now()

        paid_this_month = (
            get_landlord_paid_payments(landlord)
            .filter(
                paid_at__year=now.year,
                paid_at__month=now.month,
            )
        )

        rent_collected = (
            paid_this_month
            .aggregate(total=Sum("amount"))
            .get("total")
            or Decimal("0.00")
        )

        pending_invoices = (
            get_landlord_pending_invoices(landlord)
        )

        pending_rent = sum(
            (
                get_invoice_outstanding_expression(invoice)
                for invoice in pending_invoices
            ),
            Decimal("0.00"),
        )

        occupancy_rate = (
            round(
                occupied_units / unit_count * 100,
                1,
            )
            if unit_count
            else 0
        )

        payments = (
            RentPayment.objects
            .select_related(
                "tenant__user",
                "invoice__lease__unit__property",
            )
            .filter(
                invoice__lease__unit__property__landlord=
                landlord,
            )
            .order_by("-paid_at")[:5]
        )

        recent_payments = []

        for payment in payments:
            lease = payment.invoice.lease
            unit = lease.unit
            property_instance = unit.property

            recent_payments.append({
                "id": payment.id,
                "tenant": (
                    payment.tenant.user.full_name
                ),
                "property": property_instance.name,
                "unit": unit.unit_number,
                "amount": float(payment.amount),
                "date": (
                    payment.paid_at.strftime(
                        "%d %b %Y"
                    )
                    if payment.paid_at
                    else None
                ),
                "status": payment.status,
                "reference": getattr(
                    payment,
                    "reference",
                    None,
                ),
            })

        property_overview = []

        for property_instance in properties:
            property_units = (
                property_instance.units.all()
            )

            total_units = property_units.count()

            occupied = (
                Lease.objects
                .filter(
                    unit__property=property_instance,
                    status="active",
                    lease_start__lte=today,
                    lease_end__gte=today,
                )
                .values("unit_id")
                .distinct()
                .count()
            )

            monthly_income = (
                RentPayment.objects
                .filter(
                    invoice__lease__unit__property=
                    property_instance,
                    status="success",
                    paid_at__year=now.year,
                    paid_at__month=now.month,
                )
                .aggregate(total=Sum("amount"))
                .get("total")
                or Decimal("0.00")
            )

            property_overview.append({
                "id": property_instance.id,
                "name": property_instance.name,
                "units": total_units,
                "occupied": occupied,
                "available": max(
                    total_units - occupied,
                    0,
                ),
                "occupancy_rate": (
                    round(
                        occupied / total_units * 100,
                        1,
                    )
                    if total_units
                    else 0
                ),
                "income": float(monthly_income),
            })

        return Response(
            {
                "success": True,
                "landlord": {
                    "id": landlord.id,
                    "name": landlord.user.full_name,
                    "company": {
                        "id": landlord.company_id,
                        "name": landlord.company.name,
                    },
                },
                "summary": {
                    "properties": property_count,
                    "units": unit_count,
                    "occupied_units": occupied_units,
                    "available_units": available_units,
                    "maintenance_units": maintenance_units,
                    "tenants": tenant_count,
                    "rent_collected": float(
                        rent_collected
                    ),
                    "formatted_rent_collected": (
                        f"KES {rent_collected:,.2f}"
                    ),
                    "pending_rent": float(
                        pending_rent
                    ),
                    "formatted_pending_rent": (
                        f"KES {pending_rent:,.2f}"
                    ),
                    "occupancy_rate": occupancy_rate,
                },
                "recent_payments": recent_payments,
                "properties": property_overview,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "LANDLORD DASHBOARD ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "the landlord dashboard."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# 7. LANDLORD ANALYTICS
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def landlord_analytics(request):
    try:
        company_id = request.GET.get("company_id")

        landlord = get_landlord_profile_for_user(
            request.user,
            company_id,
        )

        if not landlord:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Landlord profile not found. Supply "
                        "company_id when you belong to more "
                        "than one company."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        properties = (
            Property.objects
            .filter(
                landlord=landlord,
                company=landlord.company,
            )
            .prefetch_related("units")
        )

        units = Unit.objects.filter(
            property__landlord=landlord,
            property__company=landlord.company,
        )

        today = timezone.localdate()

        active_leases = Lease.objects.filter(
            unit__property__landlord=landlord,
            unit__property__company=landlord.company,
            status="active",
            lease_start__lte=today,
            lease_end__gte=today,
        )

        payments = get_landlord_paid_payments(
            landlord
        )

        pending_invoices = (
            get_landlord_pending_invoices(landlord)
        )

        total_units = units.count()

        occupied_units = (
            active_leases
            .values("unit_id")
            .distinct()
            .count()
        )

        available_units = max(
            total_units - occupied_units,
            0,
        )

        maintenance_units = units.filter(
            status="under_maintenance"
        ).count()

        occupancy_rate = (
            round(
                occupied_units / total_units * 100,
                2,
            )
            if total_units
            else 0
        )

        total_revenue = (
            payments
            .aggregate(total=Sum("amount"))
            .get("total")
            or Decimal("0.00")
        )

        pending_rent = sum(
            (
                get_invoice_outstanding_expression(invoice)
                for invoice in pending_invoices
            ),
            Decimal("0.00"),
        )

        billable_total = (
            total_revenue + pending_rent
        )

        collection_rate = (
            round(
                float(
                    total_revenue / billable_total * 100
                ),
                2,
            )
            if billable_total > 0
            else 0
        )

        monthly = (
            payments
            .annotate(
                month=TruncMonth("paid_at")
            )
            .values("month")
            .annotate(
                amount=Sum("amount"),
                transactions=Count("id"),
            )
            .order_by("month")
        )

        monthly_revenue = [
            {
                "month": item[
                    "month"
                ].strftime("%b %Y"),
                "amount": float(
                    item["amount"]
                    or Decimal("0.00")
                ),
                "transactions": item[
                    "transactions"
                ],
            }
            for item in monthly
            if item["month"]
        ]

        property_revenue = []
        top_properties = []

        for property_instance in properties:
            property_units = (
                property_instance.units.all()
            )

            property_unit_count = (
                property_units.count()
            )

            occupied = (
                Lease.objects
                .filter(
                    unit__property=property_instance,
                    status="active",
                    lease_start__lte=today,
                    lease_end__gte=today,
                )
                .values("unit_id")
                .distinct()
                .count()
            )

            income = (
                RentPayment.objects
                .filter(
                    invoice__lease__unit__property=
                    property_instance,
                    status="success",
                )
                .aggregate(total=Sum("amount"))
                .get("total")
                or Decimal("0.00")
            )

            rate = (
                round(
                    occupied
                    / property_unit_count
                    * 100,
                    2,
                )
                if property_unit_count
                else 0
            )

            property_revenue.append({
                "property_id": property_instance.id,
                "property": property_instance.name,
                "income": float(income),
            })

            top_properties.append({
                "id": property_instance.id,
                "name": property_instance.name,
                "total_units": property_unit_count,
                "occupied_units": occupied,
                "occupancy": rate,
                "income": float(income),
            })

        paid_invoice_count = (
            RentInvoice.objects
            .filter(
                lease__unit__property__landlord=
                landlord,
                status="paid",
            )
            .count()
        )

        pending_invoice_count = (
            pending_invoices.count()
        )

        overdue_invoice_count = (
            pending_invoices
            .filter(due_date__lt=today)
            .count()
        )

        tenant_status = [
            {
                "status": "Paid",
                "value": paid_invoice_count,
            },
            {
                "status": "Pending",
                "value": pending_invoice_count,
            },
            {
                "status": "Overdue",
                "value": overdue_invoice_count,
            },
        ]

        return Response(
            {
                "success": True,
                "landlord": {
                    "id": landlord.id,
                    "name": landlord.user.full_name,
                    "company": {
                        "id": landlord.company_id,
                        "name": landlord.company.name,
                    },
                },
                "summary": {
                    "total_revenue": float(
                        total_revenue
                    ),
                    "formatted_total_revenue": (
                        f"KES {total_revenue:,.2f}"
                    ),
                    "pending_rent": float(
                        pending_rent
                    ),
                    "formatted_pending_rent": (
                        f"KES {pending_rent:,.2f}"
                    ),
                    "total_units": total_units,
                    "occupied_units": occupied_units,
                    "available_units": available_units,
                    "maintenance_units": maintenance_units,
                    "occupancy_rate": occupancy_rate,
                    "collection_rate": collection_rate,
                },
                "monthly_revenue": monthly_revenue,
                "property_revenue": property_revenue,
                "tenant_status": tenant_status,
                "top_properties": sorted(
                    top_properties,
                    key=lambda item: item["income"],
                    reverse=True,
                ),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as error:
        print(
            "LANDLORD ANALYTICS ERROR:",
            str(error),
        )

        return Response(
            {
                "success": False,
                "message": (
                    "An error occurred while retrieving "
                    "landlord analytics."
                ),
                "error": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )