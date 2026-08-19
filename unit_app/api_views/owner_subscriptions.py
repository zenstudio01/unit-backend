from .common_imports import *



def get_subscription_manager(
    user,
    organization_id,
):
    try:
        organization = (
            Organization.objects.get(
                id=organization_id
            )
        )

    except Organization.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Organization not found."
                },
                status=404,
            ),
        )

    try:
        membership = (
            OrganizationMembership.objects
            .prefetch_related(
                "roles"
            )
            .get(
                organization=
                    organization,

                user=
                    user,

                is_active=
                    True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "You do not belong to this organization."
                },
                status=403,
            ),
        )

    roles = set(
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
    }

    if not roles.intersection(
        allowed_roles
    ):
        return (
            None,
            None,
            JsonResponse(
                {
                    "message":
                        "Only organization owners or administrators can manage subscriptions."
                },
                status=403,
            ),
        )

    return (
        organization,
        membership,
        None,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_packages(
    request
):
    packages = (
        SubscriptionPackage.objects
        .filter(
            is_active=True
        )
        .order_by(
            "sort_order",
            "monthly_price",
        )
    )

    results = []

    for package in packages:

        results.append(
            {
                "id":
                    package.id,

                "code":
                    package.code,

                "name":
                    package.name,

                "description":
                    package.description,

                "monthly_price":
                    str(
                        package.monthly_price
                    ),

                "yearly_price":
                    str(
                        package.yearly_price
                    ),

                "max_properties":
                    package.max_properties,

                "max_units":
                    package.max_units,

                "max_users":
                    package.max_users,

                "max_portfolios":
                    package.max_portfolios,

                "has_maintenance":
                    package.has_maintenance,

                "has_kaskazi_integration":
                    package.has_kaskazi_integration,

                "has_financial_reports":
                    package.has_financial_reports,

                "has_advanced_reports":
                    package.has_advanced_reports,

                "has_owner_portal":
                    package.has_owner_portal,

                "has_tenant_portal":
                    package.has_tenant_portal,

                "has_api_access":
                    package.has_api_access,
            }
        )

    return JsonResponse(
        {
            "count":
                len(results),

            "packages":
                results,
        },
        status=200,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_subscription(
    request
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

    (
        organization,
        membership,
        error_response,
    ) = get_subscription_manager(
        request.user,
        organization_id,
    )

    if error_response:
        return error_response

    try:
        subscription = (
            OrganizationSubscription.objects
            .select_related(
                "package"
            )
            .get(
                organization=
                    organization
            )
        )

    except OrganizationSubscription.DoesNotExist:

        return JsonResponse(
            {
                "subscription":
                    None,

                "message":
                    "Organization has no subscription."
            },
            status=200,
        )

    now = timezone.now()

    days_remaining = 0

    if (
        subscription.status ==
        "trial"
        and
        subscription.trial_end
    ):
        difference = (
            subscription.trial_end -
            now
        )

        days_remaining = max(
            difference.days,
            0,
        )

    elif (
        subscription.status ==
        "active"
        and
        subscription.current_period_end
    ):
        difference = (
            subscription.current_period_end -
            now
        )

        days_remaining = max(
            difference.days,
            0,
        )

    package = (
        subscription.package
    )

    return JsonResponse(
        {
            "subscription": {
                "id":
                    subscription.id,

                "status":
                    subscription.status,

                "billing_cycle":
                    subscription.billing_cycle,

                "days_remaining":
                    days_remaining,

                "trial_start": (
                    subscription.trial_start
                    .isoformat()
                    if subscription.trial_start
                    else None
                ),

                "trial_end": (
                    subscription.trial_end
                    .isoformat()
                    if subscription.trial_end
                    else None
                ),

                "trial_end_display": (
                    subscription.trial_end
                    .strftime(
                        "%d %b %Y"
                    )
                    if subscription.trial_end
                    else None
                ),

                "current_period_start": (
                    subscription
                    .current_period_start
                    .isoformat()
                    if subscription
                    .current_period_start
                    else None
                ),

                "current_period_end": (
                    subscription
                    .current_period_end
                    .isoformat()
                    if subscription
                    .current_period_end
                    else None
                ),

                "auto_renew":
                    subscription.auto_renew,

                "package": {
                    "id":
                        package.id,

                    "code":
                        package.code,

                    "name":
                        package.name,

                    "monthly_price":
                        str(
                            package.monthly_price
                        ),

                    "yearly_price":
                        str(
                            package.yearly_price
                        ),
                },
            },
        },
        status=200,
    )