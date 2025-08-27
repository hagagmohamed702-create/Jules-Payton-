from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ..models import Settlement, Partner, PartnersGroup
from ..services.settlement_service import SettlementService


def settlement_list(request):
    """عرض قائمة التسويات"""
    settlements = Settlement.objects.select_related(
        'from_partner',
        'to_partner',
        'partners_group'
    ).order_by('-created_at')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        settlements = settlements.filter(
            Q(from_partner__name__icontains=search_query) |
            Q(to_partner__name__icontains=search_query) |
            Q(settlement_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # التصفية حسب المجموعة
    group_id = request.GET.get('group_id')
    if group_id:
        settlements = settlements.filter(partners_group_id=group_id)
    
    # التصفية حسب الحالة
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(status=status)
    
    # التصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        settlements = settlements.filter(settlement_date__gte=date_from)
    if date_to:
        settlements = settlements.filter(settlement_date__lte=date_to)
    
    # الصفحات
    paginator = Paginator(settlements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_settlements': Settlement.objects.count(),
        'pending_settlements': Settlement.objects.filter(status='pending').count(),
        'completed_settlements': Settlement.objects.filter(status='completed').count(),
        'total_amount': Settlement.objects.aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'group_id': group_id,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'stats': stats,
        'partners_groups': PartnersGroup.objects.all(),
        'statuses': Settlement.STATUS_CHOICES,
    }
    
    return render(request, 'accounting/settlements/settlement_list.html', context)


def settlement_detail(request, pk):
    """عرض تفاصيل التسوية"""
    settlement = get_object_or_404(
        Settlement.objects.select_related(
            'from_partner',
            'to_partner',
            'partners_group'
        ),
        pk=pk
    )
    
    context = {
        'settlement': settlement,
    }
    
    return render(request, 'accounting/settlements/settlement_detail.html', context)


@require_http_methods(["GET", "POST"])
def settlement_create(request):
    """إنشاء تسوية يدوية"""
    from ..forms.settlements import SettlementForm
    
    if request.method == 'POST':
        form = SettlementForm(request.POST)
        if form.is_valid():
            settlement = form.save(commit=False)
            settlement.created_by = request.user
            settlement.save()
            
            messages.success(
                request,
                f'تم إنشاء التسوية رقم {settlement.settlement_number} بنجاح.'
            )
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:settlement_list')
            return redirect('accounting:settlement_detail', pk=settlement.pk)
    else:
        form = SettlementForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounting/settlements/settlement_form.html', context)


@require_http_methods(["POST"])
def settlement_execute(request, pk):
    """تنفيذ التسوية"""
    settlement = get_object_or_404(Settlement, pk=pk)
    
    if settlement.status != 'pending':
        messages.error(request, 'هذه التسوية تم تنفيذها مسبقاً.')
        return redirect('accounting:settlement_detail', pk=settlement.pk)
    
    try:
        # تنفيذ التسوية
        SettlementService.execute_settlement(settlement)
        
        messages.success(request, 'تم تنفيذ التسوية بنجاح.')
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('accounting:settlement_detail', pk=settlement.pk)


@require_http_methods(["POST"])
def settlement_cancel(request, pk):
    """إلغاء التسوية"""
    settlement = get_object_or_404(Settlement, pk=pk)
    
    if settlement.status == 'completed':
        messages.error(request, 'لا يمكن إلغاء تسوية منفذة.')
        return redirect('accounting:settlement_detail', pk=settlement.pk)
    
    settlement.status = 'cancelled'
    settlement.save()
    
    messages.success(request, 'تم إلغاء التسوية.')
    
    return redirect('accounting:settlement_detail', pk=settlement.pk)


def calculate_settlements(request):
    """حساب التسويات المطلوبة"""
    group_id = request.GET.get('group_id')
    
    if not group_id:
        messages.error(request, 'يرجى اختيار مجموعة شركاء.')
        return redirect('accounting:settlement_list')
    
    group = get_object_or_404(PartnersGroup, pk=group_id)
    
    # حساب التسويات المطلوبة
    settlements_data = SettlementService.calculate_settlements(group)
    
    # عرض النتائج
    context = {
        'group': group,
        'settlements_data': settlements_data,
        'can_create': settlements_data['settlements_needed'],
    }
    
    return render(request, 'accounting/settlements/calculate_settlements.html', context)


@require_http_methods(["POST"])
def create_auto_settlements(request):
    """إنشاء التسويات تلقائياً"""
    group_id = request.POST.get('group_id')
    
    if not group_id:
        messages.error(request, 'يرجى اختيار مجموعة شركاء.')
        return redirect('accounting:settlement_list')
    
    group = get_object_or_404(PartnersGroup, pk=group_id)
    
    try:
        # إنشاء التسويات
        settlements = SettlementService.create_settlements(group, request.user)
        
        if settlements:
            messages.success(
                request,
                f'تم إنشاء {len(settlements)} تسوية بنجاح.'
            )
        else:
            messages.info(request, 'لا توجد تسويات مطلوبة.')
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('accounting:settlement_list')


def partner_settlements(request, partner_id):
    """عرض تسويات شريك معين"""
    partner = get_object_or_404(Partner, pk=partner_id)
    
    settlements = Settlement.objects.filter(
        Q(from_partner=partner) | Q(to_partner=partner)
    ).select_related(
        'from_partner',
        'to_partner',
        'partners_group'
    ).order_by('-created_at')
    
    # حساب الإحصائيات
    stats = {
        'total_received': settlements.filter(
            to_partner=partner,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_paid': settlements.filter(
            from_partner=partner,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_to_receive': settlements.filter(
            to_partner=partner,
            status='pending'
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_to_pay': settlements.filter(
            from_partner=partner,
            status='pending'
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    context = {
        'partner': partner,
        'settlements': settlements,
        'stats': stats,
    }
    
    return render(request, 'accounting/settlements/partner_settlements.html', context)


def settlement_report(request):
    """تقرير التسويات"""
    # الفترة الزمنية
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    settlements = Settlement.objects.all()
    
    if date_from:
        settlements = settlements.filter(settlement_date__gte=date_from)
    if date_to:
        settlements = settlements.filter(settlement_date__lte=date_to)
    
    # تجميع حسب المجموعة
    group_stats = {}
    for settlement in settlements:
        group = settlement.partners_group
        if group.id not in group_stats:
            group_stats[group.id] = {
                'group': group,
                'count': 0,
                'total_amount': 0,
                'completed': 0,
                'pending': 0,
            }
        
        group_stats[group.id]['count'] += 1
        group_stats[group.id]['total_amount'] += settlement.amount
        
        if settlement.status == 'completed':
            group_stats[group.id]['completed'] += 1
        elif settlement.status == 'pending':
            group_stats[group.id]['pending'] += 1
    
    # إحصائيات عامة
    general_stats = {
        'total_settlements': settlements.count(),
        'total_amount': settlements.aggregate(Sum('amount'))['amount__sum'] or 0,
        'completed_count': settlements.filter(status='completed').count(),
        'pending_count': settlements.filter(status='pending').count(),
        'cancelled_count': settlements.filter(status='cancelled').count(),
    }
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'group_stats': group_stats.values(),
        'general_stats': general_stats,
    }
    
    return render(request, 'accounting/settlements/settlement_report.html', context)