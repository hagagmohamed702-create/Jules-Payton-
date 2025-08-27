from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...services.notification_service import NotificationService


class Command(BaseCommand):
    help = 'يولد الإشعارات والتنبيهات بناءً على البيانات الحالية'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('جاري فحص وإنشاء الإشعارات...'))
        
        try:
            # فحص وإنشاء جميع أنواع الإشعارات
            NotificationService.check_and_create_notifications()
            
            # عرض ملخص الإشعارات المنشأة
            users = User.objects.filter(is_active=True)
            total_notifications = 0
            
            for user in users:
                summary = NotificationService.get_notification_summary(user)
                if summary['total'] > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'المستخدم {user.username}: {summary["total"]} إشعار '
                            f'({summary["unread"]} غير مقروء)'
                        )
                    )
                    total_notifications += summary['total']
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ تم إنشاء {total_notifications} إشعار بنجاح!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'حدث خطأ: {str(e)}')
            )