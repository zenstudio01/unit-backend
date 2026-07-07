from .common_imports import *

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    """
    Paginated master search view. Computes sub-assets and returns
    comprehensive operational summaries across all profiles.
    """
    try:
        queryset = User.objects.all().order_by('-created_at')

        # 1. Apply Filtering Vectors
        search_query = request.GET.get('search', '')
        role_filter = request.GET.get('role', '')
        status_filter = request.GET.get('status', '')

        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(username__icontains=search_query)
            )

        if role_filter:
            queryset = queryset.filter(role__iexact=role_filter)

        if status_filter == 'verified':
            queryset = queryset.filter(is_verified=True)
        elif status_filter == 'unverified':
            queryset = queryset.filter(is_verified=False)
        elif status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)

        # 2. Extract Analytical Metric Summaries
        summary_data = {
            "total": User.objects.count(),
            "pm": User.objects.filter(role='property manager').count(),
            "landlord": User.objects.filter(role='landlord').count(),
            "tenant": User.objects.filter(role='tenant').count(),
            "provider": User.objects.filter(role='service provider').count(),
        }

        # 3. Simple Manual Frame Pagination Logic
        page = int(request.GET.get('page', 1))
        limit = 10
        start = (page - 1) * limit
        end = start + limit

        total_count = queryset.count()
        paginated_users = queryset[start:end]

        serialized_results = []

        for u in paginated_users:
            # Determine the user's infrastructure assets count dynamically
            assets_count = 0

            if u.role == 'property manager':
                assets_count = Property.objects.filter(owner=u).count()
            elif u.role == 'landlord':
                assets_count = Property.objects.filter(landlord=u).count()

            serialized_results.append({
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "phone_number": u.phone_number,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "profile_image": u.profile_image,
                "id_front_image": u.id_front_image,
                "id_back_image": u.id_back_image,
                "assets_count": assets_count,
                "created_at": u.created_at.isoformat(),
            })

        return Response({
            "count": total_count,
            "summary": summary_data,
            "results": serialized_results
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "An error occurred while retrieving users.",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_toggle_active(request, pk):
    try:
        user_node = User.objects.get(pk=pk)
        user_node.is_active = not user_node.is_active
        user_node.save()
        return Response({"detail": f"State set to {user_node.is_active}"}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "User record lookup miss."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_verify_user(request, pk):
    try:
        user_node = User.objects.get(pk=pk)
        user_node.is_verified = True
        user_node.save()
        return Response({"detail": "Identity clearances committed successfully."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "User record lookup miss."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reset_password(request, pk):
    try:
        user_node = User.objects.get(pk=pk)
        # Construct an instantly generated temporary system override bypass key
        temp_secret = str(uuid.uuid4())[:8]
        user_node.set_password(temp_secret)
        user_node.save()
        return Response({"temporary_password": temp_secret}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "User record lookup miss."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_update_profile(request, pk):
    try:
        user_node = User.objects.get(pk=pk)
        user_node.role = request.data.get('role', user_node.role)
        user_node.is_active = request.data.get('is_active', user_node.is_active)
        user_node.save()
        return Response({"detail": "Profile parameters updated smoothly."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "User record lookup miss."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_user(request, pk):
    try:
        user_node = User.objects.get(pk=pk)
        user_node.delete()
        return Response({"detail": "User completely removed from system rows."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "User record lookup miss."}, status=status.HTTP_404_NOT_FOUND)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_metrics(request):
    """
    Assembles platform analytics data, transactional statistics, 
    and recent activity timelines for the system administrator overview.
    """
    timeframe = request.GET.get('timeframe', 'this_month')

    # 1. Gather Global Summary Counts
    total_users_count = User.objects.count()
    total_units_count = Unit.objects.count()
    occupied_units_count = Unit.objects.filter(status='occupied').count()
    open_tickets_count = MaintenanceRequest.objects.filter(status='pending').count()

    # Safely compute occupancy percent
    occupancy_rate_pct = int((occupied_units_count / total_units_count * 100)) if total_units_count > 0 else 0

    # 2. Compute Financial GMV Sums (Simulating payment channel history aggregates)
    gmv_volume_total = RentPayment.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0

    # 3. Compile Demographic Segment Sets for Chart Proportions
    demographics_queryset = User.objects.values('role').annotate(count=Count('id'))
    role_mapping = {
        'admin': 'Admin',
        'property manager': 'PMs',
        'landlord': 'Landlords',
        'tenant': 'Tenants',
        'service provider': 'Providers'
    }
    
    demographics_chart_data = []
    # Instantiate zeroed baseline targets to ensure structured data visualization output
    count_by_role = {role: 0 for role in role_mapping.keys()}
    for entry in demographics_queryset:
        r_type = entry['role'].lower()
        if r_type in count_by_role:
            count_by_role[r_type] = entry['count']

    for db_role, ui_label in role_mapping.items():
        demographics_chart_data.append({
            "role": ui_label,
            "count": count_by_role[db_role]
        })

    # 4. Generate Revenue Timeline Segments (Mocking historical trends)
    revenue_chart_history = [
        {"name": "Jan", "volume": int(gmv_volume_total * 0.4)},
        {"name": "Feb", "volume": int(gmv_volume_total * 0.55)},
        {"name": "Mar", "volume": int(gmv_volume_total * 0.7)},
        {"name": "Apr", "volume": int(gmv_volume_total * 0.82)},
        {"name": "May", "volume": int(gmv_volume_total * 0.95)},
        {"name": "Jun", "volume": int(gmv_volume_total)}
    ]

    # 5. Build Dynamic Core Activity Logs
    activity_timeline = []
    
    recent_users = User.objects.all().order_by('-created_at')[:2]
    for u in recent_users:
        activity_timeline.append({
            "message": f"New profile registration logged for {u.full_name} matching authorization scope: '{u.role}'.",
            "timestamp": "Just Now",
            "module": "Identity"
        })

    recent_payments = RentPayment.objects.filter(is_paid=True).order_by('-payment_date')[:2]
    for p in recent_payments:
        activity_timeline.append({
            "message": f"Payment transaction processed successfully: KES {p.amount:,.0f} logged from Tenant node.",
            "timestamp": "10m ago",
            "module": "Gateway"
        })

    # Fallback to verify feed integrity if system logging metrics are blank
    if not activity_timeline:
        activity_timeline = [{"message": "System logs standing by. Integrity loops active.", "timestamp": "Active", "module": "Core"}]

    return Response({
        "cards": {
            "gmv": f"KES {gmv_volume_total:,.0f}",
            "total_users": f"{total_users_count:,}",
            "total_units": f"{total_units_count:,}",
            "occupancy_rate": f"{occupancy_rate_pct}%",
            "open_tickets": str(open_tickets_count)
        },
        "charts": {
            "revenue_history": revenue_chart_history,
            "demographics": demographics_chart_data
        },
        "activities": activity_timeline
    }, status=status.HTTP_200_OK)