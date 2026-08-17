from .common_imports import *


def can_manage_units(
    user,
    organization,
):
    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                user=user,
                organization=organization,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return False

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

    return bool(
        role_codes.intersection({
            "organization_owner",
            "organization_admin",
            "property_manager",
        })
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unit_form_options(request):
    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    property_id = (
        request.GET.get(
            "property_id"
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

    if not property_id:
        return JsonResponse(
            {
                "message":
                    "property_id is required."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    if not can_manage_units(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to manage units."
            },
            status=403,
        )

    try:
        property_obj = (
            Property.objects.get(
                id=property_id,
                organization=organization,
            )
        )

    except Property.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Property not found."
            },
            status=404,
        )

    buildings = (
        Building.objects
        .filter(
            property=property_obj,
            status="active",
        )
        .prefetch_related(
            "floors"
        )
        .order_by(
            "name"
        )
    )

    buildings_data = []

    for building in buildings:

        floors = (
            building.floors
            .filter(
                status="active"
            )
            .order_by(
                "floor_number"
            )
        )

        buildings_data.append(
            {
                "id":
                    building.id,

                "name":
                    building.name,

                "building_code":
                    building.building_code,

                "number_of_floors":
                    building.number_of_floors,

                "floors": [
                    {
                        "id":
                            floor.id,

                        "name":
                            floor.name,

                        "floor_code":
                            floor.floor_code,

                        "floor_number":
                            floor.floor_number,
                    }
                    for floor
                    in floors
                ],
            }
        )

    amenities = (
        Amenity.objects
        .all()
        .order_by(
            "name"
        )
    )

    amenities_data = [
        {
            "id":
                amenity.id,

            "name":
                amenity.name,

            "description":
                amenity.description,

            "amenity_type":
                amenity.amenity_type,
        }
        for amenity
        in amenities
    ]

    return JsonResponse(
        {
            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "property_code":
                    property_obj.property_code,
            },

            "buildings":
                buildings_data,

            "amenities":
                amenities_data,
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_unit(request):
    user = request.user
    data = request.data

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    property_id = (
        data.get(
            "property_id"
        )
    )

    building_id = (
        data.get(
            "building_id"
        )
    )

    floor_id = (
        data.get(
            "floor_id"
        )
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    unit_code = str(
        data.get(
            "unit_code",
            ""
        )
    ).strip().upper()

    unit_type = str(
        data.get(
            "unit_type",
            ""
        )
    ).strip()

    bedrooms = (
        data.get(
            "bedrooms"
        )
    )

    bathrooms = (
        data.get(
            "bathrooms"
        )
    )

    square_footage = (
        data.get(
            "square_footage"
        )
    )

    monthly_rent = (
        data.get(
            "monthly_rent"
        )
    )

    deposit_amount = (
        data.get(
            "deposit_amount"
        )
    )

    service_charge = (
        data.get(
            "service_charge"
        )
    )

    amenity_ids = (
        data.get(
            "amenity_ids",
            []
        )
    )

    # =====================================================
    # REQUIRED
    # =====================================================

    required = {
        "organization_id":
            organization_id,

        "property_id":
            property_id,

        "building_id":
            building_id,

        "floor_id":
            floor_id,

        "name":
            name,

        "unit_code":
            unit_code,

        "unit_type":
            unit_type,

        "bedrooms":
            bedrooms,

        "bathrooms":
            bathrooms,

        "monthly_rent":
            monthly_rent,

        "deposit_amount":
            deposit_amount,
    }

    missing = [
        key
        for key, value
        in required.items()
        if value is None
        or value == ""
    ]

    if missing:
        return JsonResponse(
            {
                "message":
                    "Missing required fields.",

                "fields":
                    missing,
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    if not can_manage_units(
        user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to add units."
            },
            status=403,
        )

    # =====================================================
    # PROPERTY
    # =====================================================

    try:
        property_obj = (
            Property.objects.get(
                id=property_id,
                organization=organization,
            )
        )

    except Property.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Property not found."
            },
            status=404,
        )

    # =====================================================
    # BUILDING
    # =====================================================

    try:
        building = (
            Building.objects.get(
                id=building_id,
                property=property_obj,
            )
        )

    except Building.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Building does not belong to this property."
            },
            status=400,
        )

    # =====================================================
    # FLOOR
    # =====================================================

    try:
        floor = (
            Floor.objects.get(
                id=floor_id,
                building=building,
            )
        )

    except Floor.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Floor does not belong to the selected building."
            },
            status=400,
        )

    # =====================================================
    # UNIQUE CODE
    # =====================================================

    if (
        Unit.objects
        .filter(
            unit_code__iexact=
                unit_code
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "A unit with this code already exists."
            },
            status=400,
        )

    # =====================================================
    # NUMBERS
    # =====================================================

    try:
        bedrooms = int(
            bedrooms
        )

        bathrooms = int(
            bathrooms
        )

        monthly_rent = Decimal(
            str(
                monthly_rent
            )
        )

        deposit_amount = Decimal(
            str(
                deposit_amount
            )
        )

        square_footage = (
            Decimal(
                str(
                    square_footage
                )
            )
            if square_footage
            not in (
                None,
                "",
            )
            else None
        )

        service_charge = (
            Decimal(
                str(
                    service_charge
                )
            )
            if service_charge
            not in (
                None,
                "",
            )
            else None
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid numeric values."
            },
            status=400,
        )

    if (
        bedrooms < 0
        or bathrooms < 0
    ):
        return JsonResponse(
            {
                "message":
                    "Bedrooms and bathrooms cannot be negative."
            },
            status=400,
        )

    if monthly_rent <= 0:
        return JsonResponse(
            {
                "message":
                    "Monthly rent must be greater than zero."
            },
            status=400,
        )

    # =====================================================
    # AMENITIES
    # =====================================================

    amenities = list(
        Amenity.objects.filter(
            id__in=
                amenity_ids
        )
    )

    if len(amenities) != len(
        set(amenity_ids)
    ):
        return JsonResponse(
            {
                "message":
                    "One or more amenities are invalid."
            },
            status=400,
        )

    # =====================================================
    # CREATE
    # =====================================================

    try:
        with transaction.atomic():

            unit = (
                Unit.objects.create(
                    property=
                        property_obj,

                    building=
                        building,

                    floor=
                        floor,

                    name=
                        name,

                    unit_code=
                        unit_code,

                    unit_type=
                        unit_type,

                    bedrooms=
                        bedrooms,

                    bathrooms=
                        bathrooms,

                    square_footage=
                        square_footage,

                    monthly_rent=
                        monthly_rent,

                    deposit_amount=
                        deposit_amount,

                    service_charge=
                        service_charge,

                    status=
                        "available",
                )
            )

            UnitAmenity.objects.bulk_create(
                [
                    UnitAmenity(
                        unit=unit,
                        amenity=amenity,
                    )
                    for amenity
                    in amenities
                ]
            )

        return JsonResponse(
            {
                "message":
                    f"{unit.name} created successfully.",

                "unit": {
                    "id":
                        unit.id,

                    "name":
                        unit.name,

                    "unit_code":
                        unit.unit_code,

                    "unit_type":
                        unit.unit_type,

                    "status":
                        unit.status,
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE UNIT ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create unit.",

                "error":
                    str(error),
            },
            status=500,
        )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_create_units(request):
    user = request.user
    data = request.data

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    property_id = (
        data.get(
            "property_id"
        )
    )

    building_id = (
        data.get(
            "building_id"
        )
    )

    floor_id = (
        data.get(
            "floor_id"
        )
    )

    prefix = str(
        data.get(
            "prefix",
            ""
        )
    ).strip().upper()

    start_number = (
        data.get(
            "start_number",
            1
        )
    )

    number_of_units = (
        data.get(
            "number_of_units"
        )
    )

    unit_type = str(
        data.get(
            "unit_type",
            ""
        )
    ).strip()

    bedrooms = (
        data.get(
            "bedrooms"
        )
    )

    bathrooms = (
        data.get(
            "bathrooms"
        )
    )

    square_footage = (
        data.get(
            "square_footage"
        )
    )

    monthly_rent = (
        data.get(
            "monthly_rent"
        )
    )

    deposit_amount = (
        data.get(
            "deposit_amount"
        )
    )

    service_charge = (
        data.get(
            "service_charge"
        )
    )

    amenity_ids = (
        data.get(
            "amenity_ids",
            []
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not all([
        organization_id,
        property_id,
        building_id,
        floor_id,
        prefix,
        unit_type,
    ]):
        return JsonResponse(
            {
                "message":
                    "Missing required fields."
            },
            status=400,
        )

    try:
        start_number = int(
            start_number
        )

        number_of_units = int(
            number_of_units
        )

        bedrooms = int(
            bedrooms
        )

        bathrooms = int(
            bathrooms
        )

        monthly_rent = Decimal(
            str(
                monthly_rent
            )
        )

        deposit_amount = Decimal(
            str(
                deposit_amount
            )
        )

        square_footage = (
            Decimal(
                str(
                    square_footage
                )
            )
            if square_footage
            not in (
                None,
                "",
            )
            else None
        )

        service_charge = (
            Decimal(
                str(
                    service_charge
                )
            )
            if service_charge
            not in (
                None,
                "",
            )
            else None
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid numeric values."
            },
            status=400,
        )

    if start_number < 0:
        return JsonResponse(
            {
                "message":
                    "Start number cannot be negative."
            },
            status=400,
        )

    if (
        number_of_units < 1
        or number_of_units > 200
    ):
        return JsonResponse(
            {
                "message":
                    "You can create between 1 and 200 units at once."
            },
            status=400,
        )

    if (
        bedrooms < 0
        or bathrooms < 0
    ):
        return JsonResponse(
            {
                "message":
                    "Bedrooms and bathrooms cannot be negative."
            },
            status=400,
        )

    if monthly_rent <= 0:
        return JsonResponse(
            {
                "message":
                    "Monthly rent must be greater than zero."
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    if not can_manage_units(
        user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to create units."
            },
            status=403,
        )

    # =====================================================
    # PROPERTY / BUILDING / FLOOR
    # =====================================================

    try:
        property_obj = (
            Property.objects.get(
                id=property_id,
                organization=organization,
            )
        )

    except Property.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Property not found."
            },
            status=404,
        )

    try:
        building = (
            Building.objects.get(
                id=building_id,
                property=property_obj,
            )
        )

    except Building.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Building does not belong to this property."
            },
            status=400,
        )

    try:
        floor = (
            Floor.objects.get(
                id=floor_id,
                building=building,
            )
        )

    except Floor.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Floor does not belong to this building."
            },
            status=400,
        )

    # =====================================================
    # GENERATE UNIT CODES
    # =====================================================

    generated_units = []

    generated_codes = []

    for index in range(
        number_of_units
    ):
        number = (
            start_number +
            index
        )

        number_string = (
            str(number)
            .zfill(2)
        )

        code = (
            f"{prefix}"
            f"{number_string}"
        )

        generated_codes.append(
            code
        )

    # =====================================================
    # CHECK DUPLICATES BEFORE CREATING ANYTHING
    # =====================================================

    existing_codes = list(
        Unit.objects
        .filter(
            unit_code__in=
                generated_codes
        )
        .values_list(
            "unit_code",
            flat=True,
        )
    )

    if existing_codes:
        return JsonResponse(
            {
                "message":
                    "Some generated unit codes already exist.",

                "duplicates":
                    existing_codes,
            },
            status=400,
        )

    # =====================================================
    # AMENITIES
    # =====================================================

    amenities = list(
        Amenity.objects
        .filter(
            id__in=
                amenity_ids
        )
    )

    if len(amenities) != len(
        set(amenity_ids)
    ):
        return JsonResponse(
            {
                "message":
                    "One or more amenities are invalid."
            },
            status=400,
        )

    # =====================================================
    # CREATE EVERYTHING ATOMICALLY
    # =====================================================

    try:
        with transaction.atomic():

            for code in generated_codes:

                unit = (
                    Unit.objects.create(
                        property=
                            property_obj,

                        building=
                            building,

                        floor=
                            floor,

                        name=
                            f"Unit {code}",

                        unit_code=
                            code,

                        unit_type=
                            unit_type,

                        bedrooms=
                            bedrooms,

                        bathrooms=
                            bathrooms,

                        square_footage=
                            square_footage,

                        monthly_rent=
                            monthly_rent,

                        deposit_amount=
                            deposit_amount,

                        service_charge=
                            service_charge,

                        status=
                            "available",
                    )
                )

                generated_units.append(
                    unit
                )

            unit_amenities = []

            for unit in generated_units:
                for amenity in amenities:

                    unit_amenities.append(
                        UnitAmenity(
                            unit=
                                unit,

                            amenity=
                                amenity,
                        )
                    )

            if unit_amenities:
                UnitAmenity.objects.bulk_create(
                    unit_amenities
                )

        return JsonResponse(
            {
                "message": (
                    f"{len(generated_units)} "
                    "units created successfully."
                ),

                "count":
                    len(
                        generated_units
                    ),

                "units": [
                    {
                        "id":
                            unit.id,

                        "name":
                            unit.name,

                        "unit_code":
                            unit.unit_code,

                        "status":
                            unit.status,
                    }
                    for unit
                    in generated_units
                ],
            },
            status=201,
        )

    except Exception as error:
        print(
            "BULK CREATE UNITS ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create units.",

                "error":
                    str(error),
            },
            status=500,
        )