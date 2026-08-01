from .common_imports import *

from datetime import timedelta
import uuid

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken


# ============================================================
# HELPERS
# ============================================================

def serialize_company_membership(membership):
    """
    Convert a CompanyStaff membership into JSON-safe data.
    """

    company = membership.company

    return {
        "membership_id": membership.id,
        "company_id": company.id,
        "company_name": company.name,
        "company_logo": company.logo,
        "company_email": company.email,
        "company_phone_number": company.phone_number,
        "company_city": company.city,
        "company_country": company.country,
        "staff_role": membership.role,
        "is_active": membership.is_active,
        "is_owner": company.owner_id == membership.user_id,
    }


def get_user_companies(user):
    """
    Return all active companies where the user is a staff member.
    """

    memberships = (
        CompanyStaff.objects
        .filter(user=user, is_active=True)
        .select_related("company")
        .order_by("company__name")
    )

    return [
        serialize_company_membership(membership)
        for membership in memberships
    ]


def serialize_user(user):
    """
    Standard user response used by signin and auth_check.
    """

    companies = get_user_companies(user)

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "phone_verified": user.phone_verified,
        "email_verified": user.email_verified,
        "profile_image": user.profile_image,
        "platform_role": user.role,
        "is_verified": user.is_verified,
        "date_joined": user.date_joined.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "companies": companies,
        "has_company": len(companies) > 0,
    }


def normalize_boolean(value):
    """
    Convert JSON, form-data, and string boolean values.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "on",
        }

    return bool(value)


# ============================================================
# TEST EMAIL
# ============================================================

@api_view(["POST"])
def send_test_email(request):
    to_email = request.data.get("email")

    if not to_email:
        return JsonResponse(
            {"message": "Email is required"},
            status=400,
        )

    subject = "Test Email from Unit"

    html = """
        <h1>This is a test email from Unit</h1>
        <p>If you received this email, email sending works.</p>
    """

    try:
        send_email(to_email, subject, html)

        return JsonResponse({
            "message": "Test email sent successfully",
        })

    except Exception as e:
        return JsonResponse(
            {
                "message": "Failed to send test email",
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# SIGNUP
# ============================================================

@api_view(["POST"])
def signup(request):
    data = request.data

    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone_number = str(data.get("phone_number", "")).strip()
    password = data.get("password")

    create_company = normalize_boolean(
        data.get("create_company", False)
    )

    # Company information
    company_name = str(
        data.get("company_name", "")
    ).strip()

    company_email = str(
        data.get("company_email", email)
    ).strip().lower()

    company_phone_number = str(
        data.get("company_phone_number", phone_number)
    ).strip()

    company_address = str(
        data.get("company_address", "")
    ).strip()

    company_city = str(
        data.get("company_city", "")
    ).strip()

    company_country = str(
        data.get("company_country", "Kenya")
    ).strip()

    company_website = str(
        data.get("company_website", "")
    ).strip()

    company_description = str(
        data.get("company_description", "")
    ).strip()

    # --------------------------------------------------------
    # Validate user fields
    # --------------------------------------------------------

    missing_fields = []

    if not full_name:
        missing_fields.append("full_name")

    if not email:
        missing_fields.append("email")

    if not phone_number:
        missing_fields.append("phone_number")

    if not password:
        missing_fields.append("password")

    if missing_fields:
        return JsonResponse(
            {
                "message": "Missing required fields",
                "fields": missing_fields,
            },
            status=400,
        )

    # --------------------------------------------------------
    # Validate company fields when company creation is requested
    # --------------------------------------------------------

    if create_company:
        missing_company_fields = []

        if not company_name:
            missing_company_fields.append("company_name")

        if not company_email:
            missing_company_fields.append("company_email")

        if not company_phone_number:
            missing_company_fields.append(
                "company_phone_number"
            )

        if not company_address:
            missing_company_fields.append(
                "company_address"
            )

        if not company_city:
            missing_company_fields.append("company_city")

        if not company_country:
            missing_company_fields.append(
                "company_country"
            )

        if missing_company_fields:
            return JsonResponse(
                {
                    "message": (
                        "Missing required company fields"
                    ),
                    "fields": missing_company_fields,
                },
                status=400,
            )

    # --------------------------------------------------------
    # Check duplicate user details
    # --------------------------------------------------------

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"message": "Email already exists"},
            status=400,
        )

    if User.objects.filter(username__iexact=email).exists():
        return JsonResponse(
            {"message": "Email already exists"},
            status=400,
        )

    if User.objects.filter(
        phone_number=phone_number
    ).exists():
        return JsonResponse(
            {"message": "Phone number already exists"},
            status=400,
        )

    # --------------------------------------------------------
    # Validate password using Django validators
    # --------------------------------------------------------

    try:
        validate_password(password)

    except ValidationError as error:
        return JsonResponse(
            {
                "message": "Password does not meet requirements",
                "errors": list(error.messages),
            },
            status=400,
        )

    email_token = str(uuid.uuid4())

    try:
        with transaction.atomic():

            # Username remains the email because signin authenticates
            # using the supplied email.
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                full_name=full_name,
                phone_number=phone_number,
                role="user",
                email_verification_token=email_token,
                email_verified=False,
            )

            company = None
            membership = None
            subscription = None

            # ------------------------------------------------
            # Create company onboarding records
            # ------------------------------------------------

            if create_company:
                company = Company.objects.create(
                    owner=user,
                    name=company_name,
                    email=company_email,
                    phone_number=company_phone_number,
                    address=company_address,
                    city=company_city,
                    country=company_country,
                    website=company_website,
                    description=company_description,
                )

                membership = CompanyStaff.objects.create(
                    company=company,
                    user=user,
                    role="admin",
                    is_active=True,
                )

                # Assumes CompanyWallet is OneToOneField and uses
                # available_balance, pending_balance and reserved_balance.
                CompanyWallet.objects.create(
                    company=company,
                    available_balance=0,
                    pending_balance=0,
                    reserved_balance=0,
                )

                starter_package = Package.objects.filter(
                    name="starter bundle"
                ).first()

                if starter_package:
                    subscription = Subscription.objects.create(
                        company=company,
                        package=starter_package,
                        billing_cycle="monthly",
                        start_date=timezone.now(),
                        end_date=(
                            timezone.now()
                            + timedelta(
                                days=starter_package.month_days
                            )
                        ),
                        status="active",
                    )

        # Send email after the database transaction succeeds.
        verification_link = (
            "https://unit-backend-lof1.onrender.com/"
            f"verify_email?token={email_token}"
        )

        email_sent = True

        try:
            send_email(
                email,
                "Verify Your Unit Account",
                f"""
                <div style="
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: auto;
                    padding: 20px;
                    color: #333;
                ">
                    <h2 style="color: #2563EB;">
                        Welcome to Unit
                    </h2>

                    <p>Hello {full_name},</p>

                    <p>
                        Thank you for registering with Unit.
                        Verify your email address to complete
                        your account setup.
                    </p>

                    <div style="margin: 30px 0;">
                        <a
                            href="{verification_link}"
                            style="
                                background-color: #2563EB;
                                color: white;
                                padding: 12px 24px;
                                text-decoration: none;
                                border-radius: 8px;
                                font-weight: bold;
                                display: inline-block;
                            "
                        >
                            Verify Email
                        </a>
                    </div>

                    <p>
                        You can also copy and paste this link:
                    </p>

                    <p style="
                        word-break: break-all;
                        color: #2563EB;
                    ">
                        {verification_link}
                    </p>

                    <hr style="margin: 30px 0;" />

                    <p style="
                        font-size: 14px;
                        color: #777;
                    ">
                        If you did not create this account,
                        you can ignore this email.
                    </p>

                    <p style="
                        font-size: 14px;
                        color: #777;
                    ">
                        The Unit Team
                    </p>
                </div>
                """,
            )

        except Exception as email_error:
            email_sent = False
            print(
                "VERIFICATION EMAIL ERROR:",
                str(email_error),
            )

        response = {
            "message": (
                "Account created successfully. "
                "Verify your email."
            ),
            "email_sent": email_sent,
            "user": serialize_user(user),
        }

        if company:
            response["company"] = {
                "company_id": company.id,
                "company_name": company.name,
                "staff_role": membership.role,
                "subscription_created": (
                    subscription is not None
                ),
            }

        return JsonResponse(response, status=201)

    except Exception as e:
        print("SIGNUP ERROR:", str(e))

        return JsonResponse(
            {
                "message": "Signup failed",
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# VERIFY EMAIL
# ============================================================

@api_view(["GET"])
def verify_email(request):
    token = request.GET.get("token")

    if not token:
        return render(
            request,
            "auth/email_result.html",
            {
                "status": "error",
                "title": "Invalid Request",
                "message": (
                    "Verification token is missing."
                ),
            },
        )

    user = User.objects.filter(
        email_verification_token=token
    ).first()

    if not user:
        return render(
            request,
            "auth/email_result.html",
            {
                "status": "error",
                "title": "Invalid Token",
                "message": (
                    "This verification link is invalid "
                    "or has expired."
                ),
            },
        )

    if user.email_verified:
        return render(
            request,
            "auth/email_result.html",
            {
                "status": "success",
                "title": "Already Verified",
                "message": (
                    "Your email is already verified."
                ),
            },
        )

    user.email_verified = True
    user.email_verification_token = None

    user.save(
        update_fields=[
            "email_verified",
            "email_verification_token",
        ]
    )

    return render(
        request,
        "auth/email_result.html",
        {
            "status": "success",
            "title": "Email Verified",
            "message": (
                "Your account has been successfully verified. "
                "You can now log in."
            ),
        },
    )


# ============================================================
# RESEND EMAIL VERIFICATION
# ============================================================

@api_view(["POST"])
def resend_verification_email(request):
    email = str(
        request.data.get("email", "")
    ).strip().lower()

    if not email:
        return JsonResponse(
            {"message": "Email is required"},
            status=400,
        )

    user = User.objects.filter(
        email__iexact=email
    ).first()

    # Avoid exposing whether an account exists.
    generic_message = (
        "If the account exists and is not verified, "
        "a verification email has been sent."
    )

    if not user:
        return JsonResponse({
            "message": generic_message,
        })

    if user.email_verified:
        return JsonResponse({
            "message": "Email is already verified",
        })

    token = str(uuid.uuid4())

    user.email_verification_token = token
    user.save(
        update_fields=["email_verification_token"]
    )

    verification_link = (
        "https://unit-backend-lof1.onrender.com/"
        f"verify_email?token={token}"
    )

    try:
        send_email(
            user.email,
            "Verify Your Unit Account",
            f"""
            <div style="
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: auto;
                padding: 20px;
            ">
                <h2>Verify your Unit account</h2>

                <p>
                    Click the link below to verify your email.
                </p>

                <a href="{verification_link}">
                    Verify Email
                </a>

                <p>{verification_link}</p>
            </div>
            """,
        )

    except Exception as e:
        print("RESEND VERIFICATION ERROR:", str(e))

        return JsonResponse(
            {
                "message": (
                    "Failed to send verification email"
                ),
                "error": str(e),
            },
            status=500,
        )

    return JsonResponse({
        "message": generic_message,
    })


# ============================================================
# SIGN IN
# ============================================================

@api_view(["POST"])
def signin(request):
    try:
        email = str(
            request.data.get("email", "")
        ).strip().lower()

        password = request.data.get("password")

        if not email or not password:
            return JsonResponse(
                {
                    "message": (
                        "Email and password are required"
                    ),
                },
                status=400,
            )

        # User.username is set to email during signup.
        user = authenticate(
            request,
            username=email,
            password=password,
        )

        if not user:
            return JsonResponse(
                {"message": "Invalid email or password"},
                status=401,
            )

        if not user.is_active:
            return JsonResponse(
                {"message": "This account is disabled"},
                status=403,
            )

        if not user.email_verified:
            return JsonResponse(
                {
                    "message": "Verify your email first",
                    "email_verified": False,
                },
                status=403,
            )

        refresh = RefreshToken.for_user(user)

        return JsonResponse({
            "message": "Login successful",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": serialize_user(user),
        })

    except Exception as e:
        print("SIGNIN ERROR:", str(e))

        return JsonResponse(
            {
                "message": "Login failed",
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# REQUEST PASSWORD RESET
# ============================================================

@api_view(["POST"])
def request_reset(request):
    email = str(
        request.data.get("email", "")
    ).strip().lower()

    if not email:
        return JsonResponse(
            {"message": "Email is required"},
            status=400,
        )

    user = User.objects.filter(
        email__iexact=email
    ).first()

    generic_message = (
        "If an account exists with that email, "
        "a password reset link has been sent."
    )

    # Do not expose whether the email exists.
    if not user:
        return JsonResponse({
            "message": generic_message,
        })

    token = str(uuid.uuid4())

    user.reset_token = token
    user.save(update_fields=["reset_token"])

    reset_link = (
        "https://unit-backend-lof1.onrender.com/"
        f"reset_password?token={token}"
    )

    try:
        send_email(
            email,
            "Reset Your Unit Password",
            f"""
            <div style="
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: auto;
                padding: 20px;
                color: #333;
            ">
                <h2 style="color: #2563EB;">
                    Password Reset Request
                </h2>

                <p>
                    We received a request to reset your
                    Unit account password.
                </p>

                <div style="margin: 30px 0;">
                    <a
                        href="{reset_link}"
                        style="
                            background-color: #DC2626;
                            color: white;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: bold;
                            display: inline-block;
                        "
                    >
                        Reset Password
                    </a>
                </div>

                <p>
                    You can also copy and paste this link:
                </p>

                <p style="
                    word-break: break-all;
                    color: #2563EB;
                ">
                    {reset_link}
                </p>

                <hr style="margin: 30px 0;" />

                <p style="
                    font-size: 14px;
                    color: #777;
                ">
                    If you did not request a password reset,
                    you can ignore this email.
                </p>

                <p style="
                    font-size: 14px;
                    color: #777;
                ">
                    The Unit Team
                </p>
            </div>
            """,
        )

    except Exception as e:
        print("PASSWORD RESET EMAIL ERROR:", str(e))

        return JsonResponse(
            {
                "message": "Failed to send reset email",
                "error": str(e),
            },
            status=500,
        )

    return JsonResponse({
        "message": generic_message,
    })


# ============================================================
# RESET PASSWORD
# ============================================================

@api_view(["GET", "POST"])
def reset_password(request):
    token = (
        request.GET.get("token")
        or request.data.get("token")
    )

    if not token:
        return render(
            request,
            "auth/reset_result.html",
            {
                "status": "error",
                "message": "Missing reset token.",
            },
        )

    user = User.objects.filter(
        reset_token=token
    ).first()

    if not user:
        return render(
            request,
            "auth/reset_result.html",
            {
                "status": "error",
                "message": (
                    "Invalid or expired reset link."
                ),
            },
        )

    if request.method == "GET":
        return render(
            request,
            "auth/reset_password.html",
            {"token": token},
        )

    password = request.data.get("password")
    confirm_password = request.data.get(
        "confirm_password"
    )

    if not password or not confirm_password:
        return render(
            request,
            "auth/reset_password.html",
            {
                "token": token,
                "error": "All fields are required",
            },
        )

    if password != confirm_password:
        return render(
            request,
            "auth/reset_password.html",
            {
                "token": token,
                "error": "Passwords do not match",
            },
        )

    try:
        validate_password(password, user=user)

    except ValidationError as error:
        return render(
            request,
            "auth/reset_password.html",
            {
                "token": token,
                "error": " ".join(error.messages),
            },
        )

    user.set_password(password)
    user.reset_token = None

    user.save(
        update_fields=[
            "password",
            "reset_token",
        ]
    )

    return render(
        request,
        "auth/reset_result.html",
        {
            "status": "success",
            "message": (
                "Password updated successfully. "
                "You can now log in."
            ),
        },
    )


# ============================================================
# REFRESH ACCESS TOKEN
# ============================================================

@api_view(["POST"])
def refresh_token(request):
    refresh_token_value = request.data.get(
        "refresh_token"
    )

    if not refresh_token_value:
        return JsonResponse(
            {"message": "Refresh token is required"},
            status=400,
        )

    try:
        refresh = RefreshToken(refresh_token_value)

        return JsonResponse({
            "access_token": str(refresh.access_token),
        })

    except Exception:
        return JsonResponse(
            {"message": "Invalid refresh token"},
            status=401,
        )


# ============================================================
# AUTHENTICATION CHECK
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_check(request):
    return JsonResponse({
        "authenticated": True,
        "user": serialize_user(request.user),
    })


# ============================================================
# DELETE ACCOUNT
# ============================================================

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    try:
        user = request.user

        # PROTECT relationships may prevent deletion where the user
        # owns important financial or tenancy records.
        user.delete()

        return JsonResponse(
            {"message": "Account deleted successfully"},
            status=200,
        )

    except Exception as e:
        print("DELETE ACCOUNT ERROR:", str(e))

        return JsonResponse(
            {
                "message": (
                    "The account could not be deleted. "
                    "It may be connected to protected company, "
                    "lease, or financial records."
                ),
                "error": str(e),
            },
            status=409,
        )