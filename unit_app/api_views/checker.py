from django.utils import timezone


def get_organization_subscription(organization):
    try:
        subscription = (
            organization.subscription
        )

    except OrganizationSubscription.DoesNotExist:
        return None

    return subscription


def organization_has_access(organization):
    subscription = (
        get_organization_subscription(
            organization
        )
    )

    if not subscription:
        return False

    if subscription.status == "trial":
        return (
            subscription.trial_end
            and
            timezone.now()
            <
            subscription.trial_end
        )

    if subscription.status == "active":
        return (
            subscription.current_period_end
            and
            timezone.now()
            <
            subscription.current_period_end
        )

    return False


def package_has_feature(organization, feature_name):
    try:
        subscription = (organization.subscription)

    except OrganizationSubscription.DoesNotExist:
        return False

    if not organization_has_access(
        organization
    ):
        return False

    package = (
        subscription.package
    )

    return bool(
        getattr(
            package,
            feature_name,
            False,
        )
    )