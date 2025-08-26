from django.db import models
from django.contrib.postgres.fields import JSONField
from decimal import Decimal


class Settlement(models.Model):
    """نموذج التسويات بين الشركاء"""
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settlements',
        verbose_name="المشروع"
    )
    period_from = models.DateField(
        verbose_name="من تاريخ"
    )
    period_to = models.DateField(
        verbose_name="إلى تاريخ"
    )
    pre_balances = models.JSONField(
        default=dict,
        verbose_name="الأرصدة قبل التسوية",
        help_text="{'partner_id': balance}"
    )
    post_balances = models.JSONField(
        default=dict,
        verbose_name="الأرصدة بعد التسوية",
        help_text="{'partner_id': balance}"
    )
    details = models.JSONField(
        default=dict,
        verbose_name="تفاصيل التسوية",
        help_text="التحويلات المطلوبة بين الشركاء"
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
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أنشأ بواسطة"
    )

    class Meta:
        verbose_name = "تسوية"
        verbose_name_plural = "التسويات"
        ordering = ['-period_to', '-created_at']
        indexes = [
            models.Index(fields=['period_from', 'period_to']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        project_name = self.project.name if self.project else "عام"
        return f"تسوية {project_name} ({self.period_from} - {self.period_to})"
    
    def calculate_settlement(self):
        """حساب التسوية المطلوبة"""
        from ..services.settlements import SettlementService
        return SettlementService.calculate_settlement(
            self.period_from,
            self.period_to,
            self.project
        )
    
    def get_transfers_summary(self):
        """ملخص التحويلات المطلوبة"""
        if not self.details or 'transfers' not in self.details:
            return []
        
        transfers = []
        for transfer in self.details.get('transfers', []):
            transfers.append({
                'from_partner': transfer.get('from_partner_name'),
                'to_partner': transfer.get('to_partner_name'),
                'amount': Decimal(str(transfer.get('amount', 0)))
            })
        
        return transfers