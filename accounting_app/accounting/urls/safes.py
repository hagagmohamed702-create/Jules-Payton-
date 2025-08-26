from django.urls import path
from ..views import safes


urlpatterns = [
    path('', safes.safes_list, name='safes_list'),
    path('create/', safes.safe_create, name='safe_create'),
    path('<int:pk>/edit/', safes.safe_edit, name='safe_edit'),
    path('<int:pk>/', safes.safe_detail, name='safe_detail'),
    path('transfer/', safes.safe_transfer, name='safe_transfer'),
]