from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from unit_app.models import (
    OffPlanUnit, OffPlanBuyer, OffPlanLead, OffPlanReservation,
    OffPlanSale, OffPlanInstallment, OffPlanPayment,
    OffPlanPaymentAllocation, OffPlanCommission, OffPlanUnitHandover,
)

ZERO = Decimal("0.00")


def _check_model(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        if hasattr(exc, "message_dict"):
            raise serializers.ValidationError(exc.message_dict)
        raise serializers.ValidationError(exc.messages)


def _id(obj):
    return getattr(obj, "pk", obj)


class ScopedWriteMixin:
    """Guard relations and assign organization/project from trusted view context."""

    def _organization(self):
        org = self.context.get("organization")
        if org is None:
            raise serializers.ValidationError({"organization": "Authorized organization context is required."})
        return org

    def _project(self):
        project = self.context.get("project")
        if project is None:
            raise serializers.ValidationError({"project": "Authorized project context is required."})
        if project.organization_id != _id(self._organization()):
            raise serializers.ValidationError({"project": "Project is outside the selected organization."})
        return project

    def _require_org(self, obj, field):
        if obj is not None and obj.organization_id != _id(self._organization()):
            raise serializers.ValidationError({field: "Record does not belong to this organization."})

    def _require_project_unit(self, obj, field="offplan_unit"):
        self._require_org(obj, field)
        if obj is not None and obj.project_id != _id(self._project()):
            raise serializers.ValidationError({field: "Unit does not belong to this project."})

    def _require_project_sale(self, obj, field="sale"):
        self._require_org(obj, field)
        if obj is not None and obj.offplan_unit.project_id != _id(self._project()):
            raise serializers.ValidationError({field: "Sale does not belong to this project."})

    def _stamp(self, validated_data, *, project=False):
        validated_data["organization"] = self._organization()
        if project:
            validated_data["project"] = self._project()
        return validated_data

    def _actor(self):
        user = self.context.get("request") and self.context["request"].user
        return user if user is not None and user.is_authenticated else None


class FullCleanCreateMixin:
    """Model-level clean/validators before INSERT; DB constraints remain final guard."""

    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        _check_model(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        _check_model(instance)
        instance.save()
        return instance


class OffPlanUnitSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    unit_code = serializers.CharField(source="unit.unit_code", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = OffPlanUnit
        fields = (
            "id", "organization", "project", "unit", "unit_code", "project_name",
            "listing_price", "currency", "minimum_booking_amount",
            "construction_progress", "expected_completion_date", "status",
            "is_published", "description", "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "project", "status", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        project = self._project()
        unit = attrs.get("unit", getattr(self.instance, "unit", None))
        if unit is not None:
            if not project.property_id:
                raise serializers.ValidationError({"project": "Link the project to a property first."})
            if unit.property_id != project.property_id:
                raise serializers.ValidationError({"unit": "Unit must belong to the project property."})
        price = attrs.get("listing_price", getattr(self.instance, "listing_price", None))
        booking = attrs.get("minimum_booking_amount", getattr(self.instance, "minimum_booking_amount", ZERO))
        if price is not None and booking > price:
            raise serializers.ValidationError({"minimum_booking_amount": "Cannot exceed listing price."})
        return attrs

    def create(self, validated_data):
        self._stamp(validated_data, project=True)
        validated_data["created_by"] = self._actor()
        return super().create(validated_data)


class OffPlanBuyerSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    class Meta:
        model = OffPlanBuyer
        fields = (
            "id", "organization", "user", "full_name", "email", "phone_number",
            "id_number", "kra_pin", "address", "notes", "created_by",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_by", "created_at", "updated_at")
        extra_kwargs = {"user": {"required": False, "allow_null": True}}

    def validate_user(self, user):
        if user is not None:
            qs = OffPlanBuyer.objects.filter(organization=self._organization(), user=user)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("This account already has a buyer profile in this organization.")
        return user

    def create(self, validated_data):
        self._stamp(validated_data)
        validated_data["created_by"] = self._actor()
        return super().create(validated_data)


class OffPlanLeadSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    buyer_name = serializers.CharField(source="buyer.full_name", read_only=True)

    class Meta:
        model = OffPlanLead
        fields = (
            "id", "organization", "project", "offplan_unit", "buyer", "buyer_name",
            "contact_name", "contact_phone", "contact_email", "source", "status",
            "assigned_to", "next_follow_up", "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "project", "created_at", "updated_at")

    def validate(self, attrs):
        self._project()
        unit = attrs.get("offplan_unit", getattr(self.instance, "offplan_unit", None))
        buyer = attrs.get("buyer", getattr(self.instance, "buyer", None))
        if unit is not None:
            self._require_project_unit(unit)
        self._require_org(buyer, "buyer")
        return attrs

    def create(self, validated_data):
        self._stamp(validated_data, project=True)
        return super().create(validated_data)


class OffPlanReservationSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    buyer_name = serializers.CharField(source="buyer.full_name", read_only=True)
    unit_code = serializers.CharField(source="offplan_unit.unit.unit_code", read_only=True)

    class Meta:
        model = OffPlanReservation
        fields = (
            "id", "organization", "offplan_unit", "unit_code", "buyer", "buyer_name",
            "reservation_reference", "agreed_price", "booking_amount_due", "expires_at",
            "status", "notes", "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "status", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        unit = attrs.get("offplan_unit", getattr(self.instance, "offplan_unit", None))
        buyer = attrs.get("buyer", getattr(self.instance, "buyer", None))
        if unit is not None:
            self._require_project_unit(unit)
        self._require_org(buyer, "buyer")
        if self.instance is None:
            expiry = attrs.get("expires_at")
            if expiry and expiry <= timezone.now():
                raise serializers.ValidationError({"expires_at": "Expiry must be in the future."})
        return attrs

    def create(self, validated_data):
        self._stamp(validated_data)
        validated_data["created_by"] = self._actor()
        return super().create(validated_data)


class OffPlanSaleSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    buyer_name = serializers.CharField(source="buyer.full_name", read_only=True)
    unit_code = serializers.CharField(source="offplan_unit.unit.unit_code", read_only=True)
    confirmed_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    outstanding_balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = OffPlanSale
        fields = (
            "id", "organization", "offplan_unit", "unit_code", "buyer", "buyer_name",
            "reservation", "sale_reference", "sale_price", "currency", "deposit_required",
            "contract_date", "agreement_url", "agreement_public_id", "status",
            "sales_agent", "created_by", "notes", "confirmed_total", "outstanding_balance",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "status", "created_by", "confirmed_total",
            "outstanding_balance", "created_at", "updated_at",
        )

    def validate(self, attrs):
        unit = attrs.get("offplan_unit", getattr(self.instance, "offplan_unit", None))
        buyer = attrs.get("buyer", getattr(self.instance, "buyer", None))
        reservation = attrs.get("reservation", getattr(self.instance, "reservation", None))
        if unit is not None:
            self._require_project_unit(unit)
        self._require_org(buyer, "buyer")
        if reservation is not None:
            self._require_org(reservation, "reservation")
            if unit is not None and reservation.offplan_unit_id != unit.pk:
                raise serializers.ValidationError({"reservation": "Reservation belongs to a different unit."})
            if buyer is not None and reservation.buyer_id != buyer.pk:
                raise serializers.ValidationError({"buyer": "Buyer differs from reservation buyer."})
        price = attrs.get("sale_price", getattr(self.instance, "sale_price", None))
        deposit = attrs.get("deposit_required", getattr(self.instance, "deposit_required", ZERO))
        if price is not None and deposit > price:
            raise serializers.ValidationError({"deposit_required": "Deposit cannot exceed sale price."})
        return attrs

    def create(self, validated_data):
        self._stamp(validated_data)
        validated_data["created_by"] = self._actor()
        return super().create(validated_data)


class OffPlanInstallmentSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    amount_paid = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = OffPlanInstallment
        fields = (
            "id", "sale", "installment_number", "description", "due_date",
            "amount_due", "amount_paid", "balance", "status", "created_at", "updated_at",
        )
        read_only_fields = ("id", "amount_paid", "balance", "status", "created_at", "updated_at")

    def validate(self, attrs):
        sale = attrs.get("sale", getattr(self.instance, "sale", None))
        if sale is not None:
            self._require_project_sale(sale)
        return attrs


class OffPlanPaymentSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    sale_reference = serializers.CharField(source="sale.sale_reference", read_only=True)

    class Meta:
        model = OffPlanPayment
        fields = (
            "id", "organization", "sale", "sale_reference", "payment_reference",
            "external_reference", "amount", "currency", "method", "status",
            "paid_at", "confirmed_at", "recorded_by", "receipt_url", "notes",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "status", "confirmed_at", "recorded_by",
            "created_at", "updated_at",
        )

    def validate(self, attrs):
        sale = attrs.get("sale", getattr(self.instance, "sale", None))
        if sale is not None:
            self._require_project_sale(sale)
            currency = attrs.get("currency", getattr(self.instance, "currency", sale.currency))
            if currency != sale.currency:
                raise serializers.ValidationError({"currency": "Currency must match the sale."})
        return attrs

    def create(self, validated_data):
        self._stamp(validated_data)
        validated_data["recorded_by"] = self._actor()
        return super().create(validated_data)


class OffPlanPaymentAllocationSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    class Meta:
        model = OffPlanPaymentAllocation
        fields = ("id", "payment", "installment", "amount", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        payment = attrs.get("payment", getattr(self.instance, "payment", None))
        installment = attrs.get("installment", getattr(self.instance, "installment", None))
        if payment is not None:
            self._require_project_sale(payment.sale, "payment")
        if installment is not None:
            self._require_project_sale(installment.sale, "installment")
        if payment is not None and installment is not None and payment.sale_id != installment.sale_id:
            raise serializers.ValidationError({"installment": "Payment and installment must belong to the same sale."})
        return attrs


class OffPlanCommissionSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    class Meta:
        model = OffPlanCommission
        fields = (
            "id", "sale", "agent", "commission_rate", "commission_amount",
            "status", "paid_at", "created_at",
        )
        read_only_fields = ("id", "status", "paid_at", "created_at")

    def validate(self, attrs):
        sale = attrs.get("sale", getattr(self.instance, "sale", None))
        if sale is not None:
            self._require_project_sale(sale)
        return attrs


class OffPlanUnitHandoverSerializer(ScopedWriteMixin, FullCleanCreateMixin, serializers.ModelSerializer):
    class Meta:
        model = OffPlanUnitHandover
        fields = (
            "id", "sale", "status", "scheduled_date", "handed_over_at",
            "buyer_accepted_at", "keys_released", "documents_released",
            "buyer_notes", "manager_notes", "recorded_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "status", "handed_over_at", "buyer_accepted_at",
            "keys_released", "documents_released", "buyer_notes", "recorded_by",
            "created_at", "updated_at",
        )

    def validate(self, attrs):
        sale = attrs.get("sale", getattr(self.instance, "sale", None))
        if sale is not None:
            self._require_project_sale(sale)
        return attrs

    def create(self, validated_data):
        validated_data["recorded_by"] = self._actor()
        return super().create(validated_data)


# ------------------------ ACTION INPUTS ------------------------
# Views/services must lock affected rows (select_for_update) and perform
# state transitions atomically after validating these input serializers.

class ReservationStatusActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["confirm", "cancel", "expire", "convert"])
    notes = serializers.CharField(required=False, allow_blank=True)


class SaleStatusActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["submit_contract", "activate", "cancel", "default", "complete"])
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentConfirmationSerializer(serializers.Serializer):
    external_reference = serializers.CharField(max_length=150, required=False, allow_blank=True)
    paid_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentAllocationInputSerializer(serializers.Serializer):
    installment = serializers.PrimaryKeyRelatedField(queryset=OffPlanInstallment.objects.all())
    amount = serializers.DecimalField(max_digits=16, decimal_places=2, min_value=Decimal("0.01"))


class AllocatePaymentSerializer(ScopedWriteMixin, serializers.Serializer):
    allocations = PaymentAllocationInputSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        payment = self.context.get("payment")
        if payment is None:
            raise serializers.ValidationError("Payment context is required.")
        self._require_project_sale(payment.sale, "payment")
        allocations = attrs["allocations"]
        ids = [entry["installment"].pk for entry in allocations]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({"allocations": "Each installment may appear only once."})
        if any(entry["installment"].sale_id != payment.sale_id for entry in allocations):
            raise serializers.ValidationError({"allocations": "All installments must belong to the payment sale."})
        if sum((entry["amount"] for entry in allocations), ZERO) > payment.amount:
            raise serializers.ValidationError({"allocations": "Total allocation exceeds payment amount."})
        return attrs


class HandoverStatusActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["start_inspection", "mark_ready", "complete"])
    manager_notes = serializers.CharField(required=False, allow_blank=True)


class BuyerHandoverAcceptanceSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    buyer_notes = serializers.CharField(required=False, allow_blank=True)


# ------------------------ BUYER PORTAL (READ ONLY) ------------------------
# The buyer portal MUST filter buyer profiles by user=request.user and then
# filter all related objects by those buyer IDs. Do not accept a buyer ID
# from query parameters as an authorization mechanism.

class BuyerPortalUnitSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source="unit.unit_code", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = OffPlanUnit
        fields = (
            "id", "unit_code", "project_name", "description", "currency",
            "construction_progress", "expected_completion_date", "status",
        )
        read_only_fields = fields


class BuyerPortalReservationSerializer(serializers.ModelSerializer):
    unit = BuyerPortalUnitSerializer(source="offplan_unit", read_only=True)

    class Meta:
        model = OffPlanReservation
        fields = (
            "id", "reservation_reference", "unit", "agreed_price", "booking_amount_due",
            "expires_at", "status", "created_at",
        )
        read_only_fields = fields


class BuyerPortalInstallmentSerializer(serializers.ModelSerializer):
    amount_paid = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = OffPlanInstallment
        fields = ("id", "installment_number", "description", "due_date", "amount_due", "amount_paid", "balance", "status")
        read_only_fields = fields


class BuyerPortalPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffPlanPayment
        fields = (
            "id", "payment_reference", "amount", "currency", "method",
            "status", "paid_at", "confirmed_at", "receipt_url", "created_at",
        )
        read_only_fields = fields


class BuyerPortalHandoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffPlanUnitHandover
        fields = (
            "id", "status", "scheduled_date", "handed_over_at", "buyer_accepted_at",
            "keys_released", "documents_released", "buyer_notes", "created_at",
        )
        read_only_fields = fields


class BuyerPortalSaleSerializer(serializers.ModelSerializer):
    unit = BuyerPortalUnitSerializer(source="offplan_unit", read_only=True)
    installments = BuyerPortalInstallmentSerializer(many=True, read_only=True)
    payments = BuyerPortalPaymentSerializer(many=True, read_only=True)
    handover = serializers.SerializerMethodField()
    confirmed_total = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    outstanding_balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = OffPlanSale
        fields = (
            "id", "sale_reference", "unit", "sale_price", "currency", "deposit_required",
            "contract_date", "agreement_url", "status", "confirmed_total", "outstanding_balance",
            "installments", "payments", "handover", "created_at",
        )
        read_only_fields = fields

    def get_handover(self, obj):
        try:
            handover = obj.unit_handover
        except OffPlanUnitHandover.DoesNotExist:
            return None
        return BuyerPortalHandoverSerializer(handover, context=self.context).data