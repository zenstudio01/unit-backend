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



# get company bookings api
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company_bookings(request):
    try:
        # Get the logged-in user's company
        company = Company.objects.get(owner=request.user)

        # Get all bookings for that company
        bookings = CompanyBooking.objects.filter(
            company=company
        ).select_related("customer").order_by("-created_at")

        data = []

        for booking in bookings:
            data.append({
                "id": booking.id,
                "customer_id": booking.customer.id,
                "customer_name": booking.customer.full_name,
                "customer_email": booking.customer.email,

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
            "bookings": data,
        }, status=200)

    except Company.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "You don't have a registered company."
        }, status=404)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)




# company dashboard
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_dashboard(request):
    try:
        company = Company.objects.get(owner=request.user)

        pending_requests = CompanyBooking.objects.filter(
            company=company,
            status="pending"
        ).count()

        in_progress = CompanyBooking.objects.filter(
            company=company,
            status="accepted"
        ).count()

        completed_jobs = CompanyBooking.objects.filter(
            company=company,
            status="completed"
        ).count()

        total_revenue = CompanyBookingPayment.objects.filter(
            company_booking__company=company,
            payment_status="success"
        ).aggregate(
            total=Sum("revenue")
        )["total"] or Decimal("0.00")

        total_bookings = CompanyBooking.objects.filter(
            company=company
        ).count()

        return JsonResponse({
            "success": True,
            "dashboard": {
                "company_name": company.name,
                "pending_requests": pending_requests,
                "in_progress": in_progress,
                "completed_jobs": completed_jobs,
                "total_bookings": total_bookings,
                "total_revenue": float(total_revenue),
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




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_booking(request, booking_id):
    try:
        company = Company.objects.get(owner=request.user)

        booking = get_object_or_404(
            CompanyBooking,
            id=booking_id,
            company=company
        )

        if booking.status != "pending":
            return JsonResponse(
                {"message": "This booking is no longer pending."},
                status=400
            )

        booking.status = "accepted"
        booking.save()

        # Notify the customer
        if booking.customer.expo_token:
            send_push_notification(
                booking.customer.expo_token,
                title="Booking Accepted",
                body=f"{company.name} has accepted your booking request.",
                data={
                    "booking_id": booking.id,
                    "status": "accepted",
                },
            )

        return JsonResponse({
            "message": "Booking accepted successfully.",
            "status": booking.status
        })

    except Company.DoesNotExist:
        return JsonResponse({
            "message": "Company not found."
        }, status=404)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            "message": str(e)
        }, status=500)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_booking(request, booking_id):
    try:
        company = Company.objects.get(owner=request.user)

        booking = get_object_or_404(
            CompanyBooking,
            id=booking_id,
            company=company
        )

        if booking.status != "pending":
            return JsonResponse(
                {"message": "This booking cannot be rejected."},
                status=400
            )

        booking.status = "rejected"
        booking.save()

        # Notify the customer
        if booking.customer.expo_token:
            send_push_notification(
                booking.customer.expo_token,
                title="Booking Rejected",
                body=f"{company.name} has declined your booking request.",
                data={
                    "booking_id": booking.id,
                    "status": "rejected",
                },
            )

        return JsonResponse({
            "message": "Booking rejected successfully."
        })

    except Company.DoesNotExist:
        return JsonResponse({
            "message": "Company not found."
        }, status=404)

    except Exception as e:
        return JsonResponse({
            "message": str(e)
        }, status=500)
