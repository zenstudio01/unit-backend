from .common_imports import *

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_statistics(request):
    try:
        user = request.user

        properties = Property.objects.filter(owner=user)
        units = Unit.objects.filter(property__owner=user)
        tenants = Tenant.objects.filter(unit__property__owner=user)

        total_properties = properties.count()
        total_units = units.count()

        occupied_units = units.filter(status="occupied").count()
        vacant_units = units.filter(status="available").count()

        occupancy_rate = (
            round((occupied_units / total_units) * 100, 1)
            if total_units > 0
            else 0
        )

        total_tenants = tenants.count()

        total_landlords = properties.values(
            "landlord"
        ).distinct().count()

        monthly_revenue = RentPayment.objects.filter(
            tenant__unit__property__owner=user,
            is_paid=True
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        pending_maintenance = MaintenanceRequest.objects.filter(
            unit__property__owner=user,
            status="pending"
        ).count()

        completed_maintenance = MaintenanceRequest.objects.filter(
            unit__property__owner=user,
            status="completed"
        ).count()

        recent_properties = Property.objects.filter(
            owner=user
        ).order_by("-created_at")[:5]

        recent_data = []

        for property in recent_properties:
            recent_data.append({
                "id": property.id,
                "name": property.name,
                "city": property.city,
                "status": property.status,
                "units": property.units.count(),
            })

        # Monthly revenue graph
        revenue_graph = []

        today = timezone.now()

        for i in range(5, -1, -1):

            month = today - timedelta(days=i * 30)

            total = RentPayment.objects.filter(
                tenant__unit__property__owner=user,
                is_paid=True,
                payment_date__year=month.year,
                payment_date__month=month.month
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            revenue_graph.append({
                "month": month.strftime("%b"),
                "revenue": float(total)
            })

        # Occupancy graph

        occupancy_graph = [
            {
                "name": "Occupied",
                "value": occupied_units
            },
            {
                "name": "Vacant",
                "value": vacant_units
            }
        ]

        return Response({

            "statistics": {

                "properties": total_properties,

                "units": total_units,

                "tenants": total_tenants,

                "landlords": total_landlords,

                "occupied_units": occupied_units,

                "vacant_units": vacant_units,

                "occupancy_rate": occupancy_rate,

                "monthly_revenue": float(monthly_revenue),

                "pending_maintenance": pending_maintenance,

                "completed_maintenance": completed_maintenance,

            },

            "revenue_graph": revenue_graph,

            "occupancy_graph": occupancy_graph,

            "recent_properties": recent_data,

        })

    except Exception as e:
        print(f"Error: {e}")
        return Response({"message": str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_summary(request):
    try:
        user = request.user

        payments = RentPayment.objects.filter(
            tenant__unit__property__owner=user
        )

        total_collected = payments.filter(
            is_paid=True
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        total_pending = payments.filter(
            is_paid=False
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        paid_transactions = payments.filter(
            is_paid=True
        ).count()

        pending_transactions = payments.filter(
            is_paid=False
        ).count()

        return Response({
            "success": True,
            "summary": {
                "total_collected": float(total_collected),
                "total_pending": float(total_pending),
                "paid_transactions": paid_transactions,
                "pending_transactions": pending_transactions,
                "total_transactions": payments.count()
            }
        })

    except Exception as e:
        return Response({
            "success": False,
            "message": str(e)
        }, status=500)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payments(request):
    try:

        user = request.user

        payments = RentPayment.objects.filter(
            tenant__unit__property__owner=user
        ).select_related(
            "tenant",
            "tenant__unit",
            "tenant__unit__property"
        ).order_by("-created_at")

        results = []

        for payment in payments:

            results.append({

                "id": payment.id,

                "tenant_name": payment.tenant.user.full_name,

                "phone_number": payment.tenant.user.phone_number,

                "property_name": payment.tenant.unit.property.name,

                "unit_name": payment.tenant.unit.name,

                "amount": float(payment.amount),

                "status": "Paid" if payment.is_paid else "Pending",

                "payment_method": payment.payment_method,

                "transaction_code": payment.transaction_id,

                "payment_date": payment.payment_date,

                "created_at": payment.created_at

            })

        return Response({

            "success": True,

            "count": len(results),

            "payments": results

        })

    except Exception as e:
        print(f"Error: {e}")
        return Response({"success": False, "message": str(e)}, status=500)




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_profile(request):
    user = request.user

    # Active Subscription
    subscription = (
        Subscription.objects
        .select_related("package")
        .filter(user=user, is_active=True)
        .order_by("-created_at")
        .first()
    )

    properties = Property.objects.filter(owner=user)

    property_count = properties.count()

    unit_count = Unit.objects.filter(property__owner=user).count()

    tenant_count = Tenant.objects.filter(
        unit__property__owner=user
    ).count()

    landlord_count = (
        properties.exclude(landlord=None)
        .values("landlord")
        .distinct()
        .count()
    )

    if subscription:
        remaining_days = max(
            (subscription.end_date.date() - timezone.now().date()).days,
            0,
        )

        package = subscription.package

        subscription_data = {
            "package": package.name.title(),
            "status": "Active" if subscription.is_active else "Expired",
            "billing_cycle": "Monthly",
            "monthly_price": float(package.monthly_price),
            "yearly_price": float(package.yearly_price),
            "expires_at": subscription.end_date.strftime("%d %B %Y"),
            "remaining_days": remaining_days,

            "limits": {
                "properties": package.number_of_units,
                "units": package.number_of_units,
            },

            "usage": {
                "properties": property_count,
                "units": unit_count,
            },

            "features": [
                "Property Management",
                "Unit Management",
                "Tenant Management",
                "Rent Collection",

                *(
                    ["M-Pesa Daraja"]
                    if package.mpesa_daraja
                    else []
                ),

                *(
                    ["Email Notifications"]
                    if package.email_notifications
                    else []
                ),

                f"Logs ({package.logs_duration} Days)"
            ]
        }

    else:

        subscription_data = {
            "package": "No Active Package",
            "status": "Inactive",
            "billing_cycle": "",
            "monthly_price": 0,
            "yearly_price": 0,
            "expires_at": "",
            "remaining_days": 0,
            "limits": {
                "properties": 0,
                "units": 0,
            },
            "usage": {
                "properties": property_count,
                "units": unit_count,
            },
            "features": []
        }

    return Response({

        "user": {
            "id": user.id,
            "name": user.full_name,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "profile_image": user.profile_image,
            "role": user.role.title(),
            "location": user.location,
            "joined": user.created_at.strftime("%d %B %Y"),
            "verified": user.is_verified,
        },

        "statistics": {
            "properties": property_count,
            "units": unit_count,
            "tenants": tenant_count,
            "landlords": landlord_count,
        },

        "subscription": subscription_data,
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def property_manager_maintenance_requests(request):

    properties = Property.objects.filter(owner=request.user)

    requests = MaintenanceRequest.objects.filter(
        property__in=properties
    ).order_by("-created_at")

    data = []

    for item in requests:
        data.append({
            "id": item.id,
            "tenant": item.tenant.user.full_name,
            "property": item.property.name,
            "unit": item.unit.name,
            "title": item.title,
            "description": item.description,
            "priority": item.priority,
            "status": item.status,
            "created_at": item.created_at
        })

    return JsonResponse({
        "requests": data
    })



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_maintenance_status(request, request_id):

    maintenance = MaintenanceRequest.objects.filter(
        id=request_id
    ).first()

    if not maintenance:
        return JsonResponse({
            "message": "Maintenance request not found."
        }, status=404)

    status = request.data.get("status")

    valid_status = [
        "pending",
        "in_progress",
        "completed",
        "cancelled"
    ]

    if status not in valid_status:
        return JsonResponse({
            "message": "Invalid status."
        }, status=400)

    maintenance.status = status
    maintenance.save()

    return JsonResponse({
        "success": True,
        "message": "Maintenance request updated successfully."
    })


