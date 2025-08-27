from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PartnerViewSet, PartnersGroupViewSet, SafeViewSet, CustomerViewSet,
    SupplierViewSet, UnitViewSet, ContractViewSet, InstallmentViewSet,
    ProjectViewSet, ItemViewSet, StockMoveViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'partners', PartnerViewSet)
router.register(r'partner-groups', PartnersGroupViewSet)
router.register(r'safes', SafeViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'units', UnitViewSet)
router.register(r'contracts', ContractViewSet)
router.register(r'installments', InstallmentViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'items', ItemViewSet)
router.register(r'stock-moves', StockMoveViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
]