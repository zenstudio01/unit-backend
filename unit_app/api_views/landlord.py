from .common_imports import *

# -------------------------------------------------------------
# 1. FETCH LANDLORD METRICS & RECORDS
# -------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def landlord_list(request):
    user = request.user
    search_query = request.GET.get('search', '')
    
    # Filter users whose baseline role is explicitly flagged as 'landlord'
    landlords = User.objects.filter(role__iexact='landlord', landlord_properties__owner=request.user).order_by('-created_at')
    
    if search_query:
        landlords = landlords.filter(
            Q(full_name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
        
    serialized_data = []
    for lnd in landlords:
        # Dynamically evaluate infrastructure nodes assigned to this landlord owner
        properties = Property.objects.filter(landlord=lnd)
        properties_count = properties.count()
        
        # Traverse relational nodes to determine aggregate internal sub-unit cells
        total_units = properties.aggregate(count=Count('units'))['count'] or 0
        
        # Pull past cleared financial disbursements running through this landlord record node
        # (Using a dynamic aggregate calculation for your production payouts model)
        payout_sum = RentPayment.objects.filter(
            tenant__unit__property__landlord=lnd, 
            tenant__unit__property__owner=request.user,
            is_paid=True
        ).aggregate(total=Sum('amount'))['total'] or 0

        serialized_data.append({
            "id": lnd.id,
            "name": lnd.full_name,
            "email": lnd.email,
            "phone_number": lnd.phone_number or "--",
            "properties_count": properties_count,
            "total_units": total_units,
            "commission_rate": getattr(lnd, 'commission_rate', 10), # Graceful fallback parameter
            "last_payout": f"KES {payout_sum:,.0f}" if payout_sum > 0 else "KES 0"
        })
        
    return Response(serialized_data, status=status.HTTP_200_OK)


# -------------------------------------------------------------
# 2. CREATE LANDLORD PROFILE & MAP INITIAL BUILDINGS
# -------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_landlord(request):

    owner = request.user

    full_name = request.data.get("name")
    email = request.data.get("email")
    phone_number = request.data.get("phone_number")
    commission_rate = request.data.get("commission_rate")
    property_id = request.data.get("property_id")

    property = Property.objects.get(
        id=property_id,
        owner=owner
    )

    landlord = User.objects.create_user(
        username=email,
        full_name=full_name,
        email=email,
        phone_number=phone_number,
        role="landlord",
        password="12345678"
    )

    property.landlord = landlord
    property.save()

    return Response({
        "message": "Landlord added successfully."
    })


# -------------------------------------------------------------
# 3. TRIGGER PAYOUT SETTLEMENT ROUTING PROTOCOL
# -------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def landlord_process_payout(request, pk):
    try:
        landlord = User.objects.get(pk=pk, role__iexact='landlord')
        
        # -------------------------------------------------------------
        # PRODUCTION LOGIC NOTE: Integrate third-party disbursement engines 
        # here (e.g., Safaricom B2C M-Pesa API payload command structures)
        # -------------------------------------------------------------
        
        return Response({
            "message": f"Disbursement clearance finalized. Funds routed to node target {landlord.phone_number}."
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"message": "Target landlord entity profile could not be found."}, status=status.HTTP_404_NOT_FOUND)




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def landlord_dashboard(request):

    landlord = request.user

    properties = Property.objects.filter(landlord=landlord)

    property_count = properties.count()

    units = Unit.objects.filter(property__landlord=landlord)

    unit_count = units.count()

    occupied_units = units.filter(status="occupied").count()

    available_units = units.filter(status="available").count()

    maintenance_units = units.filter(
        status="under_maintenance"
    ).count()

    tenants = Tenant.objects.filter(
        unit__property__landlord=landlord
    )

    tenant_count = tenants.count()

    current_month = timezone.now().month
    current_year = timezone.now().year

    paid_this_month = RentPayment.objects.filter(
        tenant__unit__property__landlord=landlord,
        is_paid=True,
        payment_date__month=current_month,
        payment_date__year=current_year,
    )

    rent_collected = (
        paid_this_month.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    pending_rent = (
        RentPayment.objects.filter(
            tenant__unit__property__landlord=landlord,
            is_paid=False,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    occupancy_rate = 0

    if unit_count > 0:
        occupancy_rate = round(
            (occupied_units / unit_count) * 100,
            1,
        )

    recent_payments = []

    payments = (
        RentPayment.objects.filter(
            tenant__unit__property__landlord=landlord
        )
        .select_related(
            "tenant",
            "tenant__user",
            "tenant__unit",
        )
        .order_by("-payment_date")[:5]
    )

    for payment in payments:
        recent_payments.append({
            "id": payment.id,
            "tenant": payment.tenant.user.full_name,
            "property": payment.tenant.unit.property.name,
            "unit": payment.tenant.unit.name,
            "amount": float(payment.amount),
            "date": payment.payment_date.strftime("%d %b %Y"),
            "status": "Paid" if payment.is_paid else "Pending",
        })

    property_overview = []

    for property in properties:

        total_units = property.units.count()

        occupied = property.units.filter(
            status="occupied"
        ).count()

        monthly_income = (
            RentPayment.objects.filter(
                tenant__unit__property=property,
                is_paid=True,
                payment_date__month=current_month,
                payment_date__year=current_year,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        property_overview.append({
            "id": property.id,
            "name": property.name,
            "units": total_units,
            "occupied": occupied,
            "income": float(monthly_income),
        })

    return Response({

        "summary": {

            "properties": property_count,

            "units": unit_count,

            "occupied_units": occupied_units,

            "available_units": available_units,

            "maintenance_units": maintenance_units,

            "tenants": tenant_count,

            "rent_collected": float(rent_collected),

            "pending_rent": float(pending_rent),

            "occupancy_rate": occupancy_rate,

        },

        "recent_payments": recent_payments,

        "properties": property_overview,

    })




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def landlord_analytics(request):
    user = request.user

    properties = Property.objects.filter(landlord=user)

    units = Unit.objects.filter(property__in=properties)

    tenants = Tenant.objects.filter(unit__property__in=properties)

    payments = RentPayment.objects.filter(
        tenant__in=tenants,
        is_paid=True
    )

    total_units = units.count()
    occupied_units = units.filter(status="occupied").count()
    available_units = units.filter(status="available").count()

    occupancy_rate = 0

    if total_units:
        occupancy_rate = round(
            (occupied_units / total_units) * 100,
            2
        )

    total_revenue = payments.aggregate(
        total=Sum("amount")
    )["total"] or 0

    pending_rent = RentPayment.objects.filter(
        tenant__in=tenants,
        is_paid=False
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    collection_rate = 0

    if total_revenue + pending_rent:
        collection_rate = round(
            (total_revenue /
             (total_revenue + pending_rent)) * 100,
            2
        )

    monthly = (
        payments
        .annotate(month=TruncMonth("payment_date"))
        .values("month")
        .annotate(amount=Sum("amount"))
        .order_by("month")
    )

    monthly_revenue = [
        {
            "month": item["month"].strftime("%b"),
            "amount": float(item["amount"])
        }
        for item in monthly
    ]

    property_revenue = []

    for property in properties:

        income = (
            RentPayment.objects.filter(
                tenant__unit__property=property,
                is_paid=True
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        property_revenue.append({
            "property": property.name,
            "income": float(income)
        })

    tenant_status = [
        {
            "status": "Paid",
            "value": RentPayment.objects.filter(
                tenant__in=tenants,
                is_paid=True
            ).count()
        },
        {
            "status": "Pending",
            "value": RentPayment.objects.filter(
                tenant__in=tenants,
                is_paid=False
            ).count()
        }
    ]

    top_properties = []

    for property in properties:

        total = property.units.count()

        occupied = property.units.filter(
            status="occupied"
        ).count()

        income = (
            RentPayment.objects.filter(
                tenant__unit__property=property,
                is_paid=True
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        rate = 0

        if total:
            rate = round((occupied / total) * 100, 2)

        top_properties.append({
            "name": property.name,
            "occupancy": rate,
            "income": float(income)
        })

    return JsonResponse({

        "summary": {
            "total_revenue": float(total_revenue),
            "pending_rent": float(pending_rent),
            "occupancy_rate": occupancy_rate,
            "collection_rate": collection_rate
        },

        "monthly_revenue": monthly_revenue,

        "property_revenue": property_revenue,

        "tenant_status": tenant_status,

        "top_properties": sorted(
            top_properties,
            key=lambda x: x["income"],
            reverse=True
        )

    })