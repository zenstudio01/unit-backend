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