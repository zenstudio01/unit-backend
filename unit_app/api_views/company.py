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
# @api_view(["PUT"])
# @permission_classes([IsAuthenticated])
# def update_company_profile(request):
#     try:
#         company = Company.objects.get(owner=request.user)

#         company.name = request.data.get("company_name", company.name)
#         company.email = request.data.get("email", company.email)
#         company.phone_number = request.data.get("phone", company.phone_number)
#         company.address = request.data.get("location", company.address)
#         company.website = request.data.get("website", company.website)
#         company.service = request.data.get("service", company.service)
#         company.description = request.data.get("description", company.description)
#         logo = request.FILES.get('logo', None)
#         company.city = request.data.get("city", company.city)
#         company.country = request.data.get("country", company.country)
#         company.postal_code = request.data.get("postal_code", company.postal_code)
        
#         logo_url = None
#         if logo:
#             upload_result = cloudinary.uploader.upload(logo)
#             logo_url = upload_result.get("secure_url")
#             company.logo = logo_url

#         company.save()

#         return JsonResponse({
#             "success": True,
#             "message": "Company profile updated successfully."
#         })

#     except Company.DoesNotExist:
#         return JsonResponse({
#             "success": False,
#             "message": "Company not found."
#         }, status=404)

#     except Exception as e:
#         print(f"Error: {e}")
#         return JsonResponse({
#             "success": False,
#             "message": str(e)
#         }, status=500)




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
def old_company_dashboard(request):
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



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_dashboard(request):
    user = request.user

    try:
        company = Company.objects.get(owner=user)
    except Company.DoesNotExist:
        print("Company not found")
        return JsonResponse(
            {
                "success": False,
                "message": "Company not found."
            },
            status=404
        )

    bookings = CompanyBooking.objects.filter(company=company)

    payments = CompanyBookingPayment.objects.filter(
        company_booking__company=company,
        payment_status="success"
    )

    wallet = CompanyWallet.objects.filter(company=company).first()

    professionals = Professional.objects.filter(company=company)

    # -----------------------------
    # Summary
    # -----------------------------

    total_bookings = bookings.count()

    pending_bookings = bookings.filter(
        status="pending"
    ).count()

    accepted_bookings = bookings.filter(
        status="accepted"
    ).count()

    completed_bookings = bookings.filter(
        status="completed"
    ).count()

    rejected_bookings = bookings.filter(
        status="rejected"
    ).count()

    total_revenue = payments.aggregate(
        total=Sum("revenue")
    )["total"] or 0

    total_earnings = payments.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # -----------------------------
    # Monthly Revenue
    # -----------------------------

    monthly_revenue = (
        payments
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(amount=Sum("revenue"))
        .order_by("month")
    )

    monthly_revenue_data = [
        {
            "month": item["month"].strftime("%b"),
            "amount": float(item["amount"])
        }
        for item in monthly_revenue
    ]

    # -----------------------------
    # Monthly Bookings
    # -----------------------------

    monthly_bookings = (
        bookings
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(bookings=Count("id"))
        .order_by("month")
    )

    monthly_booking_data = [
        {
            "month": item["month"].strftime("%b"),
            "bookings": item["bookings"]
        }
        for item in monthly_bookings
    ]

    # -----------------------------
    # Booking Status
    # -----------------------------

    booking_status = [
        {
            "status": "Pending",
            "value": pending_bookings
        },
        {
            "status": "Accepted",
            "value": accepted_bookings
        },
        {
            "status": "Completed",
            "value": completed_bookings
        },
        {
            "status": "Rejected",
            "value": rejected_bookings
        },
    ]

    # -----------------------------
    # Recent Bookings
    # -----------------------------

    recent_bookings = []

    for booking in bookings.order_by("-created_at")[:10]:

        recent_bookings.append({
            "id": booking.id,
            "customer": booking.customer.full_name,
            "title": booking.title,
            "budget": float(booking.budget or 0),
            "status": booking.status,
            "location": booking.location,
            "preferred_date": booking.preferred_date,
            "preferred_time": str(booking.preferred_time),
            "created_at": booking.created_at,
        })

    # -----------------------------
    # Company Information
    # -----------------------------

    company_data = {
        "id": company.id,
        "name": company.name,
        "logo": company.logo,
        "service": company.service,
        "email": company.email,
        "phone_number": company.phone_number,
        "website": company.website,
        "city": company.city,
        "country": company.country,
        "professionals": professionals.count(),
    }

    # -----------------------------
    # Wallet
    # -----------------------------

    wallet_data = {
        "available_balance": float(wallet.amount) if wallet else 0,
        "pending_balance": float(wallet.pending_amount) if wallet else 0,
        "float_balance": float(wallet.float_amount) if wallet else 0,
    }

    return JsonResponse({

        "success": True,

        "summary": {

            "total_bookings": total_bookings,

            "pending_bookings": pending_bookings,

            "completed_bookings": completed_bookings,

            "wallet_balance": wallet_data["available_balance"],

            "total_revenue": float(total_revenue),

            "total_earnings": float(total_earnings),

            "professionals": professionals.count(),

        },

        "company": company_data,

        "wallet": wallet_data,

        "monthly_revenue": monthly_revenue_data,

        "monthly_bookings": monthly_booking_data,

        "booking_status": booking_status,

        "recent_bookings": recent_bookings,

    })





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_profile(request):

    user = request.user

    try:
        company = Company.objects.get(owner=user)

    except Company.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Company not found."
            },
            status=404
        )

    professionals = Professional.objects.filter(company=company).count()

    bookings = CompanyBooking.objects.filter(company=company)

    completed_jobs = bookings.filter(status="completed").count()

    wallet = CompanyWallet.objects.filter(company=company).first()

    wallet_balance = wallet.amount if wallet else 0

    data = {
        "company": {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "phone_number": company.phone_number,
            "description": company.description,
            "logo": company.logo,
            "website": company.website,
            "service": company.service,
            "address": company.address,
            "city": company.city,
            "country": company.country,
            "postal_code": company.postal_code,
            "is_available": company.is_available,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
        },

        "statistics": {

            "professionals": professionals,

            "bookings": bookings.count(),

            "completed_jobs": completed_jobs,

            "wallet": float(wallet_balance)

        }
    }

    return JsonResponse(data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_company_profile(request):

    user = request.user

    try:
        company = Company.objects.get(owner=user)

    except Company.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Company not found."
            },
            status=404
        )

    data = request.data

    company.name = data.get("name", company.name)

    company.email = data.get("email", company.email)

    company.phone_number = data.get(
        "phone_number",
        company.phone_number
    )

    company.description = data.get(
        "description",
        company.description
    )

    company.logo = data.get(
        "logo",
        company.logo
    )

    company.website = data.get(
        "website",
        company.website
    )

    company.service = data.get(
        "service",
        company.service
    )

    company.address = data.get(
        "address",
        company.address
    )

    company.city = data.get(
        "city",
        company.city
    )

    company.country = data.get(
        "country",
        company.country
    )

    company.postal_code = data.get(
        "postal_code",
        company.postal_code
    )

    company.is_available = data.get(
        "is_available",
        company.is_available
    )

    company.save()

    return JsonResponse({

        "success": True,

        "message": "Company profile updated successfully."

    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_professionals(request):

    try:
        company = Company.objects.get(owner=request.user)

    except Company.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Company not found."
            },
            status=404
        )

    professionals = Professional.objects.filter(company=company)

    data = []

    for professional in professionals:

        data.append({

            "id": professional.id,

            "professional_title": professional.professional_title,

            "years_of_experience": professional.years_of_experience,

            "bio": professional.bio,

            "user": {

                "id": professional.user.id,

                "full_name": professional.user.full_name,

                "email": professional.user.email,

                "phone_number": professional.user.phone_number,

                "username": professional.user.username,

                "profile_image": professional.user.profile_image,

                "is_active": professional.user.is_active,

            }

        })

    return JsonResponse({

        "professionals": data

    })



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_professional(request):

    try:
        company = Company.objects.get(owner=request.user)

    except Company.DoesNotExist:

        return JsonResponse({

            "success": False,

            "message": "Company not found."

        }, status=404)

    data = request.data

    if User.objects.filter(username=data["username"]).exists():
        print("Username already exists.")
        return JsonResponse({

            "success": False,

            "message": "Username already exists."

        }, status=400)

    if User.objects.filter(phone_number=data["phone_number"]).exists():
        print("Phone number already exists.")
        return JsonResponse({

            "success": False,

            "message": "Phone number already exists."

        }, status=400)

    user = User.objects.create_user(

        username=data["username"],

        email=data["email"],

        password=data["password"],

        full_name=data["full_name"],

        phone_number=data["phone_number"],

        role="company admin"

    )

    Professional.objects.create(

        user=user,

        company=company,

        professional_title=data["professional_title"],

        years_of_experience=data["years_of_experience"],

        bio=data.get("bio", "")

    )

    return JsonResponse({

        "success": True,

        "message": "Professional added successfully."

    })


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_professional(request, id):

    try:

        company = Company.objects.get(owner=request.user)

        professional = Professional.objects.get(

            id=id,

            company=company

        )

    except (Company.DoesNotExist, Professional.DoesNotExist):

        return JsonResponse({

            "success": False,

            "message": "Professional not found."

        }, status=404)

    data = request.data

    user = professional.user

    user.full_name = data.get("full_name", user.full_name)

    user.email = data.get("email", user.email)

    user.phone_number = data.get(
        "phone_number",
        user.phone_number
    )

    user.username = data.get(
        "username",
        user.username
    )

    user.save()

    professional.professional_title = data.get(

        "professional_title",

        professional.professional_title

    )

    professional.years_of_experience = data.get(

        "years_of_experience",

        professional.years_of_experience

    )

    professional.bio = data.get(

        "bio",

        professional.bio

    )

    professional.save()

    return JsonResponse({

        "success": True,

        "message": "Professional updated successfully."

    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_professional(request, id):

    try:

        company = Company.objects.get(owner=request.user)

        professional = Professional.objects.get(

            id=id,

            company=company

        )

    except (Company.DoesNotExist, Professional.DoesNotExist):

        return JsonResponse({

            "success": False,

            "message": "Professional not found."

        }, status=404)

    user = professional.user

    professional.delete()

    user.delete()

    return JsonResponse({

        "success": True,

        "message": "Professional deleted successfully."

    })




