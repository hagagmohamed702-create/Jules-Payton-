from django.urls import path, include

app_name = 'accounting'

urlpatterns = [
    path('', include('accounting.urls.dashboard')),
    path('partners/', include('accounting.urls.partners')),
    path('safes/', include('accounting.urls.safes')),
    path('customers/', include('accounting.urls.customers')),
    path('contracts/', include('accounting.urls.contracts')),
    path('units/', include('accounting.urls.units')),
    path('suppliers/', include('accounting.urls.suppliers')),
    path('installments/', include('accounting.urls.installments')),
    path('projects/', include('accounting.urls.projects')),
    path('inventory/', include('accounting.urls.inventory')),
    path('settlements/', include('accounting.urls.settlements')),
    path('vouchers/', include('accounting.urls.vouchers')),
    path('reports/', include('accounting.urls.reports')),
    path('notifications/', include('accounting.urls.notifications')),
    path('api/', include('accounting.api.urls')),
]