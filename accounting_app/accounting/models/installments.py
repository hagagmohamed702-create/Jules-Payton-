from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date


class Installment(models.Model):
    """نموذج الأقساط"""
    
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='installments',
        verbose_name="العقد"
    )
    due_date = models.DateField(
        verbose_name="تاريخ الاستحقاق"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="المبلغ"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="مدفوع"
    )
    
    # الحقول الإضافية من النموذج الأصلي
    seq_no = models.PositiveIntegerField(
        verbose_name="رقم القسط"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="المبلغ المدفوع"
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
        verbose_name = "قسط"
        verbose_name_plural = "الأقساط"
        ordering = ['contract', 'seq_no']
        unique_together = [['contract', 'seq_no']]
        indexes = [
            models.Index(fields=['contract', 'seq_no']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Installment #{self.id} - {self.amount}"
    
    def update_status(self):
        """تحديث حالة القسط"""
        if self.paid_amount >= self.amount:
            self.status = 'PAID'
        elif date.today() > self.due_date and self.paid_amount < self.amount:
            self.status = 'LATE'
        else:
            self.status = 'PENDING'
        self.save(update_fields=['status'])
    
    def add_payment(self, amount):
        """إضافة دفعة للقسط"""
        self.paid_amount += amount
        if self.paid_amount > self.amount:
            # إذا كان المدفوع أكثر من قيمة القسط، نحدد المدفوع = قيمة القسط
            self.paid_amount = self.amount
        self.update_status()
        return self.paid_amount
    
    def get_remaining_amount(self):
        """المبلغ المتبقي من القسط"""
        return self.amount - self.paid_amount
    
    @classmethod
    def get_late_installments(cls):
        """الحصول على الأقساط المتأخرة"""
        return cls.objects.filter(
            status='LATE'
        ).select_related('contract', 'contract__customer')
    
    @classmethod
    def get_upcoming_installments(cls, days=7):
        """الحصول على الأقساط المستحقة خلال الأيام القادمة"""
        from datetime import timedelta
        end_date = date.today() + timedelta(days=days)
        
        return cls.objects.filter(
            due_date__lte=end_date,
            due_date__gte=date.today(),
            status='PENDING'
        ).select_related('contract', 'contract__customer')


class InstallmentPayment(models.Model):
    """نموذج المدفوعات الخاصة بالأقساط"""
    
    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="القسط"
    )
    paid_on = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الدفع"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="المبلغ المدفوع"
    )
    method = models.CharField(
        max_length=50,
        default='cash',
        verbose_name="طريقة الدفع"
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="ملاحظة"
    )

    class Meta:
        verbose_name = "دفعة قسط"
        verbose_name_plural = "دفعات الأقساط"
        ordering = ['-paid_on']

    def __str__(self):
        return f"Payment {self.amount} for installment {self.installment.id}"