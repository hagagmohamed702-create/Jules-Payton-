from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import Installment, ReceiptVoucher, InstallmentPayment


class InstallmentService:
    """خدمة إدارة الأقساط والدفعات"""
    
    @staticmethod
    @transaction.atomic
    def process_payment(installment, amount, payment_date, safe, notes=''):
        """معالجة دفعة قسط"""
        
        # إنشاء سند قبض
        voucher = ReceiptVoucher.objects.create(
            customer=installment.contract.customer,
            contract=installment.contract,
            amount=amount,
            payment_date=payment_date,
            safe=safe,
            notes=notes or f'دفعة من القسط رقم {installment.installment_number}'
        )
        
        # إنشاء سجل دفعة القسط
        payment = InstallmentPayment.objects.create(
            installment=installment,
            receipt_voucher=voucher,
            amount=amount
        )
        
        # تحديث المبلغ المدفوع في القسط
        installment.paid_amount += amount
        
        # تحديث حالة القسط
        if installment.paid_amount >= installment.amount:
            installment.status = 'paid'
            installment.payment_date = payment_date
        else:
            installment.status = 'partial'
        
        installment.save()
        
        # تحديث رصيد الخزينة
        safe.balance += amount
        safe.save()
        
        # توزيع المبلغ على الشركاء
        if installment.contract.partners_group:
            InstallmentService._distribute_to_partners(
                installment.contract.partners_group,
                amount
            )
        
        return payment
    
    @staticmethod
    def _distribute_to_partners(partners_group, amount):
        """توزيع المبلغ على الشركاء حسب نسبهم"""
        for member in partners_group.members.all():
            share_amount = (member.share_percentage / 100) * amount
            
            # تحديث رصيد الشريك
            partner = member.partner
            partner.balance += share_amount
            partner.save()
    
    @staticmethod
    def get_overdue_installments():
        """الحصول على الأقساط المتأخرة"""
        today = timezone.now().date()
        return Installment.objects.filter(
            due_date__lt=today,
            status__in=['pending', 'partial']
        ).select_related('contract__customer', 'contract__unit')
    
    @staticmethod
    def calculate_late_fees(installment, fee_percentage=2):
        """حساب غرامات التأخير"""
        if installment.status == 'paid':
            return Decimal('0')
        
        today = timezone.now().date()
        if installment.due_date >= today:
            return Decimal('0')
        
        days_late = (today - installment.due_date).days
        remaining_amount = installment.amount - installment.paid_amount
        
        # حساب الغرامة (نسبة مئوية شهرية)
        months_late = days_late / 30
        late_fee = remaining_amount * (fee_percentage / 100) * months_late
        
        return round(late_fee, 2)
    
    @staticmethod
    def get_upcoming_installments(days=7):
        """الحصول على الأقساط القادمة خلال عدد معين من الأيام"""
        today = timezone.now().date()
        end_date = today + timezone.timedelta(days=days)
        
        return Installment.objects.filter(
            due_date__gte=today,
            due_date__lte=end_date,
            status__in=['pending', 'partial']
        ).select_related('contract__customer', 'contract__unit')
    
    @staticmethod
    def get_customer_payment_history(customer):
        """الحصول على تاريخ دفعات العميل"""
        return InstallmentPayment.objects.filter(
            installment__contract__customer=customer
        ).select_related(
            'installment',
            'receipt_voucher'
        ).order_by('-receipt_voucher__payment_date')