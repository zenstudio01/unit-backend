from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_owner_portfolios(request):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
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
    # ROLE
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
                    "You do not have permission to view portfolios."
            },
            status=403,
        )

    # =====================================================
    # CURRENT MONTH
    # =====================================================

    today = timezone.localdate()

    month_start = (
        today.replace(
            day=1
        )
    )

    if month_start.month == 12:
        next_month = (
            month_start.replace(
                year=
                    month_start.year +
                    1,

                month=1,
            )
        )

    else:
        next_month = (
            month_start.replace(
                month=
                    month_start.month +
                    1
            )
        )

    # =====================================================
    # PORTFOLIOS
    # =====================================================

    portfolios = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            status="active",
        )
        .order_by(
            "name"
        )
    )

    portfolio_data = []

    organization_properties = 0
    organization_units = 0
    organization_occupied = 0
    organization_vacant = 0

    organization_collected = (
        Decimal("0.00")
    )

    organization_outstanding = (
        Decimal("0.00")
    )

    # =====================================================
    # EACH PORTFOLIO
    # =====================================================

    for portfolio in portfolios:

        # -------------------------------------------------
        # Properties
        #
        # Your Property model currently uses:
        # portifolio = ForeignKey(...)
        # -------------------------------------------------

        properties = (
            Property.objects
            .filter(
                organization=
                    organization,

                portifolio=
                    portfolio,

                status="active",
            )
        )

        properties_count = (
            properties.count()
        )

        # -------------------------------------------------
        # Units
        # -------------------------------------------------

        units = (
            Unit.objects
            .filter(
                property__in=
                    properties
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

        vacant_units = (
            units
            .filter(
                status="vacant"
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

        # -------------------------------------------------
        # Current month rent invoices
        # -------------------------------------------------

        rent_invoices = (
            Invoice.objects
            .filter(
                organization=
                    organization,

                property__in=
                    properties,

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

        # -------------------------------------------------
        # Expected rent
        # -------------------------------------------------

        rent_expected = (
            rent_invoices
            .aggregate(
                total=Sum(
                    "total_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        # -------------------------------------------------
        # Outstanding
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Collected rent
        # -------------------------------------------------

        rent_collected = (
            PaymentAllocation.objects
            .filter(
                invoice__organization=
                    organization,

                invoice__property__in=
                    properties,

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

        # -------------------------------------------------
        # Add to organization summary
        # -------------------------------------------------

        organization_properties += (
            properties_count
        )

        organization_units += (
            total_units
        )

        organization_occupied += (
            occupied_units
        )

        organization_vacant += (
            vacant_units
        )

        organization_collected += (
            rent_collected
        )

        organization_outstanding += (
            outstanding
        )

        # -------------------------------------------------
        # Portfolio object
        # -------------------------------------------------

        portfolio_data.append(
            {
                "id":
                    portfolio.id,

                "name":
                    portfolio.name,

                "code":
                    portfolio.code,

                "description":
                    portfolio.description,

                "status":
                    portfolio.status,

                "properties_count":
                    properties_count,

                "total_units":
                    total_units,

                "occupied_units":
                    occupied_units,

                "vacant_units":
                    vacant_units,

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

                "created_at": (
                    portfolio
                    .created_at
                    .isoformat()
                    if getattr(
                        portfolio,
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

    organization_occupancy = 0

    if organization_units > 0:
        organization_occupancy = round(
            (
                organization_occupied /
                organization_units
            ) * 100
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
                "portfolios":
                    portfolios.count(),

                "properties":
                    organization_properties,

                "units":
                    organization_units,

                "occupied_units":
                    organization_occupied,

                "vacant_units":
                    organization_vacant,

                "occupancy_rate":
                    organization_occupancy,

                "rent_collected":
                    float(
                        organization_collected
                    ),

                "outstanding":
                    float(
                        organization_outstanding
                    ),
            },

            "portfolios":
                portfolio_data,

            "count":
                len(
                    portfolio_data
                ),
        },
        status=200,
    )





@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_portfolio(request):
    user = request.user
    data = request.data

    # =====================================================
    # DATA
    # =====================================================

    organization_id = data.get(
        "organization_id"
    )

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    code = str(
        data.get(
            "code",
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

    # =====================================================
    # VALIDATION
    # =====================================================

    missing_fields = []

    if not organization_id:
        missing_fields.append(
            "organization_id"
        )

    if not name:
        missing_fields.append(
            "name"
        )

    if not code:
        missing_fields.append(
            "code"
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

    if len(name) < 2:
        return JsonResponse(
            {
                "message":
                    "Portfolio name is too short."
            },
            status=400,
        )

    if len(code) < 2:
        return JsonResponse(
            {
                "message":
                    "Portfolio code is too short."
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
    # PERMISSION
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
                    "You do not have permission to create portfolios."
            },
            status=403,
        )

    # =====================================================
    # DUPLICATE NAME
    # =====================================================

    name_exists = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            name__iexact=
                name,
        )
        .exists()
    )

    if name_exists:
        return JsonResponse(
            {
                "message":
                    "A portfolio with this name already exists."
            },
            status=400,
        )

    # =====================================================
    # DUPLICATE CODE
    # =====================================================

    code_exists = (
        Portifolio.objects
        .filter(
            organization=
                organization,

            code__iexact=
                code,
        )
        .exists()
    )

    if code_exists:
        return JsonResponse(
            {
                "message":
                    "A portfolio with this code already exists."
            },
            status=400,
        )

    # =====================================================
    # CREATE PORTFOLIO
    # =====================================================

    try:
        with transaction.atomic():

            portfolio = (
                Portifolio.objects.create(
                    organization=
                        organization,

                    name=
                        name,

                    code=
                        code,

                    description=
                        description,

                    status=
                        "active",
                )
            )

        return JsonResponse(
            {
                "message":
                    "Portfolio created successfully.",

                "portfolio": {
                    "id":
                        portfolio.id,

                    "organization_id":
                        organization.id,

                    "name":
                        portfolio.name,

                    "code":
                        portfolio.code,

                    "description":
                        portfolio.description,

                    "status":
                        portfolio.status,

                    "created_at": (
                        portfolio
                        .created_at
                        .isoformat()
                        if getattr(
                            portfolio,
                            "created_at",
                            None,
                        )
                        else None
                    ),
                },
            },
            status=201,
        )

    except Exception as error:
        print(
            "CREATE PORTFOLIO ERROR:",
            str(error)
        )

        return JsonResponse(
            {
                "message":
                    "Unable to create portfolio.",

                "error":
                    str(error),
            },
            status=500,
        )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_portfolio_details(
    request,
    portfolio_id,
):
    user = request.user

    organization_id = request.GET.get(
        "organization_id"
    )

    # =====================================================
    # ORGANIZATION
    # =====================================================

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
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return JsonResponse(
            {
                "message":
                    "You do not have permission to view this portfolio."
            },
            status=403,
        )

    # =====================================================
    # PORTFOLIO
    # =====================================================

    try:
        portfolio = (
            Portifolio.objects.get(
                id=portfolio_id,

                organization=
                    organization,
            )
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
    # PROPERTIES
    # =====================================================

    properties = (
        Property.objects
        .filter(
            organization=
                organization,

            portifolio=
                portfolio,
        )
        .order_by(
            "name"
        )
    )

    active_properties = (
        properties.filter(
            status="active"
        )
    )

    properties_count = (
        active_properties.count()
    )

    # =====================================================
    # UNITS
    # =====================================================

    units = (
        Unit.objects
        .filter(
            property__in=
                active_properties
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

    vacant_units = (
        units
        .filter(
            status="vacant"
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

    today = timezone.localdate()

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
    # PORTFOLIO RENT INVOICES
    # =====================================================

    rent_invoices = (
        Invoice.objects
        .filter(
            organization=
                organization,

            property__in=
                active_properties,

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
    # COLLECTED RENT
    # =====================================================

    rent_collected = (
        PaymentAllocation.objects
        .filter(
            invoice__organization=
                organization,

            invoice__property__in=
                active_properties,

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
    # PROPERTY LIST
    # =====================================================

    property_data = []

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

        property_occupied_units = (
            property_units
            .filter(
                status="occupied"
            )
            .count()
        )

        property_vacant_units = (
            property_units
            .filter(
                status="vacant"
            )
            .count()
        )

        property_occupancy = 0

        if property_total_units > 0:
            property_occupancy = round(
                (
                    property_occupied_units /
                    property_total_units
                ) * 100
            )

        # ---------------------------------------------
        # PROPERTY RENT INVOICES
        # ---------------------------------------------

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

        # ---------------------------------------------
        # COVER IMAGE
        # ---------------------------------------------

        cover_image = (
            PropertyImage.objects
            .filter(
                property=
                    property_obj,

                is_cover=True,
            )
            .first()
        )

        if not cover_image:
            cover_image = (
                PropertyImage.objects
                .filter(
                    property=
                        property_obj
                )
                .first()
            )

        # ---------------------------------------------
        # LOCATION
        # ---------------------------------------------

        location = ", ".join(
            filter(
                None,
                [
                    getattr(
                        property_obj,
                        "city",
                        "",
                    ),

                    getattr(
                        property_obj,
                        "county",
                        "",
                    ),
                ],
            )
        )

        property_data.append(
            {
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

                "location":
                    location,

                "city":
                    property_obj.city,

                "county":
                    property_obj.county,

                "country":
                    property_obj.country,

                "status":
                    property_obj.status,

                "total_units":
                    property_total_units,

                "occupied_units":
                    property_occupied_units,

                "vacant_units":
                    property_vacant_units,

                "occupancy_rate":
                    property_occupancy,

                "rent_collected":
                    float(
                        property_collected
                    ),

                "outstanding":
                    float(
                        property_outstanding
                    ),

                "cover_image": (
                    cover_image.image_url
                    if cover_image
                    else None
                ),
            }
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return JsonResponse(
        {
            "portfolio": {
                "id":
                    portfolio.id,

                "name":
                    portfolio.name,

                "code":
                    portfolio.code,

                "description":
                    portfolio.description,

                "status":
                    portfolio.status,

                "properties_count":
                    properties_count,

                "total_units":
                    total_units,

                "occupied_units":
                    occupied_units,

                "vacant_units":
                    vacant_units,

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

                "created_at": (
                    portfolio
                    .created_at
                    .isoformat()
                    if getattr(
                        portfolio,
                        "created_at",
                        None,
                    )
                    else None
                ),
            },

            "properties":
                property_data,

            "properties_count":
                len(
                    property_data
                ),
        },
        status=200,
    )