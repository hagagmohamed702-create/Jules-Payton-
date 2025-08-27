from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import Notification


class Command(BaseCommand):
    help = 'ينظف البيانات القديمة من النظام'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='عدد الأيام للاحتفاظ بالبيانات (افتراضي: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم حذفه دون حذف فعلي'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'جاري البحث عن البيانات الأقدم من {days} يوم...'
            )
        )
        
        # تنظيف الإشعارات المقروءة القديمة
        old_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        )
        
        notifications_count = old_notifications.count()
        
        if notifications_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'سيتم حذف {notifications_count} إشعار قديم مقروء'
                )
            )
            
            if not dry_run:
                old_notifications.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ تم حذف {notifications_count} إشعار'
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('لا توجد إشعارات قديمة للحذف')
            )
        
        # يمكن إضافة تنظيف لبيانات أخرى هنا مستقبلاً
        # مثل: سجلات النشاط، التقارير المؤقتة، إلخ
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nتم تشغيل الأمر في وضع المعاينة - لم يتم حذف أي بيانات'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ تم تنظيف البيانات القديمة بنجاح!')
            )