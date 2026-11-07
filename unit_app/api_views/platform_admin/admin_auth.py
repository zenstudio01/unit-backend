
from django.contrib.auth import authenticate
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def serialize_admin(user):
    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name() or user.get_username(),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def is_platform_admin(user):
    return (
        user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def admin_signin(request):
    username = str(
        request.data.get("username", "")
    ).strip()

    password = request.data.get("password", "")

    if not username or not password:
        return Response(
            {"message": "Username and password are required."},
            status=400,
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {"message": "Invalid username or password."},
            status=401,
        )

    if not is_platform_admin(user):
        return Response(
            {
                "message": (
                    "You do not have permission to access "
                    "the UNIT administration portal."
                )
            },
            status=403,
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "message": "Signed in successfully.",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": serialize_admin(user),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_me(request):
    user = request.user

    if not is_platform_admin(user):
        return Response(
            {"message": "Administrator access required."},
            status=403,
        )

    return Response({
        "user": serialize_admin(user),
    })
