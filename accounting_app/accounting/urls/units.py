from django.urls import path
from ..views import units

app_name = 'units'

urlpatterns = [
    path('', units.unit_list, name='unit_list'),
    path('create/', units.unit_create, name='unit_create'),
    path('<int:pk>/', units.unit_detail, name='unit_detail'),
    path('<int:pk>/update/', units.unit_update, name='unit_update'),
    path('<int:pk>/delete/', units.unit_delete, name='unit_delete'),
    path('search/', units.unit_search, name='unit_search'),
]