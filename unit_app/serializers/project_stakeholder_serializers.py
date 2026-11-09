
from rest_framework import serializers
from unit_app.models import ProjectStakeholder


class ProjectStakeholderSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(
        source="get_role_display", read_only=True
    )
    type_display = serializers.CharField(
        source="get_stakeholder_type_display",
        read_only=True,
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True
    )

    class Meta:
        model = ProjectStakeholder
        fields = [
            "id",
            "project",
            "project_name",
            "organization",
            "user",
            "name",
            "company",
            "role",
            "role_display",
            "stakeholder_type",
            "type_display",
            "email",
            "phone_number",
            "responsibilities",
            "notes",
            "status",
            "is_primary_contact",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "project", "organization",
            "project_name", "created_at", "updated_at",
        ]


class StakeholderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStakeholder
        fields = [
            "user",
            "name",
            "company",
            "role",
            "stakeholder_type",
            "email",
            "phone_number",
            "responsibilities",
            "notes",
            "status",
            "is_primary_contact",
        ]
        extra_kwargs = {
            "user": {"required": False, "allow_null": True},
            "name": {"required": True},
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Stakeholder name is required."
            )
        return value

    def validate_user(self, value):
        if value is None:
            return value

        project = self.context["project"]

        if not value.organization_memberships.filter(
            organization=project.organization,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "Linked user must be an active member "
                "of this project organization."
            )
        return value
