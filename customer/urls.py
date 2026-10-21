from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomerRegisterView,
    CustomerLoginView,
    CustomerProfileView,
    CustomerSavedProductListView,
    CustomerSavedProductDetailView,
    CustomerSavedProductToggleView,
    CustomerSavedProductCheckView,
    CustomerCartView,
    CustomerCartItemDetailView,
    CustomerPaymentMethodsView,
    CustomerOrderListCreateView,
    CustomerOrderDetailView,
    CustomerMySubscriptionsView,
)

app_name = 'customer'

urlpatterns = [
    # Registration & Login
    path('register/', CustomerRegisterView.as_view(), name='register'),
    path('login/', CustomerLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Profile Management
    path('profile/', CustomerProfileView.as_view(), name='profile'),

    # Saved Products / Wishlist
    path('saved-products/', CustomerSavedProductListView.as_view(), name='saved-product-list-create'),
    path('saved-products/toggle/', CustomerSavedProductToggleView.as_view(), name='saved-product-toggle'),
    path('saved-products/<int:product_id>/', CustomerSavedProductDetailView.as_view(), name='saved-product-detail'),
    path('saved-products/check/<int:product_id>/', CustomerSavedProductCheckView.as_view(), name='saved-product-check'),

    # Shopping Cart
    path('cart/', CustomerCartView.as_view(), name='cart'),
    path('cart/<int:item_id>/', CustomerCartItemDetailView.as_view(), name='cart-item-detail'),

    # MFS Payment Methods & Order Placement
    path('payment-methods/', CustomerPaymentMethodsView.as_view(), name='payment-methods'),
    path('orders/', CustomerOrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<str:order_id>/', CustomerOrderDetailView.as_view(), name='order-detail'),
    path('my-subscriptions/', CustomerMySubscriptionsView.as_view(), name='my-subscriptions'),
]


