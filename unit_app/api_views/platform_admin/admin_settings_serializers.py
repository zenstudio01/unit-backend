
import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class GeneralSettingsSerializer(serializers.Serializer):
    platform_name = serializers.CharField(max_length=100)
    support_email = serializers.EmailField()
    website_url = serializers.URLField(allow_blank=True)
    timezone = serializers.ChoiceField(choices=[
        "Africa/Nairobi",
        "UTC",
        "Africa/Kampala",
        "Africa/Dar_es_Salaam",
    ])
    currency = serializers.ChoiceField(choices=[
        "KES", "USD", "UGX", "TZS",
    ])
    maintenance_mode = serializers.BooleanField()


class BrandingSettingsSerializer(serializers.Serializer):
    logo_url = serializers.URLField(allow_blank=True)
    favicon_url = serializers.URLField(allow_blank=True)
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        max_length=7,
    )


class SubscriptionSettingsSerializer(serializers.Serializer):
    trial_days = serializers.IntegerField(
        min_value=0, max_value=365
    )
    grace_period_days = serializers.IntegerField(
        min_value=0, max_value=90
    )
    allow_trials = serializers.BooleanField()
    auto_suspend_expired = serializers.BooleanField()
    expiry_reminder_days = serializers.IntegerField(
        min_value=0, max_value=90
    )


class PaymentSettingsSerializer(serializers.Serializer):
    enable_mpesa = serializers.BooleanField()
    enable_paystack = serializers.BooleanField()
    enable_bank_transfer = serializers.BooleanField()
    mpesa_shortcode = serializers.RegexField(
        regex=r"^[0-9]{0,12}$",
        allow_blank=True,
        max_length=12,
    )
    payment_notifications = serializers.BooleanField()


class NotificationSettingsSerializer(serializers.Serializer):
    enable_email = serializers.BooleanField()
    enable_sms = serializers.BooleanField()
    enable_push = serializers.BooleanField()
    notify_new_organization = serializers.BooleanField()
    notify_new_subscription = serializers.BooleanField()
    notify_failed_payment = serializers.BooleanField()
    notify_maintenance_alerts = serializers.BooleanField()


class SecuritySettingsSerializer(serializers.Serializer):
    session_timeout_minutes = serializers.IntegerField(
        min_value=5, max_value=1440
    )
    max_login_attempts = serializers.IntegerField(
        min_value=3, max_value=20
    )
    require_strong_passwords = serializers.BooleanField()
    require_admin_2fa = serializers.BooleanField()


SECTION_SERIALIZERS = {
    "general": GeneralSettingsSerializer,
    "branding": BrandingSettingsSerializer,
    "subscriptions": SubscriptionSettingsSerializer,
    "payments": PaymentSettingsSerializer,
    "notifications": NotificationSettingsSerializer,
    "security": SecuritySettingsSerializer,
}


DEFAULT_SETTINGS = {
    "general": {
        "platform_name": "UNIT",
        "support_email": "support@example.com",
        "website_url": "",
        "timezone": "Africa/Nairobi",
        "currency": "KES",
        "maintenance_mode": False,
    },
    "branding": {
        "logo_url": "",
        "favicon_url": "",
        "primary_color": "#FF5722",
    },
    "subscriptions": {
        "trial_days": 14,
        "grace_period_days": 7,
        "allow_trials": True,
        "auto_suspend_expired": False,
        "expiry_reminder_days": 3,
    },
    "payments": {
        "enable_mpesa": True,
        "enable_paystack": False,
        "enable_bank_transfer": False,
        "mpesa_shortcode": "",
        "payment_notifications": True,
    },
    "notifications": {
        "enable_email": True,
        "enable_sms": False,
        "enable_push": True,
        "notify_new_organization": True,
        "notify_new_subscription": True,
        "notify_failed_payment": True,
        "notify_maintenance_alerts": True,
    },
    "security": {
        "session_timeout_minutes": 60,
        "max_login_attempts": 5,
        "require_strong_passwords": True,
        "require_admin_2fa": False,
    },
}


class AdminProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        max_length=150, allow_blank=True
    )
    last_name = serializers.CharField(
        max_length=150, allow_blank=True
    )
    email = serializers.EmailField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    new_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    confirm_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(
            attrs["current_password"]
        ):
            raise serializers.ValidationError({
                "current_password": "Current password is incorrect."
            })

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({
                "new_password": "Choose a different password."
            })

        validate_password(attrs["new_password"], user)
        return attrs
