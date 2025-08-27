from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ..models import Project, PaymentVoucher, StockMove


def project_list(request):
    """عرض قائمة المشاريع"""
    projects = Project.objects.annotate(
        expenses_total=Sum('payment_vouchers__amount'),
        materials_count=Count('stock_moves', distinct=True),
        budget_percentage=F('expenses_total') * 100.0 / F('budget')
    )
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # التصفية حسب النوع
    project_type = request.GET.get('project_type')
    if project_type:
        projects = projects.filter(project_type=project_type)
    
    # التصفية حسب الحالة
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    
    # الترتيب
    order_by = request.GET.get('order_by', '-created_at')
    projects = projects.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(projects, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_projects': Project.objects.count(),
        'active_projects': Project.objects.filter(status='in_progress').count(),
        'completed_projects': Project.objects.filter(status='completed').count(),
        'total_budget': Project.objects.aggregate(total=Sum('budget'))['total'] or 0,
        'total_expenses': PaymentVoucher.objects.filter(
            project__isnull=False
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'project_type': project_type,
        'status': status,
        'stats': stats,
        'project_types': Project.PROJECT_TYPES,
        'statuses': Project.STATUS_CHOICES,
    }
    
    return render(request, 'accounting/projects/project_list.html', context)


def project_detail(request, pk):
    """عرض تفاصيل المشروع"""
    project = get_object_or_404(
        Project.objects.prefetch_related(
            'payment_vouchers__supplier',
            'stock_moves__item'
        ),
        pk=pk
    )
    
    # حساب الإحصائيات
    total_expenses = project.payment_vouchers.aggregate(Sum('amount'))['amount__sum'] or 0
    budget_remaining = project.budget - total_expenses
    budget_percentage = (total_expenses / project.budget * 100) if project.budget > 0 else 0
    
    # تجميع المصروفات حسب النوع
    expenses_by_type = {}
    for voucher in project.payment_vouchers.all():
        expense_type = voucher.expense_type or 'أخرى'
        if expense_type not in expenses_by_type:
            expenses_by_type[expense_type] = {
                'amount': 0,
                'count': 0,
                'vouchers': []
            }
        expenses_by_type[expense_type]['amount'] += voucher.amount
        expenses_by_type[expense_type]['count'] += 1
        expenses_by_type[expense_type]['vouchers'].append(voucher)
    
    # المواد المستخدمة
    materials_used = project.stock_moves.select_related('item').order_by('-created_at')
    
    # حساب مدة المشروع
    project_duration = None
    if project.start_date:
        end_date = project.end_date or timezone.now().date()
        project_duration = (end_date - project.start_date).days
    
    context = {
        'project': project,
        'total_expenses': total_expenses,
        'budget_remaining': budget_remaining,
        'budget_percentage': budget_percentage,
        'expenses_by_type': expenses_by_type,
        'materials_used': materials_used,
        'project_duration': project_duration,
    }
    
    return render(request, 'accounting/projects/project_detail.html', context)


@require_http_methods(["GET", "POST"])
def project_create(request):
    """إنشاء مشروع جديد"""
    from ..forms.projects import ProjectForm
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'تم إنشاء المشروع "{project.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:project_list')
            return redirect('accounting:project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounting/projects/project_form.html', context)


@require_http_methods(["GET", "POST"])
def project_update(request, pk):
    """تعديل مشروع"""
    from ..forms.projects import ProjectForm
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'تم تحديث المشروع "{project.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:project_list')
            return redirect('accounting:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
    }
    
    return render(request, 'accounting/projects/project_form.html', context)


@require_http_methods(["POST"])
def project_delete(request, pk):
    """حذف مشروع"""
    project = get_object_or_404(Project, pk=pk)
    
    # التحقق من وجود مصروفات
    if project.payment_vouchers.exists():
        messages.error(request, 'لا يمكن حذف مشروع له مصروفات مسجلة.')
        return redirect('accounting:project_detail', pk=project.pk)
    
    project_name = project.name
    project.delete()
    messages.success(request, f'تم حذف المشروع "{project_name}" بنجاح.')
    
    return redirect('accounting:project_list')


@require_http_methods(["POST"])
def project_change_status(request, pk):
    """تغيير حالة المشروع"""
    project = get_object_or_404(Project, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in dict(Project.STATUS_CHOICES):
        old_status = project.get_status_display()
        project.status = new_status
        
        # تحديث تاريخ الانتهاء إذا اكتمل المشروع
        if new_status == 'completed' and not project.end_date:
            project.end_date = timezone.now().date()
        
        project.save()
        
        messages.success(
            request,
            f'تم تغيير حالة المشروع من "{old_status}" إلى "{project.get_status_display()}".'
        )
    else:
        messages.error(request, 'حالة غير صالحة.')
    
    return redirect('accounting:project_detail', pk=project.pk)


@require_http_methods(["GET", "POST"])
def project_add_expense(request, pk):
    """إضافة مصروف للمشروع"""
    from ..forms.projects import ProjectExpenseForm
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectExpenseForm(request.POST, project=project)
        if form.is_valid():
            # إنشاء سند الصرف
            voucher = PaymentVoucher.objects.create(
                supplier=form.cleaned_data['supplier'],
                amount=form.cleaned_data['amount'],
                payment_date=form.cleaned_data['payment_date'],
                project=project,
                expense_type=form.cleaned_data['expense_type'],
                notes=form.cleaned_data.get('notes', ''),
                created_by=request.user
            )
            
            # خصم من الخزينة
            safe = form.cleaned_data['safe']
            safe.balance -= voucher.amount
            safe.save()
            
            messages.success(
                request,
                f'تم إضافة مصروف بقيمة {voucher.amount} للمشروع.'
            )
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:project_detail', pk=project.pk)
            return redirect('accounting:voucher_detail', voucher_type='payment', pk=voucher.pk)
    else:
        form = ProjectExpenseForm(project=project)
    
    context = {
        'form': form,
        'project': project,
    }
    
    return render(request, 'accounting/projects/project_expense_form.html', context)


def project_expenses(request, pk):
    """عرض مصروفات المشروع"""
    project = get_object_or_404(Project, pk=pk)
    
    expenses = project.payment_vouchers.select_related(
        'supplier'
    ).order_by('-payment_date')
    
    # التصفية حسب النوع
    expense_type = request.GET.get('expense_type')
    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)
    
    # التصفية حسب الفترة
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        expenses = expenses.filter(payment_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(payment_date__lte=date_to)
    
    # الصفحات
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الإحصائيات
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'project': project,
        'page_obj': page_obj,
        'expense_type': expense_type,
        'date_from': date_from,
        'date_to': date_to,
        'total_expenses': total_expenses,
        'expense_types': PaymentVoucher.EXPENSE_TYPES,
    }
    
    return render(request, 'accounting/projects/project_expenses.html', context)


def project_materials(request, pk):
    """عرض المواد المستخدمة في المشروع"""
    project = get_object_or_404(Project, pk=pk)
    
    materials = project.stock_moves.select_related(
        'item__supplier'
    ).order_by('-created_at')
    
    # تجميع حسب الصنف
    materials_summary = {}
    for move in materials:
        item = move.item
        if item.id not in materials_summary:
            materials_summary[item.id] = {
                'item': item,
                'total_quantity': 0,
                'total_cost': 0,
                'moves': []
            }
        
        materials_summary[item.id]['total_quantity'] += move.quantity
        materials_summary[item.id]['total_cost'] += move.quantity * item.unit_price
        materials_summary[item.id]['moves'].append(move)
    
    context = {
        'project': project,
        'materials': materials,
        'materials_summary': materials_summary.values(),
    }
    
    return render(request, 'accounting/projects/project_materials.html', context)