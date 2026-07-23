from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_packages(request):
    try:
        packages = Package.objects.all().order_by("monthly_price")

        data = []

        for package in packages:
            data.append({
                "id": package.id,
                "name": package.name,
                "description": package.description,
                "monthly_price": float(package.monthly_price),
                "yearly_price": float(package.yearly_price),
                "month_days": package.month_days,
                "year_days": package.year_days,
                "number_of_units": package.number_of_units,
                "mpesa_daraja": package.mpesa_daraja,
                "email_notifications": package.email_notifications,
                "logs_duration": package.logs_duration,
                "created_at": package.created_at,
                "updated_at": package.updated_at,
            })

        return Response({
            "success": True,
            "count": len(data),
            "packages": data
        }, status=200)

    except Exception as e:
        return Response({
            "success": False,
            "message": str(e)
        }, status=500)






PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def property_manager_subscribe_plan(request):

    user = request.user

    email = request.data.get("email")
    package_id = request.data.get("package_id")
    billing_cycle = request.data.get("billing_cycle", "monthly")

    if not email or not package_id:
        return Response(
            {"message": "Email and package are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        package = Package.objects.get(id=package_id)

    except Package.DoesNotExist:
        return Response(
            {"message": "Package not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if billing_cycle == "monthly":
        amount = package.monthly_price
    else:
        amount = package.yearly_price

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": int(amount * 100),
        "callback_url": "http://192.168.100.12:8000/property_manager_subscription_callback/",
        "metadata": {
            "user_id": user.id,
            "package_id": package.id,
            "billing_cycle": billing_cycle,
        },
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload,
        headers=headers,
    )

    data = response.json()

    if data.get("status"):

        reference = data["data"]["reference"]

        SubscriptionPayment.objects.create(
            user=user,
            package=package,
            amount=amount,
            reference=reference,
            payment_method="paystack",
            status="pending",
        )

        return Response({
            "authorization_url": data["data"]["authorization_url"],
            "reference": reference,
        })

    return Response(
        {
            "message": "Unable to initialize payment.",
            "paystack": data,
        },
        status=400,
    )



@api_view(["GET"])
def property_manager_verify_subscription(reference):

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers,
    )

    result = response.json()

    if not result["status"]:
        return Response(
            {"message": "Verification failed"},
            status=400,
        )

    payment_data = result["data"]

    if payment_data["status"] != "success":
        return Response(
            {"message": "Payment unsuccessful"},
            status=400,
        )

    payment = SubscriptionPayment.objects.get(
        reference=reference
    )

    payment.status = "success"
    payment.save()

    return Response({
        "message": "Payment verified."
    })


@api_view(["GET"])
def property_manager_subscription_callback(request):

    reference = request.GET.get("reference")

    if not reference:
        return Response(
            {"message": "Reference missing"},
            status=400,
        )

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers,
    )

    result = response.json()

    if not result["status"]:
        return Response(
            {"message": "Verification failed"},
            status=400,
        )

    transaction = result["data"]

    if transaction["status"] != "success":
        return Response(
            {"message": "Payment failed"},
            status=400,
        )

    try:

        payment = SubscriptionPayment.objects.get(
            reference=reference
        )

        if payment.status == "success":
            return Response({
                "message": "Already processed."
            })

        payment.status = "success"
        payment.save()

        package = payment.package

        if transaction["metadata"]["billing_cycle"] == "monthly":
            expires = timezone.now() + timedelta(
                days=package.month_days
            )
        else:
            expires = timezone.now() + timedelta(
                days=package.year_days
            )

        Subscription.objects.update_or_create(

            user=payment.user,

            defaults={

                "package": package,

                "start_date": timezone.now(),

                "end_date": expires,

                "is_active": True,

            },
        )

        Notification.objects.create(

            user=payment.user,

            title="Subscription Activated",

            message=f"Your {package.name} subscription has been activated successfully.",

            msg_type="subscription",

        )

        send_push_notification(

            payment.user.expo_token,

            title="Subscription Activated",

            body=f"Your {package.name} subscription is now active.",

            data={

                "screen": "Subscription",

            },

        )

        return render(
            request,
            "subscription/payment_success.html",
            {
                "reference": reference,
                "package_name": subscription.package.name,
                "billing_cycle": subscription.billing_cycle.title(),
                "amount": payment.amount,
            }
        )

    except SubscriptionPayment.DoesNotExist:

        return Response(
            {"message": "Payment record not found."},
            status=404,
        )




