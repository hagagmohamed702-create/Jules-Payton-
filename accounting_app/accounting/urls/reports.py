from django.urls import path
from ..views import reports

app_name = 'reports'

urlpatterns = [
    path('', reports.reports_dashboard, name='reports_dashboard'),
    path('installments/', reports.installments_report, name='installments_report'),
    path('treasury/', reports.treasury_report, name='treasury_report'),
    path('wallets/', reports.wallets_report, name='wallets_report'),
    path('projects/', reports.projects_report, name='projects_report'),
    path('inventory/', reports.inventory_full_report, name='inventory_full_report'),
    path('financial/', reports.financial_summary, name='financial_summary'),
]