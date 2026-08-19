import os
import requests
import resend


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



import cloudinary.uploader


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