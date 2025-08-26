from django.db import models
from django.core.exceptions import ValidationError
from .partners import Partner


class Safe(models.Model):
    """نموذج الخزائن والمحافظ"""
    name = models.CharField(
        max_length=200,
        verbose_name="اسم الخزنة/المحفظة"
    )
    is_partner_wallet = models.BooleanField(
        default=False,
        verbose_name="محفظة شريك؟"
    )
    partner = models.OneToOneField(
        Partner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='wallet',
        verbose_name="الشريك"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "خزنة/محفظة"
        verbose_name_plural = "الخزائن والمحافظ"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_partner_wallet']),
        ]

    def __str__(self):
        if self.is_partner_wallet and self.partner:
            return f"محفظة {self.partner.name}"
        return self.name
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.is_partner_wallet and not self.partner:
            raise ValidationError(
                "يجب تحديد الشريك عند اختيار محفظة شريك"
            )
        if not self.is_partner_wallet and self.partner:
            raise ValidationError(
                "لا يمكن ربط شريك بخزنة عامة"
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_balance(self, from_date=None, to_date=None):
        """حساب رصيد الخزنة/المحفظة"""
        from ..services.treasury import TreasuryService
        return TreasuryService.get_safe_balance(self, from_date, to_date)