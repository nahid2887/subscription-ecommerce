from django.urls import path
from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductSelectPlanView,
    CategoryListCreateView,
)

app_name = 'product'

urlpatterns = [
    # Category endpoints (placed before slug to avoid treating 'categories' as a slug)
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),

    # Product CRUD endpoints
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('create/', ProductListCreateView.as_view(), name='product-create-alias'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail-slug'),
    path('<int:pk>/select-plan/', ProductSelectPlanView.as_view(), name='product-select-plan'),
]
