from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Supplier
from ..forms.suppliers import SupplierForm


def supplier_list(request):
    """عرض قائمة الموردين"""
    suppliers = Supplier.objects.annotate(
        payments_count=Count('payment_vouchers'),
        total_payments=Sum('payment_vouchers__amount')
    )
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    # التصفية حسب النوع
    supplier_type = request.GET.get('supplier_type')
    if supplier_type:
        suppliers = suppliers.filter(supplier_type=supplier_type)
    
    # التصفية حسب الحالة
    is_active = request.GET.get('is_active')
    if is_active == 'true':
        suppliers = suppliers.filter(is_active=True)
    elif is_active == 'false':
        suppliers = suppliers.filter(is_active=False)
    
    # الترتيب
    order_by = request.GET.get('order_by', '-created_at')
    suppliers = suppliers.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_suppliers': Supplier.objects.count(),
        'active_suppliers': Supplier.objects.filter(is_active=True).count(),
        'total_payments': Supplier.objects.aggregate(
            total=Sum('payment_vouchers__amount')
        )['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'supplier_type': supplier_type,
        'is_active': is_active,
        'stats': stats,
        'supplier_types': Supplier.SUPPLIER_TYPES,
    }
    
    return render(request, 'accounting/suppliers/supplier_list.html', context)


def supplier_detail(request, pk):
    """عرض تفاصيل المورد"""
    supplier = get_object_or_404(
        Supplier.objects.prefetch_related(
            'payment_vouchers__project',
            'items'
        ),
        pk=pk
    )
    
    # آخر المعاملات
    recent_payments = supplier.payment_vouchers.select_related('project')[:10]
    
    # إحصائيات المورد
    stats = {
        'total_payments': supplier.payment_vouchers.aggregate(Sum('amount'))['amount__sum'] or 0,
        'payments_count': supplier.payment_vouchers.count(),
        'items_count': supplier.items.count(),
    }
    
    context = {
        'supplier': supplier,
        'recent_payments': recent_payments,
        'stats': stats,
    }
    
    return render(request, 'accounting/suppliers/supplier_detail.html', context)


@require_http_methods(["GET", "POST"])
def supplier_create(request):
    """إنشاء مورد جديد"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'تم إنشاء المورد "{supplier.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:supplier_list')
            return redirect('accounting:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounting/suppliers/supplier_form.html', context)


@require_http_methods(["GET", "POST"])
def supplier_update(request, pk):
    """تعديل مورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'تم تحديث المورد "{supplier.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:supplier_list')
            return redirect('accounting:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
    }
    
    return render(request, 'accounting/suppliers/supplier_form.html', context)


@require_http_methods(["POST"])
def supplier_delete(request, pk):
    """حذف مورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # التحقق من وجود معاملات
    if supplier.payment_vouchers.exists():
        messages.error(request, 'لا يمكن حذف مورد له معاملات مالية.')
        return redirect('accounting:supplier_detail', pk=supplier.pk)
    
    supplier_name = supplier.name
    supplier.delete()
    messages.success(request, f'تم حذف المورد "{supplier_name}" بنجاح.')
    
    return redirect('accounting:supplier_list')


@require_http_methods(["POST"])
def supplier_toggle_active(request, pk):
    """تغيير حالة المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save()
    
    status = 'مفعل' if supplier.is_active else 'معطل'
    messages.success(request, f'تم {status} المورد "{supplier.name}".')
    
    if request.headers.get('HX-Request'):
        return render(request, 'accounting/suppliers/_supplier_row.html', {'supplier': supplier})
    
    return redirect('accounting:supplier_detail', pk=supplier.pk)


def supplier_search(request):
    """البحث عن الموردين (AJAX)"""
    query = request.GET.get('q', '')
    active_only = request.GET.get('active_only', 'true') == 'true'
    
    suppliers = Supplier.objects.all()
    
    if active_only:
        suppliers = suppliers.filter(is_active=True)
    
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(phone__icontains=query)
        )
    
    suppliers = suppliers[:10]  # Limit results
    
    data = [{
        'id': supplier.id,
        'name': supplier.name,
        'company_name': supplier.company_name,
        'phone': supplier.phone,
        'supplier_type': supplier.get_supplier_type_display(),
        'is_active': supplier.is_active
    } for supplier in suppliers]
    
    return JsonResponse({'suppliers': data})