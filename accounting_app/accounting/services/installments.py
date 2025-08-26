from decimal import Decimal
from datetime import date
from ..models import ReceiptVoucher


class InstallmentService:
    """خدمة إدارة الأقساط والمدفوعات"""
    
    @staticmethod
    def process_payment(installment, amount):
        """معالجة دفعة على القسط"""
        if amount <= 0:
            raise ValueError("مبلغ الدفعة يجب أن يكون أكبر من صفر")
        
        # إضافة المبلغ المدفوع
        installment.paid_amount += amount
        
        # التأكد من عدم تجاوز قيمة القسط
        if installment.paid_amount > installment.amount:
            installment.paid_amount = installment.amount
        
        # تحديث حالة القسط
        installment.update_status()
        
        return installment
    
    @staticmethod
    def update_installment_status(installment):
        """تحديث حالة القسط بناءً على المدفوعات والتاريخ"""
        if installment.paid_amount >= installment.amount:
            installment.status = 'PAID'
        elif date.today() > installment.due_date and installment.paid_amount < installment.amount:
            installment.status = 'LATE'
        else:
            installment.status = 'PENDING'
        
        installment.save(update_fields=['status'])
        return installment.status
    
    @staticmethod
    def update_all_installments_status():
        """تحديث حالة جميع الأقساط في النظام"""
        from ..models import Installment
        
        # الأقساط المدفوعة بالكامل
        Installment.objects.filter(
            paid_amount__gte=models.F('amount')
        ).update(status='PAID')
        
        # الأقساط المتأخرة
        Installment.objects.filter(
            due_date__lt=date.today(),
            paid_amount__lt=models.F('amount')
        ).update(status='LATE')
        
        # الأقساط المعلقة
        Installment.objects.filter(
            due_date__gte=date.today(),
            paid_amount__lt=models.F('amount')
        ).update(status='PENDING')
    
    @staticmethod
    def get_customer_installments_summary(customer):
        """ملخص أقساط العميل"""
        from ..models import Installment
        
        installments = Installment.objects.filter(
            contract__customer=customer
        )
        
        total_amount = installments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        paid_amount = installments.aggregate(
            total=models.Sum('paid_amount')
        )['total'] or Decimal('0')
        
        late_installments = installments.filter(status='LATE')
        late_amount = late_installments.aggregate(
            total=models.Sum(models.F('amount') - models.F('paid_amount'))
        )['total'] or Decimal('0')
        
        return {
            'total_installments': installments.count(),
            'paid_installments': installments.filter(status='PAID').count(),
            'late_installments': late_installments.count(),
            'pending_installments': installments.filter(status='PENDING').count(),
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'remaining_amount': total_amount - paid_amount,
            'late_amount': late_amount,
            'payment_percentage': (paid_amount / total_amount * 100) if total_amount > 0 else 0
        }
    
    @staticmethod
    def apply_late_fees(installment, fee_percentage=2):
        """تطبيق غرامة تأخير على القسط"""
        if installment.status != 'LATE':
            return None
        
        days_late = (date.today() - installment.due_date).days
        if days_late <= 0:
            return None
        
        # حساب الغرامة
        remaining_amount = installment.amount - installment.paid_amount
        late_fee = remaining_amount * Decimal(fee_percentage / 100)
        
        # إنشاء قسط إضافي للغرامة
        from ..models import Installment
        
        # الحصول على آخر رقم قسط
        last_seq = installment.contract.installments.order_by('-seq_no').first().seq_no
        
        late_fee_installment = Installment.objects.create(
            contract=installment.contract,
            seq_no=last_seq + 1,
            due_date=date.today(),
            amount=late_fee,
            paid_amount=Decimal('0'),
            status='PENDING'
        )
        
        return late_fee_installment
    
    @staticmethod
    def distribute_payment_to_installments(contract, payment_amount):
        """توزيع دفعة على أقساط العقد حسب الأولوية"""
        remaining_payment = payment_amount
        updated_installments = []
        
        # الحصول على الأقساط غير المدفوعة بالترتيب
        unpaid_installments = contract.installments.filter(
            status__in=['LATE', 'PENDING']
        ).order_by('seq_no')
        
        for installment in unpaid_installments:
            if remaining_payment <= 0:
                break
            
            # المبلغ المتبقي من القسط
            remaining_installment = installment.amount - installment.paid_amount
            
            if remaining_installment > 0:
                # تحديد المبلغ المدفوع لهذا القسط
                payment_for_this = min(remaining_payment, remaining_installment)
                
                # تحديث القسط
                installment.paid_amount += payment_for_this
                installment.update_status()
                
                updated_installments.append(installment)
                remaining_payment -= payment_for_this
        
        return updated_installments, remaining_payment