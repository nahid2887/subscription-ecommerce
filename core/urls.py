from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from superuser.views import (
    SuperAdminLoginView,
    SuperAdminDashboardView,
    SuperAdminProfilePageView,
    SuperAdminProductsPageView,
)
from product.views import StorefrontHomeView
from customer.views import CustomerProfilePageView

urlpatterns = [
    # Public E-Commerce Storefront
    path('', StorefrontHomeView.as_view(), name='home'),
    path('store/', StorefrontHomeView.as_view(), name='store'),
    path('profile/', CustomerProfilePageView.as_view(), name='customer-profile-page'),

    # Admin
    path('admin/', admin.site.urls),

    # Super Admin Web Portal
    path('super-admin/', SuperAdminLoginView.as_view(), name='super-admin'),
    path('super-admin/login/', SuperAdminLoginView.as_view(), name='super-admin-login'),
    path('super-admin/dashboard/', SuperAdminDashboardView.as_view(), name='super-admin-dashboard'),
    path('super-admin/profile/', SuperAdminProfilePageView.as_view(), name='super-admin-profile'),
    path('super-admin/products/', SuperAdminProductsPageView.as_view(), name='super-admin-products'),

    # Superuser API Endpoints
    path('api/superuser/', include('superuser.urls')),

    # Product & Subscription Plans API Endpoints
    path('api/products/', include('product.urls')),

    # Customer Authentication & Profile API Endpoints
    path('api/customer/', include('customer.urls')),

    # Swagger / OpenAPI 3.0 Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
