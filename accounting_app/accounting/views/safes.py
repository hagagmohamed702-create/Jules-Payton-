from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Q
from ..models import Safe
from ..services import TreasuryService


@login_required
def safes_list(request):
    """قائمة الخزائن والمحافظ"""
    search_query = request.GET.get('search', '')
    filter_type = request.GET.get('type', 'all')
    
    safes = Safe.objects.select_related('partner')
    
    if search_query:
        safes = safes.filter(
            Q(name__icontains=search_query) |
            Q(partner__name__icontains=search_query)
        )
    
    if filter_type == 'wallet':
        safes = safes.filter(is_partner_wallet=True)
    elif filter_type == 'safe':
        safes = safes.filter(is_partner_wallet=False)
    
    safes = safes.order_by('name')
    
    # حساب الرصيد لكل خزنة
    for safe in safes:
        balance_data = TreasuryService.get_safe_balance(safe)
        safe.current_balance = balance_data['balance']
        safe.total_receipts = balance_data['receipts']
        safe.total_payments = balance_data['payments']
    
    context = {
        'safes': safes,
        'search_query': search_query,
        'filter_type': filter_type,
    }
    
    if request.htmx:
        return render(request, 'accounting/safes/_table.html', context)
    
    return render(request, 'accounting/safes/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def safe_create(request):
    """إنشاء خزنة/محفظة جديدة"""
    from ..forms.safes import SafeForm
    
    if request.method == 'POST':
        form = SafeForm(request.POST)
        if form.is_valid():
            safe = form.save()
            messages.success(request, f'تم إنشاء {safe.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف الجديد للجدول
                balance_data = TreasuryService.get_safe_balance(safe)
                safe.current_balance = balance_data['balance']
                safe.total_receipts = balance_data['receipts']
                safe.total_payments = balance_data['payments']
                
                html = render_to_string('accounting/safes/_row.html', {'safe': safe})
                return JsonResponse({
                    'html': html,
                    'message': f'تم إنشاء {safe.name} بنجاح'
                })
            
            return redirect('accounting:safes_list')
    else:
        form = SafeForm()
    
    context = {'form': form, 'title': 'إضافة خزنة/محفظة جديدة'}
    
    if request.htmx:
        return render(request, 'accounting/safes/_form.html', context)
    
    return render(request, 'accounting/safes/form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def safe_edit(request, pk):
    """تعديل خزنة/محفظة"""
    from ..forms.safes import SafeForm
    
    safe = get_object_or_404(Safe, pk=pk)
    
    if request.method == 'POST':
        form = SafeForm(request.POST, instance=safe)
        if form.is_valid():
            safe = form.save()
            messages.success(request, f'تم تحديث {safe.name} بنجاح')
            
            if request.htmx:
                # إرجاع الصف المحدث
                balance_data = TreasuryService.get_safe_balance(safe)
                safe.current_balance = balance_data['balance']
                safe.total_receipts = balance_data['receipts']
                safe.total_payments = balance_data['payments']
                
                html = render_to_string('accounting/safes/_row.html', {'safe': safe})
                return JsonResponse({
                    'html': html,
                    'message': f'تم تحديث {safe.name} بنجاح'
                })
            
            return redirect('accounting:safes_list')
    else:
        form = SafeForm(instance=safe)
    
    context = {
        'form': form,
        'safe': safe,
        'title': f'تعديل: {safe.name}'
    }
    
    if request.htmx:
        return render(request, 'accounting/safes/_form.html', context)
    
    return render(request, 'accounting/safes/form.html', context)


@login_required
def safe_detail(request, pk):
    """تفاصيل الخزنة/المحفظة"""
    safe = get_object_or_404(Safe, pk=pk)
    
    # الرصيد الحالي
    balance_data = TreasuryService.get_safe_balance(safe)
    
    # التدفق النقدي
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    cash_flow = TreasuryService.get_cash_flow(
        from_date=from_date,
        to_date=to_date,
        safe=safe
    )
    
    context = {
        'safe': safe,
        'balance_data': balance_data,
        'cash_flow': cash_flow,
        'from_date': from_date,
        'to_date': to_date,
    }
    
    return render(request, 'accounting/safes/detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def safe_transfer(request):
    """تحويل بين الخزائن"""
    if request.method == 'POST':
        from_safe_id = request.POST.get('from_safe')
        to_safe_id = request.POST.get('to_safe')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        
        try:
            from_safe = Safe.objects.get(pk=from_safe_id)
            to_safe = Safe.objects.get(pk=to_safe_id)
            amount = Decimal(amount)
            
            # تنفيذ التحويل
            result = TreasuryService.transfer_between_safes(
                from_safe=from_safe,
                to_safe=to_safe,
                amount=amount,
                description=description,
                user=request.user
            )
            
            messages.success(
                request,
                f'تم التحويل بنجاح: {amount} من {from_safe.name} إلى {to_safe.name}'
            )
            
            if request.htmx:
                return JsonResponse({
                    'success': True,
                    'message': f'تم التحويل بنجاح',
                    'payment_voucher': result['payment_voucher'].voucher_number,
                    'receipt_voucher': result['receipt_voucher'].voucher_number
                })
            
            return redirect('accounting:safes_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في التحويل: {str(e)}')
            
            if request.htmx:
                return JsonResponse({
                    'success': False,
                    'message': f'خطأ في التحويل: {str(e)}'
                }, status=400)
    
    safes = Safe.objects.all()
    context = {
        'safes': safes,
        'title': 'تحويل بين الخزائن'
    }
    
    if request.htmx:
        return render(request, 'accounting/safes/_transfer_form.html', context)
    
    return render(request, 'accounting/safes/transfer.html', context)