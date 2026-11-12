# unit_app/property_expense_api.py
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from unit_app.models import PropertyExpense, Property, Unit, OrganizationMembership

READ_ROLES = {'organization_owner','organization_admin','property_manager','accountant'}
WRITE_ROLES = {'organization_owner','organization_admin','property_manager','accountant'}


def authorize(request, org_id, write=False):
    membership = OrganizationMembership.objects.filter(
        organization_id=org_id, user=request.user, is_active=True
    ).prefetch_related('roles').first()
    if not membership:
        return False
    role_codes = set(membership.roles.values_list('code', flat=True))
    # Your Role model has both `code` and `name`; support either if codes differ.
    role_codes |= set(membership.roles.values_list('name', flat=True))
    if membership.primary_role_id:
        role_codes.add(membership.primary_role.code)
        role_codes.add(membership.primary_role.name)
    return bool(role_codes & (WRITE_ROLES if write else READ_ROLES))


class PropertyExpenseSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PropertyExpense
        fields = ['id','organization','property','property_name','unit','unit_name',
                  'category','title','description','amount','expense_date','vendor',
                  'payment_method','reference','receipt_url','created_by_name',
                  'created_at','updated_at']
        read_only_fields = ['id','organization','receipt_url','created_by_name','created_at','updated_at']

    def validate(self, attrs):
        org_id = self.context['org_id']
        prop = attrs.get('property', getattr(self.instance, 'property', None))
        unit = attrs.get('unit', getattr(self.instance, 'unit', None))
        if not prop or prop.organization_id != org_id:
            raise serializers.ValidationError({'property':'Property does not belong to this organization.'})
        if unit and unit.property_id != prop.id:
            raise serializers.ValidationError({'unit':'Unit must belong to the selected property.'})
        return attrs


@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def property_expenses(request):
    try:
        org_id = int(request.query_params.get('organization_id') or request.data.get('organization_id'))
    except (ValueError, TypeError):
        return Response({'message':'Valid organization_id is required.'}, status=400)
    if not authorize(request, org_id, write=request.method == 'POST'):
        return Response({'message':'Permission denied.'}, status=403)

    if request.method == 'GET':
        qs = PropertyExpense.objects.filter(organization_id=org_id).select_related('property','unit','created_by')
        if request.query_params.get('property_id'):
            qs = qs.filter(property_id=request.query_params['property_id'])
        if request.query_params.get('category'):
            qs = qs.filter(category=request.query_params['category'])
        if request.query_params.get('date_from'):
            qs = qs.filter(expense_date__gte=request.query_params['date_from'])
        if request.query_params.get('date_to'):
            qs = qs.filter(expense_date__lte=request.query_params['date_to'])
        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return Response({'expenses': PropertyExpenseSerializer(qs[:200], many=True).data,
                         'total_amount': str(total), 'count': qs.count(), 'limit': 200})

    serializer = PropertyExpenseSerializer(data=request.data, context={'org_id':org_id})
    serializer.is_valid(raise_exception=True)
    expense = serializer.save(organization_id=org_id, created_by=request.user)
    return Response({'message':'Expense recorded.', 'expense':PropertyExpenseSerializer(expense).data}, status=201)


@api_view(['GET','PATCH','DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def property_expense_detail(request, expense_id):
    try:
        org_id = int(request.query_params.get('organization_id') or request.data.get('organization_id'))
    except (ValueError, TypeError):
        return Response({'message':'Valid organization_id is required.'}, status=400)
    if not authorize(request, org_id, write=request.method != 'GET'):
        return Response({'message':'Permission denied.'}, status=403)
    expense = get_object_or_404(PropertyExpense, id=expense_id, organization_id=org_id)
    if request.method == 'GET':
        return Response({'expense': PropertyExpenseSerializer(expense).data})
    if request.method == 'DELETE':
        expense.delete()
        return Response(status=204)
    serializer = PropertyExpenseSerializer(expense, data=request.data, partial=True, context={'org_id':org_id})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'expense':serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_properties(request):
    try:
        org_id = int(request.query_params.get('organization_id'))
    except (TypeError, ValueError):
        return Response({'message':'Valid organization_id is required.'},status=400)
    if not authorize(request,org_id):
        return Response({'message':'Permission denied.'},status=403)
    props = Property.objects.filter(organization_id=org_id).order_by('name')
    return Response({'properties':[{'id':p.id,'name':p.name} for p in props]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_units(request, property_id):
    try:
        org_id = int(request.query_params.get('organization_id'))
    except (TypeError, ValueError):
        return Response({'message':'Valid organization_id is required.'},status=400)
    if not authorize(request,org_id):
        return Response({'message':'Permission denied.'},status=403)
    get_object_or_404(Property, id=property_id, organization_id=org_id)
    return Response({'units':list(Unit.objects.filter(property_id=property_id).values('id','name','unit_code'))})