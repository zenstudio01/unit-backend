from unit_app.api_views.common_imports import *



def allowed_organizations(user):
    owned = Organization.objects.filter(
        created_by=user
    ).values_list("id", flat=True)

    memberships = OrganizationMembership.objects.filter(
        user=user,
        is_active=True
    ).values_list("organization_id", flat=True)

    return Organization.objects.filter(
        id__in=list(owned) + list(memberships)
    )


def allowed_projects(user):
    return ConstructionProject.objects.filter(
        organization__in=allowed_organizations(user)
    )


def get_accessible_project(user, project_id):
    return get_object_or_404(
        allowed_projects(user),
        pk=project_id
    )


def can_manage_project(user, project):
    """
    Baseline write authorization.
    Adapt to your RolePermission rules when enforcing
    granular project_phase/project_milestone permissions.
    """
    if project.organization.created_by_id == user.id:
        return True

    return OrganizationMembership.objects.filter(
        organization=project.organization,
        user=user,
        is_active=True,
        roles__name__in=[
            "organization_owner",
            "organization_admin",
            "project_manager",
            "site_manager",
        ],
        roles__is_active=True,
    ).exists()


def write_denied():
    return Response(
        {"message": "You cannot modify this project's records."},
        status=403
    )



# boQ section helpers
def boq_write_denied():
    return Response(
        {"message": "You do not have permission to modify this BOQ."},
        status=403
    )


def section_queryset(user):
    return BOQSection.objects.filter(
        project__in=allowed_projects(user)
    )


def item_queryset(user):
    return BOQItem.objects.filter(
        section__project__in=allowed_projects(user)
    )


def section_totals(queryset):
    estimated_expression = ExpressionWrapper(
        F("items__quantity") * F("items__unit_rate"),
        output_field=DecimalField(
            max_digits=20, decimal_places=2
        ),
    )

    return queryset.annotate(
        item_count=Count("items"),
        estimated_total=Coalesce(
            Sum(estimated_expression),
            Decimal("0.00"),
            output_field=DecimalField(
                max_digits=20, decimal_places=2
            )
        ),
        actual_total=Coalesce(
            Sum("items__actual_cost"),
            Decimal("0.00"),
            output_field=DecimalField(
                max_digits=20, decimal_places=2
            )
        ),
    )