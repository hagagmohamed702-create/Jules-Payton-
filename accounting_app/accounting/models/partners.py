from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal


class Partner(models.Model):
    """نموذج الشركاء"""
    code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="كود الشريك"
    )
    name = models.CharField(
        max_length=200, 
        verbose_name="اسم الشريك"
    )
    share_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="نسبة الشراكة %"
    )
    opening_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="الرصيد الافتتاحي"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="ملاحظات"
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
        verbose_name = "شريك"
        verbose_name_plural = "الشركاء"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_current_balance(self):
        """حساب الرصيد الحالي للشريك"""
        from ..services.treasury import TreasuryService
        return TreasuryService.get_partner_balance(self)


class PartnersGroup(models.Model):
    """نموذج مجموعات الشركاء"""
    name = models.CharField(
        max_length=200,
        verbose_name="اسم المجموعة"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "مجموعة شركاء"
        verbose_name_plural = "مجموعات الشركاء"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def validate_total_percent(self):
        """التحقق من أن مجموع النسب = 100%"""
        total = self.members.aggregate(
            total=models.Sum('percent')
        )['total'] or Decimal('0')
        
        if total != Decimal('100.00'):
            raise ValidationError(
                f"مجموع نسب أعضاء المجموعة يجب أن يساوي 100% (الحالي: {total}%)"
            )


class PartnersGroupMember(models.Model):
    """نموذج أعضاء مجموعة الشركاء"""
    group = models.ForeignKey(
        PartnersGroup,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name="المجموعة"
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name='group_memberships',
        verbose_name="الشريك"
    )
    percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="النسبة في المجموعة %"
    )

    class Meta:
        verbose_name = "عضو مجموعة"
        verbose_name_plural = "أعضاء المجموعة"
        unique_together = [['group', 'partner']]
        ordering = ['group', '-percent']

    def __str__(self):
        return f"{self.partner.name} - {self.percent}%"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # التحقق من مجموع النسب بعد الحفظ
        self.group.validate_total_percent()