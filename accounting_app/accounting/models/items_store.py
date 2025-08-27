from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Item(models.Model):
    """نموذج الأصناف"""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود الصنف"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="اسم الصنف"
    )
    uom = models.CharField(
        max_length=50,
        verbose_name="وحدة القياس",
        help_text="مثل: قطعة، متر، كيلو"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        default=Decimal('0'),
        verbose_name="سعر الوحدة"
    )
    supplier = models.ForeignKey(
        'accounting.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        verbose_name="المورد الافتراضي"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "صنف"
        verbose_name_plural = "الأصناف"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_current_balance(self):
        """رصيد الصنف الحالي"""
        in_qty = self.moves.filter(direction='IN').aggregate(
            total=models.Sum('qty')
        )['total'] or Decimal('0')
        
        out_qty = self.moves.filter(direction='OUT').aggregate(
            total=models.Sum('qty')
        )['total'] or Decimal('0')
        
        return in_qty - out_qty
    
    def get_total_value(self):
        """القيمة الإجمالية للرصيد"""
        return self.get_current_balance() * self.unit_price


class StockMove(models.Model):
    """نموذج حركات المخزن"""
    
    DIRECTION_CHOICES = [
        ('IN', 'وارد'),
        ('OUT', 'صادر'),
    ]
    
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='moves',
        verbose_name="الصنف"
    )
    project = models.ForeignKey(
        'accounting.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_moves',
        verbose_name="المشروع"
    )
    qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="الكمية"
    )
    direction = models.CharField(
        max_length=3,
        choices=DIRECTION_CHOICES,
        verbose_name="نوع الحركة"
    )
    date = models.DateField(
        verbose_name="التاريخ"
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

    class Meta:
        verbose_name = "حركة مخزن"
        verbose_name_plural = "حركات المخزن"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['item', 'direction']),
            models.Index(fields=['date']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        direction_text = "وارد" if self.direction == "IN" else "صادر"
        return f"{direction_text} - {self.item.name} ({self.qty} {self.item.uom})"
    
    def get_move_value(self):
        """قيمة الحركة"""
        return self.qty * self.item.unit_price