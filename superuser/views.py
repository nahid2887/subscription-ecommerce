from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from rest_framework_simplejwt.tokens import RefreshToken

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
