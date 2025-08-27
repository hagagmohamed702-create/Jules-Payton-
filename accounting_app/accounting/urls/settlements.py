from django.urls import path
from ..views import settlements

app_name = 'settlements'

urlpatterns = [
    path('', settlements.settlement_list, name='settlement_list'),
    path('create/', settlements.settlement_create, name='settlement_create'),
    path('<int:pk>/', settlements.settlement_detail, name='settlement_detail'),
    path('<int:pk>/execute/', settlements.settlement_execute, name='settlement_execute'),
    path('<int:pk>/cancel/', settlements.settlement_cancel, name='settlement_cancel'),
    path('calculate/', settlements.calculate_settlements, name='calculate_settlements'),
    path('create-auto/', settlements.create_auto_settlements, name='create_auto_settlements'),
    path('partner/<int:partner_id>/', settlements.partner_settlements, name='partner_settlements'),
    path('report/', settlements.settlement_report, name='settlement_report'),
]