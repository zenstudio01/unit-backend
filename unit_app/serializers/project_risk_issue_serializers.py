
from rest_framework import serializers
from unit_app.models import ProjectRiskIssue, ProjectStakeholder


class ProjectRiskIssueSerializer(serializers.ModelSerializer):
    risk_score = serializers.IntegerField(read_only=True)
    severity = serializers.CharField(read_only=True)
    stakeholder_name = serializers.CharField(
        source="stakeholder.name",
        read_only=True,
        default=None,
    )
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    class Meta:
        model = ProjectRiskIssue
        fields = [
            "id",
            "reference",
            "project",
            "project_name",
            "organization",
            "stakeholder",
            "stakeholder_name",
            "item_type",
            "category",
            "category_display",
            "title",
            "description",
            "likelihood",
            "impact",
            "risk_score",
            "severity",
            "mitigation_plan",
            "resolution_notes",
            "status",
            "target_date",
            "resolved_at",
            "created_at",
            "updated_at",
        ]


class ProjectRiskIssueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRiskIssue
        fields = [
            "stakeholder",
            "item_type",
            "category",
            "title",
            "description",
            "likelihood",
            "impact",
            "mitigation_plan",
            "resolution_notes",
            "status",
            "target_date",
        ]

    def validate_stakeholder(self, value):
        if value is None:
            return value

        project = self.context["project"]

        if (
            value.project_id != project.pk
            or value.organization_id != project.organization_id
        ):
            raise serializers.ValidationError(
                "Stakeholder does not belong to this project."
            )

        return value

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Title is required."
            )
        return value

    def validate(self, attrs):
        status_value = attrs.get(
            "status",
            getattr(self.instance, "status", "open"),
        )
        notes = attrs.get(
            "resolution_notes",
            getattr(self.instance, "resolution_notes", ""),
        )

        if status_value in ("resolved", "closed") and not notes.strip():
            raise serializers.ValidationError({
                "resolution_notes":
                    "Resolution notes are required before resolving or closing."
            })

        return attrs
