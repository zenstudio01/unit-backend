from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_bookings(request):
    try:
        bookings = CompanyBooking.objects.filter(
            customer=request.user
        ).select_related("company").order_by("-created_at")

        data = []

        for booking in bookings:
            data.append({
                "id": booking.id,
                "company_id": booking.company.id,
                "company_name": booking.company.name,
                "company_logo": booking.company.logo,
                "title": booking.title,
                "description": booking.description,
                "location": booking.location,
                "preferred_date": booking.preferred_date,
                "preferred_time": booking.preferred_time.strftime("%H:%M"),
                "budget": booking.budget,
                "status": booking.status,
                "created_at": booking.created_at,
            })

        return JsonResponse({
            "success": True,
            "count": len(data),
            "bookings": data
        }, status=200)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)