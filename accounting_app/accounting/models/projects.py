from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Project(models.Model):
    """نموذج المشاريع"""
    
    PROJECT_TYPES = [
        ('build', 'بناء'),
        ('maintenance', 'صيانة'),
        ('renovation', 'تجديد'),
    ]
    
    STATUS_CHOICES = [
        ('ongoing', 'جاري'),
        ('done', 'منتهي'),
        ('hold', 'معلق'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود المشروع"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="اسم المشروع"
    )
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPES,
        default='build',
        verbose_name="نوع المشروع"
    )
    start_date = models.DateField(
        verbose_name="تاريخ البداية"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ النهاية"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ongoing',
        verbose_name="الحالة"
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        default=Decimal('0'),
        verbose_name="الميزانية"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "مشروع"
        verbose_name_plural = "المشاريع"
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_total_expenses(self):
        """إجمالي مصروفات المشروع"""
        total = self.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # إضافة تكلفة المواد المستخدمة
        from .items_store import StockMove
        materials_cost = StockMove.objects.filter(
            project=self,
            direction='OUT'
        ).aggregate(
            total=models.Sum(
                models.F('qty') * models.F('item__unit_price')
            )
        )['total'] or Decimal('0')
        
        return total + materials_cost
    
    def get_budget_remaining(self):
        """المتبقي من الميزانية"""
        return self.budget - self.get_total_expenses()
    
    def get_budget_percentage(self):
        """نسبة استهلاك الميزانية"""
        if self.budget == 0:
            return 0
        return (self.get_total_expenses() / self.budget) * 100
    
    def is_over_budget(self):
        """هل تجاوز المشروع الميزانية"""
        return self.get_total_expenses() > self.budget