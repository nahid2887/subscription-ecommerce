from django.db.models import Q
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiExample
from rest_framework_simplejwt.views import TokenRefreshView

from .models import SavedProduct, CustomerCartItem, Order, OrderItem
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerLoginSerializer,
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    CustomerAuthResponseSerializer,
    SavedProductSerializer,
    SavedProductCreateSerializer,
    SavedProductToggleSerializer,
    SavedProductActionResponseSerializer,
    SavedProductListResponseSerializer,
    SavedProductCheckResponseSerializer,
    CustomerCartItemSerializer,
    CustomerCartAddSerializer,
    CustomerCartUpdateSerializer,
    CustomerCartResponseSerializer,
    CustomerCartActionResponseSerializer,
    OrderItemSerializer,
    OrderSerializer,
    CustomerOrderCreateSerializer,
    AdminOrderApprovalSerializer,
    AdminOrderRejectionSerializer,
    OrderActionResponseSerializer,
)




class CustomerProfilePageView(TemplateView):
    """
    Renders the dedicated Customer Profile and Account Details web page.
    """
    template_name = 'customer/profile.html'


class CustomerRegisterView(APIView):
    """
    Customer Registration Endpoint.
    Allows customers to register using their Email (e.g. Gmail) and Password.
    Returns Bearer access and refresh tokens upon successful registration.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Customer Authentication'],
        summary='Register Customer Account',
        description='Register a new customer account using Email (e.g. yourname@gmail.com) and Password. Returns Bearer access and refresh tokens.',
        request=CustomerRegistrationSerializer,
        responses={
            201: CustomerAuthResponseSerializer,
            400: OpenApiResponse(description='Validation error (e.g., email already exists or password mismatch)'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = serializer.save()
        user = result['user']
        user_data = CustomerProfileSerializer(user, context={'request': request}).data

        response_data = {
            "message": "Customer registered successfully.",
            "token_type": result['token_type'],
            "access_token": result['access_token'],
            "refresh_token": result['refresh_token'],
            "user": user_data,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class CustomerLoginView(APIView):
    """
    Customer Login Endpoint.
    Authenticates a customer via Email (Gmail) and Password.
    Returns Bearer access token, refresh token, and customer profile details.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Customer Authentication'],
        summary='Customer Login',
        description='Authenticate with your registered Email (e.g. Gmail) and Password to receive Bearer access and refresh tokens.',
        request=CustomerLoginSerializer,
        responses={
            200: CustomerAuthResponseSerializer,
            400: OpenApiResponse(description='Invalid email or password credentials'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = validated_data['user']
        user_data = CustomerProfileSerializer(user, context={'request': request}).data

        response_data = {
            "message": "Login successful.",
            "token_type": validated_data['token_type'],
            "access_token": validated_data['access_token'],
            "refresh_token": validated_data['refresh_token'],
            "user": user_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CustomerProfileView(APIView):
    """
    Customer Profile Endpoint.
    Requires Bearer Token in Authorization header:
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Customer Profile'],
        summary='Get Current Customer Profile',
        description='Retrieve the profile details of the currently authenticated customer using Bearer token.',
        responses={
            200: CustomerProfileSerializer,
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = CustomerProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Profile'],
        summary='Update Customer Profile',
        description='Update personal information, phone number, address, and profile avatar (file or Base64).',
        request=CustomerProfileUpdateSerializer,
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(description='Validation error in update data'),
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def put(self, request, *args, **kwargs):
        return self._update_profile(request)

    @extend_schema(
        tags=['Customer Profile'],
        summary='Partial Update Customer Profile',
        description='Partially update customer profile fields.',
        request=CustomerProfileUpdateSerializer,
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(description='Validation error in update data'),
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def patch(self, request, *args, **kwargs):
        return self._update_profile(request)

    def _update_profile(self, request):
        serializer = CustomerProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_user = serializer.save()
        response_serializer = CustomerProfileSerializer(updated_user, context={'request': request})
        return Response({
            "message": "Profile updated successfully.",
            "user": response_serializer.data
        }, status=status.HTTP_200_OK)


class CustomerSavedProductListView(APIView):
    """
    Customer Saved Products / Wishlist Endpoint.
    
    Allows an authenticated customer user to:
    - GET: View all of their saved products with complete product and plan details.
    - POST: Save a product to their saved items list.
    
    Requires Bearer Token in Authorization header:
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_saved_products_list',
        summary='List Customer Saved Products',
        description='Retrieve all products saved/bookmarked by the currently authenticated customer, ordered by most recently saved.',
        parameters=[
            OpenApiParameter('search', str, description='Search saved products by title, category, or personal notes'),
            OpenApiParameter('category', str, description='Filter saved products by category ID or slug'),
        ],
        responses={
            200: SavedProductListResponseSerializer,
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def get(self, request, *args, **kwargs):
        qs = SavedProduct.objects.filter(user=request.user).select_related('product', 'product__category', 'product__selected_plan')

        # Filter by search
        search_term = request.query_params.get('search', '').strip()
        if search_term:
            qs = qs.filter(
                Q(product__name__icontains=search_term) |
                Q(product__category__name__icontains=search_term) |
                Q(notes__icontains=search_term)
            )

        # Filter by category
        category_param = request.query_params.get('category', '').strip()
        if category_param:
            if category_param.isdigit():
                qs = qs.filter(product__category_id=int(category_param))
            else:
                qs = qs.filter(product__category__slug__iexact=category_param)

        serializer = SavedProductSerializer(qs, many=True, context={'request': request})
        return Response({
            "count": qs.count(),
            "saved_products": serializer.data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_save_product',
        summary='Save a Product for Customer',
        description='Save a product to the customer\'s saved products list. Accepts `product_id` (or `slug`) and optional `notes`.',
        request=SavedProductCreateSerializer,
        responses={
            201: SavedProductActionResponseSerializer,
            200: SavedProductActionResponseSerializer,
            400: OpenApiResponse(description='Validation error or missing product_id'),
            401: OpenApiResponse(description='Unauthorized: Missing or invalid token'),
        },
        examples=[
            OpenApiExample(
                'Save Product Example',
                value={"product_id": 1, "notes": "Plan to subscribe next month"},
                request_only=True
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = SavedProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product_obj = serializer.validated_data['product_instance']
        notes = serializer.validated_data.get('notes')

        saved_item, created = SavedProduct.objects.get_or_create(
            user=request.user,
            product=product_obj,
            defaults={'notes': notes or ''}
        )

        if not created and notes is not None:
            saved_item.notes = notes
            saved_item.save(update_fields=['notes', 'updated_at'])

        saved_data = SavedProductSerializer(saved_item, context={'request': request}).data

        if created:
            return Response({
                "message": f"'{product_obj.name}' saved to your saved products successfully.",
                "is_saved": True,
                "product_id": product_obj.id,
                "saved_product": saved_data,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message": f"'{product_obj.name}' is already in your saved products.",
                "is_saved": True,
                "product_id": product_obj.id,
                "saved_product": saved_data,
            }, status=status.HTTP_200_OK)


class CustomerSavedProductDetailView(APIView):
    """
    Customer Saved Product Detail / Remove Endpoint.
    
    Allows an authenticated customer user to:
    - GET: Inspect a specific saved product item by product ID or record ID.
    - DELETE: Remove a product from their saved items list.
    """
    permission_classes = [IsAuthenticated]

    def _get_saved_item(self, user, product_id):
        return SavedProduct.objects.filter(user=user).filter(
            Q(product_id=product_id) | Q(id=product_id)
        ).select_related('product', 'product__category', 'product__selected_plan').first()

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_saved_product_detail',
        summary='Get Saved Product Item',
        description='Retrieve a specific saved product item by its product ID or saved record ID.',
        responses={
            200: SavedProductSerializer,
            404: OpenApiResponse(description='Saved product not found in your list'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def get(self, request, product_id, *args, **kwargs):
        saved_item = self._get_saved_item(request.user, product_id)
        if not saved_item:
            return Response(
                {"error": "Saved product not found in your saved items list."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = SavedProductSerializer(saved_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_remove_saved_product',
        summary='Remove Saved Product',
        description='Remove a product from the customer\'s saved products list using product ID or record ID.',
        responses={
            200: SavedProductActionResponseSerializer,
            404: OpenApiResponse(description='Saved product not found in your list'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def delete(self, request, product_id, *args, **kwargs):
        saved_item = self._get_saved_item(request.user, product_id)
        if not saved_item:
            return Response(
                {"error": "Saved product not found in your saved items list."},
                status=status.HTTP_404_NOT_FOUND
            )

        product_name = saved_item.product.name if saved_item.product else "Product"
        deleted_product_id = saved_item.product_id
        saved_item.delete()

        return Response({
            "message": f"'{product_name}' removed from your saved items successfully.",
            "is_saved": False,
            "product_id": deleted_product_id,
            "saved_product": None,
        }, status=status.HTTP_200_OK)


class CustomerSavedProductToggleView(APIView):
    """
    Customer Saved Product Toggle Endpoint.
    
    If the product is currently saved, removes it.
    If the product is not currently saved, saves it.
    Ideal for single-click bookmark / heart buttons on product cards.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_toggle_saved_product',
        summary='Toggle Save Product',
        description='Convenience endpoint: Toggles saved state. If product is saved, it is removed; if not saved, it is added to customer\'s saved list.',
        request=SavedProductToggleSerializer,
        responses={
            200: SavedProductActionResponseSerializer,
            201: SavedProductActionResponseSerializer,
            400: OpenApiResponse(description='Validation error or missing product_id'),
            401: OpenApiResponse(description='Unauthorized'),
        },
        examples=[
            OpenApiExample(
                'Toggle Example',
                value={"product_id": 1},
                request_only=True
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = SavedProductToggleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product_obj = serializer.validated_data['product_instance']
        notes = serializer.validated_data.get('notes')

        existing = SavedProduct.objects.filter(user=request.user, product=product_obj).first()

        if existing:
            existing.delete()
            return Response({
                "message": f"'{product_obj.name}' removed from your saved items.",
                "is_saved": False,
                "product_id": product_obj.id,
                "saved_product": None,
            }, status=status.HTTP_200_OK)
        else:
            new_item = SavedProduct.objects.create(
                user=request.user,
                product=product_obj,
                notes=notes or ''
            )
            saved_data = SavedProductSerializer(new_item, context={'request': request}).data
            return Response({
                "message": f"'{product_obj.name}' saved to your favorites successfully.",
                "is_saved": True,
                "product_id": product_obj.id,
                "saved_product": saved_data,
            }, status=status.HTTP_201_CREATED)


class CustomerSavedProductCheckView(APIView):
    """
    Check if a specific product is saved by the currently authenticated customer.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Saved Products'],
        operation_id='customer_check_saved_product',
        summary='Check Product Saved Status',
        description='Quickly check if a specific product ID is currently saved by the authenticated customer.',
        responses={
            200: SavedProductCheckResponseSerializer,
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def get(self, request, product_id, *args, **kwargs):
        saved_item = SavedProduct.objects.filter(user=request.user, product_id=product_id).first()
        return Response({
            "is_saved": bool(saved_item),
            "product_id": product_id,
            "saved_product_id": saved_item.id if saved_item else None,
        }, status=status.HTTP_200_OK)


# ==============================================================================
# CUSTOMER SHOPPING CART VIEWS
# ==============================================================================
def _build_cart_payload(user, request):
    qs = CustomerCartItem.objects.filter(user=user).select_related('product', 'product__category', 'plan')
    total_amount = sum((item.total_price or 0) for item in qs)
    total_quantity = sum(item.quantity for item in qs)
    currency_symbol = '৳'
    first_item = qs.first()
    if first_item:
        currency_symbol = first_item.currency_symbol

    serializer = CustomerCartItemSerializer(qs, many=True, context={'request': request})
    return {
        "items_count": qs.count(),
        "total_quantity": total_quantity,
        "total_amount": total_amount,
        "currency_symbol": currency_symbol,
        "items": serializer.data,
        "cart_items": serializer.data,
        "cart_count": total_quantity,
        "cart_total": total_amount,
    }


class CustomerCartView(APIView):
    """
    Customer Shopping Cart Endpoint.
    
    Allows an authenticated customer to:
    - GET: View all items currently in their shopping cart.
    - POST: Add a product and plan tier to their cart (or increment quantity).
    - DELETE: Clear all items from their cart.

    Requires Bearer Token in Authorization header:
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    def permission_denied(self, request, message=None, code=None):
        from rest_framework import exceptions
        if not request.user or not request.user.is_authenticated:
            raise exceptions.NotAuthenticated(
                detail="Authentication credentials were not provided. You must be logged in to add items to your cart or view your cart."
            )
        super().permission_denied(request, message=message, code=code)

    @extend_schema(
        tags=['Customer Shopping Cart'],
        operation_id='customer_get_cart',
        summary='View Customer Shopping Cart',
        description='Retrieve all items, quantities, and subtotal for the authenticated customer.',
        responses={
            200: CustomerCartResponseSerializer,
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def get(self, request, *args, **kwargs):
        return Response(_build_cart_payload(request.user, request), status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Shopping Cart'],
        operation_id='customer_add_to_cart',
        summary='Add Item to Cart',
        description='Add a product with chosen plan tier and quantity to the customer\'s cart. If the item with the same plan already exists in cart, increments quantity.',
        request=CustomerCartAddSerializer,
        responses={
            201: CustomerCartActionResponseSerializer,
            200: CustomerCartActionResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized'),
        },
        examples=[
            OpenApiExample(
                'Add to Cart Example',
                value={"product_id": 1, "plan_id": 2, "quantity": 1},
                request_only=True
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerCartAddSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product_obj = serializer.validated_data['product_instance']
        plan_obj = serializer.validated_data.get('plan_instance')
        quantity = serializer.validated_data.get('quantity', 1)

        cart_item, created = CustomerCartItem.objects.get_or_create(
            user=request.user,
            product=product_obj,
            plan=plan_obj,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=['quantity', 'updated_at'])

        plan_display = f" ({plan_obj.name})" if plan_obj else ""
        msg = f"'{product_obj.name}'{plan_display} added to your cart."
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        item_data = CustomerCartItemSerializer(cart_item, context={'request': request}).data
        cart_data = _build_cart_payload(request.user, request)

        return Response({
            "message": msg,
            "item": item_data,
            "cart": cart_data
        }, status=status_code)

    @extend_schema(
        tags=['Customer Shopping Cart'],
        operation_id='customer_clear_cart',
        summary='Clear Entire Cart',
        description='Remove all items from the customer\'s shopping cart.',
        responses={
            200: CustomerCartActionResponseSerializer,
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def delete(self, request, *args, **kwargs):
        CustomerCartItem.objects.filter(user=request.user).delete()
        cart_data = _build_cart_payload(request.user, request)
        return Response({
            "message": "Cart cleared successfully.",
            "cart": cart_data,
            "item": None
        }, status=status.HTTP_200_OK)


class CustomerCartItemDetailView(APIView):
    """
    Manage specific item in Customer Shopping Cart.
    - PATCH: Update quantity
    - DELETE: Remove item from cart

    Requires Bearer Token in Authorization header:
    Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    def permission_denied(self, request, message=None, code=None):
        from rest_framework import exceptions
        if not request.user or not request.user.is_authenticated:
            raise exceptions.NotAuthenticated(
                detail="Authentication credentials were not provided. You must be logged in to update or remove items from your cart."
            )
        super().permission_denied(request, message=message, code=code)

    def _get_item(self, user, item_id):
        return CustomerCartItem.objects.filter(user=user).filter(
            Q(id=item_id) | Q(product_id=item_id)
        ).select_related('product', 'plan').first()

    @extend_schema(
        tags=['Customer Shopping Cart'],
        operation_id='customer_update_cart_item',
        summary='Update Cart Item Quantity',
        description='Update quantity for a cart item. Set quantity to 0 to remove it from cart.',
        request=CustomerCartUpdateSerializer,
        responses={
            200: CustomerCartActionResponseSerializer,
            404: OpenApiResponse(description='Cart item not found'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def patch(self, request, item_id, *args, **kwargs):
        cart_item = self._get_item(request.user, item_id)
        if not cart_item:
            return Response({"error": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerCartUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_qty = serializer.validated_data['quantity']
        if new_qty <= 0:
            cart_item.delete()
            item_data = None
            msg = "Item removed from cart."
        else:
            cart_item.quantity = new_qty
            cart_item.save(update_fields=['quantity', 'updated_at'])
            item_data = CustomerCartItemSerializer(cart_item, context={'request': request}).data
            msg = "Cart item quantity updated."

        cart_data = _build_cart_payload(request.user, request)
        return Response({
            "message": msg,
            "item": item_data,
            "cart": cart_data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Customer Shopping Cart'],
        operation_id='customer_remove_cart_item',
        summary='Remove Item from Cart',
        description='Remove a specific product or item from the customer\'s cart.',
        responses={
            200: CustomerCartActionResponseSerializer,
            404: OpenApiResponse(description='Cart item not found'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def delete(self, request, item_id, *args, **kwargs):
        cart_item = self._get_item(request.user, item_id)
        if not cart_item:
            return Response({"error": "Cart item not found in your cart."}, status=status.HTTP_404_NOT_FOUND)

        prod_name = cart_item.product.name
        cart_item.delete()

        cart_data = _build_cart_payload(request.user, request)
        return Response({
            "message": f"'{prod_name}' removed from your cart successfully.",
            "cart": cart_data,
            "item": None
        }, status=status.HTTP_200_OK)


# ==============================================================================
# CUSTOMER ORDERS & MFS PAYMENT VERIFICATION VIEWS
# ==============================================================================

class CustomerPaymentMethodsView(APIView):
    """
    Public information endpoint returning supported MFS payment options in Bangladesh
    (bKash, Nagad, Rocket, Bangla QR) with account details, instructions, and logos.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Customer Orders & Payments'],
        operation_id='customer_get_payment_methods',
        summary='Get Supported Payment Methods & MFS Instructions',
        description='Returns official payment instructions, recipient account numbers, and brand assets for bKash, Nagad, Rocket, and Bangla QR.',
        responses={200: OpenApiResponse(description='List of MFS payment methods with instructions and account details')}
    )
    def get(self, request, *args, **kwargs):
        payment_methods = [
            {
                "id": "bkash",
                "name": "bKash",
                "brand_color": "#e2136e",
                "badge": "Popular MFS",
                "account_number": "01712-345678",
                "account_type": "Personal (Send Money)",
                "steps": [
                    "Open the bKash App or dial *247# on your handset.",
                    "Tap or choose the 'Send Money' option.",
                    "Enter recipient bKash number: 01712-345678.",
                    "Enter the exact total amount in BDT (৳).",
                    "Enter your Name or Email as reference.",
                    "Enter your bKash PIN to confirm payment.",
                    "Copy the 10-character TrxID from SMS or receipt and paste it below."
                ],
                "logo": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23e2136e'/><path d='M22 68 L48 24 L56 46 L38 52 Z' fill='%23ffffff'/><path d='M48 24 L78 38 L62 50 L56 46 Z' fill='%23f9fafb'/><path d='M62 50 L78 38 L68 76 L52 64 Z' fill='%23ffffff'/></svg>"
            },
            {
                "id": "nagad",
                "name": "Nagad",
                "brand_color": "#f97316",
                "badge": "Instant Gateway",
                "account_number": "01912-345678",
                "account_type": "Personal (Send Money)",
                "steps": [
                    "Open the Nagad App or dial *167# on your mobile phone.",
                    "Select the 'Send Money' service.",
                    "Enter recipient Nagad number: 01912-345678.",
                    "Enter the exact total amount in BDT (৳).",
                    "Enter reference: your registered username or email.",
                    "Enter your secret Nagad PIN and tap & hold to complete.",
                    "Copy the 8-digit TxnID from SMS or statement and paste it below."
                ],
                "logo": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23f97316'/><circle cx='50' cy='50' r='28' fill='none' stroke='%23ffffff' stroke-width='8'/><path d='M35 50 Q50 28 65 50 T35 50' fill='%23ffffff'/></svg>"
            },
            {
                "id": "rocket",
                "name": "Rocket (DBBL)",
                "brand_color": "#8b5cf6",
                "badge": "Dutch-Bangla Bank MFS",
                "account_number": "01812-345678-9",
                "account_type": "Personal (Send Money)",
                "steps": [
                    "Open Rocket App or dial *322#.",
                    "Select 'Send Money'.",
                    "Enter 12-digit recipient Rocket number: 01812-345678-9.",
                    "Enter the exact order amount in BDT (৳).",
                    "Enter your 4-digit Rocket PIN to confirm.",
                    "Copy the Transaction ID from the transaction confirmation SMS and paste below."
                ],
                "logo": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%238b5cf6'/><path d='M50 20 L68 50 L58 50 L64 78 L36 48 L46 48 Z' fill='%23ffffff'/></svg>"
            },
            {
                "id": "bangla_qr",
                "name": "Bangla QR",
                "brand_color": "#06b6d4",
                "badge": "Interoperable QR Scan",
                "account_number": "MERCHANT: SUB-BD-QR01",
                "account_type": "National Bangla QR Standard",
                "steps": [
                    "Open any Bangladeshi Bank or MFS app (bKash, Nagad, Citytouch, BRAC Astha, etc.).",
                    "Tap on 'Scan QR' / 'Bangla QR'.",
                    "Scan our merchant Bangla QR code displayed in the checkout modal.",
                    "Confirm the payment amount and authorize the transfer.",
                    "Copy the Transaction Reference / TrxID from your app receipt and paste below."
                ],
                "logo": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%2306b6d4'/><rect x='25' y='25' width='22' height='22' rx='4' fill='none' stroke='%23ffffff' stroke-width='6'/><rect x='32' y='32' width='8' height='8' fill='%23ffffff'/><rect x='53' y='25' width='22' height='22' rx='4' fill='none' stroke='%23ffffff' stroke-width='6'/><rect x='60' y='32' width='8' height='8' fill='%23ffffff'/><rect x='25' y='53' width='22' height='22' rx='4' fill='none' stroke='%23ffffff' stroke-width='6'/><rect x='32' y='60' width='8' height='8' fill='%23ffffff'/><rect x='55' y='55' width='8' height='8' fill='%23ffffff'/><rect x='67' y='55' width='8' height='8' fill='%23ffffff'/><rect x='55' y='67' width='20' height='8' fill='%23ffffff'/></svg>"
            }
        ]
        return Response({"payment_methods": payment_methods}, status=status.HTTP_200_OK)


class CustomerOrderListCreateView(APIView):
    """
    Customer Orders Endpoint.
    - GET: List all orders placed by the authenticated customer.
    - POST: Place a new order with MFS payment details and TrxID.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Orders & Payments'],
        operation_id='customer_list_orders',
        summary='List Customer Orders',
        description='Retrieve all orders placed by the authenticated customer, with optional filtering by status (PENDING, APPROVED, REJECTED).',
        parameters=[
            OpenApiParameter('status', type=str, description='Filter by status: PENDING, APPROVED, REJECTED', required=False)
        ],
        responses={
            200: OrderSerializer(many=True),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def get(self, request, *args, **kwargs):
        qs = Order.objects.filter(user=request.user).prefetch_related('items', 'items__product', 'items__plan').order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        serializer = OrderSerializer(qs, many=True, context={'request': request})
        return Response({
            "count": qs.count(),
            "orders_count": qs.count(),
            "orders": serializer.data
        }, status=status.HTTP_200_OK)


    @extend_schema(
        tags=['Customer Orders & Payments'],
        operation_id='customer_create_order',
        summary='Place Order with MFS Transaction ID',
        description="""
        Place a new subscription order with MFS payment verification.
        - Checks out current items from customer's shopping cart (`source: 'cart'`) or a specific product (`source: 'direct'`).
        - Requires `payment_method` (bkash, nagad, rocket, bangla_qr), `sender_number`, and `transaction_id`.
        - The order is submitted as `PENDING` until approved by Super Admin.
        """,
        request=CustomerOrderCreateSerializer,
        responses={
            201: OrderActionResponseSerializer,
            400: OpenApiResponse(description='Validation error in order data or duplicate Transaction ID'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CustomerOrderCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order = serializer.save()
        order_data = OrderSerializer(order, context={'request': request}).data
        return Response({
            "message": f"Order {order.order_number} confirmed! Your {order.get_payment_method_display()} transaction ({order.transaction_id}) is pending super admin verification.",
            "order": order_data
        }, status=status.HTTP_201_CREATED)


class CustomerOrderDetailView(APIView):
    """
    Retrieve specific order details for the authenticated customer.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Orders & Payments'],
        operation_id='customer_get_order_detail',
        summary='Get Customer Order Details',
        description='Retrieve full details, purchased items, MFS payment info, and digital license credentials for an order.',
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(description='Order not found'),
            401: OpenApiResponse(description='Unauthorized'),
        }
    )
    def get(self, request, order_id, *args, **kwargs):
        order = Order.objects.filter(user=request.user).filter(
            Q(id=order_id) | Q(order_number=str(order_id))
        ).prefetch_related('items').first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomerMySubscriptionsView(APIView):
    """
    Retrieve active approved digital subscriptions and licenses owned by the authenticated customer.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Customer Orders & Payments'],
        operation_id='customer_get_active_subscriptions',
        summary='Get Customer Owned Subscriptions & License Keys',
        description='Retrieve all approved / purchased subscriptions, access credentials, and license keys for the customer.',
        responses={
            200: OpenApiResponse(description='List of active approved products and subscription licenses'),
            401: OpenApiResponse(description='Unauthorized')
        }
    )
    def get(self, request, *args, **kwargs):
        approved_orders = Order.objects.filter(
            user=request.user,
            status=Order.STATUS_APPROVED
        ).prefetch_related('items', 'items__product', 'items__plan').order_by('-approved_at', '-created_at')

        subscriptions = []
        for ord in approved_orders:
            for item in ord.items.all():
                subscriptions.append({
                    "order_id": ord.id,
                    "order_number": ord.order_number,
                    "order_date": ord.created_at,
                    "approved_at": ord.approved_at,
                    "product_id": item.product.id if item.product else None,
                    "product_name": item.product_name,
                    "product_image": item.product_image or (item.product.image.url if item.product and item.product.image else None),
                    "plan_id": item.plan.id if item.plan else None,
                    "plan_name": item.plan_name,
                    "devices": item.devices,
                    "billing_cycle": item.billing_cycle,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "currency_symbol": ord.currency_symbol,
                    "license_key": ord.license_key or "SUB-ACTIVE-KEY-GRANTED",
                    "admin_notes": ord.admin_notes or "License verified & active. Instant credentials granted.",
                    "status": "Active",
                    "is_active": True
                })


        return Response({
            "count": len(subscriptions),
            "subscriptions": subscriptions
        }, status=status.HTTP_200_OK)


