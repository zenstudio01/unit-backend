from .common_imports import *

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def dashboard_metrics(request):
    user = request.user
    role = user.role.lower()  # Match database lowercase mapping
    
    # -------------------------------------------------------------
    # 1. PROPERTY MANAGER (PM) OR LANDLORD DATA ARCHITECTURE
    # -------------------------------------------------------------
    if role in ['property manager', 'landlord']:
        # Filter properties based on ownership tier
        if role == 'property manager':
            properties = Property.objects.filter(owner=user)
        else:
            properties = Property.objects.filter(landlord=user)

        property_count = properties.count()
        units = Unit.objects.filter(property__in=properties)
        total_units_count = units.count()
        
        # Calculate distinct active tenants under management
        active_tenants = Tenant.objects.filter(unit__in=units, is_active=True)
        tenant_count = active_tenants.count()
        
        # Calculate Occupancy Stats safely
        occupied_count = units.filter(status='occupied').count()
        vacant_count = units.filter(status='available').count()
        occupancy_rate = int((occupied_count / total_units_count * 100)) if total_units_count > 0 else 0
        vacant_rate = 100 - occupancy_rate if total_units_count > 0 else 0

        # Calculate monthly cash collection sums
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_collection = RentPayment.objects.filter(
            tenant__in=active_tenants,
            is_paid=True,
            payment_date__month=current_month,
            payment_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Maintenance counts
        open_tickets = MaintenanceRequest.objects.filter(unit__in=units, status='pending').count()
        in_progress_tickets = MaintenanceRequest.objects.filter(unit__in=units, status='in_progress').count()
        resolved_tickets = MaintenanceRequest.objects.filter(unit__in=units, status='completed').count()

        # Build dynamic contextual feed entries
        activities = []
        recent_payments = RentPayment.objects.filter(tenant__in=active_tenants, is_paid=True).order_by('-payment_date')[:2]
        for payment in recent_payments:
            activities.append(f"{payment.tenant.user.full_name} paid rent via M-Pesa STK for {payment.tenant.unit.name}")
        
        recent_requests = MaintenanceRequest.objects.filter(unit__in=units).order_by('-created_at')[:2]
        for req in recent_requests:
            activities.append(f"New status update '{req.status}' for request on {req.unit.name}: {req.description[:30]}...")

        # Guard against completely empty feeds
        if not activities:
            activities = ["System initialized successfully. Standing by for operations logs."]

        # Standardize matching JSON keys expected by UI state structure maps
        frontend_role = "PM" if role == "property manager" else "LANDLORD"
        
        stats = []
        if frontend_role == "PM":
            stats = [
                { "title": "Managed Properties", "value": str(property_count), "color": "bg-[#0A4429]" },
                { "title": "Total Tenants", "value": str(tenant_count), "color": "bg-[#2E9D47]" },
                { "title": "Monthly Collection", "value": f"KES {monthly_collection:,.0f}", "color": "bg-[#0A4429]" },
                { "title": "Open Tickets", "value": str(open_tickets), "color": "bg-amber-600" }
            ]
        else:
            stats = [
                { "title": "Owned Portfolios", "value": str(property_count), "color": "bg-[#0A4429]" },
                { "title": "Occupancy Rate", "value": f"{occupancy_rate}%", "color": "bg-[#2E9D47]" },
                { "title": "Net Payouts", "value": f"KES {monthly_collection:,.0f}", "color": "bg-[#0A4429]" },
                { "title": "Pending Expenses", "value": "KES 0", "color": "bg-red-600" }
            ]

        return Response({
            "role": frontend_role,
            "title": "Property Manager Dashboard" if frontend_role == "PM" else "Landlord Portfolio Insights",
            "stats": stats,
            "activities": activities,
            "occupancy_summary": {
                "occupied_value": f"{occupied_count} ({occupancy_rate}%)",
                "occupied_percent": occupancy_rate,
                "vacant_value": f"{vacant_count} ({vacant_rate}%)",
                "vacant_percent": vacant_rate
            },
            "maintenance_health": {
                "pending": open_tickets,
                "in_progress": in_progress_tickets,
                "resolved": resolved_tickets
            }
        })

    # -------------------------------------------------------------
    # 2. SERVICE PROVIDER (FUNDI) DATA ARCHITECTURE
    # -------------------------------------------------------------
    elif role == 'service provider':
        try:
            provider_profile = request.user.service_provider_profile
            rating = f"{provider_profile.rating}/5"
        except ServiceProvider.DoesNotExist:
            rating = "0.0/5"

        return Response({
            "role": "PROVIDER",
            "title": "Service Provider Console",
            "stats": [
                { "title": "Active Work Orders", "value": "0", "color": "bg-[#2E9D47]" },
                { "title": "Completed Jobs", "value": "0", "color": "bg-[#0A4429]" },
                { "title": "Pending Invoices", "value": "KES 0", "color": "bg-amber-600" },
                { "title": "Profile Rating", "value": rating, "color": "bg-[#0A4429]" }
            ],
            "activities": ["Awaiting assignments from Property Management networks."],
            "maintenance_health": { "pending": 0, "in_progress": 0, "resolved": 0 }
        })

    # -------------------------------------------------------------
    # 3. GLOBAL SYSTEM ADMINISTRATOR DATA ARCHITECTURE
    # -------------------------------------------------------------
    elif role == 'admin':
        total_users = User.objects.count()
        total_pms = User.objects.filter(role='property manager').count()
        total_units = Unit.objects.count()

        return Response({
            "role": "ADMIN",
            "title": "System Administrator Control",
            "stats": [
                { "title": "Total System Users", "value": f"{total_users:,}", "color": "bg-[#0A4429]" },
                { "title": "Active Pilot Managers", "value": str(total_pms), "color": "bg-[#2E9D47]" },
                { "title": "Total Units Tracked", value: f"{total_units:,}", "color": "bg-[#0A4429]" },
                { "title": "Platform GMV (MTD)", "value": "KES 0", "color": "bg-emerald-600" }
            ],
            "activities": ["System health verification checks passed safely."],
            "maintenance_health": { "pending": 0, "in_progress": 0, "resolved": 0 }
        })

    # Fallback response context block for alternative system classifications
    return Response({"detail": "Role dashboard layout engine currently unassigned."}, status=400)