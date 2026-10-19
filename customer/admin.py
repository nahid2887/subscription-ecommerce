from django.contrib import admin
from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'city', 'country', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number', 'city']
    list_filter = ['is_verified', 'country', 'created_at']
