from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ..models import Item, StockMove, Supplier, Project


def item_list(request):
    """عرض قائمة الأصناف"""
    items = Item.objects.select_related('supplier').annotate(
        total_in=Sum('stock_moves__quantity', filter=Q(stock_moves__move_type='in')),
        total_out=Sum('stock_moves__quantity', filter=Q(stock_moves__move_type='out')),
        stock_value=F('current_stock') * F('unit_price')
    )
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # التصفية حسب المورد
    supplier_id = request.GET.get('supplier_id')
    if supplier_id:
        items = items.filter(supplier_id=supplier_id)
    
    # التصفية حسب مستوى المخزون
    stock_level = request.GET.get('stock_level')
    if stock_level == 'low':
        items = items.filter(current_stock__lte=F('minimum_stock'))
    elif stock_level == 'out':
        items = items.filter(current_stock=0)
    elif stock_level == 'available':
        items = items.filter(current_stock__gt=0)
    
    # الترتيب
    order_by = request.GET.get('order_by', 'name')
    items = items.order_by(order_by)
    
    # الصفحات
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإحصائيات
    stats = {
        'total_items': Item.objects.count(),
        'low_stock_items': Item.objects.filter(
            current_stock__lte=F('minimum_stock')
        ).count(),
        'out_of_stock': Item.objects.filter(current_stock=0).count(),
        'total_value': Item.objects.aggregate(
            total=Sum(F('current_stock') * F('unit_price'))
        )['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'supplier_id': supplier_id,
        'stock_level': stock_level,
        'stats': stats,
        'suppliers': Supplier.objects.filter(is_active=True),
    }
    
    return render(request, 'accounting/inventory/item_list.html', context)


def item_detail(request, pk):
    """عرض تفاصيل الصنف"""
    item = get_object_or_404(
        Item.objects.select_related('supplier').prefetch_related(
            'stock_moves__project'
        ),
        pk=pk
    )
    
    # حركات المخزون
    stock_moves = item.stock_moves.select_related('project').order_by('-created_at')[:20]
    
    # إحصائيات الصنف
    stats = {
        'total_in': item.stock_moves.filter(move_type='in').aggregate(
            Sum('quantity')
        )['quantity__sum'] or 0,
        'total_out': item.stock_moves.filter(move_type='out').aggregate(
            Sum('quantity')
        )['quantity__sum'] or 0,
        'stock_value': item.current_stock * item.unit_price,
        'moves_count': item.stock_moves.count(),
    }
    
    # المشاريع التي استخدمت الصنف
    projects_used = Project.objects.filter(
        stock_moves__item=item
    ).distinct().annotate(
        quantity_used=Sum('stock_moves__quantity')
    )
    
    context = {
        'item': item,
        'stock_moves': stock_moves,
        'stats': stats,
        'projects_used': projects_used,
    }
    
    return render(request, 'accounting/inventory/item_detail.html', context)


@require_http_methods(["GET", "POST"])
def item_create(request):
    """إنشاء صنف جديد"""
    from ..forms.inventory import ItemForm
    
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'تم إنشاء الصنف "{item.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:item_list')
            return redirect('accounting:item_detail', pk=item.pk)
    else:
        form = ItemForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounting/inventory/item_form.html', context)


@require_http_methods(["GET", "POST"])
def item_update(request, pk):
    """تعديل صنف"""
    from ..forms.inventory import ItemForm
    
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'تم تحديث الصنف "{item.name}" بنجاح.')
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:item_list')
            return redirect('accounting:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)
    
    context = {
        'form': form,
        'item': item,
    }
    
    return render(request, 'accounting/inventory/item_form.html', context)


@require_http_methods(["POST"])
def item_delete(request, pk):
    """حذف صنف"""
    item = get_object_or_404(Item, pk=pk)
    
    # التحقق من وجود حركات
    if item.stock_moves.exists():
        messages.error(request, 'لا يمكن حذف صنف له حركات مخزنية.')
        return redirect('accounting:item_detail', pk=item.pk)
    
    item_name = item.name
    item.delete()
    messages.success(request, f'تم حذف الصنف "{item_name}" بنجاح.')
    
    return redirect('accounting:item_list')


@require_http_methods(["GET", "POST"])
def stock_in(request):
    """إدخال مخزون"""
    from ..forms.inventory import StockMoveForm
    
    if request.method == 'POST':
        form = StockMoveForm(request.POST, move_type='in')
        if form.is_valid():
            stock_move = form.save(commit=False)
            stock_move.move_type = 'in'
            stock_move.save()
            
            # تحديث رصيد الصنف
            item = stock_move.item
            item.current_stock += stock_move.quantity
            item.save()
            
            messages.success(
                request,
                f'تم إضافة {stock_move.quantity} {item.unit} من "{item.name}" إلى المخزون.'
            )
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:item_list')
            return redirect('accounting:item_detail', pk=item.pk)
    else:
        form = StockMoveForm(move_type='in')
    
    context = {
        'form': form,
        'move_type': 'in',
    }
    
    return render(request, 'accounting/inventory/stock_move_form.html', context)


@require_http_methods(["GET", "POST"])
def stock_out(request):
    """إخراج مخزون"""
    from ..forms.inventory import StockMoveForm
    
    if request.method == 'POST':
        form = StockMoveForm(request.POST, move_type='out')
        if form.is_valid():
            stock_move = form.save(commit=False)
            stock_move.move_type = 'out'
            
            # التحقق من توفر الكمية
            item = stock_move.item
            if item.current_stock < stock_move.quantity:
                messages.error(
                    request,
                    f'الكمية المطلوبة ({stock_move.quantity}) أكبر من المتوفر ({item.current_stock}).'
                )
                return render(request, 'accounting/inventory/stock_move_form.html', {
                    'form': form,
                    'move_type': 'out',
                })
            
            stock_move.save()
            
            # تحديث رصيد الصنف
            item.current_stock -= stock_move.quantity
            item.save()
            
            messages.success(
                request,
                f'تم إخراج {stock_move.quantity} {item.unit} من "{item.name}" من المخزون.'
            )
            
            if request.headers.get('HX-Request'):
                return redirect('accounting:item_list')
            return redirect('accounting:item_detail', pk=item.pk)
    else:
        form = StockMoveForm(move_type='out')
    
    context = {
        'form': form,
        'move_type': 'out',
    }
    
    return render(request, 'accounting/inventory/stock_move_form.html', context)


def stock_moves(request):
    """عرض حركات المخزون"""
    moves = StockMove.objects.select_related('item', 'project').order_by('-created_at')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        moves = moves.filter(
            Q(item__name__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # التصفية حسب النوع
    move_type = request.GET.get('move_type')
    if move_type in ['in', 'out']:
        moves = moves.filter(move_type=move_type)
    
    # التصفية حسب الصنف
    item_id = request.GET.get('item_id')
    if item_id:
        moves = moves.filter(item_id=item_id)
    
    # التصفية حسب المشروع
    project_id = request.GET.get('project_id')
    if project_id:
        moves = moves.filter(project_id=project_id)
    
    # التصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        moves = moves.filter(created_at__date__gte=date_from)
    if date_to:
        moves = moves.filter(created_at__date__lte=date_to)
    
    # الصفحات
    paginator = Paginator(moves, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'move_type': move_type,
        'item_id': item_id,
        'project_id': project_id,
        'date_from': date_from,
        'date_to': date_to,
        'items': Item.objects.all(),
        'projects': Project.objects.filter(status='in_progress'),
    }
    
    return render(request, 'accounting/inventory/stock_moves.html', context)


def low_stock_items(request):
    """عرض الأصناف منخفضة المخزون"""
    items = Item.objects.filter(
        current_stock__lte=F('minimum_stock')
    ).select_related('supplier').annotate(
        stock_percentage=F('current_stock') * 100.0 / F('minimum_stock'),
        needed_quantity=F('minimum_stock') - F('current_stock')
    ).order_by('stock_percentage')
    
    context = {
        'items': items,
    }
    
    return render(request, 'accounting/inventory/low_stock_items.html', context)


def inventory_report(request):
    """تقرير المخزون الشامل"""
    # إحصائيات عامة
    stats = {
        'total_items': Item.objects.count(),
        'total_value': Item.objects.aggregate(
            total=Sum(F('current_stock') * F('unit_price'))
        )['total'] or 0,
        'low_stock_items': Item.objects.filter(
            current_stock__lte=F('minimum_stock')
        ).count(),
        'out_of_stock': Item.objects.filter(current_stock=0).count(),
        'total_in_this_month': StockMove.objects.filter(
            move_type='in',
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'total_out_this_month': StockMove.objects.filter(
            move_type='out',
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0,
    }
    
    # أعلى الأصناف قيمة
    top_value_items = Item.objects.annotate(
        stock_value=F('current_stock') * F('unit_price')
    ).order_by('-stock_value')[:10]
    
    # أكثر الأصناف حركة
    most_active_items = Item.objects.annotate(
        moves_count=Count('stock_moves')
    ).order_by('-moves_count')[:10]
    
    context = {
        'stats': stats,
        'top_value_items': top_value_items,
        'most_active_items': most_active_items,
    }
    
    return render(request, 'accounting/inventory/inventory_report.html', context)