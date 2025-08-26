from django.urls import path, include

app_name = 'accounting'

urlpatterns = [
    path('', include('accounting.urls.dashboard')),
    path('partners/', include('accounting.urls.partners')),
    path('safes/', include('accounting.urls.safes')),
    path('customers/', include('accounting.urls.customers')),
    path('contracts/', include('accounting.urls.contracts')),
]