from django.urls import path
from ..views import projects

app_name = 'projects'

urlpatterns = [
    path('', projects.project_list, name='project_list'),
    path('create/', projects.project_create, name='project_create'),
    path('<int:pk>/', projects.project_detail, name='project_detail'),
    path('<int:pk>/update/', projects.project_update, name='project_update'),
    path('<int:pk>/delete/', projects.project_delete, name='project_delete'),
    path('<int:pk>/change-status/', projects.project_change_status, name='project_change_status'),
    path('<int:pk>/add-expense/', projects.project_add_expense, name='project_add_expense'),
    path('<int:pk>/expenses/', projects.project_expenses, name='project_expenses'),
    path('<int:pk>/materials/', projects.project_materials, name='project_materials'),
]