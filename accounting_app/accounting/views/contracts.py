from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Q, Sum, Count
from decimal import Decimal
from ..models import Contract, Unit, Customer, Installment
from ..services import ContractService


@login_required
def contracts_list(request):
    """قائمة العقود"""
    search_query = request.GET.get('search', '')
    customer_filter = request.GET.get('customer')
    
    contracts = Contract.objects.select_related(
        'customer', 'unit', 'partners_group'
    ).prefetch_related('installments')
    
    if search_query:
        contracts = contracts.filter(
            Q(code__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(unit__name__icontains=search_query)
        )
    
    if customer_filter:
        contracts = contracts.filter(customer_id=customer_filter)
    
    contracts = contracts.order_by('-created_at')
    
    # إحصائيات لكل عقد
    for contract in contracts:
        contract.paid_installments = contract.installments.filter(status='PAID').count()
        contract.late_installments = contract.installments.filter(status='LATE').count()
        contract.total_paid = contract.get_total_paid()
        contract.balance_due = contract.get_balance_due()
    
    # قائمة العملاء للفلتر
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'contracts': contracts,
        'customers': customers,
        'search_query': search_query,
        'customer_filter': customer_filter,
    }
    
    if request.htmx:
        return render(request, 'accounting/contracts/_table.html', context)
    
    return render(request, 'accounting/contracts/list.html', context)


@login_required
def contract_create_wizard(request):
    """معالج إنشاء عقد جديد"""
    from ..forms.contracts import ContractForm
    
    if request.method == 'POST':
        step = request.POST.get('step', '1')
        
        if step == '1':
            # الخطوة الأولى: بيانات العقد
            form = ContractForm(request.POST)
            if form.is_valid():
                # حفظ البيانات في الجلسة
                request.session['contract_data'] = form.cleaned_data
                request.session['contract_data']['unit'] = form.cleaned_data['unit'].id
                request.session['contract_data']['customer'] = form.cleaned_data['customer'].id
                request.session['contract_data']['partners_group'] = form.cleaned_data['partners_group'].id if form.cleaned_data.get('partners_group') else None
                request.session['contract_data']['start_date'] = form.cleaned_data['start_date'].isoformat()
                
                # توليد جدول الأقساط للمعاينة
                contract_data = form.cleaned_data
                installments_preview = []
                
                if contract_data['installments_count'] > 0:
                    remaining_amount = contract_data['unit_value'] - contract_data['down_payment']
                    base_installment = remaining_amount / contract_data['installments_count']
                    base_installment = base_installment.quantize(Decimal('0.01'))
                    
                    current_date = contract_data['start_date']
                    total_amount = Decimal('0')
                    
                    for i in range(contract_data['installments_count']):
                        if i == contract_data['installments_count'] - 1:
                            installment_amount = remaining_amount - total_amount
                        else:
                            installment_amount = base_installment
                            total_amount += installment_amount
                        
                        installments_preview.append({
                            'seq_no': i + 1,
                            'due_date': current_date,
                            'amount': installment_amount
                        })
                        
                        # حساب التاريخ التالي
                        if contract_data['schedule_type'] == 'monthly':
                            from dateutil.relativedelta import relativedelta
                            current_date += relativedelta(months=1)
                        elif contract_data['schedule_type'] == 'quarterly':
                            from dateutil.relativedelta import relativedelta
                            current_date += relativedelta(months=3)
                        else:
                            from dateutil.relativedelta import relativedelta
                            current_date += relativedelta(years=1)
                
                request.session['installments_preview'] = [
                    {
                        'seq_no': inst['seq_no'],
                        'due_date': inst['due_date'].isoformat(),
                        'amount': str(inst['amount'])
                    }
                    for inst in installments_preview
                ]
                
                # الانتقال للخطوة الثانية
                context = {
                    'step': '2',
                    'contract_data': contract_data,
                    'installments_preview': installments_preview,
                }
                return render(request, 'accounting/contracts/create_wizard.html', context)
        
        elif step == '2':
            # الخطوة الثانية: تأكيد وحفظ
            if 'contract_data' in request.session:
                try:
                    # استرجاع البيانات من الجلسة
                    contract_data = request.session['contract_data']
                    
                    # إنشاء العقد
                    contract = Contract()
                    contract.code = contract_data['code']
                    contract.customer_id = contract_data['customer']
                    contract.unit_id = contract_data['unit']
                    contract.unit_value = Decimal(str(contract_data['unit_value']))
                    contract.down_payment = Decimal(str(contract_data['down_payment']))
                    contract.installments_count = contract_data['installments_count']
                    contract.schedule_type = contract_data['schedule_type']
                    contract.start_date = contract_data['start_date']
                    if contract_data.get('partners_group'):
                        contract.partners_group_id = contract_data['partners_group']
                    
                    contract.save()
                    
                    # حذف البيانات من الجلسة
                    del request.session['contract_data']
                    if 'installments_preview' in request.session:
                        del request.session['installments_preview']
                    
                    messages.success(request, f'تم إنشاء العقد {contract.code} بنجاح')
                    return redirect('accounting:contract_detail', pk=contract.pk)
                    
                except Exception as e:
                    messages.error(request, f'خطأ في إنشاء العقد: {str(e)}')
                    return redirect('accounting:contract_create_wizard')
    
    else:
        # عرض الخطوة الأولى
        form = ContractForm()
        context = {
            'form': form,
            'step': '1',
        }
        return render(request, 'accounting/contracts/create_wizard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def contract_edit(request, pk):
    """تعديل عقد"""
    from ..forms.contracts import ContractForm
    
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            # التحقق من إمكانية التعديل
            if contract.installments.filter(status='PAID').exists():
                messages.warning(request, 'لا يمكن تعديل بيانات العقد الأساسية بعد دفع أقساط')
                return redirect('accounting:contract_detail', pk=contract.pk)
            
            contract = form.save()
            messages.success(request, f'تم تحديث العقد {contract.code} بنجاح')
            
            if request.htmx:
                return JsonResponse({
                    'message': f'تم تحديث العقد {contract.code} بنجاح',
                    'redirect': f'/accounting/contracts/{contract.pk}/'
                })
            
            return redirect('accounting:contract_detail', pk=contract.pk)
    else:
        form = ContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'title': f'تعديل العقد: {contract.code}'
    }
    
    if request.htmx:
        return render(request, 'accounting/contracts/_form.html', context)
    
    return render(request, 'accounting/contracts/form.html', context)


@login_required
def contract_detail(request, pk):
    """تفاصيل العقد"""
    contract = get_object_or_404(
        Contract.objects.select_related(
            'customer', 'unit', 'partners_group'
        ),
        pk=pk
    )
    
    # ملخص العقد
    summary = ContractService.get_contract_summary(contract)
    
    # الأقساط
    installments = contract.installments.order_by('seq_no')
    
    # سندات القبض المرتبطة
    receipts = contract.receipts.select_related('safe').order_by('-date')
    
    context = {
        'contract': contract,
        'summary': summary,
        'installments': installments,
        'receipts': receipts,
    }
    
    return render(request, 'accounting/contracts/detail.html', context)


@login_required
@require_http_methods(["POST"])
def contract_recalculate_installments(request, pk):
    """إعادة حساب الأقساط"""
    contract = get_object_or_404(Contract, pk=pk)
    
    try:
        # إعادة حساب الأقساط
        ContractService.recalculate_installments(contract)
        
        messages.success(request, 'تم إعادة حساب الأقساط بنجاح')
        
        if request.htmx:
            # إرجاع جدول الأقساط المحدث
            installments = contract.installments.order_by('seq_no')
            html = render_to_string('accounting/contracts/_installments_table.html', {
                'installments': installments,
                'contract': contract
            })
            return JsonResponse({
                'html': html,
                'message': 'تم إعادة حساب الأقساط بنجاح'
            })
    
    except Exception as e:
        messages.error(request, f'خطأ في إعادة حساب الأقساط: {str(e)}')
        
        if request.htmx:
            return JsonResponse({
                'message': f'خطأ في إعادة حساب الأقساط: {str(e)}'
            }, status=400)
    
    return redirect('accounting:contract_detail', pk=contract.pk)


@login_required
def contract_print(request, pk):
    """طباعة العقد"""
    contract = get_object_or_404(
        Contract.objects.select_related(
            'customer', 'unit', 'partners_group'
        ),
        pk=pk
    )
    
    # الأقساط
    installments = contract.installments.order_by('seq_no')
    
    context = {
        'contract': contract,
        'installments': installments,
    }
    
    return render(request, 'accounting/contracts/print.html', context)