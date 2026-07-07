from .common_imports import *

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def property_list(request):
    user = request.user

    # Determine property lookup scope based on user role classification
    if user.role.lower() == 'landlord':
        properties = Property.objects.filter(landlord=user)
    else:
        properties = Property.objects.all()

    serialized_data = []
    for prop in properties:
        # Dynamically aggregate real-time counts and yield statistics
        total_units = prop.units.count()
        occupied_units = prop.units.filter(status='occupied').count()
        monthly_rent_sum = prop.units.aggregate(total=Sum('price_per_month'))['total'] or 0

        # Format choice metrics to match frontend UI string states safely
        ui_property_type = prop.property_type.title()
        if prop.property_type == 'condo':
            ui_property_type = 'Mixed Use'

        serialized_data.append({
            "id": prop.id,
            "name": prop.name,
            "location": prop.address,
            "total_units": total_units,
            "occupied_units": occupied_units,
            "property_type": ui_property_type,
            "monthly_rent": f"KES {monthly_rent_sum:,.0f}" if monthly_rent_sum > 0 else "KES 0",
            "description": prop.description
        })

    return Response(serialized_data, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def property_create(request):
    user = request.user
    data = request.data
    
    name = data.get('name')
    location = data.get('location')
    property_type_input = data.get('property_type', 'Residential').lower()
    description = data.get('description', '')
    total_units_count = int(data.get('total_units', 0))

    if not name or not location:
        return Response(
            {"message": "Property name and location address parameters are strictly required."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Clean frontend categorization inputs into valid internal model choices
    db_property_type = 'apartment'
    if 'commercial' in property_type_input:
        db_property_type = 'townhouse'
    elif 'mixed' in property_type_input:
        db_property_type = 'condo'

    # Build the foundational master asset node inside your database
    property_asset = Property.objects.create(
        owner=user,
        landlord=user if user.role.lower() == 'landlord' else None,
        name=name,
        address=location,
        property_type=db_property_type,
        description=description,
        legal_plot_number="PENDING-VERIFICATION",
        city=location.split(',')[1].strip() if ',' in location else "Nairobi",
        state="Nairobi",
        country="Kenya",
        status='available'
    )

    # Initialize shell individual sub-units to instantly build up matching totals structures
    if total_units_count > 0:
        units_to_create = [
            Unit(
                name=f"Unit {i:02d}",
                description="System shell initialization asset slot placeholder.",
                property=property_asset,
                price_per_month=0.00,
                bedrooms=1,
                bathrooms=1,
                max_guests=2,
                status='available'
            ) for i in range(1, total_units_count + 1)
        ]
        Unit.objects.bulk_create(units_to_create)

    # Return structure modeled directly after the optimistic state updates inside React
    return Response({
        "id": property_asset.id,
        "name": property_asset.name,
        "location": property_asset.address,
        "total_units": total_units_count,
        "occupied_units": 0,
        "property_type": data.get('property_type', 'Residential'),
        "monthly_rent": "KES 0",
        "description": property_asset.description
    }, status=status.HTTP_201_CREATED)