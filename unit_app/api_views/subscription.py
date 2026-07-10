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




# verify subscription payment
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_subscription_payment(request):

    reference = request.data.get("reference")

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers,
    )

    result = response.json()

    if not result["status"]:
        return Response(
            {"message": "Verification failed"},
            status=400
        )

    payment = result["data"]

    if payment["status"] != "success":
        return Response(
            {"message": "Payment not successful"},
            status=400
        )

    metadata = payment["metadata"]

    package = Package.objects.get(
        id=metadata["package_id"]
    )

    if metadata["billing_cycle"] == "monthly":
        end_date = timezone.now() + timedelta(
            days=package.month_days
        )
    else:
        end_date = timezone.now() + timedelta(
            days=package.year_days
        )

    Subscription.objects.update_or_create(
        user=request.user,
        defaults={
            "package": package,
            "start_date": timezone.now(),
            "end_date": end_date,
            "is_active": True,
        },
    )

    return Response({
        "message": "Subscription activated successfully."
    })