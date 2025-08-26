from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
from ..models import Installment


class ContractService:
    """خدمة إدارة العقود والأقساط"""
    
    @staticmethod
    def generate_installments(contract):
        """توليد جدول الأقساط للعقد"""
        if contract.installments_count == 0:
            return []
        
        # حساب قيمة القسط الأساسية
        remaining_amount = contract.unit_value - contract.down_payment
        base_installment = remaining_amount / contract.installments_count
        
        # تقريب قيمة القسط إلى أقرب قرش
        base_installment = base_installment.quantize(
            Decimal('0.01'), 
            rounding=ROUND_HALF_UP
        )
        
        installments = []
        current_date = contract.start_date
        total_installments_amount = Decimal('0')
        
        # حدد الفترة الزمنية حسب نوع الجدولة
        if contract.schedule_type == 'monthly':
            delta = relativedelta(months=1)
        elif contract.schedule_type == 'quarterly':
            delta = relativedelta(months=3)
        else:  # yearly
            delta = relativedelta(years=1)
        
        # إنشاء الأقساط
        for i in range(contract.installments_count):
            if i == contract.installments_count - 1:
                # آخر قسط يأخذ الفرق لضمان دقة المجموع
                installment_amount = remaining_amount - total_installments_amount
            else:
                installment_amount = base_installment
                total_installments_amount += installment_amount
            
            installment = Installment(
                contract=contract,
                seq_no=i + 1,
                due_date=current_date,
                amount=installment_amount,
                paid_amount=Decimal('0'),
                status='PENDING'
            )
            installments.append(installment)
            
            current_date += delta
        
        # حفظ جميع الأقساط
        Installment.objects.bulk_create(installments)
        
        return installments
    
    @staticmethod
    def recalculate_installments(contract, new_schedule=None):
        """إعادة حساب الأقساط (في حالة تعديل العقد)"""
        # حذف الأقساط غير المدفوعة
        contract.installments.filter(status__in=['PENDING', 'LATE']).delete()
        
        # حساب المبلغ المتبقي
        total_paid = contract.installments.filter(status='PAID').aggregate(
            total=models.Sum('paid_amount')
        )['total'] or Decimal('0')
        
        remaining_amount = contract.unit_value - contract.down_payment - total_paid
        remaining_count = contract.installments_count - contract.installments.filter(status='PAID').count()
        
        if remaining_count > 0 and remaining_amount > 0:
            # إنشاء أقساط جديدة للمبلغ المتبقي
            base_installment = remaining_amount / remaining_count
            base_installment = base_installment.quantize(
                Decimal('0.01'), 
                rounding=ROUND_HALF_UP
            )
            
            # الحصول على آخر قسط مدفوع
            last_paid = contract.installments.filter(status='PAID').order_by('-seq_no').first()
            start_seq = (last_paid.seq_no + 1) if last_paid else 1
            
            # تحديد تاريخ البداية
            if last_paid:
                current_date = last_paid.due_date
                if contract.schedule_type == 'monthly':
                    current_date += relativedelta(months=1)
                elif contract.schedule_type == 'quarterly':
                    current_date += relativedelta(months=3)
                else:
                    current_date += relativedelta(years=1)
            else:
                current_date = new_schedule or contract.start_date
            
            # إنشاء الأقساط الجديدة
            installments = []
            total_new_amount = Decimal('0')
            
            for i in range(remaining_count):
                if i == remaining_count - 1:
                    installment_amount = remaining_amount - total_new_amount
                else:
                    installment_amount = base_installment
                    total_new_amount += installment_amount
                
                installment = Installment(
                    contract=contract,
                    seq_no=start_seq + i,
                    due_date=current_date,
                    amount=installment_amount,
                    paid_amount=Decimal('0'),
                    status='PENDING'
                )
                installments.append(installment)
                
                if contract.schedule_type == 'monthly':
                    current_date += relativedelta(months=1)
                elif contract.schedule_type == 'quarterly':
                    current_date += relativedelta(months=3)
                else:
                    current_date += relativedelta(years=1)
            
            Installment.objects.bulk_create(installments)
    
    @staticmethod
    def get_contract_summary(contract):
        """الحصول على ملخص العقد"""
        installments = contract.installments.all()
        
        paid_installments = installments.filter(status='PAID')
        late_installments = installments.filter(status='LATE')
        pending_installments = installments.filter(status='PENDING')
        
        total_paid = paid_installments.aggregate(
            total=models.Sum('paid_amount')
        )['total'] or Decimal('0')
        
        return {
            'contract_value': contract.unit_value,
            'down_payment': contract.down_payment,
            'total_installments': contract.installments_count,
            'paid_installments_count': paid_installments.count(),
            'late_installments_count': late_installments.count(),
            'pending_installments_count': pending_installments.count(),
            'total_paid': contract.down_payment + total_paid,
            'remaining_amount': contract.unit_value - (contract.down_payment + total_paid),
            'completion_percentage': ((contract.down_payment + total_paid) / contract.unit_value * 100) if contract.unit_value > 0 else 0
        }