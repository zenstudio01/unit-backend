from unit_app.api_views.common_imports import *

from .helper import *

from .serializers import (
    BOQSectionSerializer,
    BOQItemSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def boq_sections(request):
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

        sections = section_totals(
            BOQSection.objects.filter(project=project)
        ).order_by("sequence", "id")

        return Response({
            "results": BOQSectionSerializer(
                sections, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return Response(
            {"project": ["This field is required."]},
            status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )

    if not can_manage_project(request.user, project):
        return boq_write_denied()

    serializer = BOQSectionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    section = serializer.save(project=project)

    return Response(
        BOQSectionSerializer(section).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def boq_section_detail(request, section_id):
    section = get_object_or_404(
        section_queryset(request.user).select_related("project"),
        pk=section_id
    )

    if request.method == "GET":
        annotated = section_totals(
            BOQSection.objects.filter(pk=section.pk)
        ).first()
        return Response(
            BOQSectionSerializer(annotated).data
        )

    if not can_manage_project(request.user, section.project):
        return boq_write_denied()

    if request.method == "DELETE":
        if section.items.exists():
            return Response({
                "message":
                    "Delete or move the BOQ items before deleting this section."
            }, status=400)

        section.delete()
        return Response(status=204)

    serializer = BOQSectionSerializer(
        section,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def boq_items(request):
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

        items = BOQItem.objects.filter(
            section__project=project
        ).select_related("section").order_by(
            "section__sequence", "id"
        )

        section_id = request.query_params.get("section_id")
        if section_id:
            items = items.filter(section_id=section_id)

        return Response({
            "results": BOQItemSerializer(
                items, many=True
            ).data
        })

    section_id = request.data.get("section")
    if not section_id:
        return Response(
            {"section": ["This field is required."]},
            status=400
        )

    section = get_object_or_404(
        section_queryset(request.user).select_related("project"),
        pk=section_id
    )

    if not can_manage_project(request.user, section.project):
        return boq_write_denied()

    serializer = BOQItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    item = serializer.save(section=section)

    return Response(
        BOQItemSerializer(item).data,
        status=201
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def boq_item_detail(request, item_id):
    item = get_object_or_404(
        item_queryset(request.user).select_related(
            "section", "section__project"
        ),
        pk=item_id
    )

    if request.method == "GET":
        return Response(
            BOQItemSerializer(item).data
        )

    if not can_manage_project(
        request.user, item.section.project
    ):
        return boq_write_denied()

    if request.method == "DELETE":
        item.delete()
        return Response(status=204)

    serializer = BOQItemSerializer(
        item,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def boq_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return Response(
            {"message": "project_id is required."},
            status=400
        )

    project = get_accessible_project(
        request.user, project_id
    )

    sections = BOQSection.objects.filter(project=project)
    items = BOQItem.objects.filter(
        section__project=project
    )

    estimated_expression = ExpressionWrapper(
        F("quantity") * F("unit_rate"),
        output_field=DecimalField(
            max_digits=20, decimal_places=2
        )
    )

    totals = items.aggregate(
        estimated_cost=Coalesce(
            Sum(estimated_expression),
            Decimal("0.00"),
            output_field=DecimalField(
                max_digits=20, decimal_places=2
            )
        ),
        actual_cost=Coalesce(
            Sum("actual_cost"),
            Decimal("0.00"),
            output_field=DecimalField(
                max_digits=20, decimal_places=2
            )
        ),
    )

    estimated = totals["estimated_cost"]
    actual = totals["actual_cost"]

    return Response({
        "project_id": project.id,
        "currency": "KES",
        "total_sections": sections.count(),
        "total_items": items.count(),
        "estimated_cost": estimated,
        "actual_cost": actual,
        "variance": estimated - actual,
    })
