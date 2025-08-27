from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import ReceiptVoucher, PaymentVoucher, InstallmentPayment, Installment


class VoucherService:
    """خدمة إدارة سندات القبض والصرف"""
    
    @staticmethod
    @transaction.atomic
    def create_receipt_voucher(customer, amount, payment_date, safe, contract=None, notes='', created_by=None):
        """إنشاء سند قبض"""
        
        # إنشاء السند
        voucher = ReceiptVoucher.objects.create(
            customer=customer,
            contract=contract,
            amount=amount,
            payment_date=payment_date,
            safe=safe,
            notes=notes,
            created_by=created_by
        )
        
        # تحديث رصيد الخزينة
        safe.balance += amount
        safe.save()
        
        # توزيع المبلغ على الشركاء إذا كان هناك عقد
        if contract and contract.partners_group:
            VoucherService._distribute_receipt_to_partners(
                contract.partners_group,
                amount
            )
        
        return voucher
    
    @staticmethod
    @transaction.atomic
    def create_payment_voucher(supplier, amount, payment_date, safe, project=None, 
                             expense_type=None, notes='', created_by=None):
        """إنشاء سند صرف"""
        
        # التحقق من رصيد الخزينة
        if safe.balance < amount:
            raise ValueError('رصيد الخزينة غير كافي')
        
        # إنشاء السند
        voucher = PaymentVoucher.objects.create(
            supplier=supplier,
            project=project,
            amount=amount,
            payment_date=payment_date,
            safe=safe,
            expense_type=expense_type,
            notes=notes,
            created_by=created_by
        )
        
        # تحديث رصيد الخزينة
        safe.balance -= amount
        safe.save()
        
        # خصم المبلغ من الشركاء
        VoucherService._distribute_payment_to_partners(amount, created_by)
        
        return voucher
    
    @staticmethod
    def _distribute_receipt_to_partners(partners_group, amount):
        """توزيع إيرادات على الشركاء"""
        for member in partners_group.members.all():
            share_amount = (member.share_percentage / 100) * amount
            partner = member.partner
            partner.balance += share_amount
            partner.save()
    
    @staticmethod
    def _distribute_payment_to_partners(amount, created_by=None):
        """خصم مصروفات من الشركاء"""
        # هنا يمكن تحديد منطق توزيع المصروفات
        # مثلاً: خصم من الشريك الذي قام بالصرف
        if created_by and hasattr(created_by, 'partner'):
            partner = created_by.partner
            partner.balance -= amount
            partner.save()
    
    @staticmethod
    @transaction.atomic
    def link_receipt_to_installments(voucher, installment_ids):
        """ربط سند القبض بالأقساط"""
        
        if not voucher.contract:
            raise ValueError('السند غير مرتبط بعقد')
        
        remaining_amount = voucher.amount
        
        # الحصول على الأقساط المحددة
        installments = Installment.objects.filter(
            id__in=installment_ids,
            contract=voucher.contract,
            status__in=['pending', 'partial']
        ).order_by('installment_number')
        
        for installment in installments:
            if remaining_amount <= 0:
                break
            
            # حساب المبلغ المتبقي من القسط
            installment_remaining = installment.amount - installment.paid_amount
            
            # تحديد المبلغ المدفوع
            payment_amount = min(remaining_amount, installment_remaining)
            
            # إنشاء سجل دفعة القسط
            InstallmentPayment.objects.create(
                installment=installment,
                receipt_voucher=voucher,
                amount=payment_amount
            )
            
            # تحديث القسط
            installment.paid_amount += payment_amount
            
            if installment.paid_amount >= installment.amount:
                installment.status = 'paid'
                installment.payment_date = voucher.payment_date
            else:
                installment.status = 'partial'
            
            installment.save()
            
            remaining_amount -= payment_amount
        
        return voucher
    
    @staticmethod
    @transaction.atomic
    def cancel_receipt_voucher(voucher):
        """إلغاء سند قبض"""
        
        if voucher.is_cancelled:
            raise ValueError('هذا السند ملغي بالفعل')
        
        # إلغاء دفعات الأقساط المرتبطة
        for payment in voucher.installment_payments.all():
            installment = payment.installment
            installment.paid_amount -= payment.amount
            
            # تحديث حالة القسط
            if installment.paid_amount == 0:
                installment.status = 'pending'
                installment.payment_date = None
            else:
                installment.status = 'partial'
            
            installment.save()
            payment.delete()
        
        # تحديث رصيد الخزينة
        voucher.safe.balance -= voucher.amount
        voucher.safe.save()
        
        # عكس توزيع المبلغ على الشركاء
        if voucher.contract and voucher.contract.partners_group:
            for member in voucher.contract.partners_group.members.all():
                share_amount = (member.share_percentage / 100) * voucher.amount
                partner = member.partner
                partner.balance -= share_amount
                partner.save()
        
        # وضع علامة الإلغاء
        voucher.is_cancelled = True
        voucher.cancelled_at = timezone.now()
        voucher.save()
        
        return voucher
    
    @staticmethod
    @transaction.atomic
    def cancel_payment_voucher(voucher):
        """إلغاء سند صرف"""
        
        if voucher.is_cancelled:
            raise ValueError('هذا السند ملغي بالفعل')
        
        # تحديث رصيد الخزينة
        voucher.safe.balance += voucher.amount
        voucher.safe.save()
        
        # عكس خصم المبلغ من الشركاء
        if voucher.created_by and hasattr(voucher.created_by, 'partner'):
            partner = voucher.created_by.partner
            partner.balance += voucher.amount
            partner.save()
        
        # وضع علامة الإلغاء
        voucher.is_cancelled = True
        voucher.cancelled_at = timezone.now()
        voucher.save()
        
        return voucher
    
    @staticmethod
    def get_voucher_statistics(date_from=None, date_to=None):
        """إحصائيات السندات"""
        
        receipt_vouchers = ReceiptVoucher.objects.filter(is_cancelled=False)
        payment_vouchers = PaymentVoucher.objects.filter(is_cancelled=False)
        
        if date_from:
            receipt_vouchers = receipt_vouchers.filter(payment_date__gte=date_from)
            payment_vouchers = payment_vouchers.filter(payment_date__gte=date_from)
        
        if date_to:
            receipt_vouchers = receipt_vouchers.filter(payment_date__lte=date_to)
            payment_vouchers = payment_vouchers.filter(payment_date__lte=date_to)
        
        total_receipts = sum(v.amount for v in receipt_vouchers)
        total_payments = sum(v.amount for v in payment_vouchers)
        
        return {
            'total_receipts': total_receipts,
            'total_payments': total_payments,
            'net_amount': total_receipts - total_payments,
            'receipts_count': receipt_vouchers.count(),
            'payments_count': payment_vouchers.count()
        }