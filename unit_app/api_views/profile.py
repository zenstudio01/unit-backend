from .common_imports import *


@api_view(["PATCH", "POST"])
@permission_classes([IsAuthenticated])
def complete_profile(request):
    user = request.user
    data = request.data

    national_id_number = str(
        data.get("national_id_number", "")
    ).strip()

    kra_pin = str(
        data.get("kra_pin", "")
    ).strip()

    gender = str(
        data.get("gender", "")
    ).strip()

    date_of_birth_raw = str(
        data.get("date_of_birth", "")
    ).strip()

    county = str(
        data.get("county", "")
    ).strip()

    city = str(
        data.get("city", "")
    ).strip()

    address = str(
        data.get("address", "")
    ).strip()

    if not county or not city:
        return JsonResponse(
            {
                "message":
                    "County and city are required."
            },
            status=400,
        )

    date_of_birth = None

    if date_of_birth_raw:
        date_of_birth = parse_date(
            date_of_birth_raw
        )

        if not date_of_birth:
            return JsonResponse(
                {
                    "message":
                        "Date of birth must use YYYY-MM-DD format."
                },
                status=400,
            )

    try:
        with transaction.atomic():
            profile, created = (
                UserProfile.objects.get_or_create(
                    user=user
                )
            )

            profile.national_id_number = (
                national_id_number or None
            )

            profile.kra_pin = (
                kra_pin or None
            )

            profile.gender = (
                gender or None
            )

            profile.date_of_birth = (
                date_of_birth
            )

            profile.county = county
            profile.city = city

            profile.address = (
                address or None
            )

            profile.save()

        return JsonResponse(
            {
                "message":
                    "Profile completed successfully.",

                "requested_role":
                    user.requested_role,

                "next_step":
                    "create_or_join_organization",

                "profile": {
                    "national_id_number":
                        profile.national_id_number,

                    "kra_pin":
                        profile.kra_pin,

                    "gender":
                        profile.gender,

                    "date_of_birth":
                        (
                            profile.date_of_birth.isoformat()
                            if profile.date_of_birth
                            else None
                        ),

                    "county":
                        profile.county,

                    "city":
                        profile.city,

                    "address":
                        profile.address,
                },
            },
            status=200,
        )

    except Exception as error:
        print(
            "COMPLETE PROFILE ERROR:",
            str(error),
        )

        return JsonResponse(
            {
                "message":
                    "Unable to complete profile."
            },
            status=500,
        )