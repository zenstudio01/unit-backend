
from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from unit_app.models import (
    MaintenanceTicket,
    MaintenanceMedia,
    MaintenanceComment,
    MaintenanceStatusHistory,
    MaintenanceApproval,
    MaintenanceWarranty,
)


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


class MaintenancePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def display_user(user):
    if not user:
        return None

    return {
        "id": user.pk,
        "name": user.get_full_name() or user.get_username(),
        "email": user.email,
    }


def iso(value):
    return value.isoformat() if value else None


def amount(value):
    return str(value) if value is not None else None


def choices(model, field_name):
    return [
        {"value": key, "label": str(label)}
        for key, label in model._meta.get_field(
            field_name
        ).flatchoices
    ]


def ticket_queryset():
    return MaintenanceTicket.objects.select_related(
        "organization",
        "property",
        "building",
        "unit",
        "reported_by",
        "assigned_to",
    )


def serialize_ticket(ticket):
    return {
        "id": ticket.pk,
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "source": ticket.source,
        "status": ticket.status,
        "organization": {
            "id": ticket.organization_id,
            "name": ticket.organization.name,
        },
        "property": {
            "id": ticket.property_id,
            "name": ticket.property.name,
        },
        "building": (
            {
                "id": ticket.building_id,
                "name": ticket.building.name,
            }
            if ticket.building_id else None
        ),
        "unit": (
            {
                "id": ticket.unit_id,
                "name": ticket.unit.name,
            }
            if ticket.unit_id else None
        ),
        "reported_by": display_user(ticket.reported_by),
        "assigned_to": display_user(ticket.assigned_to),
        "preferred_date": iso(ticket.preferred_date),
        "scheduled_at": iso(ticket.scheduled_at),
        "completed_at": iso(ticket.completed_at),
        "closed_at": iso(ticket.closed_at),
        "estimated_cost": amount(ticket.estimated_cost),
        "actual_cost": amount(ticket.actual_cost),
        "created_at": iso(ticket.created_at),
        "updated_at": iso(ticket.updated_at),
    }


def paginate(request, queryset, serializer):
    paginator = MaintenancePagination()
    page = paginator.paginate_queryset(queryset, request)

    return paginator.get_paginated_response([
        serializer(item) for item in page
    ])


def apply_filters(request, queryset):
    search = request.query_params.get(
        "search", ""
    ).strip()

    status = request.query_params.get(
        "status", ""
    ).strip()

    priority = request.query_params.get(
        "priority", ""
    ).strip()

    category = request.query_params.get(
        "category", ""
    ).strip()

    organization_id = request.query_params.get(
        "organization_id", ""
    ).strip()

    if search:
        queryset = queryset.filter(
            Q(ticket_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(organization__name__icontains=search)
            | Q(property__name__icontains=search)
        )

    for field_name, selected in (
        ("status", status),
        ("priority", priority),
        ("category", category),
    ):
        if not selected:
            continue

        valid = {
            item["value"]
            for item in choices(
                MaintenanceTicket,
                field_name,
            )
        }

        if selected not in valid:
            return None, Response(
                {
                    "message": (
                        f"Invalid maintenance {field_name}."
                    )
                },
                status=400,
            )

        queryset = queryset.filter(
            **{field_name: selected}
        )

    if organization_id:
        if not organization_id.isdigit():
            return None, Response(
                {"message": "Invalid organization ID."},
                status=400,
            )

        queryset = queryset.filter(
            organization_id=int(organization_id)
        )

    return queryset, None


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_maintenance_tickets(request):
    queryset, error = apply_filters(
        request,
        ticket_queryset(),
    )

    if error is not None:
        return error

    queryset = queryset.order_by(
        "-created_at",
        "-id",
    )

    return paginate(
        request,
        queryset,
        serialize_ticket,
    )


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_maintenance_stats(request):
    tickets = MaintenanceTicket.objects.all()

    today = timezone.now()
    last_30_days = today - timedelta(days=30)

    totals = tickets.aggregate(
        total_estimated_cost=Sum("estimated_cost"),
        total_actual_cost=Sum("actual_cost"),
    )

    status_counts = {
        row["status"]: row["count"]
        for row in tickets.values("status").annotate(
            count=Count("id")
        )
    }

    priority_counts = {
        row["priority"]: row["count"]
        for row in tickets.values("priority").annotate(
            count=Count("id")
        )
    }

    category_counts = list(
        tickets.values("category")
        .annotate(count=Count("id"))
        .order_by("-count", "category")
    )

    completed_count = tickets.filter(
        status__in=["completed", "closed"]
    ).count()

    total_count = tickets.count()

    return Response({
        "total_tickets": total_count,
        "open_tickets": status_counts.get("open", 0),
        "under_review_tickets": status_counts.get(
            "under_review", 0
        ),
        "approved_tickets": status_counts.get(
            "approved", 0
        ),
        "assigned_tickets": status_counts.get(
            "assigned", 0
        ),
        "in_progress_tickets": status_counts.get(
            "in_progress", 0
        ),
        "awaiting_approval_tickets": status_counts.get(
            "awaiting_approval", 0
        ),
        "completed_tickets": completed_count,
        "closed_tickets": status_counts.get("closed", 0),
        "cancelled_tickets": status_counts.get(
            "cancelled", 0
        ),
        "unassigned_tickets": tickets.filter(
            assigned_to__isnull=True
        ).exclude(
            status__in=["completed", "closed", "cancelled"]
        ).count(),
        "urgent_tickets": tickets.filter(
            priority__in=["urgent", "emergency"]
        ).exclude(
            status__in=["completed", "closed", "cancelled"]
        ).count(),
        "new_last_30_days": tickets.filter(
            created_at__gte=last_30_days
        ).count(),
        "completion_rate": (
            round(completed_count / total_count * 100, 1)
            if total_count else 0
        ),
        "total_estimated_cost": str(
            totals["total_estimated_cost"]
            or Decimal("0")
        ),
        "total_actual_cost": str(
            totals["total_actual_cost"]
            or Decimal("0")
        ),
        "pending_approvals": (
            MaintenanceApproval.objects.filter(
                status="pending"
            ).count()
        ),
        "active_warranties": (
            MaintenanceWarranty.objects.filter(
                status="active",
                end_date__gte=timezone.localdate(),
            ).count()
        ),
        "status_breakdown": status_counts,
        "priority_breakdown": priority_counts,
        "category_breakdown": category_counts,
        "status_choices": choices(
            MaintenanceTicket, "status"
        ),
        "priority_choices": choices(
            MaintenanceTicket, "priority"
        ),
        "category_choices": choices(
            MaintenanceTicket, "category"
        ),
    })


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def admin_maintenance_detail(request, ticket_id):
    ticket = get_object_or_404(
        ticket_queryset(),
        pk=ticket_id,
    )

    media = (
        MaintenanceMedia.objects
        .filter(maintenance_ticket_id=ticket_id)
        .select_related("uploaded_by")
        .order_by("-created_at")[:100]
    )

    comments = (
        MaintenanceComment.objects
        .filter(maintenance_ticket_id=ticket_id)
        .select_related("user")
        .order_by("-created_at")[:100]
    )

    history = (
        MaintenanceStatusHistory.objects
        .filter(maintenance_ticket_id=ticket_id)
        .select_related("changed_by")
        .order_by("-created_at")[:100]
    )

    approvals = (
        MaintenanceApproval.objects
        .filter(maintenance_ticket_id=ticket_id)
        .select_related("requested_from")
        .order_by("-created_at")[:100]
    )

    warranties = (
        MaintenanceWarranty.objects
        .filter(maintenance_ticket_id=ticket_id)
        .order_by("-created_at")[:100]
    )

    return Response({
        "ticket": serialize_ticket(ticket),

        "media": [
            {
                "id": item.pk,
                "file_url": item.file_url,
                "file_type": item.file_type,
                "media_stage": item.media_stage,
                "caption": item.caption,
                "uploaded_by": display_user(
                    item.uploaded_by
                ),
                "created_at": iso(item.created_at),
            }
            for item in media
        ],

        "comments": [
            {
                "id": item.pk,
                "comment": item.comment,
                "is_internal": item.is_internal,
                "user": display_user(item.user),
                "created_at": iso(item.created_at),
            }
            for item in comments
        ],

        "status_history": [
            {
                "id": item.pk,
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "notes": item.notes,
                "changed_by": display_user(
                    item.changed_by
                ),
                "created_at": iso(item.created_at),
            }
            for item in history
        ],

        "approvals": [
            {
                "id": item.pk,
                "approval_type": item.approval_type,
                "status": item.status,
                "comments": item.comments,
                "requested_from": display_user(
                    item.requested_from
                ),
                "approved_at": iso(item.approved_at),
                "created_at": iso(item.created_at),
            }
            for item in approvals
        ],

        "warranties": [
            {
                "id": item.pk,
                "provider_type": item.provider_type,
                "external_provider_id": (
                    item.external_provider_id
                ),
                "start_date": iso(item.start_date),
                "end_date": iso(item.end_date),
                "terms": item.terms,
                "status": item.status,
            }
            for item in warranties
        ],
    })
