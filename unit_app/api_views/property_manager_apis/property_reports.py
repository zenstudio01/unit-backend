from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange
from django.db.models import Sum, Count, Q
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unit_app.models import (OrganizationMembership, Property, Unit, Invoice, PaymentAllocation,
                     PropertyExpense, MaintenanceTicket)

ROLES = {'organization_owner', 'organization_admin', 'property_manager', 'accountant', 'landlord'}
ZERO = Decimal('0')

def sum_field(qs, field):
    return qs.aggregate(value=Sum(field))['value'] or ZERO

def month_bounds(year, month):
    start = date(year, month, 1)
    return start, date(year, month, monthrange(year, month)[1])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def property_manager_reports(request):
    try:
        org_id = int(request.query_params.get('organization_id', ''))
    except (TypeError, ValueError):
        return Response({'detail': 'Valid organization_id is required.'}, status=400)
    membership = OrganizationMembership.objects.filter(user=request.user, organization_id=org_id, is_active=True).prefetch_related('roles').first()
    if not membership:
        return Response({'detail': 'Organization access denied.'}, status=403)
    roles = set(membership.roles.values_list('code', flat=True)) | set(membership.roles.values_list('name', flat=True))
    if membership.primary_role_id:
        roles.update([membership.primary_role.code, membership.primary_role.name])
    if not roles.intersection(ROLES):
        return Response({'detail': 'You do not have permission to view financial reports.'}, status=403)

    today = date.today()
    start = parse_date(request.query_params.get('date_from', '')) if request.query_params.get('date_from') else today.replace(day=1)
    end = parse_date(request.query_params.get('date_to', '')) if request.query_params.get('date_to') else today
    if not start or not end or start > end or (end - start).days > 3660:
        return Response({'detail': 'Provide a valid date range of up to 10 years.'}, status=400)

    properties = Property.objects.filter(organization_id=org_id)
    prop_id = request.query_params.get('property_id')
    if prop_id:
        try:
            prop_id = int(prop_id)
        except ValueError:
            return Response({'detail': 'Invalid property_id.'}, status=400)
        if not properties.filter(id=prop_id).exists():
            return Response({'detail': 'Property not found in this organization.'}, status=404)
        properties = properties.filter(id=prop_id)

    property_ids = properties.values_list('id', flat=True)
    units = Unit.objects.filter(property_id__in=property_ids)
    invoices = Invoice.objects.filter(organization_id=org_id, property_id__in=property_ids)
    expenses = PropertyExpense.objects.filter(organization_id=org_id, property_id__in=property_ids)
    tickets = MaintenanceTicket.objects.filter(organization_id=org_id, property_id__in=property_ids)
    # Cash received is derived from allocations to property invoices, not all tenant payments.
    # PaymentAllocation.allocated_amount is assumed to be the posted, confirmed allocation.
    allocations = PaymentAllocation.objects.filter(
        invoice__organization_id=org_id, invoice__property_id__in=property_ids,
        payment__organization_id=org_id, payment__status='completed',
        payment__paid_at__date__gte=start, payment__paid_at__date__lte=end,
    )
    billed = sum_field(invoices.filter(issue_date__range=(start, end)).exclude(status__in=['cancelled', 'void', 'draft']), 'total_amount')
    collected = sum_field(allocations, 'allocated_amount')
    spent = sum_field(expenses.filter(expense_date__range=(start, end)), 'amount')
    outstanding = sum_field(invoices.exclude(status__in=['cancelled', 'void', 'draft']), 'balance')
    occupied = units.filter(status='occupied').count()
    total_units = units.count()
    maintenance_open = tickets.exclude(status__in=['closed', 'completed', 'cancelled']).count()
    # Report last six calendar months ending in the selected end month.
    monthly = []
    for offset in range(5, -1, -1):
        absolute = end.year * 12 + end.month - 1 - offset
        year, month = divmod(absolute, 12)
        month += 1
        ms, me = month_bounds(year, month)
        monthly.append({
            'month': ms.strftime('%Y-%m'),
            'label': ms.strftime('%b %Y'),
            'billed': str(sum_field(invoices.filter(issue_date__range=(ms, me)).exclude(status__in=['cancelled','void','draft']), 'total_amount')),
            'collected': str(sum_field(PaymentAllocation.objects.filter(
                invoice__organization_id=org_id, invoice__property_id__in=property_ids,
                payment__organization_id=org_id, payment__status='completed',
                payment__paid_at__date__range=(ms, me)), 'allocated_amount')),
            'expenses': str(sum_field(expenses.filter(expense_date__range=(ms, me)), 'amount')),
        })
    categories = list(expenses.filter(expense_date__range=(start, end)).values('category').annotate(total=Sum('amount'), count=Count('id')).order_by('-total'))
    by_property = []
    for prop in properties.order_by('name')[:100]:
        pu = units.filter(property_id=prop.id)
        by_property.append({
            'id': prop.id, 'name': prop.name, 'units': pu.count(),
            'occupied': pu.filter(status='occupied').count(),
            'billed': str(sum_field(invoices.filter(property_id=prop.id, issue_date__range=(start, end)).exclude(status__in=['cancelled','void','draft']), 'total_amount')),
            'collected': str(sum_field(allocations.filter(invoice__property_id=prop.id), 'allocated_amount')),
            'expenses': str(sum_field(expenses.filter(property_id=prop.id, expense_date__range=(start, end)), 'amount')),
        })
    return Response({
        'period': {'date_from': start.isoformat(), 'date_to': end.isoformat()},
        'summary': {'billed': str(billed), 'collected': str(collected), 'expenses': str(spent),
                    'net_cash_flow': str(collected - spent), 'outstanding_balance': str(outstanding),
                    'properties': properties.count(), 'units': total_units, 'occupied_units': occupied,
                    'occupancy_rate': round(occupied / total_units * 100, 1) if total_units else 0,
                    'open_maintenance': maintenance_open},
        'monthly': monthly,
        'expense_categories': [{'category': x['category'], 'total': str(x['total']), 'count': x['count']} for x in categories],
        'properties': by_property,
    })