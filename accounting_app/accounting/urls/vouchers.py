from django.urls import path
from ..views import vouchers

app_name = 'vouchers'

urlpatterns = [
    path('<str:voucher_type>/', vouchers.voucher_list, name='voucher_list'),
    path('<str:voucher_type>/<int:pk>/', vouchers.voucher_detail, name='voucher_detail'),
    path('receipt/create/', vouchers.receipt_voucher_create, name='receipt_voucher_create'),
    path('payment/create/', vouchers.payment_voucher_create, name='payment_voucher_create'),
    path('receipt/<int:pk>/link-installments/', vouchers.link_voucher_installments, name='link_voucher_installments'),
    path('<str:voucher_type>/<int:pk>/cancel/', vouchers.voucher_cancel, name='voucher_cancel'),
    path('<str:voucher_type>/<int:pk>/print/', vouchers.voucher_print, name='voucher_print'),
    path('report/', vouchers.voucher_report, name='voucher_report'),
]