from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta


class Contract(models.Model):
    """نموذج العقود"""
    
    SCHEDULE_TYPES = [
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('yearly', 'سنوي'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود العقد"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name="العميل"
    )
    unit = models.OneToOneField(
        'units.Unit',
        on_delete=models.PROTECT,
        related_name='contract',
        verbose_name="الوحدة"
    )
    unit_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="قيمة الوحدة"
    )
    down_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        default=Decimal('0'),
        verbose_name="الدفعة المقدمة"
    )
    installments_count = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="عدد الأقساط"
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        default='monthly',
        verbose_name="نوع الجدولة"
    )
    start_date = models.DateField(
        verbose_name="تاريخ البداية"
    )
    partners_group = models.ForeignKey(
        'partners.PartnersGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts',
        verbose_name="مجموعة الشركاء"
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
        verbose_name = "عقد"
        verbose_name_plural = "العقود"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['customer']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"{self.code} - {self.customer.name}"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.down_payment > self.unit_value:
            raise ValidationError(
                "الدفعة المقدمة لا يمكن أن تكون أكبر من قيمة الوحدة"
            )
        
        if self.down_payment == self.unit_value and self.installments_count > 0:
            raise ValidationError(
                "لا يمكن وجود أقساط إذا كانت الدفعة المقدمة تساوي قيمة الوحدة"
            )
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)
        
        # توليد الأقساط عند إنشاء عقد جديد
        if is_new and self.installments_count > 0:
            self.generate_installments()
        
        # تحديد الوحدة كمباعة
        self.unit.mark_as_sold()
    
    def generate_installments(self):
        """توليد جدول الأقساط"""
        from ..services.contracts import ContractService
        ContractService.generate_installments(self)
    
    def get_remaining_amount(self):
        """المبلغ المتبقي بعد الدفعة المقدمة"""
        return self.unit_value - self.down_payment
    
    def get_installment_amount(self):
        """قيمة القسط الواحد"""
        if self.installments_count == 0:
            return Decimal('0')
        return self.get_remaining_amount() / self.installments_count
    
    def get_total_paid(self):
        """إجمالي المبالغ المدفوعة"""
        paid = self.installments.aggregate(
            total=models.Sum('paid_amount')
        )['total'] or Decimal('0')
        return self.down_payment + paid
    
    def get_balance_due(self):
        """المبلغ المستحق"""
        return self.unit_value - self.get_total_paid()