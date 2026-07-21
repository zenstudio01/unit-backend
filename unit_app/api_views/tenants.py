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


# get tenant dashboard data
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_dashboard(request):
    user = request.user

    try:
        tenant = Tenant.objects.select_related(
            "unit",
            "unit__property"
        ).get(user=user)

    except Tenant.DoesNotExist:
        return JsonResponse(
            {
                "message": "Tenant profile not found."
            },
            status=404
        )

    property = tenant.unit.property

    # Latest unpaid rent
    unpaid_payment = (
        RentPayment.objects
        .filter(
            tenant=tenant,
            is_paid=False
        )
        .order_by("payment_date")
        .first()
    )

    current_rent = (
        float(unpaid_payment.amount)
        if unpaid_payment
        else 0
    )

    next_due_date = (
        unpaid_payment.payment_date.strftime("%d %b %Y")
        if unpaid_payment
        else "No pending rent"
    )

    # Outstanding balance
    balance = (
        RentPayment.objects.filter(
            tenant=tenant,
            is_paid=False
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # Pending maintenance requests
    pending_requests = 0

    if "MaintenanceRequest" in globals():
        pending_requests = MaintenanceRequest.objects.filter(
            tenant=tenant,
            status="pending"
        ).count()

    # Latest announcements
    announcements = []

    if "Announcement" in globals():

        latest = (
            Announcement.objects
            .filter(property=property)
            .order_by("-created_at")[:5]
        )

        announcements = [
            {
                "id": item.id,
                "title": item.title,
                "message": item.message,
                "date": item.created_at.strftime("%d %b %Y"),
            }
            for item in latest
        ]

    return JsonResponse(
        {
            "dashboard": {
                "tenant_name": tenant.user.full_name,
                "property_name": property.name,
                "unit_name": tenant.unit.name,
                "current_rent": current_rent,
                "balance": float(balance),
                "next_due_date": next_due_date,
                "pending_requests": pending_requests,
                "announcements": announcements,
            }
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_announcements(request):
    user = request.user

    try:
        tenant = Tenant.objects.select_related(
            "unit",
            "unit__property"
        ).get(user=user)

    except Tenant.DoesNotExist:
        return JsonResponse(
            {
                "message": "Tenant profile not found."
            },
            status=404
        )

    announcements = (
        Announcement.objects.filter(
            is_active=True
        ).filter(
            Q(target="all") |
            Q(target="property", property=tenant.unit.property) |
            Q(target="unit", unit=tenant.unit)
        ).order_by("-created_at")
    )

    data = []

    for announcement in announcements:
        data.append({
            "id": announcement.id,
            "title": announcement.title,
            "message": announcement.message,
            "target": announcement.target,
            "date": announcement.created_at.strftime("%d %b %Y"),
            "created_by": announcement.created_by.full_name,
        })

    return JsonResponse({
        "announcements": data
    })




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_maintenance_request(request):
    try:
        tenant = Tenant.objects.filter(user=request.user).first()

        if not tenant:
            return JsonResponse({
                "success": False,
                "message": "Tenant profile not found."
            }, status=404)

        title = request.data.get("title")
        description = request.data.get("description")
        priority = request.data.get("priority", "medium")

        if not title or not description:
            return JsonResponse({
                "success": False,
                "message": "Title and description are required."
            }, status=400)

        maintenance = MaintenanceRequest.objects.create(
            tenant=tenant,
            property=tenant.unit.property,
            unit=tenant.unit,
            title=title,
            description=description,
            priority=priority
        )

        return JsonResponse({
            "success": True,
            "message": "Maintenance request submitted successfully.",
            "request": {
                "id": maintenance.id,
                "title": maintenance.title,
                "description": maintenance.description,
                "priority": maintenance.priority,
                "status": maintenance.status,
                "created_at": maintenance.created_at
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_maintenance_requests(request):
    tenant = Tenant.objects.filter(user=request.user).first()

    if not tenant:
        return JsonResponse({
            "success": False,
            "message": "Tenant profile not found."
        }, status=404)

    requests = MaintenanceRequest.objects.filter(
        tenant=tenant
    ).order_by("-created_at")

    data = []

    for item in requests:
        data.append({
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "priority": item.priority,
            "status": item.status,
            "property": item.property.name,
            "unit": item.unit.name,
            "created_at": item.created_at
        })

    return JsonResponse({
        "success": True,
        "requests": data
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_rent_payments(request):
    try:
        tenant = Tenant.objects.filter(user=request.user).first()

        if not tenant:
            return JsonResponse({
                "success": False,
                "message": "Tenant profile not found."
            }, status=404)

        payments = RentPayment.objects.filter(
            tenant=tenant
        ).order_by("-payment_date")

        data = []

        for payment in payments:
            data.append({
                "id": payment.id,
                "amount": float(payment.amount),
                "payment_date": payment.payment_date.strftime("%d %b %Y"),
                "receipt_number": payment.receipt_number,
                "transaction_id": payment.transaction_id,
                "payment_method": payment.payment_method,
                "tenant": payment.tenant.user.full_name,
                "property": payment.tenant.unit.property.name,
                "unit": payment.tenant.unit.name,
                "is_paid": payment.is_paid
            })

        return JsonResponse({
            "success": True,
            "payments": data
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



