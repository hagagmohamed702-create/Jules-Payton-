from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ..models import ReceiptVoucher, PaymentVoucher, Safe, Customer, Supplier, Contract, Project
from ..forms.vouchers import ReceiptVoucherForm, PaymentVoucherForm
from ..services.voucher_service import VoucherService


def voucher_list(request, voucher_type='receipt'):
    """عرض قائمة السندات"""
    if voucher_type == 'receipt':
        vouchers = ReceiptVoucher.objects.select_related('customer', 'contract', 'safe')
        model_class = ReceiptVoucher
    else:
        vouchers = PaymentVoucher.objects.select_related('supplier', 'project', 'safe')
        model_class = PaymentVoucher
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        if voucher_type == 'receipt':
            vouchers = vouchers.filter(
                Q(voucher_number__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        else:
            vouchers = vouchers.filter(
                Q(voucher_number__icontains=search_query) |
                Q(supplier__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
    
    # التصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        vouchers = vouchers.filter(payment_date__gte=date_from)
    if date_to:
        vouchers = vouchers.filter(payment_date__lte=date_to)
    
    # التصفية حسب المبلغ
    amount_from = request.GET.get('amount_from')
    amount_to = request.GET.get('amount_to')
    if amount_from:
        vouchers = vouchers.filter(amount__gte=amount_from)
    if amount_to:
        vouchers = vouchers.filter(amount__lte=amount_to)
    
    # التصفية حسب الخزينة
    safe_id = request.GET.get('safe_id')
    if safe_id:
        vouchers = vouchers.filter(safe_id=safe_id)
    
    # الترتيب
    order_by = request.GET.get('order_by', '-payment_date')
    vouchers = vouchers.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(vouchers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_count': model_class.objects.count(),
        'total_amount': model_class.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'today_count': model_class.objects.filter(payment_date=timezone.now().date()).count(),
        'today_amount': model_class.objects.filter(
            payment_date=timezone.now().date()
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'voucher_type': voucher_type,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'amount_from': amount_from,
        'amount_to': amount_to,
        'safe_id': safe_id,
        'stats': stats,
        'safes': Safe.objects.all(),
    }
    
    return render(request, 'accounting/vouchers/voucher_list.html', context)


def voucher_detail(request, voucher_type, pk):
    """عرض تفاصيل السند"""
    if voucher_type == 'receipt':
        voucher = get_object_or_404(
            ReceiptVoucher.objects.select_related(
                'customer',
                'contract__unit',
                'safe'
            ).prefetch_related(
                'installment_payments__installment'
            ),
            pk=pk
        )
    else:
        voucher = get_object_or_404(
            PaymentVoucher.objects.select_related(
                'supplier',
                'project',
                'safe'
            ),
            pk=pk
        )
    
    context = {
        'voucher': voucher,
        'voucher_type': voucher_type,
    }
    
    return render(request, 'accounting/vouchers/voucher_detail.html', context)


@require_http_methods(["GET", "POST"])
def receipt_voucher_create(request):
    """إنشاء سند قبض"""
    if request.method == 'POST':
        form = ReceiptVoucherForm(request.POST)
        if form.is_valid():
            try:
                voucher = VoucherService.create_receipt_voucher(
                    customer=form.cleaned_data['customer'],
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data['payment_date'],
                    safe=form.cleaned_data['safe'],
                    contract=form.cleaned_data.get('contract'),
                    notes=form.cleaned_data.get('notes', ''),
                    created_by=request.user
                )
                
                messages.success(
                    request,
                    f'تم إنشاء سند القبض رقم {voucher.voucher_number} بنجاح.'
                )
                
                # إذا كان هناك عقد، اسأل عن ربط السند بالأقساط
                if voucher.contract and voucher.contract.installments.filter(
                    status__in=['pending', 'partial']
                ).exists():
                    return redirect('accounting:link_voucher_installments', pk=voucher.pk)
                
                if request.headers.get('HX-Request'):
                    return redirect('accounting:voucher_list', voucher_type='receipt')
                return redirect('accounting:voucher_detail', voucher_type='receipt', pk=voucher.pk)
                
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = ReceiptVoucherForm()
    
    context = {
        'form': form,
        'voucher_type': 'receipt',
    }
    
    return render(request, 'accounting/vouchers/voucher_form.html', context)


@require_http_methods(["GET", "POST"])
def payment_voucher_create(request):
    """إنشاء سند صرف"""
    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST)
        if form.is_valid():
            try:
                voucher = VoucherService.create_payment_voucher(
                    supplier=form.cleaned_data.get('supplier'),
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data['payment_date'],
                    safe=form.cleaned_data['safe'],
                    project=form.cleaned_data.get('project'),
                    expense_type=form.cleaned_data.get('expense_type'),
                    notes=form.cleaned_data.get('notes', ''),
                    created_by=request.user
                )
                
                messages.success(
                    request,
                    f'تم إنشاء سند الصرف رقم {voucher.voucher_number} بنجاح.'
                )
                
                if request.headers.get('HX-Request'):
                    return redirect('accounting:voucher_list', voucher_type='payment')
                return redirect('accounting:voucher_detail', voucher_type='payment', pk=voucher.pk)
                
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = PaymentVoucherForm()
    
    context = {
        'form': form,
        'voucher_type': 'payment',
    }
    
    return render(request, 'accounting/vouchers/voucher_form.html', context)


@require_http_methods(["GET", "POST"])
def link_voucher_installments(request, pk):
    """ربط سند القبض بالأقساط"""
    voucher = get_object_or_404(
        ReceiptVoucher.objects.select_related('contract'),
        pk=pk
    )
    
    if not voucher.contract:
        messages.error(request, 'هذا السند غير مرتبط بعقد.')
        return redirect('accounting:voucher_detail', voucher_type='receipt', pk=voucher.pk)
    
    # الأقساط المستحقة
    pending_installments = voucher.contract.installments.filter(
        status__in=['pending', 'partial']
    ).order_by('installment_number')
    
    if request.method == 'POST':
        installment_ids = request.POST.getlist('installment_ids')
        
        if installment_ids:
            try:
                VoucherService.link_receipt_to_installments(
                    voucher,
                    installment_ids
                )
                
                messages.success(request, 'تم ربط السند بالأقساط بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
        else:
            messages.warning(request, 'لم يتم اختيار أي أقساط.')
        
        return redirect('accounting:voucher_detail', voucher_type='receipt', pk=voucher.pk)
    
    context = {
        'voucher': voucher,
        'pending_installments': pending_installments,
    }
    
    return render(request, 'accounting/vouchers/link_installments.html', context)


@require_http_methods(["POST"])
def voucher_cancel(request, voucher_type, pk):
    """إلغاء سند"""
    if voucher_type == 'receipt':
        voucher = get_object_or_404(ReceiptVoucher, pk=pk)
    else:
        voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    try:
        if voucher_type == 'receipt':
            VoucherService.cancel_receipt_voucher(voucher)
        else:
            VoucherService.cancel_payment_voucher(voucher)
        
        messages.success(request, f'تم إلغاء السند رقم {voucher.voucher_number}.')
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('accounting:voucher_list', voucher_type=voucher_type)


def voucher_print(request, voucher_type, pk):
    """طباعة سند"""
    if voucher_type == 'receipt':
        voucher = get_object_or_404(
            ReceiptVoucher.objects.select_related(
                'customer',
                'contract__unit',
                'safe'
            ),
            pk=pk
        )
    else:
        voucher = get_object_or_404(
            PaymentVoucher.objects.select_related(
                'supplier',
                'project',
                'safe'
            ),
            pk=pk
        )
    
    context = {
        'voucher': voucher,
        'voucher_type': voucher_type,
    }
    
    return render(request, 'accounting/vouchers/voucher_print.html', context)


def voucher_report(request):
    """تقرير السندات"""
    # الفترة الزمنية
    date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # سندات القبض
    receipt_vouchers = ReceiptVoucher.objects.filter(
        payment_date__gte=date_from,
        payment_date__lte=date_to
    )
    
    # سندات الصرف
    payment_vouchers = PaymentVoucher.objects.filter(
        payment_date__gte=date_from,
        payment_date__lte=date_to
    )
    
    # إحصائيات سندات القبض
    receipt_stats = {
        'count': receipt_vouchers.count(),
        'total': receipt_vouchers.aggregate(Sum('amount'))['amount__sum'] or 0,
        'by_customer': receipt_vouchers.values('customer__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:10],
    }
    
    # إحصائيات سندات الصرف
    payment_stats = {
        'count': payment_vouchers.count(),
        'total': payment_vouchers.aggregate(Sum('amount'))['amount__sum'] or 0,
        'by_supplier': payment_vouchers.values('supplier__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:10],
        'by_type': payment_vouchers.values('expense_type').annotate(
            total=Sum('amount')
        ).order_by('-total'),
    }
    
    # صافي الحركة
    net_amount = receipt_stats['total'] - payment_stats['total']
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'receipt_stats': receipt_stats,
        'payment_stats': payment_stats,
        'net_amount': net_amount,
    }
    
    return render(request, 'accounting/vouchers/voucher_report.html', context)