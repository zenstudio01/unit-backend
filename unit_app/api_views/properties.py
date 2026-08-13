from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_properties(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    # =====================================================
    # GET ORGANIZATION
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

    # =====================================================
    # VERIFY MEMBERSHIP
    # =====================================================

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

    # =====================================================
    # OPTIONAL FILTERS
    # =====================================================

    search = str(
        request.GET.get(
            "search",
            ""
        )
    ).strip()

    status_filter = str(
        request.GET.get(
            "status",
            ""
        )
    ).strip()

    property_type = str(
        request.GET.get(
            "property_type",
            ""
        )
    ).strip()

    # =====================================================
    # PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=organization
        )
        .order_by(
            "-created_at"
        )
    )

    if status_filter:
        properties = properties.filter(
            status=status_filter
        )

    if property_type:
        properties = properties.filter(
            property_type=property_type
        )

    if search:
        properties = properties.filter(
            Q(
                name__icontains=search
            )
            |
            Q(
                city__icontains=search
            )
            |
            Q(
                county__icontains=search
            )
            |
            Q(
                property_type__icontains=search
            )
        )

    # =====================================================
    # RESPONSE DATA
    # =====================================================

    property_data = []

    total_units = 0
    total_occupied = 0
    total_vacant = 0

    for property_obj in properties:

        property_units = (
            Unit.objects.filter(
                property=property_obj
            )
        )

        units_count = (
            property_units.count()
        )

        occupied_units = (
            property_units.filter(
                status="occupied"
            ).count()
        )

        vacant_units = (
            property_units.filter(
                status="vacant"
            ).count()
        )

        total_units += (
            units_count
        )

        total_occupied += (
            occupied_units
        )

        total_vacant += (
            vacant_units
        )

        occupancy_rate = (
            round(
                (
                    occupied_units
                    / units_count
                ) * 100
            )
            if units_count > 0
            else 0
        )

        property_data.append(
            {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "code":
                    getattr(
                        property_obj,
                        "code",
                        None,
                    ),

                "property_type":
                    property_obj
                    .property_type,

                "ownership_type":
                    getattr(
                        property_obj,
                        "ownership_type",
                        None,
                    ),

                "country":
                    getattr(
                        property_obj,
                        "country",
                        "",
                    ),

                "county":
                    getattr(
                        property_obj,
                        "county",
                        "",
                    ),

                "city":
                    getattr(
                        property_obj,
                        "city",
                        "",
                    ),

                "address":
                    getattr(
                        property_obj,
                        "address",
                        "",
                    ),

                "status":
                    getattr(
                        property_obj,
                        "status",
                        "active",
                    ),

                "units_count":
                    units_count,

                "occupied_units":
                    occupied_units,

                "vacant_units":
                    vacant_units,

                "occupancy_rate":
                    occupancy_rate,

                "created_at":
                    (
                        property_obj
                        .created_at
                        .isoformat()
                        if getattr(
                            property_obj,
                            "created_at",
                            None,
                        )
                        else None
                    ),
            }
        )

    # =====================================================
    # SUMMARY
    # =====================================================

    summary = {
        "properties":
            len(property_data),

        "units":
            total_units,

        "occupied":
            total_occupied,

        "vacant":
            total_vacant,
    }

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "summary":
                summary,

            "properties":
                property_data,

            "count":
                len(property_data),
        },
        status=200,
    )






@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_form_options(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
            },
            status=400,
        )

    try:
        organization = Organization.objects.get(
            id=organization_id
        )

    except Organization.DoesNotExist:
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

    portfolios = (
        Portifolio.objects
        .filter(
            organization=organization,
            status="active",
        )
        .order_by("name")
    )

    amenities = (
        Amenity.objects
        .all()
        .order_by(
            "amenity_type",
            "name",
        )
    )

    return JsonResponse(
        {
            "portfolios": [
                {
                    "id": item.id,
                    "name": item.name,
                    "code": item.code,
                    "description":
                        item.description,
                }
                for item in portfolios
            ],

            "amenities": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description":
                        item.description,
                    "amenity_type":
                        item.amenity_type,
                }
                for item in amenities
            ],

            "property_types": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label
                in Property.PROPERTY_TYPES
            ],
        },
        status=200,
    )




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_property(request):
    user = request.user
    data = request.data

    organization_id = data.get(
        "organization_id"
    )

    portfolio_id = data.get(
        "portifolio_id"
    )

    property_code = str(
        data.get("property_code", "")
    ).strip().upper()

    code = str(
        data.get("code", "")
    ).strip().upper()

    name = str(
        data.get("name", "")
    ).strip()

    property_type = str(
        data.get("property_type", "")
    ).strip()

    ownership_type = str(
        data.get("ownership_type", "")
    ).strip()

    description = str(
        data.get("description", "")
        or ""
    ).strip()

    address = str(
        data.get("address", "")
    ).strip()

    city = str(
        data.get("city", "")
    ).strip()

    county = str(
        data.get("county", "")
    ).strip()

    country = str(
        data.get("country", "")
    ).strip()

    postal_code = str(
        data.get("postal_code", "")
        or ""
    ).strip()

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    year_built = data.get(
        "year_built"
    )

    total_land_area = data.get(
        "total_land_area"
    )

    # =====================================================
    # REQUIRED FIELDS
    # =====================================================

    missing_fields = []

    required = {
        "organization_id":
            organization_id,

        "portifolio_id":
            portfolio_id,

        "property_code":
            property_code,

        "code":
            code,

        "name":
            name,

        "property_type":
            property_type,

        "ownership_type":
            ownership_type,

        "address":
            address,

        "city":
            city,

        "county":
            county,

        "country":
            country,
    }

    for field, value in required.items():
        if not value:
            missing_fields.append(
                field
            )

    if missing_fields:
        return JsonResponse(
            {
                "message":
                    "Missing required fields.",

                "fields":
                    missing_fields,
            },
            status=400,
        )

    # =====================================================
    # ORGANIZATION
    # =====================================================

    try:
        organization = Organization.objects.get(
            id=organization_id
        )

    except Organization.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Organization not found."
            },
            status=404,
        )

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related("roles")
            .get(
                user=user,
                organization=organization,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # PORTFOLIO
    # =====================================================

    try:
        portfolio = Portifolio.objects.get(
            id=portfolio_id,
            organization=organization,
            status="active",
        )

    except Portifolio.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "Portfolio not found."
            },
            status=404,
        )

    # =====================================================
    # PROPERTY TYPE
    # =====================================================

    valid_property_types = {
        choice[0]
        for choice
        in Property.PROPERTY_TYPES
    }

    if (
        property_type
        not in valid_property_types
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid property type."
            },
            status=400,
        )

    # =====================================================
    # UNIQUE CODES
    # =====================================================

    if Property.objects.filter(
        property_code__iexact=
            property_code
    ).exists():
        return JsonResponse(
            {
                "message":
                    "Property code already exists."
            },
            status=400,
        )

    if Property.objects.filter(
        code__iexact=code
    ).exists():
        return JsonResponse(
            {
                "message":
                    "Property code already exists."
            },
            status=400,
        )

    # =====================================================
    # OPTIONAL NUMERIC VALUES
    # =====================================================

    parsed_year = None

    if year_built not in [
        None,
        "",
    ]:
        try:
            parsed_year = int(
                year_built
            )

        except ValueError:
            return JsonResponse(
                {
                    "message":
                        "year_built must be a valid year."
                },
                status=400,
            )

    parsed_land_area = None

    if total_land_area not in [
        None,
        "",
    ]:
        try:
            parsed_land_area = Decimal(
                str(total_land_area)
            )

        except InvalidOperation:
            return JsonResponse(
                {
                    "message":
                        "Invalid total_land_area."
                },
                status=400,
            )

    parsed_latitude = None
    parsed_longitude = None

    if latitude not in [
        None,
        "",
    ]:
        try:
            parsed_latitude = Decimal(
                str(latitude)
            )
        except InvalidOperation:
            return JsonResponse(
                {
                    "message":
                        "Invalid latitude."
                },
                status=400,
            )

    if longitude not in [
        None,
        "",
    ]:
        try:
            parsed_longitude = Decimal(
                str(longitude)
            )
        except InvalidOperation:
            return JsonResponse(
                {
                    "message":
                        "Invalid longitude."
                },
                status=400,
            )

    # =====================================================
    # AMENITIES
    # =====================================================

    amenity_ids_raw = data.get(
        "amenity_ids",
        "[]",
    )

    try:
        if isinstance(
            amenity_ids_raw,
            str,
        ):
            amenity_ids = json.loads(
                amenity_ids_raw
            )
        else:
            amenity_ids = (
                amenity_ids_raw
            )

    except Exception:
        return JsonResponse(
            {
                "message":
                    "Invalid amenity_ids."
            },
            status=400,
        )

    amenities = Amenity.objects.filter(
        id__in=amenity_ids
    )

    if (
        len(amenity_ids)
        != amenities.count()
    ):
        return JsonResponse(
            {
                "message":
                    "One or more selected amenities are invalid."
            },
            status=400,
        )

    # =====================================================
    # IMAGES
    # =====================================================

    images = request.FILES.getlist(
        "images"
    )

    if not images:
        return JsonResponse(
            {
                "message":
                    "At least one property image is required."
            },
            status=400,
        )

    # =====================================================
    # CREATE
    # =====================================================

    try:
        with transaction.atomic():

            property_obj = (
                Property.objects.create(
                    organization=
                        organization,

                    portifolio=
                        portfolio,

                    created_by=
                        user,

                    property_code=
                        property_code,

                    name=
                        name,

                    property_type=
                        property_type,

                    ownership_type=
                        ownership_type,

                    code=
                        code,

                    description=
                        description,

                    address=
                        address,

                    city=
                        city,

                    county=
                        county,

                    country=
                        country,

                    postal_code=(
                        postal_code
                        or None
                    ),

                    latitude=
                        parsed_latitude,

                    longitude=
                        parsed_longitude,

                    year_built=
                        parsed_year,

                    total_land_area=
                        parsed_land_area,

                    status=
                        "active",
                )
            )

            # =========================================
            # AMENITIES
            # =========================================

            PropertyAmenity.objects.bulk_create(
                [
                    PropertyAmenity(
                        property=
                            property_obj,
                        amenity=
                            amenity,
                    )
                    for amenity
                    in amenities
                ]
            )

            # =========================================
            # IMAGES
            # =========================================

            uploaded_images = []

            for index, image in enumerate(
                images
            ):
                upload = (
                    cloudinary.uploader.upload(
                        image,
                        folder=(
                            f"unit/properties/"
                            f"{property_obj.id}"
                        ),
                        resource_type="image",
                    )
                )

                property_image = (
                    PropertyImage.objects.create(
                        property=
                            property_obj,

                        image_url=
                            upload[
                                "secure_url"
                            ],

                        public_id=
                            upload.get(
                                "public_id"
                            ),

                        is_cover=(
                            index == 0
                        ),
                    )
                )

                uploaded_images.append(
                    {
                        "id":
                            property_image.id,

                        "image_url":
                            property_image.image_url,

                        "is_cover":
                            property_image.is_cover,
                    }
                )

        return JsonResponse(
            {
                "message":
                    "Property created successfully.",

                "property": {
                    "id":
                        property_obj.id,

                    "property_code":
                        property_obj.property_code,

                    "code":
                        property_obj.code,

                    "name":
                        property_obj.name,

                    "property_type":
                        property_obj.property_type,

                    "ownership_type":
                        property_obj.ownership_type,

                    "portfolio": {
                        "id":
                            portfolio.id,

                        "name":
                            portfolio.name,
                    },

                    "address":
                        property_obj.address,

                    "city":
                        property_obj.city,

                    "county":
                        property_obj.county,

                    "country":
                        property_obj.country,

                    "postal_code":
                        property_obj.postal_code,

                    "year_built":
                        property_obj.year_built,

                    "total_land_area": (
                        str(
                            property_obj
                            .total_land_area
                        )
                        if property_obj
                        .total_land_area
                        is not None
                        else None
                    ),

                    "amenities": [
                        {
                            "id":
                                amenity.id,

                            "name":
                                amenity.name,
                        }
                        for amenity
                        in amenities
                    ],

                    "images":
                        uploaded_images,
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE PROPERTY ERROR:",
            str(error)
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create property.",

                "error":
                    str(error),
            },
            status=500,
        )





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_property_details(
    request,
    property_id,
):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # ORGANIZATION REQUIRED
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
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

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization=
                    organization,

                user=user,

                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # ROLE ACCESS
    # =====================================================

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
        "owner",
        "landlord",
        "property_manager",
        "caretaker",
        "accountant",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view this property."
            },
            status=403,
        )

    # =====================================================
    # PROPERTY
    # =====================================================

    try:
        property_obj = (
            Property.objects
            .select_related(
                "organization",
                "portifolio",
                "created_by",
            )
            .get(
                id=property_id,

                organization=
                    organization,
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
    # UNITS
    # =====================================================

    units = (
        Unit.objects
        .filter(
            property=
                property_obj
        )
        .select_related(
            "building",
            "floor",
        )
        .order_by(
            "building__name",
            "floor__floor_number",
            "name",
        )
    )

    total_units = (
        units.count()
    )

    occupied_units = (
        units
        .filter(
            status="occupied"
        )
        .count()
    )

    available_units = (
        units
        .filter(
            status="available"
        )
        .count()
    )

    maintenance_units = (
        units
        .filter(
            status=
                "under_maintenance"
        )
        .count()
    )

    occupancy_rate = 0

    if total_units > 0:
        occupancy_rate = round(
            (
                occupied_units /
                total_units
            ) * 100
        )

    # =====================================================
    # CURRENT MONTH
    # =====================================================

    today = (
        timezone.localdate()
    )

    month_start = (
        today.replace(
            day=1
        )
    )

    if month_start.month == 12:
        next_month = (
            month_start.replace(
                year=
                    month_start.year + 1,

                month=1,
            )
        )

    else:
        next_month = (
            month_start.replace(
                month=
                    month_start.month + 1
            )
        )

    # =====================================================
    # RENT INVOICES
    # =====================================================

    rent_invoices = (
        Invoice.objects
        .filter(
            organization=
                organization,

            property=
                property_obj,

            invoice_type="rent",

            issue_date__gte=
                month_start,

            issue_date__lt=
                next_month,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
    )

    # =====================================================
    # EXPECTED RENT
    # =====================================================

    rent_expected = (
        rent_invoices
        .aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # OUTSTANDING
    # =====================================================

    outstanding = (
        rent_invoices
        .filter(
            balance__gt=0
        )
        .aggregate(
            total=Sum(
                "balance"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # RENT COLLECTED
    # =====================================================

    rent_collected = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            invoice__property=
                property_obj,

            invoice__invoice_type=
                "rent",

            invoice__issue_date__gte=
                month_start,

            invoice__issue_date__lt=
                next_month,

            payment__status=
                "completed",
        )
        .aggregate(
            total=Sum(
                "allocated_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # =====================================================
    # COLLECTION RATE
    # =====================================================

    collection_rate = 0

    if rent_expected > 0:
        collection_rate = round(
            (
                rent_collected /
                rent_expected
            ) * 100
        )

    # =====================================================
    # AMENITIES
    # =====================================================

    property_amenities = (
        PropertyAmenity.objects
        .filter(
            property=
                property_obj
        )
        .select_related(
            "amenity"
        )
        .order_by(
            "amenity__name"
        )
    )

    amenities_data = []

    for property_amenity in (
        property_amenities
    ):
        amenities_data.append(
            {
                "id":
                    property_amenity
                    .amenity.id,

                "name":
                    property_amenity
                    .amenity.name,

                "description":
                    property_amenity
                    .amenity
                    .description,

                "amenity_type":
                    property_amenity
                    .amenity
                    .amenity_type,

                "notes":
                    property_amenity
                    .notes,
            }
        )

    # =====================================================
    # BUILDINGS
    # =====================================================

    buildings = (
        Building.objects
        .filter(
            property=
                property_obj
        )
        .order_by(
            "name"
        )
    )

    buildings_data = []

    for building in buildings:

        building_units = (
            units.filter(
                building=
                    building
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

                "description":
                    building.description,

                "year_built":
                    building.year_built,

                "number_of_floors":
                    building.number_of_floors,

                "status":
                    building.status,

                "units_count":
                    building_units.count(),

                "occupied_units":
                    building_units
                    .filter(
                        status=
                            "occupied"
                    )
                    .count(),

                "available_units":
                    building_units
                    .filter(
                        status=
                            "available"
                    )
                    .count(),

                "maintenance_units":
                    building_units
                    .filter(
                        status=
                            "under_maintenance"
                    )
                    .count(),
            }
        )

    # =====================================================
    # UNITS RESPONSE
    # =====================================================

    units_data = []

    for unit in units:

        units_data.append(
            {
                "id":
                    unit.id,

                "name":
                    unit.name,

                "unit_code":
                    unit.unit_code,

                "unit_type":
                    unit.unit_type,

                "bedrooms":
                    unit.bedrooms,

                "bathrooms":
                    unit.bathrooms,

                "square_footage": (
                    float(
                        unit.square_footage
                    )
                    if unit.square_footage
                    is not None
                    else None
                ),

                "monthly_rent":
                    float(
                        unit.monthly_rent
                    ),

                "deposit_amount":
                    float(
                        unit.deposit_amount
                    ),

                "service_charge": (
                    float(
                        unit.service_charge
                    )
                    if unit.service_charge
                    is not None
                    else None
                ),

                "status":
                    unit.status,

                "building": {
                    "id":
                        unit.building.id,

                    "name":
                        unit.building.name,
                },

                "floor": {
                    "id":
                        unit.floor.id,

                    "name":
                        unit.floor.name,

                    "floor_number":
                        unit.floor
                        .floor_number,
                },
            }
        )

    # =====================================================
    # PROPERTY IMAGES
    #
    # This uses the PropertyImage model we added for your
    # image upload feature. If you named it differently,
    # change this section to that model.
    # =====================================================

    images_data = []

    try:
        property_images = (
            property_obj.images
            .all()
            .order_by(
                "-is_cover",
                "created_at",
            )
        )

        for image in property_images:
            images_data.append(
                {
                    "id":
                        image.id,

                    "image_url":
                        image.image_url,

                    "is_cover":
                        image.is_cover,
                }
            )

    except Exception:
        images_data = []

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "property": {
                "id":
                    property_obj.id,

                "organization_id":
                    organization.id,

                "property_code":
                    property_obj
                    .property_code,

                "code":
                    property_obj.code,

                "name":
                    property_obj.name,

                "property_type":
                    property_obj
                    .property_type,

                "property_type_display":
                    property_obj
                    .get_property_type_display(),

                "ownership_type":
                    property_obj
                    .ownership_type,

                "description":
                    property_obj
                    .description,

                "status":
                    property_obj.status,

                # -----------------------------
                # Portfolio
                # -----------------------------

                "portfolio": {
                    "id":
                        property_obj
                        .portifolio.id,

                    "name":
                        property_obj
                        .portifolio.name,

                    "code":
                        property_obj
                        .portifolio.code,
                },

                # -----------------------------
                # Location
                # -----------------------------

                "address":
                    property_obj.address,

                "city":
                    property_obj.city,

                "county":
                    property_obj.county,

                "country":
                    property_obj.country,

                "postal_code":
                    property_obj
                    .postal_code,

                "latitude": (
                    str(
                        property_obj
                        .latitude
                    )
                    if property_obj.latitude
                    is not None
                    else None
                ),

                "longitude": (
                    str(
                        property_obj
                        .longitude
                    )
                    if property_obj.longitude
                    is not None
                    else None
                ),

                # -----------------------------
                # Property information
                # -----------------------------

                "year_built":
                    property_obj
                    .year_built,

                "total_land_area": (
                    float(
                        property_obj
                        .total_land_area
                    )
                    if property_obj
                    .total_land_area
                    is not None
                    else None
                ),

                # -----------------------------
                # Statistics
                # -----------------------------

                "statistics": {
                    "buildings":
                        buildings.count(),

                    "total_units":
                        total_units,

                    "occupied_units":
                        occupied_units,

                    "available_units":
                        available_units,

                    "maintenance_units":
                        maintenance_units,

                    "occupancy_rate":
                        occupancy_rate,
                },

                # -----------------------------
                # Finance
                # -----------------------------

                "finance": {
                    "rent_expected":
                        float(
                            rent_expected
                        ),

                    "rent_collected":
                        float(
                            rent_collected
                        ),

                    "outstanding":
                        float(
                            outstanding
                        ),

                    "collection_rate":
                        collection_rate,
                },

                "created_at":
                    property_obj
                    .created_at
                    .isoformat(),

                "updated_at":
                    property_obj
                    .updated_at
                    .isoformat(),
            },

            "images":
                images_data,

            "amenities":
                amenities_data,

            "buildings":
                buildings_data,

            "units":
                units_data,
        },
        status=200,
    )






@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_owner_properties(request):
    user = request.user

    organization_id = (
        request.GET.get(
            "organization_id"
        )
    )

    # =====================================================
    # ORGANIZATION ID
    # =====================================================

    if not organization_id:
        return JsonResponse(
            {
                "message":
                    "organization_id is required."
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

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization=
                    organization,

                user=user,

                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return JsonResponse(
            {
                "message":
                    "You do not have access to this organization."
            },
            status=403,
        )

    # =====================================================
    # OWNER ACCESS
    # =====================================================

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
        "owner",
        "landlord",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view owner properties."
            },
            status=403,
        )

    # =====================================================
    # CURRENT MONTH
    # =====================================================

    today = (
        timezone.localdate()
    )

    month_start = (
        today.replace(
            day=1
        )
    )

    if month_start.month == 12:
        next_month = (
            month_start.replace(
                year=
                    month_start.year + 1,

                month=1,
            )
        )

    else:
        next_month = (
            month_start.replace(
                month=
                    month_start.month + 1
            )
        )

    # =====================================================
    # PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=
                organization
        )
        .select_related(
            "portifolio"
        )
        .order_by(
            "name"
        )
    )

    # =====================================================
    # PORTFOLIOS
    # =====================================================

    portfolios = (
        Portifolio.objects
        .filter(
            organization=
                organization
        )
        .order_by(
            "name"
        )
    )

    portfolios_data = [
        {
            "id":
                portfolio.id,

            "name":
                portfolio.name,

            "code":
                portfolio.code,

            "status":
                portfolio.status,
        }
        for portfolio
        in portfolios
    ]

    # =====================================================
    # ORGANIZATION SUMMARY
    # =====================================================

    organization_units = (
        Unit.objects
        .filter(
            property__organization=
                organization
        )
    )

    total_units = (
        organization_units.count()
    )

    occupied_units = (
        organization_units
        .filter(
            status="occupied"
        )
        .count()
    )

    available_units = (
        organization_units
        .filter(
            status="available"
        )
        .count()
    )

    maintenance_units = (
        organization_units
        .filter(
            status=
                "under_maintenance"
        )
        .count()
    )

    occupancy_rate = 0

    if total_units > 0:
        occupancy_rate = round(
            (
                occupied_units /
                total_units
            ) * 100
        )

    # =====================================================
    # CURRENT MONTH ORGANIZATION RENT
    # =====================================================

    organization_invoices = (
        Invoice.objects
        .filter(
            organization=
                organization,

            invoice_type="rent",

            issue_date__gte=
                month_start,

            issue_date__lt=
                next_month,
        )
        .exclude(
            status__in=[
                "cancelled",
                "void",
            ]
        )
    )

    rent_expected = (
        organization_invoices
        .aggregate(
            total=Sum(
                "total_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    outstanding = (
        organization_invoices
        .filter(
            balance__gt=0
        )
        .aggregate(
            total=Sum(
                "balance"
            )
        )["total"]
        or Decimal("0.00")
    )

    rent_collected = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            invoice__invoice_type=
                "rent",

            invoice__issue_date__gte=
                month_start,

            invoice__issue_date__lt=
                next_month,

            payment__status=
                "completed",
        )
        .aggregate(
            total=Sum(
                "allocated_amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    collection_rate = 0

    if rent_expected > 0:
        collection_rate = round(
            (
                rent_collected /
                rent_expected
            ) * 100
        )

    # =====================================================
    # PROPERTY RESPONSE
    # =====================================================

    properties_data = []

    for property_obj in properties:

        property_units = (
            Unit.objects
            .filter(
                property=
                    property_obj
            )
        )

        property_total_units = (
            property_units.count()
        )

        property_occupied = (
            property_units
            .filter(
                status="occupied"
            )
            .count()
        )

        property_available = (
            property_units
            .filter(
                status="available"
            )
            .count()
        )

        property_maintenance = (
            property_units
            .filter(
                status=
                    "under_maintenance"
            )
            .count()
        )

        property_occupancy_rate = 0

        if property_total_units > 0:
            property_occupancy_rate = round(
                (
                    property_occupied /
                    property_total_units
                ) * 100
            )

        # =================================================
        # PROPERTY RENT
        # =================================================

        property_invoices = (
            Invoice.objects
            .filter(
                organization=
                    organization,

                property=
                    property_obj,

                invoice_type=
                    "rent",

                issue_date__gte=
                    month_start,

                issue_date__lt=
                    next_month,
            )
            .exclude(
                status__in=[
                    "cancelled",
                    "void",
                ]
            )
        )

        property_expected = (
            property_invoices
            .aggregate(
                total=Sum(
                    "total_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_outstanding = (
            property_invoices
            .filter(
                balance__gt=0
            )
            .aggregate(
                total=Sum(
                    "balance"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_collected = (
            PaymentAllocation.objects
            .filter(
                invoice__organization=
                    organization,

                invoice__property=
                    property_obj,

                invoice__invoice_type=
                    "rent",

                invoice__issue_date__gte=
                    month_start,

                invoice__issue_date__lt=
                    next_month,

                payment__status=
                    "completed",
            )
            .aggregate(
                total=Sum(
                    "allocated_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        property_collection_rate = 0

        if property_expected > 0:
            property_collection_rate = round(
                (
                    property_collected /
                    property_expected
                ) * 100
            )

        # =================================================
        # IMAGE
        # =================================================

        cover_image_url = None

        try:
            cover_image = (
                property_obj.images
                .filter(
                    is_cover=True
                )
                .first()
            )

            if not cover_image:
                cover_image = (
                    property_obj.images
                    .all()
                    .first()
                )

            if cover_image:
                cover_image_url = (
                    cover_image
                    .image_url
                )

        except Exception:
            cover_image_url = None

        # =================================================
        # RESPONSE ITEM
        # =================================================

        properties_data.append(
            {
                "id":
                    property_obj.id,

                "property_code":
                    property_obj
                    .property_code,

                "code":
                    property_obj.code,

                "name":
                    property_obj.name,

                "property_type":
                    property_obj
                    .property_type,

                "property_type_display":
                    property_obj
                    .get_property_type_display(),

                "ownership_type":
                    property_obj
                    .ownership_type,

                "description":
                    property_obj
                    .description,

                "status":
                    property_obj.status,

                # -----------------------------
                # Portfolio
                # -----------------------------

                "portfolio": {
                    "id":
                        property_obj
                        .portifolio.id,

                    "name":
                        property_obj
                        .portifolio.name,

                    "code":
                        property_obj
                        .portifolio.code,
                },

                # -----------------------------
                # Location
                # -----------------------------

                "address":
                    property_obj.address,

                "city":
                    property_obj.city,

                "county":
                    property_obj.county,

                "country":
                    property_obj.country,

                # -----------------------------
                # Units
                # -----------------------------

                "total_units":
                    property_total_units,

                "occupied_units":
                    property_occupied,

                "available_units":
                    property_available,

                "maintenance_units":
                    property_maintenance,

                "occupancy_rate":
                    property_occupancy_rate,

                # -----------------------------
                # Finance
                # -----------------------------

                "rent_expected":
                    float(
                        property_expected
                    ),

                "rent_collected":
                    float(
                        property_collected
                    ),

                "outstanding":
                    float(
                        property_outstanding
                    ),

                "collection_rate":
                    property_collection_rate,

                # -----------------------------
                # Image
                # -----------------------------

                "cover_image":
                    cover_image_url,

                "created_at":
                    property_obj
                    .created_at
                    .isoformat(),
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "organization": {
                "id":
                    organization.id,

                "name":
                    organization.name,
            },

            "summary": {
                "properties":
                    properties.count(),

                "units":
                    total_units,

                "occupied_units":
                    occupied_units,

                "available_units":
                    available_units,

                "maintenance_units":
                    maintenance_units,

                "occupancy_rate":
                    occupancy_rate,

                "rent_expected":
                    float(
                        rent_expected
                    ),

                "rent_collected":
                    float(
                        rent_collected
                    ),

                "outstanding":
                    float(
                        outstanding
                    ),

                "collection_rate":
                    collection_rate,
            },

            "portfolios":
                portfolios_data,

            "properties":
                properties_data,

            "count":
                len(
                    properties_data
                ),
        },
        status=200,
    )