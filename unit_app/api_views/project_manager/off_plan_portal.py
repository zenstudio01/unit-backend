"""Buyer-only UNIT off-plan portal. Never accept buyer_id as proof of ownership."""
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unit_app.models import (
    OffPlanBuyer, OffPlanReservation, OffPlanSale, OffPlanInstallment,
    OffPlanPayment, OffPlanUnitHandover,
)
from unit_app.serializers.off_plan_sales_serializers import (
    BuyerPortalUnitSerializer, BuyerPortalReservationSerializer,
    BuyerPortalSaleSerializer, BuyerPortalInstallmentSerializer,
    BuyerPortalPaymentSerializer, BuyerPortalHandoverSerializer,
    BuyerHandoverAcceptanceSerializer,
)


def buyers(request):
    return OffPlanBuyer.objects.filter(user=request.user)


def sales(request):
    return OffPlanSale.objects.filter(buyer__in=buyers(request)).exclude(status='draft')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    qs = sales(request)
    paid = OffPlanPayment.objects.filter(sale__in=qs, status='confirmed').aggregate(total=Sum('amount'))['total'] or 0
    return Response({
        'buyer_profiles': buyers(request).count(),
        'reservations': OffPlanReservation.objects.filter(buyer__in=buyers(request)).count(),
        'purchases': qs.count(), 'confirmed_payments_total': paid,
        'units': BuyerPortalUnitSerializer([s.offplan_unit for s in qs.select_related('offplan_unit__unit', 'offplan_unit__project')[:100]], many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reservations(request):
    qs = OffPlanReservation.objects.filter(buyer__in=buyers(request)).select_related('offplan_unit__unit').order_by('-id')[:300]
    return Response(BuyerPortalReservationSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def purchases(request):
    return Response(BuyerPortalSaleSerializer(sales(request).select_related('offplan_unit__unit').order_by('-id')[:300], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def purchase_detail(request, sale_id):
    obj = get_object_or_404(sales(request), pk=sale_id)
    return Response({
        'sale': BuyerPortalSaleSerializer(obj).data,
        'unit': BuyerPortalUnitSerializer(obj.offplan_unit).data,
        'installments': BuyerPortalInstallmentSerializer(obj.installments.order_by('installment_number'), many=True).data,
        'payments': BuyerPortalPaymentSerializer(obj.payments.filter(status='confirmed').order_by('-id'), many=True).data,
        'handover': BuyerPortalHandoverSerializer(obj.unit_handover).data if hasattr(obj, 'unit_handover') else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def installments(request):
    qs = OffPlanInstallment.objects.filter(sale__in=sales(request)).order_by('sale_id', 'installment_number')[:500]
    return Response(BuyerPortalInstallmentSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payments(request):
    qs = OffPlanPayment.objects.filter(sale__in=sales(request), status='confirmed').order_by('-id')[:500]
    return Response(BuyerPortalPaymentSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def handovers(request):
    qs = OffPlanUnitHandover.objects.filter(sale__in=sales(request)).order_by('-id')[:300]
    return Response(BuyerPortalHandoverSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_handover(request, handover_id):
    serializer = BuyerHandoverAcceptanceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        obj = get_object_or_404(OffPlanUnitHandover.objects.select_for_update().filter(sale__in=sales(request)), pk=handover_id)
        if obj.status != 'ready': raise ValidationError('This handover is not ready for buyer review.')
        if obj.buyer_accepted_at: raise ValidationError('An acceptance decision has already been recorded.')
        obj.buyer_notes = serializer.validated_data.get('buyer_notes', '')
        if serializer.validated_data['accepted']:
            obj.buyer_accepted_at = timezone.now()
        else:
            # A declined handover returns to inspection for remediation.
            obj.status = 'inspection'
        obj.save(update_fields=['buyer_notes', 'buyer_accepted_at', 'status', 'updated_at'])
    return Response(BuyerPortalHandoverSerializer(obj).data)