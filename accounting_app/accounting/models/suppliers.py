from django.db import models
from django.core.validators import RegexValidator


class Supplier(models.Model):
    """نموذج الموردين"""
    name = models.CharField(
        max_length=200,
        verbose_name="اسم المورد"
    )
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[0-9+\-\s]+$',
                message='رقم الهاتف يجب أن يحتوي على أرقام فقط'
            )
        ],
        blank=True,
        null=True,
        verbose_name="رقم الهاتف"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردين"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def get_total_payments(self):
        """إجمالي المدفوعات للمورد"""
        from ..models.vouchers import PaymentVoucher
        return PaymentVoucher.objects.filter(
            supplier=self
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0