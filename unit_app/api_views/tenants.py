from .common_imports import *

# get tenants for a property based on the user role (PM or LANDLORD)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_tenants(request):

    user = request.user

    if user.role == "property manager":
        tenants = Tenant.objects.filter(
            unit__property__owner=user
        ).select_related(
            "user",
            "unit",
            "unit__property"
        )

    elif user.role == "landlord":
        tenants = Tenant.objects.filter(
            unit__property__landlord=user
        ).select_related(
            "user",
            "unit",
            "unit__property"
        )

    else:
        return Response({
            "success": False,
            "message": "Permission denied."
        }, status=403)

    data = []

    for tenant in tenants:

        latest_payment = RentPayment.objects.filter(
            tenant=tenant
        ).order_by("-payment_date").first()

        if latest_payment:

            if latest_payment.is_paid:
                payment_status = "Paid"
            else:
                payment_status = "Pending"

        else:
            payment_status = "Overdue"

        data.append({
            "id": tenant.id,
            "name": tenant.user.full_name,
            "email": tenant.user.email,
            "phone_number": tenant.user.phone_number,

            "property_name": tenant.unit.property.name,
            "unit_number": tenant.unit.name,

            "rent_amount": tenant.unit.rent,

            "status": payment_status,
        })
    print(f"Data: {data}")

    return Response({
        "success": True,
        "count": len(data),
        "tenants": data
    })



# add a tenant to a unit
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_tenant(request):
    full_name = request.data.get("full_name")
    email = request.data.get("email")
    phone_number = request.data.get("phone_number")
    unit_id = request.data.get("unit_id")
    lease_start = request.data.get("lease_start", "2026-06-02")
    lease_end = request.data.get("lease_end","2027-06-02")
    property_id = request.data.get("property")
    unit = request.data.get("unit")

    try:
        user = User.objects.create(full_name=full_name, email=email, username=email, password="123456", phone_number=phone_number, role="tenant", is_verified=True)
        property = Property.objects.get(id=property_id)
        unit = Unit.objects.get(property=property, id=unit)

        if Tenant.objects.filter(user=user).exists():
            return Response({"success": False, "message": "Tenant already exists."})

        tenant = Tenant.objects.create(
            user=user,
            unit=unit,
            lease_end_date=timezone.now() + timedelta(days=30),
            is_active=True
        )

        unit.status = "occupied"
        unit.save()

        return Response({"success": True, "message": "Tenant added successfully."})

    except User.DoesNotExist:
        return Response({"success": False, "message": "User not found."})

    except Unit.DoesNotExist:
        return Response({"success": False, "message": "Unit not found."})



# request rent from a tenant
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_rent(request):

    tenant_id = request.data.get("tenant_id")

    try:

        tenant = Tenant.objects.select_related(
            "user",
            "unit"
        ).get(id=tenant_id)

        phone = tenant.user.phone_number

        amount = tenant.unit.price_per_month

        # Call your Daraja STK Push here

        return Response({

            "success": True,

            "message": "STK Push sent.",

            "phone": phone,

            "amount": amount

        })

    except Tenant.DoesNotExist:

        return Response({

            "success": False,

            "message": "Tenant not found."

        }, status=404)