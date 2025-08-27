from django.urls import path
from ..views import inventory

app_name = 'inventory'

urlpatterns = [
    path('items/', inventory.item_list, name='item_list'),
    path('items/create/', inventory.item_create, name='item_create'),
    path('items/<int:pk>/', inventory.item_detail, name='item_detail'),
    path('items/<int:pk>/update/', inventory.item_update, name='item_update'),
    path('items/<int:pk>/delete/', inventory.item_delete, name='item_delete'),
    path('stock-in/', inventory.stock_in, name='stock_in'),
    path('stock-out/', inventory.stock_out, name='stock_out'),
    path('stock-moves/', inventory.stock_moves, name='stock_moves'),
    path('low-stock/', inventory.low_stock_items, name='low_stock_items'),
    path('report/', inventory.inventory_report, name='inventory_report'),
]