from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Q, Sum
from decimal import Decimal
from ..models import Customer, Contract, Installment, ReceiptVoucher
from ..forms.customers import CustomerForm
from ..services import InstallmentService


@login_required
def customers_list(request):
    """قائمة العملاء"""
    search_query = request.GET.get('search', '')
    filter_active = request.GET.get('active', 'all')
    
    customers = Customer.objects.all()
    
    if search_query:
        customers = customers.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if filter_active == 'active':
        customers = customers.filter(is_active=True)
    elif filter_active == 'inactive':
        customers = customers.filter(is_active=False)
    
    customers = customers.order_by('code')
    
    # إحصائيات لكل عميل
    for customer in customers:
        customer.contracts_count = customer.contracts.count()
        customer.total_contracts_value = customer.get_total_contracts_value()
        customer.total_paid = customer.get_total_paid()
    
    context = {
        'customers': customers,
        'search_query': search_query,
        'filter_active': filter_active,
    }
    
    if request.htmx:
        return render(request, 'accounting/customers/_table.html', context)
    
    return render(request, 'accounting/customers/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def customer_create(request):
    """إنشاء عميل جديد"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'تم إنشاء العميل {customer.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف الجديد للجدول
                customer.contracts_count = 0
                customer.total_contracts_value = 0
                customer.total_paid = 0
                
                html = render_to_string('accounting/customers/_row.html', {'customer': customer})
                return JsonResponse({
                    'html': html,
                    'message': f'تم إنشاء العميل {customer.name} بنجاح'
                })
            
            return redirect('accounting:customers_list')
    else:
        form = CustomerForm()
    
    context = {'form': form, 'title': 'إضافة عميل جديد'}
    
    if request.htmx:
        return render(request, 'accounting/customers/_form.html', context)
    
    return render(request, 'accounting/customers/form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def customer_edit(request, pk):
    """تعديل عميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'تم تحديث العميل {customer.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف المحدث
                customer.contracts_count = customer.contracts.count()
                customer.total_contracts_value = customer.get_total_contracts_value()
                customer.total_paid = customer.get_total_paid()
                
                html = render_to_string('accounting/customers/_row.html', {'customer': customer})
                return JsonResponse({
                    'html': html,
                    'message': f'تم تحديث العميل {customer.name} بنجاح'
                })
            
            return redirect('accounting:customers_list')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'تعديل العميل: {customer.name}'
    }
    
    if request.htmx:
        return render(request, 'accounting/customers/_form.html', context)
    
    return render(request, 'accounting/customers/form.html', context)


@login_required
def customer_detail(request, pk):
    """تفاصيل العميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # العقود
    contracts = customer.contracts.select_related('unit').order_by('-created_at')
    
    # ملخص الأقساط
    installments_summary = InstallmentService.get_customer_installments_summary(customer)
    
    # سندات القبض الأخيرة
    recent_receipts = ReceiptVoucher.objects.filter(
        customer=customer
    ).select_related('safe').order_by('-date', '-created_at')[:10]
    
    # الأقساط المتأخرة
    late_installments = Installment.objects.filter(
        contract__customer=customer,
        status='LATE'
    ).select_related('contract').order_by('due_date')
    
    context = {
        'customer': customer,
        'contracts': contracts,
        'installments_summary': installments_summary,
        'recent_receipts': recent_receipts,
        'late_installments': late_installments,
    }
    
    return render(request, 'accounting/customers/detail.html', context)


@login_required
@require_http_methods(["DELETE"])
def customer_delete(request, pk):
    """حذف عميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # التحقق من وجود عقود
    if customer.contracts.exists():
        messages.error(request, 'لا يمكن حذف عميل له عقود')
        
        if request.htmx:
            return JsonResponse({
                'message': 'لا يمكن حذف عميل له عقود',
                'deleted': False
            }, status=400)
    else:
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'تم حذف العميل {customer_name} بنجاح')
        
        if request.htmx:
            return JsonResponse({
                'message': f'تم حذف العميل {customer_name} بنجاح',
                'deleted': True
            })
    
    return redirect('accounting:customers_list')


@login_required
def customer_statement(request, pk):
    """كشف حساب العميل"""
    customer = get_object_or_404(Customer, pk=pk)
    
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # جميع المعاملات
    transactions = []
    
    # العقود
    contracts = customer.contracts.all()
    for contract in contracts:
        transactions.append({
            'date': contract.created_at.date(),
            'type': 'contract',
            'description': f'عقد {contract.code} - وحدة {contract.unit.name}',
            'debit': contract.unit_value,
            'credit': Decimal('0'),
            'reference': contract.code
        })
        
        if contract.down_payment > 0:
            transactions.append({
                'date': contract.created_at.date(),
                'type': 'down_payment',
                'description': f'دفعة مقدمة - عقد {contract.code}',
                'debit': Decimal('0'),
                'credit': contract.down_payment,
                'reference': contract.code
            })
    
    # سندات القبض
    receipts = ReceiptVoucher.objects.filter(customer=customer)
    if from_date:
        receipts = receipts.filter(date__gte=from_date)
    if to_date:
        receipts = receipts.filter(date__lte=to_date)
    
    for receipt in receipts:
        transactions.append({
            'date': receipt.date,
            'type': 'receipt',
            'description': receipt.description,
            'debit': Decimal('0'),
            'credit': receipt.amount,
            'reference': receipt.voucher_number
        })
    
    # ترتيب حسب التاريخ
    transactions.sort(key=lambda x: x['date'])
    
    # حساب الرصيد التراكمي
    running_balance = Decimal('0')
    for transaction in transactions:
        running_balance += transaction['debit'] - transaction['credit']
        transaction['balance'] = running_balance
    
    context = {
        'customer': customer,
        'transactions': transactions,
        'from_date': from_date,
        'to_date': to_date,
        'final_balance': running_balance,
    }
    
    return render(request, 'accounting/customers/statement.html', context)