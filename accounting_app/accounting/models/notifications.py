from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Notification(models.Model):
    """نموذج الإشعارات"""
    
    NOTIFICATION_TYPES = [
        ('installment_due', 'قسط مستحق'),
        ('installment_overdue', 'قسط متأخر'),
        ('low_stock', 'مخزون منخفض'),
        ('project_budget', 'تجاوز ميزانية مشروع'),
        ('settlement_pending', 'تسوية معلقة'),
        ('contract_created', 'عقد جديد'),
        ('payment_received', 'دفعة مستلمة'),
        ('voucher_created', 'سند جديد'),
        ('general', 'عام'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='المستخدم'
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='general',
        verbose_name='نوع الإشعار'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium',
        verbose_name='الأولوية'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='العنوان'
    )
    
    message = models.TextField(
        verbose_name='الرسالة'
    )
    
    link = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='الرابط'
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name='مقروء'
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ القراءة'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    
    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.title} - {self.user.username}'
    
    def mark_as_read(self):
        """وضع علامة مقروء على الإشعار"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @classmethod
    def create_notification(cls, user, notification_type, title, message, 
                          link=None, priority='medium'):
        """إنشاء إشعار جديد"""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            priority=priority
        )


class NotificationSettings(models.Model):
    """إعدادات الإشعارات للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='المستخدم'
    )
    
    # إعدادات الأقساط
    notify_installment_due = models.BooleanField(
        default=True,
        verbose_name='تنبيه استحقاق الأقساط'
    )
    
    installment_due_days = models.IntegerField(
        default=7,
        verbose_name='أيام التنبيه قبل الاستحقاق'
    )
    
    notify_installment_overdue = models.BooleanField(
        default=True,
        verbose_name='تنبيه تأخر الأقساط'
    )
    
    # إعدادات المخزون
    notify_low_stock = models.BooleanField(
        default=True,
        verbose_name='تنبيه انخفاض المخزون'
    )
    
    # إعدادات المشاريع
    notify_project_budget = models.BooleanField(
        default=True,
        verbose_name='تنبيه تجاوز ميزانية المشروع'
    )
    
    budget_threshold_percentage = models.IntegerField(
        default=80,
        verbose_name='نسبة التنبيه من الميزانية (%)'
    )
    
    # إعدادات التسويات
    notify_settlements = models.BooleanField(
        default=True,
        verbose_name='تنبيه التسويات المعلقة'
    )
    
    # إعدادات عامة
    email_notifications = models.BooleanField(
        default=False,
        verbose_name='إرسال إشعارات بالبريد الإلكتروني'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'إعدادات الإشعارات'
        verbose_name_plural = 'إعدادات الإشعارات'
    
    def __str__(self):
        return f'إعدادات إشعارات {self.user.username}'