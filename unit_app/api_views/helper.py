import os
import requests
import resend
import cloudinary.uploader
from datetime import timedelta
from django.utils import timezone

from unit_app.models import SubscriptionPackage, OrganizationSubscription, Organization, OrganizationMembership
from django.http import JsonResponse



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