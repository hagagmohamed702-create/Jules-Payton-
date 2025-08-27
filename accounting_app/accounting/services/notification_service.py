from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from ..models import (
    Notification, NotificationSettings, Installment, 
    Item, Project, Settlement, Contract
)


class NotificationService:
    """خدمة إدارة الإشعارات والتنبيهات"""
    
    @staticmethod
    def check_and_create_notifications():
        """فحص وإنشاء جميع الإشعارات المطلوبة"""
        NotificationService.check_installments_due()
        NotificationService.check_overdue_installments()
        NotificationService.check_low_stock_items()
        NotificationService.check_project_budgets()
        NotificationService.check_pending_settlements()
    
    @staticmethod
    def check_installments_due():
        """فحص الأقساط القادمة وإنشاء تنبيهات"""
        today = timezone.now().date()
        
        # الحصول على المستخدمين مع إعدادات التنبيه
        users_with_settings = User.objects.filter(
            notification_settings__notify_installment_due=True
        )
        
        for user in users_with_settings:
            settings = user.notification_settings
            due_date = today + timedelta(days=settings.installment_due_days)
            
            # الأقساط المستحقة قريباً
            upcoming_installments = Installment.objects.filter(
                due_date__lte=due_date,
                due_date__gt=today,
                status__in=['pending', 'partial']
            ).select_related('contract__customer', 'contract__unit')
            
            for installment in upcoming_installments:
                # التحقق من عدم وجود إشعار سابق
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='installment_due',
                    created_at__date=today,
                    message__contains=f'القسط رقم {installment.installment_number}'
                ).exists()
                
                if not existing:
                    days_until_due = (installment.due_date - today).days
                    
                    Notification.create_notification(
                        user=user,
                        notification_type='installment_due',
                        title='قسط قادم',
                        message=f'القسط رقم {installment.installment_number} للعميل {installment.contract.customer.name} مستحق بعد {days_until_due} أيام',
                        link=reverse('accounting:installment_detail', kwargs={'pk': installment.pk}),
                        priority='medium' if days_until_due > 3 else 'high'
                    )
    
    @staticmethod
    def check_overdue_installments():
        """فحص الأقساط المتأخرة وإنشاء تنبيهات"""
        today = timezone.now().date()
        
        # المستخدمون مع تفعيل تنبيهات التأخر
        users = User.objects.filter(
            notification_settings__notify_installment_overdue=True
        )
        
        # الأقساط المتأخرة
        overdue_installments = Installment.objects.filter(
            due_date__lt=today,
            status__in=['pending', 'partial']
        ).select_related('contract__customer', 'contract__unit')
        
        for user in users:
            for installment in overdue_installments:
                # التحقق من عدم وجود إشعار اليوم
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='installment_overdue',
                    created_at__date=today,
                    message__contains=f'القسط رقم {installment.installment_number}'
                ).exists()
                
                if not existing:
                    days_overdue = (today - installment.due_date).days
                    remaining = installment.amount - installment.paid_amount
                    
                    Notification.create_notification(
                        user=user,
                        notification_type='installment_overdue',
                        title='قسط متأخر',
                        message=f'القسط رقم {installment.installment_number} للعميل {installment.contract.customer.name} متأخر {days_overdue} يوم - المتبقي: {remaining}',
                        link=reverse('accounting:installment_detail', kwargs={'pk': installment.pk}),
                        priority='urgent' if days_overdue > 30 else 'high'
                    )
    
    @staticmethod
    def check_low_stock_items():
        """فحص المخزون المنخفض وإنشاء تنبيهات"""
        # المستخدمون مع تفعيل تنبيهات المخزون
        users = User.objects.filter(
            notification_settings__notify_low_stock=True
        )
        
        # الأصناف المنخفضة
        low_stock_items = Item.objects.filter(
            current_stock__lte=models.F('minimum_stock')
        )
        
        today = timezone.now().date()
        
        for user in users:
            for item in low_stock_items:
                # التحقق من عدم وجود إشعار هذا الأسبوع
                week_start = today - timedelta(days=today.weekday())
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='low_stock',
                    created_at__date__gte=week_start,
                    message__contains=item.name
                ).exists()
                
                if not existing:
                    stock_percentage = (item.current_stock / item.minimum_stock * 100) if item.minimum_stock > 0 else 0
                    
                    priority = 'urgent' if item.current_stock == 0 else (
                        'high' if stock_percentage < 50 else 'medium'
                    )
                    
                    Notification.create_notification(
                        user=user,
                        notification_type='low_stock',
                        title='مخزون منخفض',
                        message=f'الصنف "{item.name}" وصل إلى الحد الأدنى - المتوفر: {item.current_stock} {item.unit}',
                        link=reverse('accounting:item_detail', kwargs={'pk': item.pk}),
                        priority=priority
                    )
    
    @staticmethod
    def check_project_budgets():
        """فحص ميزانيات المشاريع وإنشاء تنبيهات"""
        # المستخدمون مع تفعيل تنبيهات المشاريع
        users = User.objects.filter(
            notification_settings__notify_project_budget=True
        )
        
        today = timezone.now().date()
        
        for user in users:
            settings = user.notification_settings
            threshold = settings.budget_threshold_percentage
            
            # المشاريع النشطة
            projects = Project.objects.filter(
                status='in_progress'
            ).annotate(
                total_expenses=models.Sum('payment_vouchers__amount'),
                expense_percentage=models.F('total_expenses') * 100.0 / models.F('budget')
            ).filter(
                expense_percentage__gte=threshold
            )
            
            for project in projects:
                # التحقق من عدم وجود إشعار هذا الأسبوع
                week_start = today - timedelta(days=today.weekday())
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='project_budget',
                    created_at__date__gte=week_start,
                    message__contains=project.name
                ).exists()
                
                if not existing:
                    remaining_budget = project.budget - project.total_expenses
                    
                    priority = 'urgent' if project.expense_percentage >= 100 else (
                        'high' if project.expense_percentage >= 90 else 'medium'
                    )
                    
                    Notification.create_notification(
                        user=user,
                        notification_type='project_budget',
                        title='تنبيه ميزانية مشروع',
                        message=f'المشروع "{project.name}" استهلك {project.expense_percentage:.0f}% من الميزانية - المتبقي: {remaining_budget}',
                        link=reverse('accounting:project_detail', kwargs={'pk': project.pk}),
                        priority=priority
                    )
    
    @staticmethod
    def check_pending_settlements():
        """فحص التسويات المعلقة وإنشاء تنبيهات"""
        # المستخدمون مع تفعيل تنبيهات التسويات
        users = User.objects.filter(
            notification_settings__notify_settlements=True
        )
        
        # التسويات المعلقة لأكثر من 7 أيام
        week_ago = timezone.now().date() - timedelta(days=7)
        old_settlements = Settlement.objects.filter(
            status='pending',
            created_at__date__lte=week_ago
        )
        
        today = timezone.now().date()
        
        for user in users:
            for settlement in old_settlements:
                # التحقق من عدم وجود إشعار هذا الأسبوع
                week_start = today - timedelta(days=today.weekday())
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='settlement_pending',
                    created_at__date__gte=week_start,
                    message__contains=settlement.settlement_number
                ).exists()
                
                if not existing:
                    days_pending = (today - settlement.created_at.date()).days
                    
                    Notification.create_notification(
                        user=user,
                        notification_type='settlement_pending',
                        title='تسوية معلقة',
                        message=f'التسوية رقم {settlement.settlement_number} معلقة منذ {days_pending} يوم - المبلغ: {settlement.amount}',
                        link=reverse('accounting:settlement_detail', kwargs={'pk': settlement.pk}),
                        priority='high' if days_pending > 14 else 'medium'
                    )
    
    @staticmethod
    def notify_contract_created(contract):
        """إشعار بإنشاء عقد جديد"""
        # إشعار جميع المستخدمين النشطين
        users = User.objects.filter(is_active=True)
        
        for user in users:
            Notification.create_notification(
                user=user,
                notification_type='contract_created',
                title='عقد جديد',
                message=f'تم إنشاء عقد جديد رقم {contract.contract_number} للعميل {contract.customer.name}',
                link=reverse('accounting:contract_detail', kwargs={'pk': contract.pk}),
                priority='low'
            )
    
    @staticmethod
    def notify_payment_received(receipt_voucher):
        """إشعار باستلام دفعة"""
        # إشعار المستخدمين المعنيين
        users = User.objects.filter(is_active=True)
        
        for user in users:
            customer_name = receipt_voucher.customer.name
            amount = receipt_voucher.amount
            
            message = f'تم استلام دفعة بقيمة {amount} من العميل {customer_name}'
            if receipt_voucher.contract:
                message += f' للعقد رقم {receipt_voucher.contract.contract_number}'
            
            Notification.create_notification(
                user=user,
                notification_type='payment_received',
                title='دفعة جديدة',
                message=message,
                link=reverse('accounting:voucher_detail', kwargs={
                    'voucher_type': 'receipt',
                    'pk': receipt_voucher.pk
                }),
                priority='medium'
            )
    
    @staticmethod
    def get_user_notifications(user, unread_only=False):
        """الحصول على إشعارات المستخدم"""
        notifications = user.notifications.all()
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        return notifications
    
    @staticmethod
    def mark_notifications_as_read(notification_ids):
        """وضع علامة مقروء على مجموعة من الإشعارات"""
        Notification.objects.filter(
            id__in=notification_ids
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @staticmethod
    def get_notification_summary(user):
        """الحصول على ملخص الإشعارات للمستخدم"""
        notifications = user.notifications.all()
        
        return {
            'total': notifications.count(),
            'unread': notifications.filter(is_read=False).count(),
            'urgent': notifications.filter(priority='urgent', is_read=False).count(),
            'high': notifications.filter(priority='high', is_read=False).count(),
            'by_type': {
                ntype: notifications.filter(notification_type=ntype[0]).count()
                for ntype in Notification.NOTIFICATION_TYPES
            }
        }