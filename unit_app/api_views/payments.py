from .common_imports import *


PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe_plan(request):
    customer = request.user

    # Only clients can book workers
    if customer.role != "client":
        return Response({"message": "Only clients can book workers."}, status=status.HTTP_403_FORBIDDEN)


    email = request.data.get("email")
    company_id = request.data.get("company_id")
    title = request.data.get("title")
    description = request.data.get("description")
    location = request.data.get("location")
    preferred_date = request.data.get("preferred_date")
    preferred_time = request.data.get("preferred_time")
    budget = request.data.get("budget")
    # print(f"Email: {email}")

    print(f"Title: {title}")

    required_fields = [email, company_id,title, description, budget, location, preferred_date, preferred_time]

    if not all(required_fields):
        return Response({"message": "All required fields must be provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        company = Company.objects.get(id=company_id, is_available=True)
    except Company.DoesNotExist:
        return Response({"message": "Company not found."},status=status.HTTP_404_NOT_FOUND)
    

    amount = int(budget) * 100  # Paystack uses kobo/cents

    # work_sample_image_url = None
    # if work_sample_image:
    #     upload_result = cloudinary.uploader.upload(work_sample_image)
    #     work_sample_image_url = upload_result.get("secure_url")

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": amount,
        "callback_url": "https://fea7-129-222-147-94.ngrok-free.app/payment_callback/",
        "metadata": {
            "user_id": customer.id,
        }
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload,
        headers=headers
    )

    data = response.json()

    if data.get("status"):

        authorization_url = data["data"]["authorization_url"]
        reference = data["data"]["reference"]

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
        # calculate revue
        revenue = Decimal(str(budget)) * Decimal("0.15")

        # Save pending payment
        CompanyBookingPayment.objects.create(
            company_booking=booking,
            amount=budget,
            revenue=revenue,
            payment_method="paystack",
            payment_status="pending",
            paid_at=timezone.now(),
            receipt_number=reference
        )

        return Response({
            "authorization_url": authorization_url,
            "reference": reference,
            "data": data
        })
    print("Paystack initialization failed:", data)
    return Response({
        "message": "Failed to initialize payment",
        "paystack_response": data
    }, status=400)


@api_view(["GET"])
def verify_payment(request, reference):

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    )

    data = response.json()

    if data["data"]["status"] == "success":

        payment = CompanyBookingPayment.objects.get(receipt_number=reference)
        payment.payment_status = "verified"
        payment.save()

        company_booking = payment.company_booking
        company_booking.payment_status = "verified"
        company_booking.save()

        return Response({"message": "Payment verified"})

    return Response({"message": "Payment not successful"}, status=400)



@api_view(["GET"])
def payment_callback(request):
    reference = request.GET.get("reference")

    if not reference:
        return Response({"message": "Reference not provided"}, status=400)

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"

    response = requests.get(verify_url, headers=headers)
    data = response.json()

    if not data.get("status"):
        return Response({
            "message": "Payment verification failed",
            "paystack_response": data
        }, status=400)

    payment_data = data["data"]

    if payment_data["status"] == "success":

        try:
            payment = CompanyBookingPayment.objects.get(receipt_number=reference)

            payment.payment_status = "paid"
            payment.paid_at = timezone.now()
            payment.save()

            company_booking = payment.company_booking
            company_booking.payment_status = "paid"
            company_booking.save()

            # save company share
            company_share = payment.amount * Decimal("0.85")
            company_payment, created = CompanyWallet.objects.get_or_create(company=company_booking.company)
            company_payment.amount += company_share
            company_payment.float_amount = company_share
            company_payment.save()

            Notification.objects.create(
                user=payment.company_booking.owner,
                title=f"Payment confirmation.",
                message=f"{payment.receipt_number} Confirmed. Pyament of Ksh. {payment.amount} received successfully.",
                msg_type='payment'
            )

            # send push notification
            send_push_notification(
                payment.company_booking.company.owner.expo_token, 
                title="New Booking Request",
                body=f"You have a new booking request from {payment.company_booking.owner.full_name}.",
                data={"screen": "BookingDetails", "booking_id": ""}
            )

            # send notification
            Notification.objects.create(
                user=payment.job.worker.user,
                title=f"New Booking Request",
                message=f"You have a new booking request from {payment.company_booking.owner.full_name}.",
                msg_type='booking'
            )

            return Response({
                "message": "Payment verified successfully",
            })

        except CompanyBookingPayment.DoesNotExist:
            return Response({"message": "Payment record not found"}, status=404)

    return Response({
        "message": "Payment not successful"
    }, status=400)




# pay for house
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_property(request):
    customer = request.user

    # Only clients can book workers
    if customer.role != "client":
        return Response({"message": "Only clients can book properties."}, status=status.HTTP_403_FORBIDDEN)


    email = request.data.get("email")
    unit_id = request.data.get("unit_id")
    amount = request.data.get("amount")
    # print(f"Email: {email}")


    required_fields = [email, unit_id, amount]

    if not all(required_fields):
        return Response({"message": "All required fields must be provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        unit = Unit.objects.get(id=unit_id, status="available")
    except Unit.DoesNotExist:
        return Response({"message": "Unit not found."},status=status.HTTP_404_NOT_FOUND)
    

    amount = int(float(amount) * 100)  # Paystack uses kobo/cents

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": amount,
        "callback_url": "https://fea7-129-222-147-94.ngrok-free.app/property_booking_payment_callback/",
        "metadata": {
            "user_id": customer.id,
        }
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=payload,
        headers=headers
    )

    data = response.json()

    if data.get("status"):

        authorization_url = data["data"]["authorization_url"]
        reference = data["data"]["reference"]

        property_booking = PropertyBooking.objects.create(
            customer=customer,
            unit=unit
        )
        # calculate revue
        revenue = Decimal(str(amount)) * Decimal("0.15")

        # Save pending payment
        PropertyBookingPayment.objects.create(
            property_booking=property_booking,
            amount=amount,
            revenue=revenue,
            payment_method="paystack",
            payment_status="pending",
            paid_at=timezone.now(),
            receipt_number=reference
        )

        return Response({
            "authorization_url": authorization_url,
            "reference": reference,
            "data": data
        })
    print("Paystack initialization failed:", data)
    return Response({
        "message": "Failed to initialize payment",
        "paystack_response": data
    }, status=400)


@api_view(["GET"])
def verify_property_booking_payment(request, reference):

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    )

    data = response.json()

    if data["data"]["status"] == "success":

        payment = PropertyBookingPayment.objects.get(receipt_number=reference)
        payment.payment_status = "verified"
        payment.save()

        property_booking = payment.property_booking
        property_booking.payment_status = "verified"
        property_booking.save()

        return Response({"message": "Payment verified"})

    return Response({"message": "Payment not successful"}, status=400)



@api_view(["GET"])
def property_booking_payment_callback(request):
    reference = request.GET.get("reference")

    if not reference:
        return Response({"message": "Reference not provided"}, status=400)

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"

    response = requests.get(verify_url, headers=headers)
    data = response.json()

    if not data.get("status"):
        return Response({
            "message": "Payment verification failed",
            "paystack_response": data
        }, status=400)

    payment_data = data["data"]

    if payment_data["status"] == "success":

        try:
            payment = PropertyBookingPayment.objects.get(receipt_number=reference)

            payment.payment_status = "paid"
            payment.paid_at = timezone.now()
            payment.save()

            property_booking = payment.property_booking
            property_booking.payment_status = "paid"
            property_booking.save()

            unit = payment.property_booking.unit
            unit.status = "occupied"
            unit.save()

            # save propety manager share
            property_manager_share = payment.amount * Decimal("0.85")
            property_payment, created = PropManagerWallet.objects.get_or_create(user=property_booking.unit.property.owner)
            property_payment.amount += property_manager_share
            property_payment.float_amount = property_manager_share
            property_payment.save()

            Notification.objects.create(
                user=payment.property_booking.customer,
                title=f"Payment confirmation.",
                message=f"{payment.receipt_number} Confirmed. Pyament of Ksh. {payment.amount} received successfully.",
                msg_type='payment'
            )


            # send notification
            Notification.objects.create(
                user=payment.property_booking.unit.property.owner,
                title=f"New Booking Request",
                message=f"You have a new booking request from {payment.property_booking.customer.full_name}.",
                msg_type='booking'
            )

            return Response({
                "message": "Payment verified successfully",
            })

        except PropertyBookingPayment.DoesNotExist:
            return Response({"message": "Payment record not found"}, status=404)

    return Response({
        "message": "Payment not successful"
    }, status=400)