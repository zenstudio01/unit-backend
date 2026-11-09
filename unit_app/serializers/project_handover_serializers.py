from rest_framework import serializers
from unit_app.models import (
    ProjectHandover, HandoverChecklistItem, HandoverDocument,
    HandoverInspection, HandoverAcceptance,
)


class ProjectHandoverSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, allow_null=True)

    class Meta:
        model = ProjectHandover
        fields = ["id", "project", "project_name", "organization", "client", "client_name",
                  "title", "description", "status", "target_handover_date", "actual_handover_date",
                  "review_notes", "handover_notes", "created_by", "created_by_name", "created_at", "updated_at"]
        read_only_fields = ["id", "project", "organization", "status", "actual_handover_date",
                            "created_by", "created_at", "updated_at"]


class HandoverChecklistItemSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True, allow_null=True)
    completed_by_name = serializers.CharField(source="completed_by.username", read_only=True, allow_null=True)

    class Meta:
        model = HandoverChecklistItem
        fields = ["id", "handover", "title", "description", "category", "status", "assigned_to",
                  "assigned_to_name", "due_date", "completed_at", "completed_by", "completed_by_name",
                  "notes", "sequence", "created_at", "updated_at"]
        read_only_fields = ["id", "handover", "completed_at", "completed_by", "created_at", "updated_at"]


class HandoverDocumentSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="document.title", read_only=True)
    document_status = serializers.CharField(source="document.status", read_only=True)

    class Meta:
        model = HandoverDocument
        fields = ["id", "handover", "document", "document_title", "document_status", "category",
                  "is_required", "notes", "added_by", "created_at"]
        read_only_fields = ["id", "handover", "added_by", "created_at"]


class HandoverInspectionSerializer(serializers.ModelSerializer):
    inspection_title = serializers.CharField(source="inspection.title", read_only=True)
    inspection_status = serializers.CharField(source="inspection.status", read_only=True)
    inspection_number = serializers.CharField(source="inspection.inspection_number", read_only=True)

    class Meta:
        model = HandoverInspection
        fields = ["id", "handover", "inspection", "inspection_title", "inspection_number",
                  "inspection_status", "is_required", "notes", "created_at"]
        read_only_fields = ["id", "handover", "created_at"]


class HandoverAcceptanceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    recorded_by_name = serializers.CharField(source="recorded_by.username", read_only=True, allow_null=True)

    class Meta:
        model = HandoverAcceptance
        fields = ["id", "handover", "client", "client_name", "decision", "comments",
                  "recorded_by", "recorded_by_name", "decided_at", "created_at"]
        read_only_fields = fields


class HandoverDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "rejected", "changes_requested"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class HandoverFinalizeSerializer(serializers.Serializer):
    handover_notes = serializers.CharField(required=False, allow_blank=True)