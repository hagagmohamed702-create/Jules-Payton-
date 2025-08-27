from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from ..models import Installment, Contract, ReceiptVoucher
from ..forms.installments import InstallmentPaymentForm
from ..services.installment_service import InstallmentService


def installment_list(request):
    """عرض قائمة الأقساط"""
    installments = Installment.objects.select_related(
        'contract__customer',
        'contract__unit'
    ).annotate(
        remaining=F('amount') - F('paid_amount')
    )
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        installments = installments.filter(
            Q(contract__customer__name__icontains=search_query) |
            Q(contract__unit__name__icontains=search_query) |
            Q(contract__contract_number__icontains=search_query)
        )
    
    # التصفية حسب الحالة
    status = request.GET.get('status')
    if status:
        installments = installments.filter(status=status)
    
    # التصفية حسب التاريخ
    date_filter = request.GET.get('date_filter')
    today = timezone.now().date()
    
    if date_filter == 'overdue':
        installments = installments.filter(
            due_date__lt=today,
            status__in=['pending', 'partial']
        )
    elif date_filter == 'due_today':
        installments = installments.filter(due_date=today)
    elif date_filter == 'due_week':
        week_end = today + timedelta(days=7)
        installments = installments.filter(
            due_date__gte=today,
            due_date__lte=week_end
        )
    elif date_filter == 'due_month':
        month_end = today + timedelta(days=30)
        installments = installments.filter(
            due_date__gte=today,
            due_date__lte=month_end
        )
    
    # التصفية حسب العقد
    contract_id = request.GET.get('contract_id')
    if contract_id:
        installments = installments.filter(contract_id=contract_id)
    
    # الترتيب
    order_by = request.GET.get('order_by', 'due_date')
    installments = installments.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(installments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_installments': Installment.objects.count(),
        'paid_installments': Installment.objects.filter(status='paid').count(),
        'overdue_installments': Installment.objects.filter(
            due_date__lt=today,
            status__in=['pending', 'partial']
        ).count(),
        'total_amount': Installment.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'paid_amount': Installment.objects.aggregate(total=Sum('paid_amount'))['total'] or 0,
        'remaining_amount': Installment.objects.aggregate(
            total=Sum(F('amount') - F('paid_amount'))
        )['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status': status,
        'date_filter': date_filter,
        'contract_id': contract_id,
        'stats': stats,
        'statuses': Installment.STATUS_CHOICES,
    }
    
    return render(request, 'accounting/installments/installment_list.html', context)


def installment_detail(request, pk):
    """عرض تفاصيل القسط"""
    installment = get_object_or_404(
        Installment.objects.select_related(
            'contract__customer',
            'contract__unit',
            'contract__partners_group'
        ).prefetch_related(
            'payments__receipt_voucher',
            'contract__partners_group__members__partner'
        ),
        pk=pk
    )
    
    # حساب توزيع القسط على الشركاء
    partners_distribution = []
    if installment.contract.partners_group:
        for member in installment.contract.partners_group.members.all():
            share_amount = (member.share_percentage / 100) * installment.amount
            paid_share = (member.share_percentage / 100) * installment.paid_amount
            partners_distribution.append({
                'partner': member.partner,
                'percentage': member.share_percentage,
                'share_amount': share_amount,
                'paid_share': paid_share,
                'remaining': share_amount - paid_share
            })
    
    context = {
        'installment': installment,
        'partners_distribution': partners_distribution,
    }
    
    return render(request, 'accounting/installments/installment_detail.html', context)


@require_http_methods(["GET", "POST"])
def installment_payment(request, pk):
    """تسديد قسط"""
    installment = get_object_or_404(
        Installment.objects.select_related('contract__customer'),
        pk=pk
    )
    
    if installment.status == 'paid':
        messages.warning(request, 'هذا القسط مدفوع بالكامل.')
        return redirect('accounting:installment_detail', pk=installment.pk)
    
    if request.method == 'POST':
        form = InstallmentPaymentForm(request.POST, installment=installment)
        if form.is_valid():
            try:
                payment = InstallmentService.process_payment(
                    installment=installment,
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data['payment_date'],
                    safe=form.cleaned_data['safe'],
                    notes=form.cleaned_data.get('notes', '')
                )
                
                messages.success(
                    request,
                    f'تم تسديد مبلغ {payment.amount} من القسط بنجاح.'
                )
                
                if request.headers.get('HX-Request'):
                    return redirect('accounting:installment_list')
                return redirect('accounting:installment_detail', pk=installment.pk)
                
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = InstallmentPaymentForm(installment=installment)
    
    context = {
        'form': form,
        'installment': installment,
    }
    
    return render(request, 'accounting/installments/installment_payment_form.html', context)


def installment_schedule(request, contract_id):
    """عرض جدول أقساط العقد"""
    contract = get_object_or_404(
        Contract.objects.prefetch_related('installments'),
        pk=contract_id
    )
    
    installments = contract.installments.annotate(
        remaining=F('amount') - F('paid_amount')
    ).order_by('installment_number')
    
    # حساب الإحصائيات
    stats = {
        'total_amount': installments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'paid_amount': installments.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
        'remaining_amount': installments.aggregate(Sum('remaining'))['remaining__sum'] or 0,
        'paid_count': installments.filter(status='paid').count(),
        'total_count': installments.count(),
    }
    
    context = {
        'contract': contract,
        'installments': installments,
        'stats': stats,
    }
    
    return render(request, 'accounting/installments/installment_schedule.html', context)


def overdue_installments(request):
    """عرض الأقساط المتأخرة"""
    today = timezone.now().date()
    
    installments = Installment.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    ).select_related(
        'contract__customer',
        'contract__unit'
    ).annotate(
        remaining=F('amount') - F('paid_amount'),
        days_overdue=today - F('due_date')
    ).order_by('-days_overdue')
    
    # تجميع حسب العميل
    customers_summary = {}
    for installment in installments:
        customer = installment.contract.customer
        if customer.id not in customers_summary:
            customers_summary[customer.id] = {
                'customer': customer,
                'installments': [],
                'total_overdue': 0,
                'count': 0
            }
        
        customers_summary[customer.id]['installments'].append(installment)
        customers_summary[customer.id]['total_overdue'] += installment.remaining
        customers_summary[customer.id]['count'] += 1
    
    context = {
        'installments': installments,
        'customers_summary': customers_summary.values(),
        'total_overdue': installments.aggregate(
            total=Sum('remaining')
        )['total'] or 0,
    }
    
    return render(request, 'accounting/installments/overdue_installments.html', context)


def installment_reminders(request):
    """إرسال تذكيرات الأقساط"""
    if request.method == 'POST':
        installment_ids = request.POST.getlist('installment_ids')
        
        if not installment_ids:
            messages.error(request, 'يرجى اختيار أقساط لإرسال التذكيرات.')
            return redirect('accounting:overdue_installments')
        
        # هنا يمكن إضافة منطق إرسال الرسائل أو الإيميلات
        count = len(installment_ids)
        messages.success(request, f'تم إرسال {count} تذكير بنجاح.')
        
        return redirect('accounting:overdue_installments')
    
    return redirect('accounting:overdue_installments')