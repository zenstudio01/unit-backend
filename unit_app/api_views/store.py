from .common_imports import *


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_stores(request):
    try:
        stores = Store.objects.select_related("owner").order_by("-created_at")

        data = []

        for store in stores:
            data.append({
                "id": store.id,
                "name": store.name,
                "description": store.description,
                "owner": {
                    "id": store.owner.id,
                    "name": store.owner.full_name,
                    "email": store.owner.email,
                    "phone_number": store.owner.phone_number,
                    "profile_image": store.owner.profile_image,
                },
                "created_at": store.created_at,
                "updated_at": store.updated_at,
            })

        return Response({
            "success": True,
            "count": len(data),
            "stores": data
        }, status=200)

    except Exception as e:
        return Response({
            "success": False,
            "message": str(e)
        }, status=500)




# store dashboard metrics telemetry
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def store_dashboard_metrics(request):
    try:
        store = Store.objects.get(owner=request.user)
    except Store.DoesNotExist:
        return Response({"message": "No active registered store entity tied to this profile profile."}, status=status.HTTP_404_NOT_FOUND)

    today = timezone.now().date()

    today_sales_sum = ProductSale.objects.filter(
        store=store, 
        sold_at__date=today
    ).aggregate(total=Sum('price'))['total'] or 0

    total_products_count = Product.objects.filter(store=store).count()

    low_stock_queryset = Product.objects.filter(
        store=store,
        stock_quantity__lte=6
    )
    low_stock_count = low_stock_queryset.count()

    
    low_stock_serialized = []
    for item in low_stock_queryset.order_by('stock_quantity')[:10]:
        low_stock_serialized.append({
            "id": item.id,
            "product_name": item.product_name,
            "current_stock": item.stock_quantity,
        })

    return Response({
        "store_name": store.store_name,
        "cards": {
            "today_sales": today_sales_sum,
            "total_products": total_products_count,
            "low_stock_count": low_stock_count
        },
        "low_stock_items": low_stock_serialized
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_sale(request):
    try:
        store = Store.objects.get(owner=request.user)
    except Store.DoesNotExist:
        return Response({"message": "Invalid store profile association."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    item_name = data.get('item')
    qty = int(data.get('qty', 1))
    amount = float(data.get('amount', 0))

    if not item_name or amount <= 0:
        return Response({"message": "Missing description parameters or structural unit totals."}, status=status.HTTP_400_BAD_REQUEST)

    # Log inside your core Sale ledger table
    ProductSale.objects.create(
        store=store,
        item_description=f"{item_name} (x{qty})",
        quantity=qty,
        total_amount=amount,
        payment_method="CASH"
    )

    # Attempt to locate matching SKU item to update remaining stock levels
    product_node = Product.objects.filter(store=store, name__icontains=item_name).first()
    if product_node:
        product_node.current_stock = max(0, product_node.current_stock - qty)
        product_node.save()

    return Response({"message": "Counter transactional entry committed safely."}, status=status.HTTP_201_CREATED)



# add product api
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_product(request):
    print("Reached add product endpoint")
    if request.method == 'POST':
        try:
            owner = request.user
            product_name = request.data.get("name")
            barcode_number = request.data.get("barcode_number")
            buying_price = request.data.get("buying_price")
            selling_price = request.data.get("selling_price")
            quantity = request.data.get("quantity")
            supplier = request.data.get("supplier_name")
            print("Received data:", product_name, barcode_number, selling_price, buying_price, quantity, supplier)

            if not all([product_name, barcode_number, selling_price, buying_price, quantity, supplier]):
                print("Missing fields in request data")
                return JsonResponse({"message": "All fields are required"}, status=400)
            
            # check shop exists
            store = Store.objects.get(owner=owner)
            if not store:
                return JsonResponse({"message": "Store not found"}, status=404)
            
            # check if product already exists
            existing_product = Product.objects.filter(barcode_number=barcode_number, store=store).exists()
            if existing_product:
                return JsonResponse({"message": "Product with this barcode already exists"}, status=400)

            product = Product.objects.create(
                store=store,
                product_name=product_name,
                barcode_number=barcode_number,
                selling_price=selling_price,
                buying_price=buying_price,
                stock_quantity=quantity,
                supplier=supplier,
            )
    
            return JsonResponse({"message": "Product added successfully", "product_id": product.id}, status=201)

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"message": "An error occurred", "error": str(e)}, status=500)

# end of add product api

# api to get product for a shop
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_products(request):
    owner = request.user
    try:
        store = Store.objects.get(owner=owner)
        products = Product.objects.filter(store=store)
        product_list = []
        for product in products:
            product_list.append({
                'id': product.id,
                'product_name': product.product_name,
                'selling_price': str(product.selling_price),
                'buying_price': str(product.buying_price),
                'quantity': product.stock_quantity,
                'barcode_number': product.barcode_number,
                'date_added': product.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        

        return JsonResponse({"products": product_list}, status=200)
    except Exception as e:
        print("Error:", str(e))
        return JsonResponse({"message": "An error occurred", "error": str(e)}, status=500)

# end of get products api

# add stock to product api
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_stock(request):
    owner = request.user
    try:
        store = Store.objects.get(owner=owner)
        product_id = request.data.get("product_id")
        price = request.data.get("price")
        additional_stock = int(request.data.get("additional_stock"))
        store = Store.objects.get(owner=owner)
        product = Product.objects.get(id=product_id, store=store)

        if additional_stock < 0:
            return JsonResponse({"message": "Stock cannot be negative"}, status=400)

        product.quantity += additional_stock
        if price:
            product.price = price
        product.save()

        return JsonResponse({"message": "Stock updated successfully", "new_stock": product.quantity}, status=200)

    except Product.DoesNotExist:
        return JsonResponse({"message": "Product not found"}, status=404)
    except Exception as e:
        print("Error:", str(e))
        return JsonResponse({"message": "An error occurred", "error": str(e)}, status=500)

# end of add stock api



