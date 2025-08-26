from django.urls import path
from ..views import contracts


urlpatterns = [
    path('', contracts.contracts_list, name='contracts_list'),
    path('create/', contracts.contract_create_wizard, name='contract_create_wizard'),
    path('<int:pk>/edit/', contracts.contract_edit, name='contract_edit'),
    path('<int:pk>/', contracts.contract_detail, name='contract_detail'),
    path('<int:pk>/recalculate/', contracts.contract_recalculate_installments, name='contract_recalculate'),
    path('<int:pk>/print/', contracts.contract_print, name='contract_print'),
]