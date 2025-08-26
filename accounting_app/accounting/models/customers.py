from django.db import models
from django.core.validators import RegexValidator


class Customer(models.Model):
    """نموذج العملاء"""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود العميل"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="اسم العميل"
    )
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[0-9+\-\s]+$',
                message='رقم الهاتف يجب أن يحتوي على أرقام فقط'
            )
        ],
        verbose_name="رقم الهاتف"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="البريد الإلكتروني"
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="العنوان"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث"
    )

    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_total_contracts_value(self):
        """إجمالي قيمة العقود للعميل"""
        return self.contracts.aggregate(
            total=models.Sum('unit_value')
        )['total'] or 0
    
    def get_total_paid(self):
        """إجمالي المبالغ المدفوعة"""
        from ..models.vouchers import ReceiptVoucher
        return ReceiptVoucher.objects.filter(
            customer=self
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0