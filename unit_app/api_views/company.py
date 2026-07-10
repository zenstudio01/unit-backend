from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_companies(request):
    try:
        companies = Company.objects.all().order_by("-created_at")

        data = []

        for company in companies:
            data.append({
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "phone_number": company.phone_number,
                "description": company.description,
                "logo": company.logo,
                "address": company.address,
                "city": company.city,
                "country": company.country,
                "service":company.service,
                "postal_code": company.postal_code,
                "created_at": company.created_at,
            })

        return JsonResponse({
            "success": True,
            "count": len(data),
            "companies": data
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }, status=500)




# get company profile
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_profile(request):
    try:
        company = Company.objects.get(owner=request.user)

        return JsonResponse({
            "success": True,
            "company": {
                "id": company.id,
                "company_name": company.name,
                "email": company.email,
                "phone": company.phone_number,
                "location": company.address,
                "description": company.description,
                "logo": company.logo,
                "city": company.city,
                "country": company.country,
                "website": company.website,
                "service":company.service,
                "postal_code": company.postal_code,
            }
        })

    except Company.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Company not found."
        }, status=404)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


# update company profile
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_company_profile(request):
    try:
        company = Company.objects.get(owner=request.user)

        company.name = request.data.get("company_name", company.name)
        company.email = request.data.get("email", company.email)
        company.phone_number = request.data.get("phone", company.phone_number)
        company.address = request.data.get("location", company.address)
        company.website = request.data.get("website", company.website)
        company.service = request.data.get("service", company.service)
        company.description = request.data.get("description", company.description)
        logo = request.FILES.get('logo', None)
        company.city = request.data.get("city", company.city)
        company.country = request.data.get("country", company.country)
        company.postal_code = request.data.get("postal_code", company.postal_code)
        
        logo_url = None
        if logo:
            upload_result = cloudinary.uploader.upload(logo)
            logo_url = upload_result.get("secure_url")
            company.logo = logo_url

        company.save()

        return JsonResponse({
            "success": True,
            "message": "Company profile updated successfully."
        })

    except Company.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Company not found."
        }, status=404)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)




# api to get one company
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company(request, company_id):
    try:
        company = Company.objects.get(id=company_id)

        return JsonResponse({
            "success": True,
            "company": {
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "phone": company.phone_number,
                "description": company.description,
                "logo": company.logo,
                "address": company.address,
                "city": company.city,
                "country": company.country,
                "service":company.service,
                "postal_code": company.postal_code,
                "website": getattr(company, "website", None),
                "created_at": company.created_at,
            }
        })

    except Company.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Company not found."
        }, status=404)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)



# book company
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_company(request):
    try:
        customer = request.user

        company_id = request.data.get("company_id")
        title = request.data.get("title")
        description = request.data.get("description")
        location = request.data.get("location")
        preferred_date = request.data.get("preferred_date")
        preferred_time = request.data.get("preferred_time")
        budget = request.data.get("budget")

        if not all([
            company_id,
            title,
            description,
            location,
            preferred_date,
            preferred_time,
        ]):
            return JsonResponse({
                "success": False,
                "message": "All required fields must be provided."
            }, status=400)

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Company not found."
            }, status=404)

        booking = CompanyBooking.objects.create(
            customer=customer,
            company=company,
            title=title,
            description=description,
            location=location,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            budget=budget if budget else None,
        )

        return JsonResponse({
            "success": True,
            "message": "Booking submitted successfully.",
            "booking_id": booking.id
        }, status=201)

    except Exception as e:
        print(f"Error {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)





