import os
import requests
import resend
import cloudinary.uploader
from datetime import timedelta
from django.utils import timezone

from unit_app.models import User, SubscriptionPackage, OrganizationSubscription, Organization, OrganizationMembership
from django.http import JsonResponse
from django.utils import timezone



# send push notification to phne
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_push_notification(token, title, body, data=None):
    if not token:
        return {"error": "No push token provided."}

    message = {
        "to": f"{token}",
        "sound": "default",
        "title": f"{title}",
        "body": f"{body}",
        "data": data or {},
    }

    try:
        response = requests.post(EXPO_PUSH_URL, json=message)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# helper function to help sending emails
resend.api_key = os.environ.get("RESEND_API_KEY")

def send_email(to_email, subject, html):
    # Debugging logs (similar to your example)
    print(f"Resend from email: {os.environ.get('RESEND_FROM_EMAIL')}")
    
    params = {
        "from": os.environ.get("RESEND_FROM_EMAIL"), # e.g., "support@vincab.services"
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    try:
        email = resend.Emails.send(params)
        print(f"Email sent! ID: {email['id']}")
    except Exception as e:
        print(f"Error sending email: {e}")    






def upload_maintenance_image(
    image_file,
    organization_id,
):
    result = (
        cloudinary.uploader.upload(
            image_file,

            folder=(
                f"unit/"
                f"organizations/"
                f"{organization_id}/"
                f"maintenance"
            ),

            resource_type=
                "image",
        )
    )

    return {
        "url":
            result.get(
                "secure_url"
            ),
    }


# helper function for creating trial subscription

def create_trial_subscription(
    organization,
):
    package = (
        SubscriptionPackage.objects
        .filter(
            code="growth",
            is_active=True,
        )
        .first()
    )

    if not package:
        raise ValueError(
            "Growth subscription package has not been configured."
        )

    now = (
        timezone.now()
    )

    return (
        OrganizationSubscription.objects.create(
            organization=
                organization,

            package=
                package,

            status=
                "trial",

            billing_cycle=
                "monthly",

            trial_start=
                now,

            trial_end=
                now +
                timedelta(
                    days=30
                ),
        )
    )





def get_manager_organization(
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
                user=user,
                organization=organization,
                is_active=True,
            )
        )

    except OrganizationMembership.DoesNotExist:
        return (
            None,
            JsonResponse(
                {
                    "message":
                        "You do not have access to this organization."
                },
                status=403,
            ),
        )

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
        "property_manager",
    }

    if not role_codes.intersection(
        allowed_roles
    ):
        return (
            None,
            JsonResponse(
                {
                    "message":
                        "You do not have permission to manage this organization."
                },
                status=403,
            ),
        )

    return (
        organization,
        None,
    )


# helpr functions for checking packages
def get_organization_subscription_access(
    organization,
):
    """
    Returns the organization's current subscription access,
    package features, limits and subscription status.
    """

    # =====================================================
    # GET SUBSCRIPTION
    # =====================================================

    try:
        subscription = (
            OrganizationSubscription.objects
            .select_related(
                "package"
            )
            .get(
                organization=organization
            )
        )

    except OrganizationSubscription.DoesNotExist:
        return {
            "has_access": False,
            "code": "subscription_not_found",
            "message":
                "This organization does not have a subscription.",
            "subscription": None,
            "package": None,
            "features": {},
            "limits": {},
        }

    now = timezone.now()

    package = (
        subscription.package
    )

    # =====================================================
    # DETERMINE ACCESS
    # =====================================================

    has_access = False
    access_type = None
    code = None
    message = None

    # ---------------------------------------------
    # FREE TRIAL
    # ---------------------------------------------

    if (
        subscription.trial_end
        and
        now <= subscription.trial_end
        and
        subscription.status == "trial"
    ):
        has_access = True
        access_type = "trial"
        code = "trial_active"
        message = (
            "Your free trial is active."
        )

    # ---------------------------------------------
    # ACTIVE PAID SUBSCRIPTION
    # ---------------------------------------------

    elif (
        subscription.status == "active"
        and
        subscription.end_date
        and
        now <= subscription.end_date
    ):
        has_access = True
        access_type = "subscription"
        code = "subscription_active"
        message = (
            "Your subscription is active."
        )

    # ---------------------------------------------
    # EXPIRED
    # ---------------------------------------------

    elif (
        subscription.end_date
        and
        now > subscription.end_date
    ):
        code = "subscription_expired"
        message = (
            "Your subscription has expired."
        )

    # ---------------------------------------------
    # TRIAL EXPIRED
    # ---------------------------------------------

    elif (
        subscription.trial_end
        and
        now > subscription.trial_end
        and
        subscription.status == "trial"
    ):
        code = "trial_expired"
        message = (
            "Your free trial has expired."
        )

    # ---------------------------------------------
    # CANCELLED
    # ---------------------------------------------

    elif (
        subscription.status == "cancelled"
    ):
        code = "subscription_cancelled"
        message = (
            "Your subscription has been cancelled."
        )

    else:
        code = "subscription_inactive"
        message = (
            "Your subscription is not active."
        )

    # =====================================================
    # PACKAGE FEATURES
    # =====================================================

    features = {}

    limits = {}

    if package:
        features = {
            "maintenance":
                package.has_maintenance,

            "kaskazi_integration":
                package.has_kaskazi_integration,

            "financial_reports":
                package.has_financial_reports,

            "advanced_reports":
                package.has_advanced_reports,

            "owner_portal":
                package.has_owner_portal,

            "tenant_portal":
                package.has_tenant_portal,

            "api_access":
                package.has_api_access,
        }

        limits = {
            "max_properties":
                package.max_properties,

            "max_units":
                package.max_units,

            "max_users":
                package.max_users,

            "max_portfolios":
                package.max_portfolios,
        }

    # =====================================================
    # DAYS REMAINING
    # =====================================================

    days_remaining = None

    if access_type == "trial":
        if subscription.trial_end:
            days_remaining = max(
                0,
                (
                    subscription.trial_end -
                    now
                ).days,
            )

    elif access_type == "subscription":
        if subscription.end_date:
            days_remaining = max(
                0,
                (
                    subscription.end_date -
                    now
                ).days,
            )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "has_access":
            has_access,

        "access_type":
            access_type,

        "code":
            code,

        "message":
            message,

        "days_remaining":
            days_remaining,

        "subscription": {
            "id":
                subscription.id,

            "status":
                subscription.status,

            "billing_cycle":
                subscription.billing_cycle,

            "trial_start":
                (
                    subscription.trial_start
                    .isoformat()
                    if subscription.trial_start
                    else None
                ),

            "trial_end":
                (
                    subscription.trial_end
                    .isoformat()
                    if subscription.trial_end
                    else None
                ),

            "start_date":
                (
                    subscription.start_date
                    .isoformat()
                    if subscription.start_date
                    else None
                ),

            "end_date":
                (
                    subscription.end_date
                    .isoformat()
                    if subscription.end_date
                    else None
                ),
        },

        "package": (
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
            }
            if package
            else None
        ),

        "features":
            features,

        "limits":
            limits,
    }



def organization_has_feature(
    organization,
    feature,
):
    access = (
        get_organization_subscription_access(
            organization
        )
    )

    if not access[
        "has_access"
    ]:
        return False

    return bool(
        access
        .get(
            "features",
            {}
        )
        .get(
            feature,
            False
        )
    )