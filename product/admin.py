from django.contrib import admin
from .models import Category, Product, ProductPlan


class ProductPlanInline(admin.TabularInline):
    model = ProductPlan
    extra = 1
    fields = ('name', 'price', 'currency', 'billing_cycle', 'duration_in_days', 'is_default', 'is_active')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'get_price_display', 'selected_plan', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'sku', 'warranty', 'delivery')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductPlanInline]
    readonly_fields = ('sku', 'created_at', 'updated_at')

    def get_price_display(self, obj):
        price = obj.price
        if price is not None:
            return f"${price} {obj.currency}"
        return "No Plan Selected"
    get_price_display.short_description = "Active Price"


@admin.register(ProductPlan)
class ProductPlanAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'price', 'currency', 'billing_cycle', 'is_default', 'is_active')
    list_filter = ('billing_cycle', 'is_default', 'is_active')
    search_fields = ('name', 'product__name')
