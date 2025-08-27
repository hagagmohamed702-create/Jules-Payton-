from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Unit, Partner, PartnersGroup


def unit_list(request):
    """عرض قائمة الوحدات"""
    units = Unit.objects.select_related('partners_group').annotate(
        contracts_count=Count('contracts')
    )
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        units = units.filter(
            Q(name__icontains=search_query) |
            Q(building_number__icontains=search_query) |
            Q(unit_type__icontains=search_query)
        )
    
    # التصفية حسب النوع
    unit_type = request.GET.get('unit_type')
    if unit_type:
        units = units.filter(unit_type=unit_type)
    
    # التصفية حسب المجموعة
    unit_group = request.GET.get('unit_group')
    if unit_group:
        units = units.filter(unit_group=unit_group)
    
    # التصفية حسب حالة البيع
    is_sold = request.GET.get('is_sold')
    if is_sold == 'true':
        units = units.filter(contracts_count__gt=0)
    elif is_sold == 'false':
        units = units.filter(contracts_count=0)
    
    # الترتيب
    order_by = request.GET.get('order_by', '-created_at')
    units = units.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(units, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_units': Unit.objects.count(),
        'sold_units': Unit.objects.filter(contracts__isnull=False).distinct().count(),
        'available_units': Unit.objects.filter(contracts__isnull=True).count(),
        'total_value': Unit.objects.aggregate(total=Sum('total_price'))['total'] or 0
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'unit_type': unit_type,
        'unit_group': unit_group,
        'is_sold': is_sold,
        'stats': stats,
        'unit_types': Unit.UNIT_TYPES,
        'unit_groups': Unit.UNIT_GROUPS,
    }
    
    return render(request, 'accounting/units/unit_list.html', context)


def unit_detail(request, pk):
    """عرض تفاصيل الوحدة"""
    unit = get_object_or_404(
        Unit.objects.select_related('partners_group').prefetch_related(
            'contracts__customer',
            'partners_group__members__partner'
        ),
        pk=pk
    )
    
    # حساب توزيع الملكية
    ownership_distribution = []
    if unit.partners_group:
        for member in unit.partners_group.members.all():
            share_value = (member.share_percentage / 100) * unit.total_price
            ownership_distribution.append({
                'partner': member.partner,
                'percentage': member.share_percentage,
                'value': share_value
            })
    
    context = {
        'unit': unit,
        'ownership_distribution': ownership_distribution,
    }
    
    return render(request, 'accounting/units/unit_detail.html', context)


@require_http_methods(["GET", "POST"])
def unit_create(request):
    """إنشاء وحدة جديدة"""
    from ..forms.units import UnitForm
    
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'تم إنشاء الوحدة "{unit.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:unit_list')
            return redirect('accounting:unit_detail', pk=unit.pk)
    else:
        form = UnitForm()
    
    context = {
        'form': form,
        'partners_groups': PartnersGroup.objects.all(),
    }
    
    return render(request, 'accounting/units/unit_form.html', context)


@require_http_methods(["GET", "POST"])
def unit_update(request, pk):
    """تعديل وحدة"""
    from ..forms.units import UnitForm
    
    unit = get_object_or_404(Unit, pk=pk)
    
    # التحقق من وجود عقود
    if unit.contracts.exists():
        messages.error(request, 'لا يمكن تعديل وحدة مرتبطة بعقود.')
        return redirect('accounting:unit_detail', pk=unit.pk)
    
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'تم تحديث الوحدة "{unit.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:unit_list')
            return redirect('accounting:unit_detail', pk=unit.pk)
    else:
        form = UnitForm(instance=unit)
    
    context = {
        'form': form,
        'unit': unit,
        'partners_groups': PartnersGroup.objects.all(),
    }
    
    return render(request, 'accounting/units/unit_form.html', context)


@require_http_methods(["POST"])
def unit_delete(request, pk):
    """حذف وحدة"""
    unit = get_object_or_404(Unit, pk=pk)
    
    # التحقق من وجود عقود
    if unit.contracts.exists():
        messages.error(request, 'لا يمكن حذف وحدة مرتبطة بعقود.')
        return redirect('accounting:unit_detail', pk=unit.pk)
    
    unit_name = unit.name
    unit.delete()
    messages.success(request, f'تم حذف الوحدة "{unit_name}" بنجاح.')
    
    return redirect('accounting:unit_list')


def unit_search(request):
    """البحث عن الوحدات (AJAX)"""
    query = request.GET.get('q', '')
    available_only = request.GET.get('available_only', 'false') == 'true'
    
    units = Unit.objects.all()
    
    if query:
        units = units.filter(
            Q(name__icontains=query) |
            Q(building_number__icontains=query)
        )
    
    if available_only:
        units = units.filter(contracts__isnull=True)
    
    units = units[:10]  # Limit results
    
    data = [{
        'id': unit.id,
        'name': unit.name,
        'building_number': unit.building_number,
        'unit_type': unit.get_unit_type_display(),
        'total_price': str(unit.total_price),
        'is_available': not unit.contracts.exists()
    } for unit in units]
    
    return JsonResponse({'units': data})