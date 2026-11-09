from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unit_app.models import (
    ConstructionProject, OffPlanUnit, OffPlanBuyer, OffPlanLead,
    OffPlanReservation, OffPlanSale, OffPlanInstallment, OffPlanPayment,
    OffPlanPaymentAllocation, OffPlanCommission, OffPlanUnitHandover,
)
from unit_app.serializers.off_plan_sales_serializers import (
    OffPlanUnitSerializer, OffPlanBuyerSerializer, OffPlanLeadSerializer,
    OffPlanReservationSerializer, OffPlanSaleSerializer, OffPlanInstallmentSerializer,
    OffPlanPaymentSerializer, OffPlanPaymentAllocationSerializer,
    OffPlanCommissionSerializer, OffPlanUnitHandoverSerializer,
    ReservationStatusActionSerializer, SaleStatusActionSerializer,
    PaymentConfirmationSerializer, AllocatePaymentSerializer,
    HandoverStatusActionSerializer,
)

ZERO = Decimal('0.00')
ACTIVE_RES = ('pending', 'confirmed')
LIVE_SALES = ('draft', 'contract_pending', 'active', 'paid', 'completed')


def scope(request, project_id):
    project = get_object_or_404(ConstructionProject, pk=project_id)
    user = request.user
    # Fail closed: adapt this to your OrganizationMembership/Role model.
    if not (user.is_superuser or project.project_manager_id == user.pk or project.created_by_id == user.pk):
        raise PermissionDenied('You are not authorized to manage this project.')
    return project


def context(request, project):
    return {'request': request, 'project': project, 'organization': project.organization}


def scoped(model, project):
    org = project.organization_id
    if model is OffPlanUnit: return model.objects.filter(project=project)
    if model is OffPlanBuyer: return model.objects.filter(organization_id=org)
    if model is OffPlanLead: return model.objects.filter(project=project)
    if model is OffPlanReservation: return model.objects.filter(organization_id=org, offplan_unit__project=project)
    if model is OffPlanSale: return model.objects.filter(organization_id=org, offplan_unit__project=project)
    if model is OffPlanInstallment: return model.objects.filter(sale__offplan_unit__project=project, sale__organization_id=org)
    if model is OffPlanPayment: return model.objects.filter(organization_id=org, sale__offplan_unit__project=project)
    if model is OffPlanPaymentAllocation: return model.objects.filter(payment__organization_id=org, payment__sale__offplan_unit__project=project)
    if model is OffPlanCommission: return model.objects.filter(sale__organization_id=org, sale__offplan_unit__project=project)
    if model is OffPlanUnitHandover: return model.objects.filter(sale__organization_id=org, sale__offplan_unit__project=project)
    raise ValueError('Unknown model')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request, project_id):
    project = scope(request, project_id)
    units = scoped(OffPlanUnit, project)
    sales = scoped(OffPlanSale, project)
    payments = scoped(OffPlanPayment, project).filter(status='confirmed')
    revenue = payments.aggregate(total=Sum('amount'))['total'] or ZERO
    prices = sales.exclude(status__in=['cancelled', 'defaulted']).aggregate(total=Sum('sale_price'))['total'] or ZERO
    return Response({
        'units_total': units.count(), 'units_by_status': list(units.values('status').annotate(count=Count('id'))),
        'leads_total': scoped(OffPlanLead, project).count(),
        'reservations_active': scoped(OffPlanReservation, project).filter(status__in=ACTIVE_RES, expires_at__gt=timezone.now()).count(),
        'sales_total': sales.count(), 'sales_by_status': list(sales.values('status').annotate(count=Count('id'))),
        'contracted_value': prices, 'confirmed_collections': revenue,
        'outstanding_value': max(ZERO, prices - revenue),
        'overdue_installments': scoped(OffPlanInstallment, project).filter(due_date__lt=timezone.localdate()).exclude(status__in=['paid', 'waived']).count(),
    })


# Generic CRUD is restricted to non-financial record creation and updates.
CRUD = {
    'units': (OffPlanUnit, OffPlanUnitSerializer),
    'buyers': (OffPlanBuyer, OffPlanBuyerSerializer),
    'leads': (OffPlanLead, OffPlanLeadSerializer),
    'commissions': (OffPlanCommission, OffPlanCommissionSerializer),
}


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def collection(request, project_id, resource):
    project = scope(request, project_id)
    if resource not in CRUD: raise ValidationError('Unknown resource.')
    model, serializer_class = CRUD[resource]
    if request.method == 'GET':
        return Response(serializer_class(scoped(model, project).order_by('-id')[:300], many=True, context=context(request, project)).data)
    serializer = serializer_class(data=request.data, context=context(request, project))
    serializer.is_valid(raise_exception=True)
    try:
        with transaction.atomic(): obj = serializer.save()
    except IntegrityError: raise ValidationError('A conflicting record already exists.')
    return Response(serializer_class(obj, context=context(request, project)).data, status=201)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def detail(request, project_id, resource, pk):
    project = scope(request, project_id)
    if resource not in CRUD: raise ValidationError('Unknown resource.')
    model, serializer_class = CRUD[resource]
    obj = get_object_or_404(scoped(model, project), pk=pk)
    if request.method == 'GET': return Response(serializer_class(obj, context=context(request, project)).data)
    if resource == 'units' and obj.status in ('sold', 'handed_over'):
        raise ValidationError('Completed units cannot be edited.')
    serializer = serializer_class(obj, data=request.data, partial=True, context=context(request, project))
    serializer.is_valid(raise_exception=True)
    try:
        with transaction.atomic(): serializer.save()
    except IntegrityError: raise ValidationError('Update conflicts with an existing record.')
    return Response(serializer.data)


def expire_reservations(unit):
    OffPlanReservation.objects.filter(offplan_unit=unit, status__in=ACTIVE_RES, expires_at__lte=timezone.now()).update(status='expired')
    if unit.status == 'reserved' and not unit.reservations.filter(status__in=ACTIVE_RES).exists():
        unit.status = 'available'; unit.save(update_fields=['status', 'updated_at'])


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reservations(request, project_id):
    project = scope(request, project_id)
    if request.method == 'GET':
        return Response(OffPlanReservationSerializer(scoped(OffPlanReservation, project).order_by('-id')[:300], many=True).data)
    ser = OffPlanReservationSerializer(data=request.data, context=context(request, project))
    ser.is_valid(raise_exception=True)
    unit_id = ser.validated_data['offplan_unit'].pk
    try:
        with transaction.atomic():
            unit = get_object_or_404(scoped(OffPlanUnit, project).select_for_update(), pk=unit_id)
            expire_reservations(unit)
            if unit.status != 'available' or unit.sales.filter(status__in=LIVE_SALES).exists() or unit.reservations.filter(status__in=ACTIVE_RES).exists():
                raise ValidationError('This unit is not available for reservation.')
            obj = ser.save()
            unit.status = 'reserved'; unit.save(update_fields=['status', 'updated_at'])
    except IntegrityError: raise ValidationError('Reservation conflicts with another active reservation.')
    return Response(OffPlanReservationSerializer(obj).data, status=201)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reservation_detail(request, project_id, pk):
    project = scope(request, project_id)
    if request.method == 'GET':
        obj = get_object_or_404(scoped(OffPlanReservation, project), pk=pk)
        return Response(OffPlanReservationSerializer(obj).data)
    action = ReservationStatusActionSerializer(data=request.data); action.is_valid(raise_exception=True)
    requested = action.validated_data['action']
    if requested == 'convert': raise ValidationError('Convert reservations through the sales creation endpoint.')
    with transaction.atomic():
        res = get_object_or_404(scoped(OffPlanReservation, project).select_for_update(), pk=pk)
        unit = get_object_or_404(OffPlanUnit.objects.select_for_update(), pk=res.offplan_unit_id)
        expire_reservations(unit); res.refresh_from_db()
        if requested == 'confirm':
            if res.status != 'pending' or res.expires_at <= timezone.now(): raise ValidationError('Only active pending reservations can be confirmed.')
            res.status = 'confirmed'
        elif requested in ('cancel', 'expire'):
            if res.status not in ACTIVE_RES: raise ValidationError('Reservation is not active.')
            if requested == 'expire' and res.expires_at > timezone.now(): raise ValidationError('Reservation has not expired.')
            res.status = 'cancelled' if requested == 'cancel' else 'expired'
        res.save(update_fields=['status', 'updated_at'])
        if res.status in ('cancelled', 'expired') and not unit.sales.filter(status__in=LIVE_SALES).exists():
            unit.status = 'available'; unit.save(update_fields=['status', 'updated_at'])
    return Response(OffPlanReservationSerializer(res).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sales(request, project_id):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanSaleSerializer(scoped(OffPlanSale, project).order_by('-id')[:300], many=True).data)
    ser = OffPlanSaleSerializer(data=request.data, context=context(request, project)); ser.is_valid(raise_exception=True)
    unit_id = ser.validated_data['offplan_unit'].pk
    try:
        with transaction.atomic():
            unit = get_object_or_404(scoped(OffPlanUnit, project).select_for_update(), pk=unit_id)
            expire_reservations(unit)
            reservation = ser.validated_data.get('reservation')
            if unit.status not in ('available', 'reserved') or unit.sales.filter(status__in=LIVE_SALES).exists():
                raise ValidationError('Unit already sold or unavailable.')
            active = unit.reservations.filter(status__in=ACTIVE_RES).first()
            if active and (not reservation or active.pk != reservation.pk): raise ValidationError('Active reservation belongs to another sale.')
            if reservation and (reservation.status not in ACTIVE_RES or reservation.expires_at <= timezone.now()):
                raise ValidationError('Reservation is not active.')
            obj = ser.save()
            if reservation:
                reservation.status = 'converted'; reservation.save(update_fields=['status', 'updated_at'])
            unit.status = 'under_contract'; unit.save(update_fields=['status', 'updated_at'])
    except IntegrityError: raise ValidationError('Another sale already exists for this unit.')
    return Response(OffPlanSaleSerializer(obj).data, status=201)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sale_detail(request, project_id, pk):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanSaleSerializer(get_object_or_404(scoped(OffPlanSale, project), pk=pk)).data)
    action = SaleStatusActionSerializer(data=request.data); action.is_valid(raise_exception=True)
    transition = action.validated_data['action']
    transitions = {'submit_contract': (('draft',), 'contract_pending'), 'activate': (('contract_pending',), 'active'),
                   'cancel': (('draft', 'contract_pending', 'active'), 'cancelled'),
                   'default': (('active',), 'defaulted'), 'complete': (('paid',), 'completed')}
    allowed, new_status = transitions[transition]
    with transaction.atomic():
        sale = get_object_or_404(scoped(OffPlanSale, project).select_for_update(), pk=pk)
        unit = get_object_or_404(OffPlanUnit.objects.select_for_update(), pk=sale.offplan_unit_id)
        if sale.status not in allowed: raise ValidationError('Invalid sale status transition.')
        if transition == 'activate' and not sale.agreement_url: raise ValidationError('Upload the signed agreement before activation.')
        if transition == 'complete' and sale.outstanding_balance > ZERO: raise ValidationError('Sale still has an outstanding balance.')
        if transition in ('cancel', 'default') and sale.confirmed_total > ZERO:
            raise ValidationError('Paid sales require a formal refund/termination workflow; do not cancel directly.')
        sale.status = new_status; sale.save(update_fields=['status', 'updated_at'])
        if new_status in ('cancelled', 'defaulted'):
            unit.status = 'available'; unit.save(update_fields=['status', 'updated_at'])
        elif new_status in ('active', 'paid', 'completed'):
            unit.status = 'sold'; unit.save(update_fields=['status', 'updated_at'])
    return Response(OffPlanSaleSerializer(sale).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def installments(request, project_id):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanInstallmentSerializer(scoped(OffPlanInstallment, project).order_by('sale_id', 'installment_number')[:500], many=True).data)
    ser = OffPlanInstallmentSerializer(data=request.data, context=context(request, project)); ser.is_valid(raise_exception=True)
    with transaction.atomic():
        sale = get_object_or_404(scoped(OffPlanSale, project).select_for_update(), pk=ser.validated_data['sale'].pk)
        if sale.status not in ('draft', 'contract_pending', 'active'): raise ValidationError('Cannot change the installment schedule for this sale.')
        obj = ser.save()
    return Response(OffPlanInstallmentSerializer(obj).data, status=201)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def installment_detail(request, project_id, pk):
    project = scope(request, project_id)
    obj = get_object_or_404(scoped(OffPlanInstallment, project), pk=pk)
    if request.method == 'GET': return Response(OffPlanInstallmentSerializer(obj).data)
    with transaction.atomic():
        obj = get_object_or_404(scoped(OffPlanInstallment, project).select_for_update(), pk=pk)
        if obj.allocations.exists(): raise ValidationError('An installment with allocations cannot be edited.')
        if obj.sale.status not in ('draft', 'contract_pending'): raise ValidationError('Schedule is locked after sale activation.')
        ser = OffPlanInstallmentSerializer(obj, data=request.data, partial=True, context=context(request, project))
        ser.is_valid(raise_exception=True); ser.save()
    return Response(ser.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payments(request, project_id):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanPaymentSerializer(scoped(OffPlanPayment, project).order_by('-id')[:500], many=True).data)
    ser = OffPlanPaymentSerializer(data=request.data, context=context(request, project)); ser.is_valid(raise_exception=True)
    with transaction.atomic():
        sale = get_object_or_404(scoped(OffPlanSale, project).select_for_update(), pk=ser.validated_data['sale'].pk)
        if sale.status not in ('active', 'paid'): raise ValidationError('Payments require an active sale.')
        if ser.validated_data['amount'] > sale.outstanding_balance: raise ValidationError('Payment exceeds outstanding balance.')
        try: obj = ser.save()
        except IntegrityError: raise ValidationError('Duplicate payment reference.')
    return Response(OffPlanPaymentSerializer(obj).data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment(request, project_id, pk):
    project = scope(request, project_id)
    ser = PaymentConfirmationSerializer(data=request.data); ser.is_valid(raise_exception=True)
    with transaction.atomic():
        payment = get_object_or_404(scoped(OffPlanPayment, project).select_for_update(), pk=pk)
        sale = get_object_or_404(OffPlanSale.objects.select_for_update(), pk=payment.sale_id)
        if payment.status != 'pending': raise ValidationError('Only pending payments can be confirmed.')
        if payment.amount > sale.outstanding_balance: raise ValidationError('Payment exceeds outstanding balance.')
        # Never trust an unverified M-Pesa/card payment from the client.
        if payment.method in ('mpesa', 'card'):
            raise ValidationError('M-Pesa/card payments must be confirmed by a verified provider callback.')
        payment.status = 'confirmed'
        payment.external_reference = ser.validated_data.get('external_reference', payment.external_reference)
        payment.paid_at = ser.validated_data.get('paid_at', timezone.now())
        payment.confirmed_at = timezone.now()
        payment.notes = ser.validated_data.get('notes', payment.notes)
        payment.save(update_fields=['status', 'external_reference', 'paid_at', 'confirmed_at', 'notes', 'updated_at'])
        if sale.outstanding_balance == ZERO and sale.status == 'active':
            sale.status = 'paid'; sale.save(update_fields=['status', 'updated_at'])
    return Response(OffPlanPaymentSerializer(payment).data)


def update_installment_status(installment):
    paid = installment.amount_paid
    if paid >= installment.amount_due: installment.status = 'paid'
    elif paid > ZERO: installment.status = 'partially_paid'
    elif installment.due_date < timezone.localdate(): installment.status = 'overdue'
    else: installment.status = 'pending'
    installment.save(update_fields=['status', 'updated_at'])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def allocate_payment(request, project_id, pk):
    project = scope(request, project_id)
    with transaction.atomic():
        payment = get_object_or_404(scoped(OffPlanPayment, project).select_for_update(), pk=pk)
        ser = AllocatePaymentSerializer(data=request.data, context={**context(request, project), 'payment': payment})
        ser.is_valid(raise_exception=True)
        if payment.status != 'confirmed': raise ValidationError('Only confirmed payments can be allocated.')
        if payment.allocations.exists(): raise ValidationError('Allocations are immutable once recorded.')
        rows = ser.validated_data['allocations']
        installments = {i.pk: i for i in OffPlanInstallment.objects.select_for_update().filter(pk__in=[r['installment'].pk for r in rows]).order_by('pk')}
        if sum((r['amount'] for r in rows), ZERO) > payment.amount: raise ValidationError('Allocations exceed payment.')
        for row in rows:
            item = installments[row['installment'].pk]
            if row['amount'] > item.balance: raise ValidationError(f'Allocation exceeds installment {item.installment_number} balance.')
        created = [OffPlanPaymentAllocation.objects.create(payment=payment, installment=installments[r['installment'].pk], amount=r['amount']) for r in rows]
        for item in installments.values(): update_installment_status(item)
    return Response(OffPlanPaymentAllocationSerializer(created, many=True).data, status=201)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def handovers(request, project_id):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanUnitHandoverSerializer(scoped(OffPlanUnitHandover, project).order_by('-id')[:300], many=True).data)
    ser = OffPlanUnitHandoverSerializer(data=request.data, context=context(request, project)); ser.is_valid(raise_exception=True)
    with transaction.atomic():
        sale = get_object_or_404(scoped(OffPlanSale, project).select_for_update(), pk=ser.validated_data['sale'].pk)
        if sale.status not in ('paid', 'completed'): raise ValidationError('Handover requires a fully paid sale.')
        if hasattr(sale, 'unit_handover'): raise ValidationError('Handover already exists.')
        obj = ser.save()
    return Response(OffPlanUnitHandoverSerializer(obj).data, status=201)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def handover_detail(request, project_id, pk):
    project = scope(request, project_id)
    if request.method == 'GET': return Response(OffPlanUnitHandoverSerializer(get_object_or_404(scoped(OffPlanUnitHandover, project), pk=pk)).data)
    ser = HandoverStatusActionSerializer(data=request.data); ser.is_valid(raise_exception=True)
    action = ser.validated_data['action']
    with transaction.atomic():
        obj = get_object_or_404(scoped(OffPlanUnitHandover, project).select_for_update(), pk=pk)
        sale = get_object_or_404(OffPlanSale.objects.select_for_update(), pk=obj.sale_id)
        if action == 'start_inspection':
            if obj.status != 'pending': raise ValidationError('Handover must be pending.')
            obj.status = 'inspection'
        elif action == 'mark_ready':
            if obj.status != 'inspection': raise ValidationError('Buyer inspection must be in progress.')
            obj.status = 'ready'
        elif action == 'complete':
            if obj.status != 'ready' or not obj.buyer_accepted_at: raise ValidationError('Buyer acceptance is required.')
            if sale.outstanding_balance > ZERO: raise ValidationError('Sale is not fully paid.')
            obj.status = 'handed_over'; obj.handed_over_at = timezone.now()
            obj.keys_released = True; obj.documents_released = True
            unit = get_object_or_404(OffPlanUnit.objects.select_for_update(), pk=sale.offplan_unit_id)
            unit.status = 'handed_over'; unit.save(update_fields=['status', 'updated_at'])
            sale.status = 'completed'; sale.save(update_fields=['status', 'updated_at'])
        obj.manager_notes = ser.validated_data.get('manager_notes', obj.manager_notes)
        obj.save()
    return Response(OffPlanUnitHandoverSerializer(obj).data)