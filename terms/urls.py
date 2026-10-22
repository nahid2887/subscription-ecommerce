from django.urls import path
from .views import (
    ActiveTermsAndConditionsView,
    TermsAndConditionsHistoryView,
    TermsAndConditionsDetailView,
)

app_name = 'terms'

urlpatterns = [
    # Active Terms and Conditions (Show for all users, Edit for super admin)
    path('', ActiveTermsAndConditionsView.as_view(), name='terms-active'),

    # List history/versions of Terms and Conditions
    path('history/', TermsAndConditionsHistoryView.as_view(), name='terms-history'),

    # Manage or view specific Terms and Conditions by ID
    path('<int:pk>/', TermsAndConditionsDetailView.as_view(), name='terms-detail'),
]
