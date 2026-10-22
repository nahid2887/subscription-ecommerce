from django.contrib import admin
from .models import TermsAndConditions


@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'version',
        'is_active',
        'effective_date',
        'updated_at',
        'updated_by',
    )
    list_filter = ('is_active', 'effective_date', 'created_at')
    search_fields = ('title', 'content', 'version')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
