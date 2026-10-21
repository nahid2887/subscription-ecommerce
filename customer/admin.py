from django.contrib import admin
from .models import CustomerProfile, SavedProduct, CustomerCartItem, Order, OrderItem


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'city', 'country', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number', 'city']
    list_filter = ['is_verified', 'country', 'created_at']


@admin.register(SavedProduct)
class SavedProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'created_at']
    search_fields = ['user__username', 'user__email', 'product__name', 'notes']
    list_filter = ['created_at']
    raw_id_fields = ['user', 'product']


@admin.register(CustomerCartItem)
class CustomerCartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'plan', 'quantity', 'created_at']
    search_fields = ['user__username', 'user__email', 'product__name']
    list_filter = ['created_at']
    raw_id_fields = ['user', 'product', 'plan']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['product', 'plan']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'payment_method', 'transaction_id', 'total_amount', 'status', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email', 'transaction_id', 'sender_number']
    list_filter = ['status', 'payment_method', 'created_at']
    raw_id_fields = ['user', 'approved_by']
    inlines = [OrderItemInline]


