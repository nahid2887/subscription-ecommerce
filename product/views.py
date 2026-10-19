from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample

from superuser.permissions import IsSuperUser
from .models import Category, Product, ProductPlan
from .serializers import (
    CategorySerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductUpdateSerializer,
    ProductPlanItemSerializer,
    ProductResponseSerializer,
)


class ProductListCreateView(APIView):
    """
    API View to:
    - POST: Allow Super Admin to create a new product with multi-lingual description,
            features, category, warranty, delivery, and plans (price dependent on selected plan).
    - GET: List all products with optional filtering by category, search term, and status.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperUser()]
        return [AllowAny()]

    @extend_schema(
        tags=['Products & Plans'],
        summary='Create Product (Super Admin Only)',
        description="""
        Create a new product. **Restricted exclusively to Super Admins**.
        
        Requires `Authorization: Bearer <access_token>` in header.
        
        ### Capabilities:
        - **name**: Product title (e.g., 'Cloud Storage Enterprise')
        - **image**: File upload via `multipart/form-data` or Base64 data URI string via JSON.
        - **category**: Category ID (integer) or category name (auto-created if not found).
        - **features**: List of feature strings or JSON array (e.g., `['24/7 Support', '1TB Cloud Drive']`).
        - **description**: Multi-lingual dictionary supporting all languages (e.g., `{'en': '...', 'es': '...', 'bn': '...'}`). If a plain string is provided, it is automatically saved under English `{'en': ...}`.
        - **warranty**: Warranty information or guarantee period.
        - **delivery**: Delivery specifications (e.g. 'Instant Digital Access').
        - **plans**: Array of plans with custom prices (e.g., `[{'name': 'Monthly', 'price': 29.99, 'billing_cycle': 'monthly', 'is_default': true}]`).
        - **selected_plan**: Or provide a single plan object to create and select. Price of the product automatically mirrors the selected plan.
        """,
        request=ProductCreateSerializer,
        responses={
            201: ProductResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized: Missing or invalid token'),
            403: OpenApiResponse(description='Forbidden: Super admin privileges required'),
        },
        examples=[
            OpenApiExample(
                'Complete Multi-lingual Subscription Product',
                value={
                    "name": "Cloud Pro Workspace",
                    "category": "Cloud Software",
                    "features": [
                        "1 TB Encrypted Cloud Storage",
                        "High Speed File Sync",
                        "Priority 24/7 Technical Support",
                        "Unlimited Team Members"
                    ],
                    "description": {
                        "en": "Enterprise-grade cloud workspace with real-time collaboration and continuous backup.",
                        "es": "Espacio de trabajo en la nube de nivel empresarial con colaboracion.",
                        "fr": "Espace de travail cloud d'entreprise avec collaboration en temps reel.",
                        "de": "Hochwertiger Cloud-Arbeitsbereich mit Echtzeit-Zusammenarbeit."
                    },
                    "warranty": "30-day money-back guarantee with zero cancellation fees",
                    "delivery": "Instant digital access via email invitation and credentials within 60 seconds",
                    "plans": [
                        {
                            "name": "Monthly Billing",
                            "price": 29.99,
                            "billing_cycle": "monthly",
                            "is_default": True
                        },
                        {
                            "name": "Annual Billing (Save 20%)",
                            "price": 289.00,
                            "billing_cycle": "yearly",
                            "is_default": False
                        }
                    ]
                },
                request_only=True
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = ProductCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.save()
        detail_serializer = ProductDetailSerializer(product, context={'request': request})

        return Response({
            "message": "Product created successfully.",
            "product": detail_serializer.data
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Products & Plans'],
        summary='List Products (Public & Admin)',
        description='Retrieve a list of products with optional filters for category, search keyword, and active status. Public visitors only see active products by default.',
        parameters=[
            OpenApiParameter(name='category', description='Filter by Category ID or slug', required=False, type=str),
            OpenApiParameter(name='search', description='Search product name, warranty, delivery, or SKU', required=False, type=str),
            OpenApiParameter(name='is_active', description='Filter by active status (true/false)', required=False, type=bool),
            OpenApiParameter(name='lang', description='Language code for localized_description (e.g. en, es, bn, ar)', required=False, type=str),
        ],
        responses={
            200: ProductDetailSerializer(many=True),
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = Product.objects.all().select_related('category', 'selected_plan', 'created_by').prefetch_related('plans')

        category = request.query_params.get('category')
        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=int(category))
            else:
                queryset = queryset.filter(Q(category__slug=category) | Q(category__name__iexact=category))

        is_superuser = bool(request.user and request.user.is_authenticated and request.user.is_superuser)
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() in ('true', '1'):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ('false', '0'):
                if is_superuser:
                    queryset = queryset.filter(is_active=False)
                else:
                    queryset = queryset.none()
        elif not is_superuser:
            # Public visitors only see active products
            queryset = queryset.filter(is_active=True)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(warranty__icontains=search) |
                Q(delivery__icontains=search)
            )

        serializer = ProductDetailSerializer(queryset, many=True, context={'request': request})
        return Response({
            "count": queryset.count(),
            "products": serializer.data
        }, status=status.HTTP_200_OK)


class ProductDetailView(APIView):
    """
    Retrieve, update or delete a specific product by ID or slug.
    Publicly accessible for GET requests by anyone.
    Updates and deletions are strictly restricted to Super Admins.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsSuperUser()]
        return [AllowAny()]

    def _get_product(self, request, pk=None, slug=None, enforce_active=True, prefetch=True):
        if prefetch:
            qs = Product.objects.select_related('category', 'selected_plan', 'created_by').prefetch_related('plans')
        else:
            qs = Product.objects.all()

        is_superuser = bool(request.user and request.user.is_authenticated and request.user.is_superuser)

        if enforce_active and not is_superuser:
            qs = qs.filter(is_active=True)

        if pk is not None:
            return get_object_or_404(qs, pk=pk)
        elif slug is not None:
            return get_object_or_404(qs, slug=slug)
        else:
            return get_object_or_404(qs, pk=None)

    @extend_schema(
        tags=['Products & Plans'],
        summary='Get Product Details (Public & Admin)',
        description='Retrieve complete details of a product by ID or slug. Public visitors can view active products with all plan options.',
        parameters=[
            OpenApiParameter(name='lang', description='Language code for localized_description (e.g. en, es, bn, ar)', required=False, type=str),
        ],
        responses={
            200: ProductDetailSerializer,
            404: OpenApiResponse(description='Product not found'),
        }
    )
    def get(self, request, pk=None, slug=None, *args, **kwargs):
        product = self._get_product(request, pk=pk, slug=slug, enforce_active=True, prefetch=True)
        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response({
            "message": "Product retrieved successfully.",
            "product": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Products & Plans'],
        summary='Update Product (Super Admin Only)',
        description='Update product fields, selected plan, category, multi-lingual description, features, warranty, or delivery.',
        request=ProductUpdateSerializer,
        responses={
            200: ProductResponseSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized: Missing or invalid token'),
            403: OpenApiResponse(description='Forbidden: Super admin privileges required'),
            404: OpenApiResponse(description='Product not found'),
        }
    )
    def patch(self, request, pk=None, slug=None, *args, **kwargs):
        product = self._get_product(request, pk=pk, slug=slug, enforce_active=False, prefetch=False)
        serializer = ProductUpdateSerializer(
            instance=product,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_product = serializer.save()
        fresh_product = Product.objects.select_related('category', 'selected_plan', 'created_by').prefetch_related('plans').get(pk=updated_product.pk)
        detail_serializer = ProductDetailSerializer(fresh_product, context={'request': request})
        return Response({
            "message": "Product updated successfully.",
            "product": detail_serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Products & Plans'],
        summary='Delete Product (Super Admin Only)',
        description='Permanently delete a product and its associated plans.',
        responses={
            200: OpenApiResponse(description='Product deleted successfully'),
            401: OpenApiResponse(description='Unauthorized: Missing or invalid token'),
            403: OpenApiResponse(description='Forbidden: Super admin privileges required'),
            404: OpenApiResponse(description='Product not found'),
        }
    )
    def delete(self, request, pk=None, slug=None, *args, **kwargs):
        product = self._get_product(request, pk=pk, slug=slug, enforce_active=False, prefetch=False)
        product_name = product.name
        product.delete()
        return Response({
            "message": f"Product '{product_name}' deleted successfully."
        }, status=status.HTTP_200_OK)


class ProductSelectPlanView(APIView):
    """
    Select/switch the active plan for a product.
    Because product pricing depends on the selected plan, updating the selected plan
    immediately updates the product's primary price.
    """
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=['Products & Plans'],
        summary='Select Active Plan for Product (Super Admin Only)',
        description='Switches the selected plan of the product, updating its active displayed price.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'plan_id': {'type': 'integer', 'description': 'ID of the plan to select'}
                },
                'required': ['plan_id']
            }
        },
        responses={
            200: ProductResponseSerializer,
            400: OpenApiResponse(description='Invalid plan ID'),
            404: OpenApiResponse(description='Product or plan not found'),
        }
    )
    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        plan_id = request.data.get('plan_id')

        if not plan_id:
            return Response({"error": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        plan = get_object_or_404(ProductPlan, pk=plan_id, product=product)

        # Update product selected_plan and plan default status
        product.selected_plan = plan
        product.save(update_fields=['selected_plan'])

        ProductPlan.objects.filter(product=product).update(is_default=False)
        plan.is_default = True
        plan.save(update_fields=['is_default'])

        detail_serializer = ProductDetailSerializer(product, context={'request': request})
        return Response({
            "message": f"Plan '{plan.name}' selected successfully. Active price updated to ${plan.price}.",
            "product": detail_serializer.data
        }, status=status.HTTP_200_OK)


class CategoryListCreateView(APIView):
    """
    List and create product categories.
    Category creation is restricted to Super Admins.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperUser()]
        return [AllowAny()]

    @extend_schema(
        tags=['Products & Plans'],
        summary='List Categories',
        description='Retrieve all product categories with their product count.',
        responses={200: CategorySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all().prefetch_related('products')
        serializer = CategorySerializer(categories, many=True)
        return Response({
            "count": categories.count(),
            "categories": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Products & Plans'],
        summary='Create Category (Super Admin Only)',
        description='Create a new product category.',
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='Forbidden'),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        category = serializer.save()
        return Response({
            "message": "Category created successfully.",
            "category": CategorySerializer(category).data
        }, status=status.HTTP_201_CREATED)


from django.views.generic import TemplateView


class StorefrontHomeView(TemplateView):
    """
    Public E-Commerce Storefront Home View.
    Displays modern hero, dynamic product catalog cards with multi-device plan selection,
    interactive details, trust badges, customer reviews, and instant checkout.
    """
    template_name = 'store/index.html'

