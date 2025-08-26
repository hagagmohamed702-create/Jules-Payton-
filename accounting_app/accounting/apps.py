from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = 'المحاسبة'
    
    def ready(self):
        # تسجيل الإشارات إذا لزم الأمر
        pass