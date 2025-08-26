from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date


class VoucherBase(models.Model):
    """نموذج أساسي للسندات"""
    date = models.DateField(
        default=date.today,
        verbose_name="التاريخ"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="المبلغ"
    )
    safe = models.ForeignKey(
        'safes.Safe',
        on_delete=models.PROTECT,
        verbose_name="الخزنة/المحفظة"
    )
    description = models.TextField(
        verbose_name="البيان"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أنشأ بواسطة"
    )

    class Meta:
        abstract = True
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['safe']),
        ]


class ReceiptVoucher(VoucherBase):
    """نموذج سندات القبض"""
    voucher_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="رقم السند"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        verbose_name="العميل"
    )
    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        verbose_name="الشريك"
    )
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        verbose_name="العقد"
    )
    installment = models.ForeignKey(
        'installments.Installment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts',
        verbose_name="القسط"
    )

    class Meta:
        verbose_name = "سند قبض"
        verbose_name_plural = "سندات القبض"

    def __str__(self):
        return f"سند قبض {self.voucher_number}"
    
    def save(self, *args, **kwargs):
        # توليد رقم السند تلقائياً إذا لم يكن موجوداً
        if not self.voucher_number:
            self.voucher_number = self.generate_voucher_number()
        
        super().save(*args, **kwargs)
        
        # تحديث القسط إذا كان مرتبطاً
        if self.installment:
            from ..services.installments import InstallmentService
            InstallmentService.process_payment(self.installment, self.amount)
    
    def generate_voucher_number(self):
        """توليد رقم السند التلقائي"""
        last_voucher = ReceiptVoucher.objects.order_by('-id').first()
        if last_voucher and last_voucher.voucher_number.startswith('RV-'):
            try:
                last_number = int(last_voucher.voucher_number.split('-')[1])
                return f"RV-{last_number + 1:06d}"
            except:
                pass
        return "RV-000001"


class PaymentVoucher(VoucherBase):
    """نموذج سندات الصرف"""
    voucher_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="رقم السند"
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name="المورد"
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name="المشروع"
    )
    expense_head = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="بند المصروف"
    )

    class Meta:
        verbose_name = "سند صرف"
        verbose_name_plural = "سندات الصرف"

    def __str__(self):
        return f"سند صرف {self.voucher_number}"
    
    def save(self, *args, **kwargs):
        # توليد رقم السند تلقائياً إذا لم يكن موجوداً
        if not self.voucher_number:
            self.voucher_number = self.generate_voucher_number()
        
        super().save(*args, **kwargs)
    
    def generate_voucher_number(self):
        """توليد رقم السند التلقائي"""
        last_voucher = PaymentVoucher.objects.order_by('-id').first()
        if last_voucher and last_voucher.voucher_number.startswith('PV-'):
            try:
                last_number = int(last_voucher.voucher_number.split('-')[1])
                return f"PV-{last_number + 1:06d}"
            except:
                pass
        return "PV-000001"