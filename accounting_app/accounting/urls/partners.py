from django.urls import path
from ..views import partners


urlpatterns = [
    # الشركاء
    path('', partners.partners_list, name='partners_list'),
    path('create/', partners.partner_create, name='partner_create'),
    path('<int:pk>/edit/', partners.partner_edit, name='partner_edit'),
    path('<int:pk>/delete/', partners.partner_delete, name='partner_delete'),
    path('<int:pk>/', partners.partner_detail, name='partner_detail'),
    
    # مجموعات الشركاء
    path('groups/', partners.groups_list, name='groups_list'),
    path('groups/create/', partners.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', partners.group_edit, name='group_edit'),
]