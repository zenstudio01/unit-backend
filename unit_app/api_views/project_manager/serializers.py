
from rest_framework import serializers
from unit_app.models import (
    ConstructionProject,
    ProjectPhase,
    ProjectMilestone,
    BOQSection,
    BOQItem,
    ProjectBudget, 
    ProjectExpense,
    ProjectDocument, 
    ProjectDocumentVersion,
    ProjectScheduleActivity,
    ProcurementSupplier,
    ProcurementMaterial,
    ProcurementPurchaseOrder,
    ProcurementOrderItem,
    ProcurementDelivery,
    ProcurementDeliveryItem,
    ProcurementMaterialIssue,

    WorkforceSubcontractor,
    WorkforceWorker,
    WorkforceAssignment,
    WorkforceAttendance,
    WorkforceTask,
    WorkforcePayment,


    QualityInspection,
    QualityChecklistItem,
    QualityDefect,
    QualityEvidence,
)


from decimal import Decimal



class ProjectPhaseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )
    milestone_count = serializers.IntegerField(
        read_only=True, default=0
    )

    class Meta:
        model = ProjectPhase
        fields = [
            "id", "project", "project_name",
            "name", "description", "sequence",
            "start_date", "end_date", "status",
            "completion_percentage", "milestone_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        project = attrs.get(
            "project", instance.project if instance else None
        )
        start = attrs.get(
            "start_date", instance.start_date if instance else None
        )
        end = attrs.get(
            "end_date", instance.end_date if instance else None
        )
        sequence = attrs.get(
            "sequence", instance.sequence if instance else 1
        )
        status = attrs.get(
            "status", instance.status if instance else "not_started"
        )
        percentage = attrs.get(
            "completion_percentage",
            instance.completion_percentage if instance else 0
        )

        if start and end and end < start:
            raise serializers.ValidationError({
                "end_date": "End date cannot precede start date."
            })

        if project:
            existing = ProjectPhase.objects.filter(
                project=project, sequence=sequence
            )
            if instance:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    "sequence": "This sequence is already used."
                })

        if status == "completed" and percentage != 100:
            raise serializers.ValidationError({
                "completion_percentage":
                    "Completed phases must have 100% progress."
            })

        if status == "not_started" and percentage != 0:
            raise serializers.ValidationError({
                "completion_percentage":
                    "Not-started phases must have 0% progress."
            })

        return attrs


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )
    phase_name = serializers.CharField(
        source="phase.name", read_only=True,
        default=None
    )

    class Meta:
        model = ProjectMilestone
        fields = [
            "id", "project", "project_name",
            "phase", "phase_name",
            "name", "description", "due_date",
            "completed_at", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "completed_at", "created_at", "updated_at"
        ]

    def validate(self, attrs):
        instance = self.instance
        project = attrs.get(
            "project", instance.project if instance else None
        )
        phase = attrs.get(
            "phase", instance.phase if instance else None
        )

        if phase and project and phase.project_id != project.id:
            raise serializers.ValidationError({
                "phase": "Phase must belong to the selected project."
            })

        return attrs


# boq section serializer


class BOQSectionSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)
    estimated_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )
    actual_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = BOQSection
        fields = [
            "id",
            "project",
            "name",
            "description",
            "sequence",
            "item_count",
            "estimated_total",
            "actual_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "project",
            "item_count",
            "estimated_total",
            "actual_total",
            "created_at",
            "updated_at",
        ]

    def validate_sequence(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Sequence must be at least 1."
            )
        return value


class BOQItemSerializer(serializers.ModelSerializer):
    estimated_cost = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )
    variance = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        read_only=True
    )
    section_name = serializers.CharField(
        source="section.name",
        read_only=True
    )

    class Meta:
        model = BOQItem
        fields = [
            "id",
            "section",
            "section_name",
            "item_code",
            "description",
            "unit",
            "quantity",
            "unit_rate",
            "actual_cost",
            "estimated_cost",
            "variance",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "section", "section_name",
            "estimated_cost", "variance",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        for field in ["quantity", "unit_rate", "actual_cost"]:
            value = attrs.get(field)
            if value is not None and value < Decimal("0"):
                raise serializers.ValidationError({
                    field: "Value cannot be negative."
                })
        return attrs


# serializer for project budget


class ProjectBudgetSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )
    phase_name = serializers.CharField(
        source="phase.name", read_only=True,
        default=None
    )
    spent = serializers.DecimalField(
        max_digits=20, decimal_places=2,
        read_only=True
    )
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = ProjectBudget
        fields = [
            "id", "project", "project_name",
            "phase", "phase_name", "name",
            "amount", "description", "spent",
            "remaining", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "project", "project_name",
            "spent", "remaining",
            "created_at", "updated_at",
        ]

    def get_remaining(self, obj):
        spent = getattr(obj, "spent", 0) or 0
        return str(obj.amount - spent)


class ProjectExpenseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )
    budget_name = serializers.CharField(
        source="budget.name", read_only=True
    )
    phase_name = serializers.CharField(
        source="phase.name", read_only=True,
        default=None
    )

    class Meta:
        model = ProjectExpense
        fields = [
            "id", "project", "project_name",
            "budget", "budget_name",
            "phase", "phase_name", "boq_item",
            "title", "description", "category",
            "amount", "expense_date", "vendor",
            "payment_reference", "status",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "project", "project_name",
            "created_by", "created_at", "updated_at",
        ]


# document serializers
class ProjectDocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocumentVersion
        fields = [
            "id",
            "version_number",
            "original_filename",
            "file_size",
            "file_format",
            "change_notes",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = fields


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDocument
        fields = [
            "id",
            "project",
            "title",
            "document_number",
            "description",
            "category",
            "status",
            "uploaded_by",
            "uploaded_by_name",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "latest_version",
            "version_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "project", "status",
            "uploaded_by", "reviewed_by",
            "reviewed_at", "review_notes",
            "created_at", "updated_at",
        ]

    def get_uploaded_by_name(self, obj):
        return (
            obj.uploaded_by.get_username()
            if obj.uploaded_by else None
        )

    def get_latest_version(self, obj):
        version = obj.versions.first()
        return (
            ProjectDocumentVersionSerializer(version).data
            if version else None
        )

    def get_version_count(self, obj):
        return obj.versions.count()





class ProjectScheduleActivitySerializer(serializers.ModelSerializer):
    phase_name = serializers.CharField(
        source="phase.name", read_only=True, default=None
    )
    predecessor_name = serializers.CharField(
        source="predecessor.name", read_only=True, default=None
    )

    class Meta:
        model = ProjectScheduleActivity
        fields = [
            "id", "project", "phase", "phase_name",
            "task", "milestone", "predecessor",
            "predecessor_name", "name", "description",
            "start_date", "end_date", "actual_end_date",
            "sequence", "status", "completion_percentage",
            "is_critical", "notes", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "project", "phase_name",
            "predecessor_name", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        start = attrs.get(
            "start_date",
            instance.start_date if instance else None
        )
        end = attrs.get(
            "end_date",
            instance.end_date if instance else None
        )

        if start and end and end < start:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        progress = attrs.get(
            "completion_percentage",
            instance.completion_percentage if instance else 0
        )
        status = attrs.get(
            "status",
            instance.status if instance else "not_started"
        )

        if status == "completed" and progress != 100:
            raise serializers.ValidationError({
                "completion_percentage":
                    "Completed activities must have 100% progress."
            })

        if status == "not_started" and progress != 0:
            raise serializers.ValidationError({
                "completion_percentage":
                    "Not started activities must have 0% progress."
            })

        return attrs





class ProcurementSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementSupplier
        fields = [
            "id", "name", "contact_person", "phone",
            "email", "address", "kra_pin", "is_active",
        ]
        read_only_fields = ["id"]


class ProcurementMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementMaterial
        fields = [
            "id", "name", "sku", "unit", "category",
            "description", "estimated_unit_price", "is_active",
        ]
        read_only_fields = ["id"]


class ProcurementOrderItemSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(
        source="material.name", read_only=True
    )
    unit = serializers.CharField(
        source="material.unit", read_only=True
    )
    total_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = ProcurementOrderItem
        fields = [
            "id", "material", "material_name", "unit",
            "boq_item", "quantity", "unit_price",
            "total_amount",
        ]


class ProcurementPurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True
    )
    items = ProcurementOrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=20, decimal_places=3, read_only=True
    )

    class Meta:
        model = ProcurementPurchaseOrder
        fields = [
            "id", "project", "supplier", "supplier_name",
            "order_number", "status", "order_date",
            "expected_delivery_date", "notes", "created_by",
            "approved_by", "approved_at", "total_amount",
            "items", "created_at",
        ]


class ProcurementDeliveryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementDeliveryItem
        fields = [
            "id", "order_item", "quantity_received",
        ]


class ProcurementDeliverySerializer(serializers.ModelSerializer):
    items = ProcurementDeliveryItemSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = ProcurementDelivery
        fields = [
            "id", "order", "delivery_number",
            "delivery_date", "notes", "received_by",
            "items", "created_at",
        ]


class ProcurementMaterialIssueSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(
        source="material.name", read_only=True
    )

    class Meta:
        model = ProcurementMaterialIssue
        fields = [
            "id", "project", "material", "material_name",
            "quantity", "issued_to", "purpose",
            "issue_date", "issued_by", "created_at",
        ]




# workforce serializers


class WorkforceSubcontractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkforceSubcontractor
        fields = [
            "id", "name", "contact_person", "phone",
            "email", "trade", "address", "kra_pin",
            "is_active",
        ]


class WorkforceWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkforceWorker
        fields = [
            "id", "worker_code", "full_name", "phone",
            "trade", "employment_type", "subcontractor",
            "default_daily_rate", "is_active",
        ]


class WorkforceAssignmentSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(
        source="worker.full_name", read_only=True
    )
    trade = serializers.CharField(
        source="worker.trade", read_only=True
    )

    class Meta:
        model = WorkforceAssignment
        fields = [
            "id", "project", "worker", "worker_name",
            "trade", "start_date", "end_date",
            "daily_rate", "is_active", "notes",
        ]
        read_only_fields = ["id", "project", "worker"]

    def validate(self, attrs):
        start = attrs.get(
            "start_date",
            self.instance.start_date if self.instance else None,
        )
        end = attrs.get(
            "end_date",
            self.instance.end_date if self.instance else None,
        )
        if end and start and end < start:
            raise serializers.ValidationError({
                "end_date": "End date cannot precede start date."
            })
        return attrs


class WorkforceAttendanceSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(
        source="assignment.worker.full_name",
        read_only=True,
    )
    earned_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = WorkforceAttendance
        fields = [
            "id", "assignment", "worker_name",
            "date", "status", "daily_rate_snapshot",
            "earned_amount", "notes", "recorded_by",
        ]
        read_only_fields = [
            "id", "daily_rate_snapshot",
            "earned_amount", "recorded_by",
        ]


class WorkforceTaskSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(
        source="assignment.worker.full_name",
        read_only=True,
    )

    class Meta:
        model = WorkforceTask
        fields = [
            "id", "assignment", "worker_name",
            "title", "description", "due_date",
            "status",
        ]


class WorkforcePaymentSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(
        source="assignment.worker.full_name",
        read_only=True,
    )

    class Meta:
        model = WorkforcePayment
        fields = [
            "id", "assignment", "worker_name",
            "amount", "payment_date",
            "payment_method", "reference",
            "notes", "recorded_by",
        ]
        read_only_fields = ["id", "recorded_by"]




# quality inspection serializers
class QualityChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityChecklistItem
        fields = [
            "id", "inspection", "title",
            "result", "remarks", "sequence",
        ]
        read_only_fields = ["id", "inspection"]


class QualityDefectSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityDefect
        fields = [
            "id", "inspection", "checklist_item",
            "title", "description", "severity",
            "status", "assigned_to", "due_date",
            "corrective_action", "verification_notes",
            "verified_by", "created_at",
        ]
        read_only_fields = [
            "id", "inspection", "status",
            "verified_by", "created_at",
        ]


class QualityEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityEvidence
        fields = [
            "id", "inspection", "defect", "file_url",
            "caption", "created_at",
        ]


class QualityInspectionSerializer(serializers.ModelSerializer):
    checklist_items = QualityChecklistSerializer(
        many=True, read_only=True
    )
    defects = QualityDefectSerializer(
        many=True, read_only=True
    )
    evidence = QualityEvidenceSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = QualityInspection
        fields = [
            "id", "project", "phase", "title",
            "inspection_number", "location",
            "description", "scheduled_date",
            "inspected_date", "status", "inspector",
            "created_by", "review_notes",
            "reviewed_by", "reviewed_at",
            "checklist_items", "defects", "evidence",
            "created_at",
        ]
        read_only_fields = [
            "id", "inspection_number", "status",
            "created_by", "reviewed_by",
            "reviewed_at", "created_at",
        ]






