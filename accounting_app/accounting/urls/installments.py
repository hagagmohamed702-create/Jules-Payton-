from django.urls import path
from ..views import installments

app_name = 'installments'

urlpatterns = [
    path('', installments.installment_list, name='installment_list'),
    path('<int:pk>/', installments.installment_detail, name='installment_detail'),
    path('<int:pk>/payment/', installments.installment_payment, name='installment_payment'),
    path('contract/<int:contract_id>/schedule/', installments.installment_schedule, name='installment_schedule'),
    path('overdue/', installments.overdue_installments, name='overdue_installments'),
    path('reminders/', installments.installment_reminders, name='installment_reminders'),
]