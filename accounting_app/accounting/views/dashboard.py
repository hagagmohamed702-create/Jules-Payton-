from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import date, timedelta
from ..models import (
    ReceiptVoucher, PaymentVoucher, Installment,
    Contract, Customer, Unit, Project
)
from ..services import TreasuryService


@login_required
def dashboard_view(request):
    """عرض لوحة التحكم الرئيسية"""
    
    # حساب KPIs
    # إجمالي القبض
    total_receipts = ReceiptVoucher.objects.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # إجمالي الصرف
    total_payments = PaymentVoucher.objects.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # الرصيد الصافي
    net_balance = total_receipts - total_payments
    
    # عدد الأقساط المتأخرة
    late_installments_count = Installment.objects.filter(
        status='LATE'
    ).count()
    
    # إحصائيات إضافية
    # عدد العقود النشطة
    active_contracts = Contract.objects.count()
    
    # عدد العملاء
    total_customers = Customer.objects.filter(is_active=True).count()
    
    # عدد الوحدات المتاحة
    available_units = Unit.objects.filter(is_sold=False).count()
    
    # المشاريع الجارية
    ongoing_projects = Project.objects.filter(status='ongoing').count()
    
    # آخر 10 سندات قبض
    recent_receipts = ReceiptVoucher.objects.select_related(
        'customer', 'safe'
    ).order_by('-date', '-created_at')[:10]
    
    # آخر 10 سندات صرف
    recent_payments = PaymentVoucher.objects.select_related(
        'supplier', 'safe', 'project'
    ).order_by('-date', '-created_at')[:10]
    
    # الأقساط المستحقة خلال 7 أيام
    upcoming_installments = Installment.get_upcoming_installments(days=7)
    
    # المشاريع التي تجاوزت الميزانية
    over_budget_projects = []
    for project in Project.objects.filter(status='ongoing'):
        if project.is_over_budget():
            over_budget_projects.append({
                'project': project,
                'over_amount': project.get_total_expenses() - project.budget,
                'percentage': project.get_budget_percentage()
            })
    
    # بيانات الرسم البياني للإيرادات والمصروفات (آخر 12 شهر)
    chart_data = []
    for i in range(11, -1, -1):
        month_date = date.today().replace(day=1) - timedelta(days=i*30)
        month_start = month_date.replace(day=1)
        
        # حساب نهاية الشهر
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
        
        month_receipts = ReceiptVoucher.objects.filter(
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_payments = PaymentVoucher.objects.filter(
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        chart_data.append({
            'month': month_date.strftime('%Y-%m'),
            'receipts': float(month_receipts),
            'payments': float(month_payments)
        })
    
    context = {
        'total_receipts': total_receipts,
        'total_payments': total_payments,
        'net_balance': net_balance,
        'late_installments_count': late_installments_count,
        'active_contracts': active_contracts,
        'total_customers': total_customers,
        'available_units': available_units,
        'ongoing_projects': ongoing_projects,
        'recent_receipts': recent_receipts,
        'recent_payments': recent_payments,
        'upcoming_installments': upcoming_installments,
        'over_budget_projects': over_budget_projects,
        'chart_data': chart_data,
    }
    
    return render(request, 'accounting/dashboard.html', context)