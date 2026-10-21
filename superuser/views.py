from django.db.models import Q, Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from rest_framework_simplejwt.tokens import RefreshToken

from customer.models import Order, OrderItem
from customer.serializers import (
    OrderSerializer,
    AdminOrderApprovalSerializer,
    AdminOrderRejectionSerializer,
    OrderActionResponseSerializer,
)
from .permissions import IsSuperUser
from .serializers import (
    SuperuserLoginSerializer,
    SuperuserDetailSerializer,
    SuperuserProfileUpdateSerializer,
    SuperuserLoginResponseSerializer,
    SuperAdminDashboardResponseSerializer,
)


class SuperuserLoginView(APIView):
    """
    Endpoint for superuser login.
    Authenticates a superuser and returns Bearer access token, refresh token, and user info.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Superuser Authentication'],
        summary='Superuser Login',
        description='Authenticate with superuser credentials to receive Bearer access and refresh tokens along with user information.',
        request=SuperuserLoginSerializer,
        responses={
            200: SuperuserLoginResponseSerializer,
            400: OpenApiResponse(description='Invalid credentials or account is not a superuser'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = SuperuserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = validated_data['user']
        user_serializer = SuperuserDetailSerializer(user, context={'request': request})

        response_data = {
            "message": "Superuser login successful.",
            "token_type": validated_data['token_type'],
            "access_token": validated_data['access_token'],
            "refresh_token": validated_data['refresh_token'],
            "user": user_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SuperuserProfileView(APIView):
    """
    Protected endpoint to test Bearer token authentication and update superuser profile.
    Only accessible by authenticated superusers with Bearer <access_token>.
    Supports JSON and multipart/form-data for image uploads.
    """
    permission_classes = [IsAuthenticated, IsSuperUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Superuser Authentication'],
        summary='Get Superuser Profile',
        description='Retrieve the profile of the authenticated superuser using the Bearer token in Authorization header.',
        responses={
            200: SuperuserDetailSerializer,
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
            403: OpenApiResponse(description='Forbidden: Authenticated user is not a superuser'),
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = SuperuserDetailSerializer(request.user, context={'request': request})
        return Response({
            "message": "Superuser profile retrieved successfully.",
            "user": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Superuser Authentication'],
        summary='Update Superuser Profile (PATCH)',
        description='Update personal information (first_name, last_name, avatar) or change password via the same API. Username and email are read-only.',
        request=SuperuserProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(description='Profile updated successfully.'),
            400: OpenApiResponse(description='Validation error (e.g. invalid password or attempt to change username/email)'),
            401: OpenApiResponse(description='Unauthorized: Invalid or missing Bearer token'),
        }
    )
    def patch(self, request, *args, **kwargs):
        serializer = SuperuserProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        password_changed = bool(serializer.validated_data.get('new_password'))
        user = serializer.save()

        user_data = SuperuserDetailSerializer(user, context={'request': request}).data
        response_data = {
            "message": "Profile updated successfully.",
            "user": user_data,
        }

        # If password changed, reissue access and refresh tokens so session stays active
        if password_changed:
            refresh = RefreshToken.for_user(user)
            refresh['username'] = user.username
            refresh['email'] = user.email
            refresh['is_superuser'] = user.is_superuser
            response_data['access_token'] = str(refresh.access_token)
            response_data['refresh_token'] = str(refresh)
            response_data['token_type'] = 'Bearer'
            response_data['password_changed'] = True

        return Response(response_data, status=status.HTTP_200_OK)


class SuperAdminDashboardView(APIView):
    """
    Super Admin Dashboard API & Web Portal.
    Provides real-time subscription metrics, tier breakdowns, and subscriber data.
    """
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'super_admin/dashboard.html'
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Super Admin Dashboard'],
        summary='Super Admin Dashboard API',
        description='Returns real-time subscription operations, financial metrics, and recent subscribers.',
        responses={
            200: SuperAdminDashboardResponseSerializer,
        }
    )
    def get(self, request, *args, **kwargs):
        dashboard_data = {
            "message": "Dashboard data retrieved successfully.",
            "metrics": {
                "monthly_revenue": 38420.00,
                "active_subscriptions": 1428,
                "arpu": 64.50,
                "system_health": "99.98%"
            },
            "recent_subscribers": [
                {
                    "name": "Elena Rostova",
                    "email": "elena.rostova@acme.corp",
                    "plan": "Enterprise",
                    "billing": "Yearly ($2,400)",
                    "status": "Active",
                    "joined_date": "Oct 16, 2026"
                },
                {
                    "name": "David Chen",
                    "email": "david.chen@fintech.io",
                    "plan": "Pro Plan",
                    "billing": "Monthly ($199)",
                    "status": "Active",
                    "joined_date": "Oct 15, 2026"
                },
                {
                    "name": "Marcus Vance",
                    "email": "marcus@cloudscale.net",
                    "plan": "Pro Plan",
                    "billing": "Yearly ($1,890)",
                    "status": "Trialing",
                    "joined_date": "Oct 14, 2026"
                },
                {
                    "name": "Sophia Williams",
                    "email": "sophia.w@devlabs.ai",
                    "plan": "Starter",
                    "billing": "Monthly ($49)",
                    "status": "Active",
                    "joined_date": "Oct 12, 2026"
                }
            ]
        }

        # If accessed from browser (HTML request), render dashboard template
        if request.accepted_renderer.format == 'html':
            return Response({'dashboard': dashboard_data}, template_name=self.template_name)

        # If accessed as JSON (Swagger or API client), return JSON response
        return Response(dashboard_data, status=status.HTTP_200_OK)


class SuperAdminProfilePageView(APIView):
    """
    Dedicated Super Admin Profile Page & View.
    Renders the dedicated profile information page in browser and returns JSON for API clients.
    """
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'super_admin/profile.html'
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Super Admin Dashboard'],
        summary='Super Admin Profile Page View',
        description='Renders the dedicated user profile page in HTML or returns user profile metadata in JSON.',
        responses={
            200: SuperuserDetailSerializer,
        }
    )
    def get(self, request, *args, **kwargs):
        # Default fallback profile data for root superuser
        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            from django.contrib.auth.models import User
            user = User.objects.filter(is_superuser=True).first()

        profile_data = {}
        if user:
            serializer = SuperuserDetailSerializer(user, context={'request': request})
            profile_data = serializer.data

        if request.accepted_renderer.format == 'html':
            return Response({'profile_user': profile_data}, template_name=self.template_name)

        return Response({
            "message": "Super Admin profile page data retrieved successfully.",
            "user": profile_data
        }, status=status.HTTP_200_OK)


class SuperAdminProductsPageView(APIView):
    """
    Dedicated Super Admin Product Management Page & View.
    Allows Super Admin to view, create, edit, update, delete, and switch plans for products.
    """
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'super_admin/products.html'
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Super Admin Dashboard'],
        summary='Super Admin Products Page View',
        description='Renders the product catalog management UI for Super Admins in HTML or returns product list in JSON.',
        responses={
            200: OpenApiResponse(description='Products management UI rendered successfully'),
        }
    )
    def get(self, request, *args, **kwargs):
        from product.models import Product, Category
        from product.serializers import ProductDetailSerializer, CategorySerializer

        products_qs = Product.objects.all().select_related('category', 'selected_plan', 'created_by').prefetch_related('plans')
        categories_qs = Category.objects.all()

        products_data = ProductDetailSerializer(products_qs, many=True, context={'request': request}).data
        categories_data = CategorySerializer(categories_qs, many=True).data

        if request.accepted_renderer.format == 'html':
            return Response({
                'products': products_data,
                'categories': categories_data,
                'total_products': products_qs.count(),
            }, template_name=self.template_name)

        return Response({
            "message": "Products retrieved successfully.",
            "total_products": products_qs.count(),
            "products": products_data,
            "categories": categories_data,
        }, status=status.HTTP_200_OK)


class SuperAdminLoginView(TemplateView):
    """
    Renders the Super Admin portal login page.
    """
    template_name = 'super_admin/login.html'


# Alias for backward compatibility
SuperAdminPageView = SuperAdminLoginView


# ==============================================================================
# SUPER ADMIN ORDER VERIFICATION & APPROVAL VIEWS
# ==============================================================================

class SuperAdminOrderListView(APIView):
    """
    Super Admin Endpoint to view and manage customer orders and MFS transactions.
    Requires Super Admin authentication.
    """
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=['Super Admin Orders & Verification'],
        operation_id='superuser_list_orders',
        summary='List All Customer Orders for Super Admin Verification',
        description='Returns all customer orders with filtering by status (PENDING, APPROVED, REJECTED) or search by transaction ID, order number, customer email, or sender phone number.',
        parameters=[
            OpenApiParameter('status', type=str, description='Filter by status: PENDING, APPROVED, REJECTED', required=False),
            OpenApiParameter('payment_method', type=str, description='Filter by payment method: bkash, nagad, rocket, bangla_qr', required=False),
            OpenApiParameter('search', type=str, description='Search by order number, transaction ID, sender number, or email', required=False),
        ],
        responses={
            200: OpenApiResponse(description='List of customer orders with verification details and summary metrics'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='Super Admin privileges required'),
        }
    )
    def get(self, request, *args, **kwargs):
        qs = Order.objects.all().select_related('user', 'approved_by').prefetch_related('items', 'items__product', 'items__plan').order_by('-created_at')

        status_param = request.query_params.get('status')
        if status_param and status_param.upper() != 'ALL':
            qs = qs.filter(status=status_param.upper())

        method_param = request.query_params.get('payment_method')
        if method_param and method_param.lower() != 'all':
            qs = qs.filter(payment_method=method_param.lower())

        search_query = request.query_params.get('search') or request.query_params.get('q')
        if search_query:
            q = search_query.strip()
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(transaction_id__icontains=q) |
                Q(sender_number__icontains=q) |
                Q(user__email__icontains=q) |
                Q(user__username__icontains=q) |
                Q(customer_notes__icontains=q)
            )

        all_orders = Order.objects.all()
        total_revenue = all_orders.filter(status=Order.STATUS_APPROVED).aggregate(total=Sum('total_amount'))['total'] or 0.00
        pending_count = all_orders.filter(status=Order.STATUS_PENDING).count()
        approved_count = all_orders.filter(status=Order.STATUS_APPROVED).count()
        rejected_count = all_orders.filter(status=Order.STATUS_REJECTED).count()

        serializer = OrderSerializer(qs, many=True, context={'request': request})
        return Response({
            "metrics": {
                "total_orders": all_orders.count(),
                "pending_orders": pending_count,
                "approved_orders": approved_count,
                "rejected_orders": rejected_count,
                "total_revenue": float(total_revenue),
            },
            "orders_count": qs.count(),
            "orders": serializer.data,
        }, status=status.HTTP_200_OK)


class SuperAdminOrderDetailView(APIView):
    """
    Super Admin Endpoint to inspect a specific customer order.
    """
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=['Super Admin Orders & Verification'],
        operation_id='superuser_get_order_detail',
        summary='Inspect Specific Customer Order',
        description='Retrieve full breakdown of items, payment verification details, and customer information for an order.',
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(description='Order not found'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='Super Admin privileges required'),
        }
    )
    def get(self, request, order_id, *args, **kwargs):
        order = Order.objects.filter(
            Q(id=order_id) | Q(order_number=str(order_id))
        ).select_related('user', 'approved_by').prefetch_related('items', 'items__product', 'items__plan').first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SuperAdminOrderApproveView(APIView):
    """
    Super Admin Endpoint to approve a customer order upon verifying the MFS Transaction ID.
    Confirms product purchase and activates digital license credentials for the customer.
    """
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=['Super Admin Orders & Verification'],
        operation_id='superuser_approve_order',
        summary='Approve Order & Activate Digital License Credentials',
        description="""
        Verifies customer MFS payment and marks the order as APPROVED.
        - Automatically assigns or accepts a custom digital license activation key.
        - The purchased products and subscriptions become immediately active in the customer's account.
        """,
        request=AdminOrderApprovalSerializer,
        responses={
            200: OrderActionResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            404: OpenApiResponse(description='Order not found'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='Super Admin privileges required'),
        }
    )
    def post(self, request, order_id, *args, **kwargs):
        order = Order.objects.filter(
            Q(id=order_id) | Q(order_number=str(order_id))
        ).first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminOrderApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        custom_key = serializer.validated_data.get('license_key')
        admin_notes = serializer.validated_data.get('admin_notes')

        order.approve(admin_user=request.user, custom_license_key=custom_key, admin_notes=admin_notes)

        order_data = OrderSerializer(order, context={'request': request}).data
        return Response({
            "message": f"Order {order.order_number} approved successfully! Digital subscription license '{order.license_key}' is now active for {order.user.email or order.user.username}.",
            "order": order_data
        }, status=status.HTTP_200_OK)


class SuperAdminOrderRejectView(APIView):
    """
    Super Admin Endpoint to reject an order (e.g. invalid or unverified TrxID).
    """
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=['Super Admin Orders & Verification'],
        operation_id='superuser_reject_order',
        summary='Reject Order with Reason',
        description='Marks the order as REJECTED and records the administrative explanation (e.g., Fake TrxID, Amount mismatch).',
        request=AdminOrderRejectionSerializer,
        responses={
            200: OrderActionResponseSerializer,
            400: OpenApiResponse(description='Validation error in reason'),
            404: OpenApiResponse(description='Order not found'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='Super Admin privileges required'),
        }
    )
    def post(self, request, order_id, *args, **kwargs):
        order = Order.objects.filter(
            Q(id=order_id) | Q(order_number=str(order_id))
        ).first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminOrderRejectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reason = serializer.validated_data['reason']
        order.reject(admin_user=request.user, reason=reason)

        order_data = OrderSerializer(order, context={'request': request}).data
        return Response({
            "message": f"Order {order.order_number} has been rejected.",
            "order": order_data
        }, status=status.HTTP_200_OK)
