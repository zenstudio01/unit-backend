from unit_app.api_views.common_imports import *
from .serializers import (
    ProcurementSupplierSerializer as SupplierSerializer,
    ProcurementMaterialSerializer as MaterialSerializer,
    ProcurementPurchaseOrderSerializer as OrderSerializer,
    ProcurementDeliverySerializer as DeliverySerializer,
    ProcurementMaterialIssueSerializer as IssueSerializer,
)
from .helper import *


def error(message, status=400):
    return Response({"message": message}, status=status)


def get_project(request, project_id):
    return get_accessible_project(request.user, project_id)


def can_write(user, project):
    return can_manage_project(user, project)


def number(value, field, positive=True):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be numeric.")

    if not result.is_finite():
        raise ValueError(f"{field} must be finite.")

    if positive and result <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    if not positive and result < 0:
        raise ValueError(f"{field} cannot be negative.")

    return result


def order_queryset(user):
    return PurchaseOrder.objects.filter(
        project__in=allowed_projects(user)
    ).select_related(
        "project", "supplier"
    ).prefetch_related("items__material")


def received_for_order_item(order_item_id):
    return (
        DeliveryItem.objects.filter(order_item_id=order_item_id)
        .aggregate(total=Sum("quantity_received"))["total"]
        or Decimal("0")
    )


def project_stock(project):
    received = defaultdict(Decimal)
    issued = defaultdict(Decimal)

    delivery_rows = DeliveryItem.objects.filter(
        delivery__order__project=project
    ).values("order_item__material_id").annotate(
        total=Sum("quantity_received")
    )

    for row in delivery_rows:
        received[row["order_item__material_id"]] += row["total"]

    issue_rows = MaterialIssue.objects.filter(
        project=project
    ).values("material_id").annotate(
        total=Sum("quantity")
    )

    for row in issue_rows:
        issued[row["material_id"]] += row["total"]

    return {
        material_id: received[material_id] - issued[material_id]
        for material_id in set(received) | set(issued)
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def procurement_suppliers(request):
    project_id = request.query_params.get(
        "project_id"
    ) if request.method == "GET" else request.data.get("project_id")

    if not project_id:
        return error("project_id is required.")

    project = get_project(request, project_id)

    if request.method == "GET":
        suppliers = Supplier.objects.filter(
            organization=project.organization
        )
        return Response({
            "results": SupplierSerializer(
                suppliers, many=True
            ).data
        })

    if not can_write(request.user, project):
        return error("Permission denied.", 403)

    serializer = SupplierSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    supplier = serializer.save(
        organization=project.organization
    )
    return Response(
        SupplierSerializer(supplier).data, status=201
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def procurement_materials(request):
    project_id = request.query_params.get(
        "project_id"
    ) if request.method == "GET" else request.data.get("project_id")

    if not project_id:
        return error("project_id is required.")

    project = get_project(request, project_id)

    if request.method == "GET":
        materials = Material.objects.filter(
            organization=project.organization
        )
        return Response({
            "results": MaterialSerializer(
                materials, many=True
            ).data
        })

    if not can_write(request.user, project):
        return error("Permission denied.", 403)

    serializer = MaterialSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    material = serializer.save(
        organization=project.organization
    )
    return Response(
        MaterialSerializer(material).data, status=201
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def procurement_orders(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error("project_id is required.")

        project = get_project(request, project_id)
        orders = order_queryset(request.user).filter(
            project=project
        )
        return Response({
            "results": OrderSerializer(
                orders, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return error("project is required.")

    project = get_project(request, project_id)

    if not can_write(request.user, project):
        return error("Permission denied.", 403)

    supplier = get_object_or_404(
        Supplier,
        pk=request.data.get("supplier"),
        organization=project.organization,
        is_active=True,
    )

    lines = request.data.get("items", [])
    if not isinstance(lines, list) or not lines:
        return error("Provide at least one order item.")

    prepared = []

    try:
        for line in lines:
            material = Material.objects.get(
                pk=line.get("material"),
                organization=project.organization,
                is_active=True,
            )
            quantity = number(line.get("quantity"), "quantity")
            price = number(
                line.get("unit_price"), "unit_price",
                positive=False,
            )

            boq = None
            if line.get("boq_item"):
                boq = BOQItem.objects.get(
                    pk=line["boq_item"],
                    project=project,
                )

            prepared.append((material, boq, quantity, price))

    except (Material.DoesNotExist, BOQItem.DoesNotExist):
        return error("Invalid material or BOQ item.")
    except ValueError as exc:
        return error(str(exc))

    with transaction.atomic():
        order = PurchaseOrder.objects.create(
            project=project,
            supplier=supplier,
            order_number=f"PO-{uuid.uuid4().hex[:12].upper()}",
            order_date=request.data.get(
                "order_date", timezone.localdate()
            ),
            expected_delivery_date=request.data.get(
                "expected_delivery_date"
            ) or None,
            notes=request.data.get("notes", ""),
            created_by=request.user,
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                material=material,
                boq_item=boq,
                quantity=quantity,
                unit_price=price,
            )
            for material, boq, quantity, price in prepared
        ])

    return Response(
        OrderSerializer(
            order_queryset(request.user).get(pk=order.pk)
        ).data,
        status=201,
    )


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def procurement_order_detail(request, order_id):
    order = get_object_or_404(
        order_queryset(request.user),
        pk=order_id,
    )

    if request.method == "GET":
        return Response(OrderSerializer(order).data)

    if not can_write(request.user, order.project):
        return error("Permission denied.", 403)

    if order.status != "draft":
        return error("Only draft orders can be deleted.")

    order.delete()
    return Response(status=204)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def procurement_order_status(request, order_id):
    order = get_object_or_404(
        order_queryset(request.user),
        pk=order_id,
    )

    if not can_write(request.user, order.project):
        return error("Permission denied.", 403)

    transitions = {
        "draft": {"pending", "cancelled"},
        "pending": {"approved", "rejected"},
        "rejected": {"draft"},
        "approved": {"cancelled"},
    }

    target = request.data.get("status")

    with transaction.atomic():
        order = PurchaseOrder.objects.select_for_update().get(
            pk=order.pk
        )

        if target not in transitions.get(order.status, set()):
            return error("Invalid purchase order status transition.")

        order.status = target

        if target == "approved":
            order.approved_by = request.user
            order.approved_at = timezone.now()
        elif target == "draft":
            order.approved_by = None
            order.approved_at = None

        order.save()

    return Response(OrderSerializer(order).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def procurement_deliveries(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error("project_id is required.")

        project = get_project(request, project_id)

        deliveries = Delivery.objects.filter(
            order__project=project
        ).prefetch_related("items")

        return Response({
            "results": DeliverySerializer(
                deliveries, many=True
            ).data
        })

    order = get_object_or_404(
        order_queryset(request.user),
        pk=request.data.get("order"),
    )

    if not can_write(request.user, order.project):
        return error("Permission denied.", 403)

    lines = request.data.get("items", [])
    if not isinstance(lines, list) or not lines:
        return error("Provide delivered items.")

    try:
        with transaction.atomic():
            order = PurchaseOrder.objects.select_for_update().get(
                pk=order.pk
            )

            if order.status not in (
                "approved", "partially_received"
            ):
                return error("Order is not ready for receiving.")

            quantities = defaultdict(Decimal)

            for line in lines:
                item = OrderItem.objects.get(
                    pk=line.get("order_item"),
                    order=order,
                )
                quantities[item.id] += number(
                    line.get("quantity_received"),
                    "quantity_received",
                )

            order_items = list(order.items.all())

            for item in order_items:
                existing = received_for_order_item(item.id)
                incoming = quantities[item.id]

                if existing + incoming > item.quantity:
                    return error(
                        f"Received quantity exceeds ordered quantity "
                        f"for item {item.id}."
                    )

            delivery = Delivery.objects.create(
                order=order,
                delivery_number=request.data.get(
                    "delivery_number", ""
                ),
                delivery_date=request.data.get(
                    "delivery_date", timezone.localdate()
                ),
                notes=request.data.get("notes", ""),
                received_by=request.user,
            )

            DeliveryItem.objects.bulk_create([
                DeliveryItem(
                    delivery=delivery,
                    order_item_id=item_id,
                    quantity_received=quantity,
                )
                for item_id, quantity in quantities.items()
            ])

            fully_received = all(
                received_for_order_item(item.id) >= item.quantity
                for item in order_items
            )

            order.status = (
                "received" if fully_received
                else "partially_received"
            )
            order.save(update_fields=["status"])

    except OrderItem.DoesNotExist:
        return error("Order item does not belong to this order.")
    except ValueError as exc:
        return error(str(exc))

    return Response(
        DeliverySerializer(delivery).data,
        status=201,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def procurement_issues(request):
    if request.method == "GET":
        project_id = request.query_params.get("project_id")
        if not project_id:
            return error("project_id is required.")

        project = get_project(request, project_id)

        issues = MaterialIssue.objects.filter(
            project=project
        ).select_related("material").order_by("-created_at")

        return Response({
            "results": IssueSerializer(
                issues, many=True
            ).data
        })

    project_id = request.data.get("project")
    if not project_id:
        return error("project is required.")

    project = get_project(request, project_id)

    if not can_write(request.user, project):
        return error("Permission denied.", 403)

    material = get_object_or_404(
        Material,
        pk=request.data.get("material"),
        organization=project.organization,
    )

    try:
        quantity = number(
            request.data.get("quantity"), "quantity"
        )
    except ValueError as exc:
        return error(str(exc))

    # Lock the project to serialize stock mutations
    # against other material issues and deliveries.
    from .models import ConstructionProject

    with transaction.atomic():
        ConstructionProject.objects.select_for_update().get(
            pk=project.pk
        )

        available = project_stock(project).get(
            material.id, Decimal("0")
        )

        if quantity > available:
            return error(
                f"Insufficient stock. Available: {available}."
            )

        issue = MaterialIssue.objects.create(
            project=project,
            material=material,
            quantity=quantity,
            issued_to=request.data.get("issued_to", ""),
            purpose=request.data.get("purpose", ""),
            issue_date=request.data.get(
                "issue_date", timezone.localdate()
            ),
            issued_by=request.user,
        )

    return Response(
        IssueSerializer(issue).data,
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def procurement_inventory(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return error("project_id is required.")

    project = get_project(request, project_id)
    stock = project_stock(project)

    materials = Material.objects.filter(
        organization=project.organization,
        id__in=stock.keys(),
    )

    return Response({
        "results": [
            {
                "material": m.id,
                "name": m.name,
                "sku": m.sku,
                "unit": m.unit,
                "available_quantity": str(stock[m.id]),
            }
            for m in materials
        ]
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def procurement_summary(request):
    project_id = request.query_params.get("project_id")
    if not project_id:
        return error("project_id is required.")

    project = get_project(request, project_id)

    orders = PurchaseOrder.objects.filter(project=project)
    lines = OrderItem.objects.filter(order__project=project)
    delivered_lines = DeliveryItem.objects.filter(
        delivery__order__project=project
    )

    committed = sum(
        (
            item.quantity * item.unit_price
            for item in lines.filter(
                order__status__in=[
                    "approved",
                    "partially_received",
                    "received",
                ]
            )
        ),
        Decimal("0"),
    )

    received_value = sum(
        (
            item.quantity_received * item.order_item.unit_price
            for item in delivered_lines.select_related("order_item")
        ),
        Decimal("0"),
    )

    return Response({
        "total_suppliers": Supplier.objects.filter(
            organization=project.organization
        ).count(),
        "total_materials": Material.objects.filter(
            organization=project.organization
        ).count(),
        "total_orders": orders.count(),
        "pending_orders": orders.filter(
            status="pending"
        ).count(),
        "total_deliveries": Delivery.objects.filter(
            order__project=project
        ).count(),
        "committed_value": str(committed),
        "received_value": str(received_value),
    })
