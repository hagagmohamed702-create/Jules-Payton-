from django.urls import path
from ..views import suppliers

app_name = 'suppliers'

urlpatterns = [
    path('', suppliers.supplier_list, name='supplier_list'),
    path('create/', suppliers.supplier_create, name='supplier_create'),
    path('<int:pk>/', suppliers.supplier_detail, name='supplier_detail'),
    path('<int:pk>/update/', suppliers.supplier_update, name='supplier_update'),
    path('<int:pk>/delete/', suppliers.supplier_delete, name='supplier_delete'),
    path('<int:pk>/toggle-active/', suppliers.supplier_toggle_active, name='supplier_toggle_active'),
    path('search/', suppliers.supplier_search, name='supplier_search'),
]