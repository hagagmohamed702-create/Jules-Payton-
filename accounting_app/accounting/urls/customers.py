from django.urls import path
from ..views import customers


urlpatterns = [
    path('', customers.customers_list, name='customers_list'),
    path('create/', customers.customer_create, name='customer_create'),
    path('<int:pk>/edit/', customers.customer_edit, name='customer_edit'),
    path('<int:pk>/delete/', customers.customer_delete, name='customer_delete'),
    path('<int:pk>/', customers.customer_detail, name='customer_detail'),
    path('<int:pk>/statement/', customers.customer_statement, name='customer_statement'),
]