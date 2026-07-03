from .common_imports import *


@api_view(['POST'])
def send_test_email(request):
    to_email = request.data.get("email")
    print("Sending test email to:", to_email)
    subject = "Test Email from Vitacura"
    html = "<h1>This is a test email from Zen Studio</h1><p>If you received this, email sending works!</p>"

    try:
        send_email(to_email, subject, html)
        return JsonResponse({"message": "Test email sent successfully"})
    except Exception as e:
        return JsonResponse({"message": "Failed to send test email", "error": str(e)}, status=500)


# email verification and password reset token generation
# signup api
@api_view(['POST'])
def signup(request):
    try:
        data = request.data

        # username = data.get("username")
        role = data.get("role")
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name", "").strip()
        phone_number = data.get("phone_number")

        username = email

        if not all([email, password, full_name, phone_number]):
            return JsonResponse({"message": "Missing required fields"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"message": "Username already exists"}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({"message": "Email already exists"}, status=400)

        token = str(uuid.uuid4())

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            phone_number=phone_number,
            role=role,
            email_verification_token=token,
            email_verified=False,
        )

        if role == 'worker':
            worker = WorkerProfile.objects.create(
                user=user
            )

            WorkerWallet.objects.create(
                worker=worker,
                amount=0.0,
                float_amount=0.0,
                pending_amount=0.0
            )

        link = f"http://192.168.100.12:8000/verify_email?token={token}"

        send_email(
            email,
            "Verify Your Unit Account",
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333;">
        
            <h2 style="color: #2563EB;">Welcome to Unit</h2>

            <p>
            Thank you for registering with Unit. To complete your account setup,
            please verify your email address by clicking the button below.
            </p>

            <div style="margin: 30px 0;">
            <a href="{link}" 
               style="
                    background-color: #2563EB;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    display: inline-block;
               ">
                Verify Email
            </a>
            </div>

            <p>
            If the button above does not work, copy and paste the link below into your browser:
            </p>

            <p style="word-break: break-all; color: #2563EB;">
            {link}
            </p>

            <hr style="margin: 30px 0;" />

            <p style="font-size: 14px; color: #777;">
            This verification link may expire after some time for security reasons.
            </p>

            <p style="font-size: 14px; color: #777;">
            The Unit Team
            </p>
            </div>
            """
            )

        return JsonResponse({"message": "Account created successfully. Verify your email."}, status=201)

    except Exception as e:
        return JsonResponse({"message": "Signup failed", "error": str(e)}, status=500)

# email verification api
@api_view(['GET'])
def verify_email(request):
    token = request.GET.get("token")

    if not token:
        return render(request, "auth/email_result.html", {
            "status": "error",
            "title": "Invalid Request",
            "message": "Verification token is missing."
        })

    user = User.objects.filter(email_verification_token=token).first()

    if not user:
        return render(request, "auth/email_result.html", {
            "status": "error",
            "title": "Invalid Token",
            "message": "This verification link is invalid or has expired."
        })

    if user.email_verified:
        return render(request, "auth/email_result.html", {
            "status": "success",
            "title": "Already Verified",
            "message": "Your email is already verified."
        })

    user.email_verified = True
    user.email_verification_token = None
    user.save(update_fields=["email_verified", "email_verification_token"])

    return render(request, "auth/email_result.html", {
        "status": "success",
        "title": "Email Verified 🎉",
        "message": "Your account has been successfully verified. You can now log in."
    })


# sign in api
@api_view(['POST'])
def signin(request):
    try:
        username = request.data.get("email")
        password = request.data.get("password")

        print("Signin attempt:", {"username": username})

        if not username or not password:
            return JsonResponse({"message": "Username and password required"}, status=400)

        user = authenticate(request, username=username, password=password)

        if not user:
            return JsonResponse({"message": "Invalid credentials"}, status=401)

        if not user.email_verified:
            return JsonResponse({"message": "Verify your email first"}, status=403)

        refresh = RefreshToken.for_user(user)

        return JsonResponse({
            "message": "Login successful",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "user_id": user.id,
                "user_name": user.full_name,
                "user_email": user.email,
                "phone_number":user.phone_number,
                "phone_verified": user.phone_verified,
                "profile_image":user.profile_image,
                "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
                "role": user.role,
                "profile_image": user.profile_image,
                "is_verified": user.is_verified,
            }
        })

    except Exception as e:
        return JsonResponse({"message": "Login failed", "error": str(e)}, status=500)


# password reset api
@api_view(['POST'])
def request_reset(request):
    email = request.data.get("email")

    user = User.objects.filter(email=email).first()
    if not user:
        return JsonResponse({"message": "User not found"}, status=404)

    token = str(uuid.uuid4())
    user.reset_token = token
    user.save()

    link = f"http://192.168.100.12:8000/reset_password?token={token}"

    send_email(
        email,
       "Reset Your Unit Password",
       f"""
       <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333;">

        <h2 style="color: #2563EB;">Password Reset Request</h2>

        <p>
            We received a request to reset your Unit account password.
        </p>

        <p>
            Click the button below to create a new password:
        </p>

        <div style="margin: 30px 0;">
            <a href="{link}"
               style="
                    background-color: #DC2626;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    display: inline-block;
               ">
                Reset Password
            </a>
          </div>

          <p>
            If the button above does not work, copy and paste the link below into your browser:
          </p>

          <p style="word-break: break-all; color: #2563EB;">
            {link}
          </p>

          <hr style="margin: 30px 0;" />

          <p style="font-size: 14px; color: #777;">
            If you did not request a password reset, you can safely ignore this email.
          </p>

          <p style="font-size: 14px; color: #777;">
            For security reasons, this password reset link may expire after some time.
          </p>

          <p style="font-size: 14px; color: #777;">
            The Unit Team
          </p>

          </div>
          """
        )

    return JsonResponse({"message": "Email sent"})


# password reset api
@api_view(['GET', 'POST'])
def reset_password(request):
    token = request.GET.get("token") or request.data.get("token")

    if not token:
        return render(request, "auth/reset_result.html", {
            "status": "error",
            "message": "Missing reset token."
        })

    user = User.objects.filter(reset_token=token).first()

    if not user:
        return render(request, "auth/reset_result.html", {
            "status": "error",
            "message": "Invalid or expired reset link."
        })

    # -------------------
    # GET → show form
    # -------------------
    if request.method == "GET":
        return render(request, "auth/reset_password.html", {
            "token": token
        })

    # -------------------
    # POST → process form
    # -------------------
    password = request.data.get("password")
    confirm_password = request.data.get("confirm_password")

    if not password or not confirm_password:
        return render(request, "auth/reset_password.html", {
            "token": token,
            "error": "All fields are required"
        })

    if password != confirm_password:
        return render(request, "auth/reset_password.html", {
            "token": token,
            "error": "Passwords do not match"
        })

    user.set_password(password)
    user.reset_token = None
    user.save(update_fields=["password", "reset_token"])

    return render(request, "auth/reset_result.html", {
        "status": "success",
        "message": "Password updated successfully. You can now log in."
    })


# refresh token api
@api_view(['POST'])
def refresh_token(request):
    try:
        refresh_token = request.data.get("refresh_token")

        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)

        return JsonResponse({
            "access_token": access_token
        })

    except Exception:
        return JsonResponse({"message": "Invalid refresh token"}, status=401)

# check authentication status api
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_check(request):

    user = request.user

    return JsonResponse({
        "authenticated": True,
        "user": {
            "user_id": user.id,
            "user_name": user.full_name,
            "user_email": user.email,
            "phone_number":user.phone_number,
            "phone_verified": user.phone_verified,
            "profile_image":user.profile_image,
            "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            "profile_image": user.profile_image,
            }
    })

# delete account api
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    try:
        user = request.user

        # Delete account
        user.delete()

        return JsonResponse({
            "message": "Account deleted successfully"
        }, status=200)

    except Exception as e:
        print("DELETE ACCOUNT ERROR:", str(e))

        return JsonResponse({
            "message": "Failed to delete account",
            "error": str(e)
        }, status=500)

