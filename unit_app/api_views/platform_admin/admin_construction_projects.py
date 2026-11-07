
from decimal import Decimal

from django.apps import apps
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    ConstructionProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectTask,
    BOQItem,
    ProjectProgressUpdate,
)


# ============================================================
# PERMISSIONS
# ============================================================

class IsPlatformAdmin(BasePermission):
    message = "UNIT platform administrator access required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and (user.is_staff or user.is_superuser)
        )


# ============================================================
# PAGINATION
# ============================================================

class ProjectPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# ============================================================
# HELPERS
# ============================================================

def optional_model(model_name):
    try:
        return apps.get_model("unit_app", model_name)
    except LookupError:
        return None


def has_field(model, field_name):
    return any(
        field.name == field_name
        for field in model._meta.fields
    )


def get_field_value(instance, field_name, default=None):
    return getattr(instance, field_name, default)


def display_user(user):
    if not user:
        return None

    return (
        user.get_full_name()
        or user.get_username()
    )


def optional_project_count(model_name, project_id=None):
    model = optional_model(model_name)

    if model is None:
        return None

    project_field = next(
        (
            field
            for field in model._meta.fields
            if field.name == "project"
            and field.is_relation
            and field.related_model == ConstructionProject
        ),
        None,
    )

    if project_field is None:
        return None

    queryset = model.objects.all()

    if project_id is not None:
        queryset = queryset.filter(project_id=project_id)

    return queryset.count()


def optional_project_amount(
    model_name,
    amount_fields,
    project_id=None,
):
    model = optional_model(model_name)

    if model is None:
        return None

    project_field = next(
        (
            field
            for field in model._meta.fields
            if field.name == "project"
            and field.is_relation
            and field.related_model == ConstructionProject
        ),
        None,
    )

    if project_field is None:
        return None

    amount_field = next(
        (
            field.name
            for field in model._meta.fields
            if field.name in amount_fields
            and field.get_internal_type() in {
                "DecimalField",
                "FloatField",
                "IntegerField",
                "PositiveIntegerField",
                "BigIntegerField",
            }
        ),
        None,
    )

    if amount_field is None:
        return None

    queryset = model.objects.all()

    if project_id is not None:
        queryset = queryset.filter(project_id=project_id)

    result = queryset.aggregate(
        total=Sum(amount_field)
    )

    return str(result["total"] or Decimal("0"))


def get_valid_choices(model, field_name):
    try:
        field = model._meta.get_field(field_name)
        return {
            value
            for value, _ in field.flatchoices
        }
    except Exception:
        return set()


# ============================================================
# PROJECT PROGRESS
# ============================================================

def project_progress(project):
    latest = (
        ProjectProgressUpdate.objects
        .filter(project_id=project.id)
        .order_by("-reported_at", "-id")
        .first()
    )

    if latest:
        return round(
            float(latest.completion_percentage or 0),
            1,
        )

    percentages = list(
        ProjectPhase.objects
        .filter(project_id=project.id)
        .values_list(
            "completion_percentage",
            flat=True,
        )
    )

    if not percentages:
        return 0

    total = sum(
        float(value or 0)
        for value in percentages
    )

    return round(total / len(percentages), 1)


# ============================================================
# PROJECT SERIALIZER
# ============================================================

def serialize_project(project):
    manager = project.project_manager

    project_id = project.id

    phases_count = ProjectPhase.objects.filter(
        project_id=project_id
    ).count()

    milestones_count = ProjectMilestone.objects.filter(
        project_id=project_id
    ).count()

    tasks_queryset = ProjectTask.objects.filter(
        project_id=project_id
    )

    tasks_count = tasks_queryset.count()

    completed_tasks_count = tasks_queryset.filter(
        status="completed"
    ).count()

    boq_count = BOQItem.objects.filter(
        section__project_id=project_id
    ).count()

    return {
        "id": project.id,
        "project_code": project.project_code,
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type,
        "status": project.status,

        "start_date": project.start_date,
        "expected_end_date": project.expected_end_date,
        "actual_end_date": project.actual_end_date,

        "approved_budget": str(
            project.approved_budget or Decimal("0")
        ),

        "created_at": project.created_at,

        "organization": {
            "id": project.organization_id,
            "name": project.organization.name,
        },

        "property": (
            {
                "id": project.property_id,
                "name": project.property.name,
            }
            if project.property_id
            else None
        ),

        "project_manager": (
            {
                "id": manager.id,
                "name": display_user(manager),
                "email": manager.email,
            }
            if manager
            else None
        ),

        "progress": project_progress(project),

        "phases": phases_count,
        "milestones": milestones_count,
        "tasks": tasks_count,
        "completed_tasks": completed_tasks_count,
        "boq_items": boq_count,
    }


# ============================================================
# GET ALL CONSTRUCTION PROJECTS
# ============================================================

@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_construction_projects(request):

    queryset = (
        ConstructionProject.objects
        .select_related(
            "organization",
            "property",
            "project_manager",
        )
    )

    search = request.query_params.get(
        "search", ""
    ).strip()

    status_filter = request.query_params.get(
        "status", ""
    ).strip()

    project_type = request.query_params.get(
        "type", ""
    ).strip()

    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    # Search
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(project_code__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(property__name__icontains=search)
            | Q(project_manager__first_name__icontains=search)
            | Q(project_manager__last_name__icontains=search)
        )

    # Status filter
    if status_filter:
        valid_statuses = get_valid_choices(
            ConstructionProject,
            "status",
        )

        if (
            valid_statuses
            and status_filter not in valid_statuses
        ):
            return Response(
                {"message": "Invalid project status."},
                status=400,
            )

        queryset = queryset.filter(
            status=status_filter
        )

    # Project type filter
    if project_type:
        valid_types = get_valid_choices(
            ConstructionProject,
            "project_type",
        )

        if (
            valid_types
            and project_type not in valid_types
        ):
            return Response(
                {"message": "Invalid project type."},
                status=400,
            )

        queryset = queryset.filter(
            project_type=project_type
        )

    # Organization filter
    if organization_id:
        if not organization_id.isdigit():
            return Response(
                {"message": "Invalid organization ID."},
                status=400,
            )

        queryset = queryset.filter(
            organization_id=int(organization_id)
        )

    queryset = queryset.order_by(
        "-created_at",
        "-id",
    )

    paginator = ProjectPagination()

    page = paginator.paginate_queryset(
        queryset,
        request,
    )

    results = [
        serialize_project(project)
        for project in page
    ]

    return paginator.get_paginated_response(
        results
    )


# ============================================================
# CONSTRUCTION PROJECT STATISTICS
# ============================================================

@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_construction_project_stats(request):

    projects = ConstructionProject.objects.all()
    tasks = ProjectTask.objects.all()

    total_budget = projects.aggregate(
        total=Sum("approved_budget")
    )["total"] or Decimal("0")

    today = timezone.localdate()

    overdue_tasks = tasks.filter(
        due_date__lt=today
    ).exclude(
        status__in=[
            "completed",
            "cancelled",
        ]
    ).count()

    return Response({
        "total_projects": projects.count(),

        "planning_projects": projects.filter(
            status="planning"
        ).count(),

        "in_progress_projects": projects.filter(
            status="in_progress"
        ).count(),

        "completed_projects": projects.filter(
            status="completed"
        ).count(),

        "on_hold_projects": projects.filter(
            status="on_hold"
        ).count(),

        "total_approved_budget": str(total_budget),

        "total_phases": ProjectPhase.objects.count(),

        "total_milestones": ProjectMilestone.objects.count(),

        "completed_milestones": (
            ProjectMilestone.objects.filter(
                status="completed"
            ).count()
        ),

        "total_tasks": tasks.count(),

        "completed_tasks": tasks.filter(
            status="completed"
        ).count(),

        "overdue_tasks": overdue_tasks,

        "total_boq_items": BOQItem.objects.count(),

        "total_expenses": optional_project_amount(
            "ProjectExpense",
            ["amount", "total_amount", "cost"],
        ),

        "workforce_workers": optional_project_count(
            "WorkforceWorker"
        ),

        "workforce_assignments": optional_project_count(
            "WorkforceAssignment"
        ),

        "procurement_orders": optional_project_count(
            "ProcurementPurchaseOrder"
        ),

        "quality_inspections": optional_project_count(
            "QualityInspection"
        ),

        "quality_defects": optional_project_count(
            "QualityDefect"
        ),
    })


# ============================================================
# CONSTRUCTION PROJECT DETAILS
# ============================================================

@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_construction_project_detail(request, project_id):

    project = get_object_or_404(
        ConstructionProject.objects.select_related(
            "organization",
            "property",
            "project_manager",
        ),
        pk=project_id,
    )

    # Phases
    phases = (
        ProjectPhase.objects
        .filter(project_id=project_id)
        .order_by("sequence", "id")
    )

    # Milestones
    milestones = (
        ProjectMilestone.objects
        .filter(project_id=project_id)
        .order_by("due_date", "id")[:100]
    )

    # Tasks
    tasks = (
        ProjectTask.objects
        .filter(project_id=project_id)
        .select_related("assigned_to")
        .order_by("-id")[:100]
    )

    # Progress reports
    progress_updates = (
        ProjectProgressUpdate.objects
        .filter(project_id=project_id)
        .select_related("reported_by")
        .order_by("-reported_at", "-id")[:20]
    )

    # BOQ items
    boq_items = (
        BOQItem.objects
        .filter(project_id=project_id)
        .order_by("id")[:100]
    )

    return Response({

        "project": serialize_project(project),

        # ----------------------------------------------------
        # PHASES
        # ----------------------------------------------------
        "phases": [
            {
                "id": phase.id,
                "name": phase.name,
                "sequence": phase.sequence,
                "status": phase.status,
                "completion_percentage": str(
                    phase.completion_percentage or 0
                ),
                "start_date": phase.start_date,
                "end_date": phase.end_date,
            }
            for phase in phases
        ],

        # ----------------------------------------------------
        # MILESTONES
        # ----------------------------------------------------
        "milestones": [
            {
                "id": item.id,
                "name": item.name,
                "status": item.status,
                "due_date": item.due_date,
                "completed_at": item.completed_at,
            }
            for item in milestones
        ],

        # ----------------------------------------------------
        # TASKS
        # ----------------------------------------------------
        "tasks": [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "due_date": item.due_date,
                "assigned_to": display_user(
                    item.assigned_to
                ),
            }
            for item in tasks
        ],

        # ----------------------------------------------------
        # BILL OF QUANTITIES
        # ----------------------------------------------------
        "boq_items": [
            {
                "id": item.id,
                "item_code": item.item_code,
                "description": item.description,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "estimated_amount": str(
                    item.estimated_amount or 0
                ),
                "status": item.status,
            }
            for item in boq_items
        ],

        # ----------------------------------------------------
        # PROGRESS REPORTS
        # ----------------------------------------------------
        "progress_updates": [
            {
                "id": item.id,
                "summary": item.summary,
                "completion_percentage": str(
                    item.completion_percentage or 0
                ),
                "reported_at": item.reported_at,
                "reported_by": display_user(
                    item.reported_by
                ),
            }
            for item in progress_updates
        ],

        # ----------------------------------------------------
        # OPTIONAL CONSTRUCTION MODULES
        # ----------------------------------------------------
        "modules": {

            "expenses": {
                "count": optional_project_count(
                    "ProjectExpense",
                    project_id,
                ),
                "total": optional_project_amount(
                    "ProjectExpense",
                    ["amount", "total_amount", "cost"],
                    project_id,
                ),
            },

            "workforce": {
                "workers": optional_project_count(
                    "WorkforceWorker",
                    project_id,
                ),
                "assignments": optional_project_count(
                    "WorkforceAssignment",
                    project_id,
                ),
                "attendance": optional_project_count(
                    "WorkforceAttendance",
                    project_id,
                ),
            },

            "procurement": {
                "purchase_orders": optional_project_count(
                    "ProcurementPurchaseOrder",
                    project_id,
                ),
                "deliveries": optional_project_count(
                    "ProcurementDelivery",
                    project_id,
                ),
            },

            "quality": {
                "inspections": optional_project_count(
                    "QualityInspection",
                    project_id,
                ),
                "defects": optional_project_count(
                    "QualityDefect",
                    project_id,
                ),
            },
        },
    })
