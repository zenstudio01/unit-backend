from .common_imports import *

from django.shortcuts import render
from django.http import HttpResponse

@api_view(["GET"])
def health(request):
    try:
        # Test database connection
        User.objects.first()

        return JsonResponse({
            "success": True,
            "status": "healthy",
            "message": "Backend is running successfully.",
            "database": "connected"
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "status": "unhealthy",
            "message": "Backend is running but something failed.",
            "error": str(e)
        }, status=500)