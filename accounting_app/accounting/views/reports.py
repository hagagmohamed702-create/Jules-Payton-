from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta
import json
from ..models import (
    Contract, Installment, ReceiptVoucher, PaymentVoucher,
    Safe, Partner, Customer, Unit, Project, Item
)


@login_required
def reports_dashboard(request):
    """لوحة التقارير الرئيسية"""
    context = {
        'report_types': [
            {
                'name': 'تقرير الأقساط',
                'description': 'عرض حالة الأقساط والمدفوعات',
                'url': 'accounting:installments_report',
                'icon': 'fa-calendar-check'
            },
            {
                'name': 'تقرير الخزينة',
                'description': 'حركة وأرصدة الخزائن',
                'url': 'accounting:treasury_report',
                'icon': 'fa-vault'
            },
            {
                'name': 'تقرير المحافظ',
                'description': 'أرصدة الشركاء ومحافظهم',
                'url': 'accounting:wallets_report',
                'icon': 'fa-wallet'
            },
            {
                'name': 'تقرير المشاريع',
                'description': 'حالة المشاريع والميزانيات',
                'url': 'accounting:projects_report',
                'icon': 'fa-project-diagram'
            },
            {
                'name': 'تقرير المخزون',
                'description': 'حركة وأرصدة المخزون',
                'url': 'accounting:inventory_full_report',
                'icon': 'fa-warehouse'
            },
            {
                'name': 'تقرير مالي شامل',
                'description': 'ملخص مالي شامل للنظام',
                'url': 'accounting:financial_summary',
                'icon': 'fa-chart-line'
            }
        ]
    }
    
    return render(request, 'accounting/reports/dashboard.html', context)


@login_required
def installments_report(request):
    """تقرير الأقساط المفصل"""
    
    # الفلاتر
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    customer_id = request.GET.get('customer_id')
    
    # الاستعلام الأساسي
    installments = Installment.objects.select_related(
        'contract__customer',
        'contract__unit'
    ).annotate(
        remaining=F('amount') - F('paid_amount')
    )
    
    # تطبيق الفلاتر
    if date_from:
        installments = installments.filter(due_date__gte=date_from)
    if date_to:
        installments = installments.filter(due_date__lte=date_to)
    if status:
        installments = installments.filter(status=status)
    if customer_id:
        installments = installments.filter(contract__customer_id=customer_id)
    
    # الإحصائيات
    stats = {
        'total_amount': installments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'paid_amount': installments.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
        'remaining_amount': installments.aggregate(Sum('remaining'))['remaining__sum'] or 0,
        'total_count': installments.count(),
        'paid_count': installments.filter(status='paid').count(),
        'pending_count': installments.filter(status='pending').count(),
        'partial_count': installments.filter(status='partial').count(),
    }
    
    # الأقساط المتأخرة
    today = timezone.now().date()
    overdue_installments = installments.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    )
    
    stats['overdue_count'] = overdue_installments.count()
    stats['overdue_amount'] = overdue_installments.aggregate(
        Sum('remaining')
    )['remaining__sum'] or 0
    
    # تجميع حسب الشهر
    monthly_data = []
    if installments.exists():
        # الحصول على نطاق التواريخ
        min_date = installments.order_by('due_date').first().due_date
        max_date = installments.order_by('-due_date').first().due_date
        
        current_date = min_date.replace(day=1)
        while current_date <= max_date:
            month_installments = installments.filter(
                due_date__year=current_date.year,
                due_date__month=current_date.month
            )
            
            monthly_data.append({
                'month': current_date.strftime('%Y-%m'),
                'month_name': current_date.strftime('%B %Y'),
                'total': month_installments.aggregate(Sum('amount'))['amount__sum'] or 0,
                'paid': month_installments.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
                'count': month_installments.count()
            })
            
            # الانتقال للشهر التالي
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    # أعلى العملاء ديوناً
    top_debtors = Customer.objects.annotate(
        total_debt=Sum(
            'contracts__installments__amount',
            filter=Q(contracts__installments__status__in=['pending', 'partial'])
        ) - Sum(
            'contracts__installments__paid_amount',
            filter=Q(contracts__installments__status__in=['pending', 'partial'])
        )
    ).filter(total_debt__gt=0).order_by('-total_debt')[:10]
    
    context = {
        'stats': stats,
        'monthly_data': json.dumps(monthly_data),
        'top_debtors': top_debtors,
        'customers': Customer.objects.filter(is_active=True),
        'statuses': Installment.STATUS_CHOICES,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'status': status,
            'customer_id': customer_id,
        }
    }
    
    return render(request, 'accounting/reports/installments_report.html', context)


@login_required
def treasury_report(request):
    """تقرير الخزينة"""
    
    # الفلاتر
    date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
    date_to = request.GET.get('date_to', timezone.now().date())
    safe_id = request.GET.get('safe_id')
    
    # الخزائن
    safes = Safe.objects.all()
    if safe_id:
        safes = safes.filter(id=safe_id)
    
    # بيانات الخزائن
    safes_data = []
    for safe in safes:
        # سندات القبض
        receipts = ReceiptVoucher.objects.filter(
            safe=safe,
            payment_date__gte=date_from,
            payment_date__lte=date_to,
            is_cancelled=False
        )
        
        # سندات الصرف
        payments = PaymentVoucher.objects.filter(
            safe=safe,
            payment_date__gte=date_from,
            payment_date__lte=date_to,
            is_cancelled=False
        )
        
        total_receipts = receipts.aggregate(Sum('amount'))['amount__sum'] or 0
        total_payments = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        safes_data.append({
            'safe': safe,
            'total_receipts': total_receipts,
            'total_payments': total_payments,
            'net_movement': total_receipts - total_payments,
            'receipts_count': receipts.count(),
            'payments_count': payments.count(),
        })
    
    # إجمالي جميع الخزائن
    total_stats = {
        'total_receipts': sum(s['total_receipts'] for s in safes_data),
        'total_payments': sum(s['total_payments'] for s in safes_data),
        'total_balance': sum(s['safe'].balance for s in safes_data),
        'net_movement': sum(s['net_movement'] for s in safes_data),
    }
    
    # الحركة اليومية
    daily_movements = []
    current_date = date_from
    while current_date <= date_to:
        day_receipts = ReceiptVoucher.objects.filter(
            payment_date=current_date,
            is_cancelled=False
        )
        if safe_id:
            day_receipts = day_receipts.filter(safe_id=safe_id)
        
        day_payments = PaymentVoucher.objects.filter(
            payment_date=current_date,
            is_cancelled=False
        )
        if safe_id:
            day_payments = day_payments.filter(safe_id=safe_id)
        
        receipts_total = day_receipts.aggregate(Sum('amount'))['amount__sum'] or 0
        payments_total = day_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        daily_movements.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'receipts': receipts_total,
            'payments': payments_total,
            'net': receipts_total - payments_total
        })
        
        current_date += timedelta(days=1)
    
    context = {
        'safes_data': safes_data,
        'total_stats': total_stats,
        'daily_movements': json.dumps(daily_movements),
        'all_safes': Safe.objects.all(),
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'safe_id': safe_id,
        }
    }
    
    return render(request, 'accounting/reports/treasury_report.html', context)


@login_required
def wallets_report(request):
    """تقرير المحافظ والشركاء"""
    
    # الشركاء مع أرصدتهم
    partners = Partner.objects.annotate(
        total_receipts=Sum(
            'groups__contracts__receipt_vouchers__amount',
            filter=Q(groups__contracts__receipt_vouchers__is_cancelled=False)
        ),
        total_payments=Sum(
            'user__payment_vouchers__amount',
            filter=Q(user__payment_vouchers__is_cancelled=False)
        )
    )
    
    partners_data = []
    for partner in partners:
        # حساب نصيب الشريك من الإيرادات
        partner_share = 0
        for group in partner.groups.all():
            member = group.members.filter(partner=partner).first()
            if member:
                group_receipts = ReceiptVoucher.objects.filter(
                    contract__partners_group=group,
                    is_cancelled=False
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                partner_share += (member.share_percentage / 100) * group_receipts
        
        partners_data.append({
            'partner': partner,
            'share_income': partner_share,
            'direct_expenses': partner.total_payments or 0,
            'balance': partner.balance,
            'groups_count': partner.groups.count()
        })
    
    # الإحصائيات الإجمالية
    total_stats = {
        'total_balance': sum(p['balance'] for p in partners_data),
        'total_income': sum(p['share_income'] for p in partners_data),
        'total_expenses': sum(p['direct_expenses'] for p in partners_data),
    }
    
    context = {
        'partners_data': partners_data,
        'total_stats': total_stats,
    }
    
    return render(request, 'accounting/reports/wallets_report.html', context)


@login_required
def projects_report(request):
    """تقرير المشاريع"""
    
    # الفلاتر
    status = request.GET.get('status')
    project_type = request.GET.get('project_type')
    
    # المشاريع
    projects = Project.objects.annotate(
        total_expenses=Sum('payment_vouchers__amount'),
        expenses_percentage=F('total_expenses') * 100.0 / F('budget'),
        materials_cost=Sum(
            F('stock_moves__quantity') * F('stock_moves__item__unit_price')
        )
    )
    
    if status:
        projects = projects.filter(status=status)
    if project_type:
        projects = projects.filter(project_type=project_type)
    
    # الإحصائيات
    stats = {
        'total_projects': projects.count(),
        'active_projects': projects.filter(status='in_progress').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'total_budget': projects.aggregate(Sum('budget'))['budget__sum'] or 0,
        'total_expenses': projects.aggregate(Sum('total_expenses'))['total_expenses__sum'] or 0,
    }
    
    # المشاريع التي تجاوزت الميزانية
    over_budget_projects = projects.filter(
        total_expenses__gt=F('budget')
    )
    
    # تحليل حسب نوع المشروع
    type_analysis = []
    for ptype, ptype_name in Project.PROJECT_TYPES:
        type_projects = projects.filter(project_type=ptype)
        type_analysis.append({
            'type': ptype_name,
            'count': type_projects.count(),
            'total_budget': type_projects.aggregate(Sum('budget'))['budget__sum'] or 0,
            'total_expenses': type_projects.aggregate(Sum('total_expenses'))['total_expenses__sum'] or 0,
        })
    
    context = {
        'projects': projects,
        'stats': stats,
        'over_budget_projects': over_budget_projects,
        'type_analysis': type_analysis,
        'project_types': Project.PROJECT_TYPES,
        'statuses': Project.STATUS_CHOICES,
        'filters': {
            'status': status,
            'project_type': project_type,
        }
    }
    
    return render(request, 'accounting/reports/projects_report.html', context)


@login_required
def inventory_full_report(request):
    """تقرير المخزون الشامل"""
    
    # الأصناف
    items = Item.objects.annotate(
        stock_value=F('current_stock') * F('unit_price'),
        total_in=Sum(
            'stock_moves__quantity',
            filter=Q(stock_moves__move_type='in')
        ),
        total_out=Sum(
            'stock_moves__quantity',
            filter=Q(stock_moves__move_type='out')
        )
    )
    
    # الإحصائيات
    stats = {
        'total_items': items.count(),
        'total_value': items.aggregate(Sum('stock_value'))['stock_value__sum'] or 0,
        'low_stock_items': items.filter(current_stock__lte=F('minimum_stock')).count(),
        'out_of_stock': items.filter(current_stock=0).count(),
    }
    
    # أعلى الأصناف قيمة
    top_value_items = items.order_by('-stock_value')[:10]
    
    # أكثر الأصناف حركة
    most_active_items = Item.objects.annotate(
        moves_count=Count('stock_moves')
    ).order_by('-moves_count')[:10]
    
    # الأصناف المنخفضة
    low_stock_items = items.filter(
        current_stock__lte=F('minimum_stock')
    ).order_by('current_stock')
    
    context = {
        'stats': stats,
        'top_value_items': top_value_items,
        'most_active_items': most_active_items,
        'low_stock_items': low_stock_items,
    }
    
    return render(request, 'accounting/reports/inventory_full_report.html', context)


@login_required
def financial_summary(request):
    """التقرير المالي الشامل"""
    
    # الفترة الزمنية
    date_from = request.GET.get('date_from', timezone.now().date().replace(day=1))
    date_to = request.GET.get('date_to', timezone.now().date())
    
    # الإيرادات
    total_receipts = ReceiptVoucher.objects.filter(
        payment_date__gte=date_from,
        payment_date__lte=date_to,
        is_cancelled=False
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # المصروفات
    total_payments = PaymentVoucher.objects.filter(
        payment_date__gte=date_from,
        payment_date__lte=date_to,
        is_cancelled=False
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # صافي الربح
    net_profit = total_receipts - total_payments
    
    # تحليل المصروفات حسب النوع
    expenses_by_type = PaymentVoucher.objects.filter(
        payment_date__gte=date_from,
        payment_date__lte=date_to,
        is_cancelled=False
    ).values('expense_type').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # العقود والوحدات
    contracts_stats = {
        'total_contracts': Contract.objects.count(),
        'active_contracts': Contract.objects.filter(
            installments__status__in=['pending', 'partial']
        ).distinct().count(),
        'total_units_value': Unit.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'sold_units': Unit.objects.filter(contracts__isnull=False).distinct().count(),
        'available_units': Unit.objects.filter(contracts__isnull=True).count(),
    }
    
    # الأقساط
    installments_stats = {
        'total_amount': Installment.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'collected_amount': Installment.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
        'remaining_amount': Installment.objects.filter(
            status__in=['pending', 'partial']
        ).aggregate(
            total=Sum(F('amount') - F('paid_amount'))
        )['total'] or 0,
    }
    
    # أداء الشهور
    monthly_performance = []
    current_date = date_from.replace(day=1)
    while current_date <= date_to:
        month_end = (current_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_receipts = ReceiptVoucher.objects.filter(
            payment_date__gte=current_date,
            payment_date__lte=month_end,
            is_cancelled=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        month_payments = PaymentVoucher.objects.filter(
            payment_date__gte=current_date,
            payment_date__lte=month_end,
            is_cancelled=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_performance.append({
            'month': current_date.strftime('%Y-%m'),
            'month_name': current_date.strftime('%B %Y'),
            'receipts': month_receipts,
            'payments': month_payments,
            'profit': month_receipts - month_payments
        })
        
        # الانتقال للشهر التالي
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    context = {
        'total_receipts': total_receipts,
        'total_payments': total_payments,
        'net_profit': net_profit,
        'expenses_by_type': expenses_by_type,
        'contracts_stats': contracts_stats,
        'installments_stats': installments_stats,
        'monthly_performance': json.dumps(monthly_performance),
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'accounting/reports/financial_summary.html', context)