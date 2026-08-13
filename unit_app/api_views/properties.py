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