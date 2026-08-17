from .common_imports import *

def can_manage_property_structure(
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
                organization=
                    organization,

                user=user,

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
def property_structure(
    request,
    property_id,
):
    organization_id = (
        request.GET.get(
            "organization_id"
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

    if not can_manage_property_structure(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
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
            property=
                property_obj
        )
        .prefetch_related(
            "floors",
            "floors__units",
        )
        .order_by(
            "name"
        )
    )

    building_data = []

    total_floors = 0

    for building in buildings:
        floors = (
            building.floors
            .all()
            .order_by(
                "floor_number"
            )
        )

        total_floors += (
            floors.count()
        )

        floor_data = []

        for floor in floors:
            floor_data.append(
                {
                    "id":
                        floor.id,

                    "name":
                        floor.name,

                    "floor_code":
                        floor.floor_code,

                    "floor_number":
                        floor.floor_number,

                    "status":
                        floor.status,

                    "units_count":
                        floor.units.count(),
                }
            )

        building_data.append(
            {
                "id":
                    building.id,

                "name":
                    building.name,

                "building_code":
                    building.building_code,

                "description":
                    building.description,

                "number_of_floors":
                    building.number_of_floors,

                "status":
                    building.status,

                "floors_count":
                    floors.count(),

                "units_count":
                    Unit.objects.filter(
                        building=
                            building
                    ).count(),

                "floors":
                    floor_data,
            }
        )

    return JsonResponse(
        {
            "property": {
                "id":
                    property_obj.id,

                "name":
                    property_obj.name,

                "buildings_count":
                    buildings.count(),

                "floors_count":
                    total_floors,

                "units_count":
                    Unit.objects.filter(
                        property=
                            property_obj
                    ).count(),
            },

            "buildings":
                building_data,
        },
        status=200,
    )



from django.db import transaction


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_building(request):
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

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    building_code = str(
        data.get(
            "building_code",
            ""
        )
    ).strip().upper()

    description = str(
        data.get(
            "description",
            ""
        )
        or ""
    ).strip()

    year_built = (
        data.get(
            "year_built"
        )
    )

    number_of_floors = (
        data.get(
            "number_of_floors"
        )
    )

    create_floors = (
        data.get(
            "create_floors",
            False
        )
    )

    floor_prefix = str(
        data.get(
            "floor_prefix",
            "Floor"
        )
    ).strip()

    if (
        not organization_id
        or not property_id
        or not name
        or not building_code
        or not number_of_floors
    ):
        return JsonResponse(
            {
                "message":
                    "Missing required fields."
            },
            status=400,
        )

    try:
        number_of_floors = int(
            number_of_floors
        )

    except (
        ValueError,
        TypeError,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid number of floors."
            },
            status=400,
        )

    if number_of_floors < 1:
        return JsonResponse(
            {
                "message":
                    "A building must have at least one floor."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
            )
        )

        property_obj = (
            Property.objects.get(
                id=
                    property_id,

                organization=
                    organization,
            )
        )

    except (
        Organization.DoesNotExist,
        Property.DoesNotExist,
    ):
        return JsonResponse(
            {
                "message":
                    "Organization or property not found."
            },
            status=404,
        )

    if not can_manage_property_structure(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
            },
            status=403,
        )

    if (
        Building.objects
        .filter(
            building_code__iexact=
                building_code
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "Building code already exists."
            },
            status=400,
        )

    try:
        with transaction.atomic():

            building = (
                Building.objects.create(
                    property=
                        property_obj,

                    name=
                        name,

                    building_code=
                        building_code,

                    description=
                        description,

                    year_built=
                        year_built,

                    number_of_floors=
                        number_of_floors,

                    status=
                        "active",
                )
            )

            floors = []

            if create_floors:
                for number in range(
                    1,
                    number_of_floors + 1
                ):

                    floor = (
                        Floor.objects.create(
                            building=
                                building,

                            name=
                                f"{floor_prefix} {number}",

                            floor_code=
                                f"{building_code}-F{number}",

                            floor_number=
                                number,

                            status=
                                "active",
                        )
                    )

                    floors.append(
                        floor
                    )

        return JsonResponse(
            {
                "message":
                    "Building created successfully.",

                "building": {
                    "id":
                        building.id,

                    "name":
                        building.name,

                    "building_code":
                        building.building_code,

                    "floors_created":
                        len(
                            floors
                        ),
                },
            },
            status=201,
        )

    except Exception as error:
        return JsonResponse(
            {
                "message":
                    "Unable to create building.",

                "error":
                    str(error),
            },
            status=500,
        )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_floor(request):
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

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    floor_code = str(
        data.get(
            "floor_code",
            ""
        )
    ).strip().upper()

    floor_number = (
        data.get(
            "floor_number"
        )
    )

    description = str(
        data.get(
            "description",
            ""
        )
        or ""
    ).strip()

    if (
        not organization_id
        or not property_id
        or not building_id
        or not name
        or not floor_code
        or floor_number is None
    ):
        return JsonResponse(
            {
                "message":
                    "Missing required fields."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
            )
        )

        property_obj = (
            Property.objects.get(
                id=
                    property_id,

                organization=
                    organization,
            )
        )

        building = (
            Building.objects.get(
                id=
                    building_id,

                property=
                    property_obj,
            )
        )

    except (
        Organization.DoesNotExist,
        Property.DoesNotExist,
        Building.DoesNotExist,
    ):
        return JsonResponse(
            {
                "message":
                    "Invalid organization, property or building."
            },
            status=404,
        )

    if not can_manage_property_structure(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
            },
            status=403,
        )

    if Floor.objects.filter(
        floor_code__iexact=
            floor_code
    ).exists():
        return JsonResponse(
            {
                "message":
                    "Floor code already exists."
            },
            status=400,
        )

    floor = (
        Floor.objects.create(
            building=
                building,

            name=
                name,

            floor_code=
                floor_code,

            description=
                description,

            floor_number=
                floor_number,

            status=
                "active",
        )
    )

    return JsonResponse(
        {
            "message":
                "Floor created successfully.",

            "floor": {
                "id":
                    floor.id,

                "name":
                    floor.name,

                "floor_code":
                    floor.floor_code,

                "floor_number":
                    floor.floor_number,
            },
        },
        status=201,
    )



from django.db.models import Q


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_amenities(request):
    organization_id = (
        request.GET.get(
            "organization_id"
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

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
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

    if not can_manage_property_structure(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission."
            },
            status=403,
        )

    amenities = (
        Amenity.objects
        .filter(
            Q(
                organization=
                    organization
            )
            |
            Q(
                organization__isnull=
                    True,

                is_system=True,
            )
        )
        .order_by(
            "name"
        )
    )

    return JsonResponse(
        {
            "amenities": [
                {
                    "id":
                        amenity.id,

                    "name":
                        amenity.name,

                    "description":
                        amenity.description,

                    "amenity_type":
                        amenity.amenity_type,

                    "is_system":
                        amenity.is_system,

                    "is_active":
                        amenity.is_active,
                }

                for amenity
                in amenities
            ]
        },
        status=200,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_amenity(request):
    data = request.data

    organization_id = (
        data.get(
            "organization_id"
        )
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    amenity_type = str(
        data.get(
            "amenity_type",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
        or ""
    ).strip()

    if (
        not organization_id
        or not name
        or not amenity_type
    ):
        return JsonResponse(
            {
                "message":
                    "Organization, name and amenity type are required."
            },
            status=400,
        )

    try:
        organization = (
            Organization.objects.get(
                id=
                    organization_id
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

    if not can_manage_property_structure(
        request.user,
        organization,
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to create amenities."
            },
            status=403,
        )

    if (
        Amenity.objects
        .filter(
            organization=
                organization,

            name__iexact=
                name,
        )
        .exists()
    ):
        return JsonResponse(
            {
                "message":
                    "This amenity already exists."
            },
            status=400,
        )

    amenity = (
        Amenity.objects.create(
            organization=
                organization,

            name=
                name,

            amenity_type=
                amenity_type,

            description=
                description,

            is_system=
                False,

            is_active=
                True,
        )
    )

    return JsonResponse(
        {
            "message":
                "Amenity created successfully.",

            "amenity": {
                "id":
                    amenity.id,

                "name":
                    amenity.name,

                "amenity_type":
                    amenity.amenity_type,

                "description":
                    amenity.description,

                "is_active":
                    amenity.is_active,
            },
        },
        status=201,
    )