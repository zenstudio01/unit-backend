from unit_app.api_views.common_imports import *

from .serializers import (
    ProjectBudgetSerializer,
    ProjectExpenseSerializer,
)
from .helper import *


COUNTED_STATUSES = ["approved", "paid"]


def budgets_for(user):
    return ProjectBudget.objects.filter(
        project__in=allowed_projects(user)
    )


def expenses_for(user):
    return ProjectExpense.objects.filter(
        project__in=allowed_projects(user)
    )


def budget_with_spending(queryset):
    return queryset.annotate(
        spent=Coalesce(
            Sum(
                "expenses__amount",
                filter=Q(
                    expenses__status__in=COUNTED_STATUSES
                ),
            ),
            Decimal("0.00"),
        )
    )


def check_expense_links(project, data, instance=None):
    budget_id = data.get(
        "budget",
        instance.budget_id if instance else None
    )
    phase_id = data.get(
        "phase",
        instance.phase_id if instance else None
    )
    boq_item_id = data.get(
        "boq_item",
        instance.boq_item_id if instance else None
    )

    budget = ProjectBudget.objects.filter(
        id=budget_id, project=project
    ).first()

    if not budget:
        return {"budget": ["Select a valid project budget."]}

    if phase_id:
        if not ProjectPhase.objects.filter(
            id=phase_id, project=project
        ).exists():
            return {"phase": ["Invalid project phase."]}

    if boq_item_id:
        if not BOQItem.objects.filter(
            id=boq_item_id,
            section__project=project
        ).exists():
            return {"boq_item": ["Invalid project BOQ item."]}

    if budget.phase_id:
        if phase_id and str(phase_id) != str(budget.phase_id):
            return {
                "phase": [
                    "Expense phase must match the budget phase."
                ]
            }

    return None


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_budgets(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"message": "project_id is required."},
                status=400
            )

        project = get_accessible_project(
            request.user, project_id
        )
        budgets = budget_with_spending(
            ProjectBudget.objects.filter(project=project)
        ).select_related("phase", "project")

        return Response({
            "results": ProjectBudgetSerializer(
                budgets, many=True
            ).data
        })

    project = get_accessible_project(
        request.user, request.data.get("project")
    )

    if not can_manage_project(request.user, project):
        return Response(
            {"message": "Permission denied."},
            status=403
        )

    phase_id = request.data.get("phase")
    if phase_id and not ProjectPhase.objects.filter(
        id=phase_id, project=project
    ).exists():
        return Response(
            {"phase": ["Invalid project phase."]},
            status=400
        )

    serializer = ProjectBudgetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    budget = serializer.save(project=project)

    return Response(
        ProjectBudgetSerializer(budget).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_budget_detail(request, budget_id):
    budget = get_object_or_404(
        budgets_for(request.user).select_related("project"),
        id=budget_id
    )

    if request.method == "GET":
        obj = budget_with_spending(
            ProjectBudget.objects.filter(id=budget.id)
        ).first()
        return Response(ProjectBudgetSerializer(obj).data)

    if not can_manage_project(request.user, budget.project):
        return Response(
            {"message": "Permission denied."}, status=403
        )

    if request.method == "DELETE":
        if budget.expenses.exists():
            return Response({
                "message": "Delete or reassign linked expenses first."
            }, status=400)
        budget.delete()
        return Response(status=204)

    phase_id = request.data.get("phase", budget.phase_id)
    if phase_id and not ProjectPhase.objects.filter(
        id=phase_id, project=budget.project
    ).exists():
        return Response(
            {"phase": ["Invalid project phase."]}, status=400
        )

    if budget.expenses.exists() and str(phase_id) != str(budget.phase_id):
        return Response({
            "phase": [
                "Cannot change phase while expenses are linked."
            ]
        }, status=400)

    serializer = ProjectBudgetSerializer(
        budget, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_expenses(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return Response(
                {"message": "project_id is required."},
                status=400
            )

        project = get_accessible_project(
            request.user, project_id
        )

        expenses = ProjectExpense.objects.filter(
            project=project
        ).select_related(
            "budget", "phase", "project"
        )

        return Response({
            "results": ProjectExpenseSerializer(
                expenses, many=True
            ).data
        })

    project = get_accessible_project(
        request.user, request.data.get("project")
    )

    if not can_manage_project(request.user, project):
        return Response(
            {"message": "Permission denied."}, status=403
        )

    errors = check_expense_links(project, request.data)
    if errors:
        return Response(errors, status=400)

    serializer = ProjectExpenseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # New expenses must begin as drafts.
    expense = serializer.save(
        project=project,
        created_by=request.user,
        status="draft",
    )

    return Response(
        ProjectExpenseSerializer(expense).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_expense_detail(request, expense_id):
    expense = get_object_or_404(
        expenses_for(request.user).select_related(
            "project", "budget", "phase"
        ),
        id=expense_id
    )

    if request.method == "GET":
        return Response(
            ProjectExpenseSerializer(expense).data
        )

    if not can_manage_project(request.user, expense.project):
        return Response(
            {"message": "Permission denied."}, status=403
        )

    if request.method == "DELETE":
        if expense.status in COUNTED_STATUSES:
            return Response({
                "message": "Approved or paid expenses cannot be deleted."
            }, status=400)
        expense.delete()
        return Response(status=204)

    if expense.status in COUNTED_STATUSES:
        return Response({
            "message":
                "Approved or paid expenses cannot be edited directly."
        }, status=400)

    errors = check_expense_links(
        expense.project, request.data, expense
    )
    if errors:
        return Response(errors, status=400)

    serializer = ProjectExpenseSerializer(
        expense, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)

    # Status changes use the dedicated endpoint.
    serializer.save(status=expense.status)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def project_expense_status(request, expense_id):
    expense = get_object_or_404(
        expenses_for(request.user).select_related("project"),
        id=expense_id
    )

    if not can_manage_project(request.user, expense.project):
        return Response(
            {"message": "Permission denied."}, status=403
        )

    target = request.data.get("status")
    allowed = {
        "draft": ["pending"],
        "pending": ["approved", "rejected"],
        "rejected": ["draft"],
        "approved": ["paid"],
        "paid": [],
    }

    if target not in allowed.get(expense.status, []):
        return Response({
            "message": "Invalid expense status transition."
        }, status=400)

    expense.status = target
    expense.save(update_fields=["status", "updated_at"])

    return Response(
        ProjectExpenseSerializer(expense).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_financial_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return Response(
            {"message": "project_id is required."}, status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )

    budgets = ProjectBudget.objects.filter(project=project)
    expenses = ProjectExpense.objects.filter(project=project)

    allocated = budgets.aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    approved = expenses.filter(
        status__in=COUNTED_STATUSES
    ).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    pending = expenses.filter(status="pending").aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    paid = expenses.filter(status="paid").aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    remaining = allocated - approved
    utilization = (
        round((approved / allocated) * 100, 2)
        if allocated > 0 else 0
    )

    by_category = list(
        expenses.filter(
            status__in=COUNTED_STATUSES
        ).values("category").annotate(
            total=Sum("amount")
        ).order_by("-total")
    )

    return Response({
        "project_id": project.id,
        "currency": "KES",
        "total_budget": allocated,
        "approved_expenses": approved,
        "pending_expenses": pending,
        "paid_expenses": paid,
        "remaining_budget": remaining,
        "utilization_percentage": utilization,
        "over_budget": remaining < 0,
        "total_allocations": budgets.count(),
        "total_expenses": expenses.count(),
        "by_category": by_category,
    })
