from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SuperuserLoginView,
    SuperuserProfileView,
    SuperAdminDashboardView,
    SuperAdminProfilePageView,
    SuperAdminProductsPageView,
    SuperAdminOrderListView,
    SuperAdminOrderDetailView,
    SuperAdminOrderApproveView,
    SuperAdminOrderRejectView,
)

from product.views import ProductListCreateView, ProductDetailView

app_name = 'superuser'

urlpatterns = [
    path('login/', SuperuserLoginView.as_view(), name='superuser-login'),
    path('profile/', SuperuserProfileView.as_view(), name='superuser-profile'),
    path('dashboard/', SuperAdminDashboardView.as_view(), name='superuser-dashboard'),
    path('profile-page/', SuperAdminProfilePageView.as_view(), name='superuser-profile-page'),
    path('products-page/', SuperAdminProductsPageView.as_view(), name='superuser-products-page'),
    path('products/', ProductListCreateView.as_view(), name='superuser-products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='superuser-product-detail'),
    path('orders/', SuperAdminOrderListView.as_view(), name='superuser-orders-list'),
    path('orders/<int:order_id>/', SuperAdminOrderDetailView.as_view(), name='superuser-order-detail'),
    path('orders/<int:order_id>/approve/', SuperAdminOrderApproveView.as_view(), name='superuser-order-approve'),
    path('orders/<int:order_id>/reject/', SuperAdminOrderRejectView.as_view(), name='superuser-order-reject'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]

