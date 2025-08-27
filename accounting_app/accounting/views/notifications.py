from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import Notification, NotificationSettings
from ..services.notification_service import NotificationService


@login_required
def notification_list(request):
    """عرض قائمة الإشعارات"""
    notifications = request.user.notifications.all()
    
    # التصفية حسب الحالة
    status = request.GET.get('status')
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # التصفية حسب النوع
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # التصفية حسب الأولوية
    priority = request.GET.get('priority')
    if priority:
        notifications = notifications.filter(priority=priority)
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    # الصفحات
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الإحصائيات
    summary = NotificationService.get_notification_summary(request.user)
    
    context = {
        'page_obj': page_obj,
        'summary': summary,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'priorities': Notification.PRIORITY_LEVELS,
        'filters': {
            'status': status,
            'type': notification_type,
            'priority': priority,
            'search': search_query,
        }
    }
    
    return render(request, 'accounting/notifications/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """عرض تفاصيل الإشعار"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    
    # وضع علامة مقروء
    notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'accounting/notifications/notification_detail.html', context)


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, pk=None):
    """وضع علامة مقروء على إشعار أو مجموعة إشعارات"""
    if pk:
        # إشعار واحد
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user
        )
        notification.mark_as_read()
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'success'})
    else:
        # مجموعة إشعارات
        notification_ids = request.POST.getlist('notification_ids')
        if notification_ids:
            NotificationService.mark_notifications_as_read(notification_ids)
            messages.success(request, f'تم وضع علامة مقروء على {len(notification_ids)} إشعار.')
    
    return redirect('accounting:notification_list')


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """وضع علامة مقروء على جميع الإشعارات"""
    request.user.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    messages.success(request, 'تم وضع علامة مقروء على جميع الإشعارات.')
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'status': 'success'})
    
    return redirect('accounting:notification_list')


@login_required
@require_http_methods(["POST"])
def delete_notification(request, pk):
    """حذف إشعار"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    
    notification.delete()
    messages.success(request, 'تم حذف الإشعار.')
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'status': 'success'})
    
    return redirect('accounting:notification_list')


@login_required
@require_http_methods(["POST"])
def delete_read_notifications(request):
    """حذف جميع الإشعارات المقروءة"""
    count = request.user.notifications.filter(is_read=True).count()
    request.user.notifications.filter(is_read=True).delete()
    
    messages.success(request, f'تم حذف {count} إشعار مقروء.')
    
    return redirect('accounting:notification_list')


@login_required
def notification_settings(request):
    """إعدادات الإشعارات"""
    settings, created = NotificationSettings.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        # تحديث الإعدادات
        settings.notify_installment_due = request.POST.get('notify_installment_due') == 'on'
        settings.installment_due_days = int(request.POST.get('installment_due_days', 7))
        settings.notify_installment_overdue = request.POST.get('notify_installment_overdue') == 'on'
        settings.notify_low_stock = request.POST.get('notify_low_stock') == 'on'
        settings.notify_project_budget = request.POST.get('notify_project_budget') == 'on'
        settings.budget_threshold_percentage = int(request.POST.get('budget_threshold_percentage', 80))
        settings.notify_settlements = request.POST.get('notify_settlements') == 'on'
        settings.email_notifications = request.POST.get('email_notifications') == 'on'
        
        settings.save()
        
        messages.success(request, 'تم حفظ إعدادات الإشعارات.')
        
        if request.headers.get('HX-Request'):
            return render(request, 'accounting/notifications/_settings_form.html', {
                'settings': settings,
                'saved': True
            })
        
        return redirect('accounting:notification_settings')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'accounting/notifications/settings.html', context)


@login_required
def notification_popup(request):
    """عرض الإشعارات في نافذة منبثقة (AJAX)"""
    unread_notifications = request.user.notifications.filter(
        is_read=False
    ).order_by('-created_at')[:5]
    
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    context = {
        'notifications': unread_notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'accounting/notifications/_popup.html', context)


@login_required
def check_new_notifications(request):
    """فحص وجود إشعارات جديدة (AJAX)"""
    # فحص وإنشاء الإشعارات الجديدة
    NotificationService.check_and_create_notifications()
    
    # عد الإشعارات غير المقروءة
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    # الحصول على آخر الإشعارات
    latest_notifications = request.user.notifications.filter(
        is_read=False
    ).order_by('-created_at')[:3]
    
    notifications_data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message[:100] + '...' if len(n.message) > 100 else n.message,
        'type': n.get_notification_type_display(),
        'priority': n.priority,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'link': n.link
    } for n in latest_notifications]
    
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data
    })