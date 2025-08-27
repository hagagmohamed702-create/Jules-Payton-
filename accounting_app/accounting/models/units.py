from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Unit(models.Model):
    """نموذج الوحدات السكنية"""
    
    UNIT_TYPES = [
        ('residential', 'سكني'),
        ('commercial', 'تجاري'),
        ('school', 'مدرسة'),
        ('other', 'أخرى'),
    ]
    
    UNIT_GROUPS = [
        ('res', 'سكني'),
        ('com', 'تجاري'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود الوحدة"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="اسم الوحدة"
    )
    building_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="رقم المبنى"
    )
    unit_type = models.CharField(
        max_length=20,
        choices=UNIT_TYPES,
        default='residential',
        verbose_name="نوع الوحدة"
    )
    price_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="السعر الإجمالي"
    )
    group = models.CharField(
        max_length=10,
        choices=UNIT_GROUPS,
        default='res',
        verbose_name="المجموعة"
    )
    partners_group = models.ForeignKey(
        'accounting.PartnersGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="مجموعة الشركاء المالكة"
    )
    is_sold = models.BooleanField(
        default=False,
        verbose_name="مباعة"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "وحدة"
        verbose_name_plural = "الوحدات"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['unit_type']),
            models.Index(fields=['is_sold']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def mark_as_sold(self):
        """تحديد الوحدة كمباعة"""
        self.is_sold = True
        self.save(update_fields=['is_sold'])