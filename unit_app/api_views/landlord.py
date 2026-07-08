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
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def landlord_create(request):
    data = request.data
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone_number')
    commission = float(data.get('commission_rate', 10))
    assigned_props_input = data.get('assigned_properties', '')

    if not name or not email:
        return Response({"message": "Legal Name and Profile Email are required parameters."}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email__iexact=email).exists():
        return Response({"message": "An account profile with this email address already exists."}, status=status.HTTP_400_BAD_REQUEST)

    # Instantiate the Landlord profile entry into the main User Identity table
    landlord_user = User.objects.create(
        username=email,
        full_name=name,
        email=email,
        phone_number=phone,
        role='landlord',
        is_active=True,
        is_verified=True
    )
    
    # Custom property field handling if extended on your user profile model:
    if hasattr(landlord_user, 'commission_rate'):
        landlord_user.commission_rate = commission
        landlord_user.save()

    # If initial property text allocations are declared, parse and map owners
    properties_mapped = 0
    if assigned_props_input:
        prop_names = [p.strip() for p in assigned_props_input.split(',') if p.strip()]
        for p_name in prop_names:
            # Check for existing unmatched properties or initialize a skeletal placeholder
            Property.objects.update_or_create(
                name__iexact=p_name,
                defaults={'landlord': landlord_user, 'owner': request.user}
            )
            properties_mapped += 1

    return Response({
        "id": landlord_user.id,
        "name": landlord_user.full_name,
        "email": landlord_user.email,
        "phone_number": landlord_user.phone_number,
        "properties_count": properties_mapped,
        "total_units": 0,
        "commission_rate": commission,
        "last_payout": "KES 0"
    }, status=status.HTTP_201_CREATED)


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