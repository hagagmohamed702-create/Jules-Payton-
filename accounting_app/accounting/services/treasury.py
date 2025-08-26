from decimal import Decimal
from datetime import date, datetime
from django.db.models import Sum, Q
from ..models import ReceiptVoucher, PaymentVoucher, Safe, Partner


class TreasuryService:
    """خدمة إدارة الخزينة والمحافظ"""
    
    @staticmethod
    def get_safe_balance(safe, from_date=None, to_date=None):
        """حساب رصيد الخزنة/المحفظة"""
        # فلترة التواريخ
        date_filter = Q()
        if from_date:
            date_filter &= Q(date__gte=from_date)
        if to_date:
            date_filter &= Q(date__lte=to_date)
        
        # حساب إجمالي القبض
        receipts_total = ReceiptVoucher.objects.filter(
            safe=safe
        ).filter(date_filter).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # حساب إجمالي الصرف
        payments_total = PaymentVoucher.objects.filter(
            safe=safe
        ).filter(date_filter).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # الرصيد = القبض - الصرف
        balance = receipts_total - payments_total
        
        return {
            'receipts': receipts_total,
            'payments': payments_total,
            'balance': balance
        }
    
    @staticmethod
    def get_partner_balance(partner):
        """حساب رصيد الشريك (محفظته + حصته من الخزائن العامة)"""
        balance = partner.opening_balance
        
        # رصيد محفظة الشريك الشخصية
        try:
            wallet = partner.wallet
            wallet_balance = TreasuryService.get_safe_balance(wallet)
            balance += wallet_balance['balance']
        except Safe.DoesNotExist:
            pass
        
        # حصة الشريك من الخزائن العامة
        general_safes = Safe.objects.filter(is_partner_wallet=False)
        for safe in general_safes:
            safe_balance = TreasuryService.get_safe_balance(safe)
            # حصة الشريك = رصيد الخزنة × نسبة الشريك
            partner_share = safe_balance['balance'] * (partner.share_percent / 100)
            balance += partner_share
        
        return balance
    
    @staticmethod
    def get_all_safes_summary():
        """ملخص جميع الخزائن والمحافظ"""
        safes = Safe.objects.all()
        summary = []
        total_balance = Decimal('0')
        
        for safe in safes:
            safe_data = TreasuryService.get_safe_balance(safe)
            safe_data['safe'] = safe
            summary.append(safe_data)
            total_balance += safe_data['balance']
        
        return {
            'safes': summary,
            'total_balance': total_balance
        }
    
    @staticmethod
    def get_cash_flow(from_date, to_date, safe=None):
        """تقرير التدفق النقدي"""
        # فلترة الخزنة
        safe_filter = Q()
        if safe:
            safe_filter = Q(safe=safe)
        
        # فلترة التواريخ
        date_filter = Q(date__gte=from_date, date__lte=to_date)
        
        # الحصول على السندات
        receipts = ReceiptVoucher.objects.filter(
            date_filter & safe_filter
        ).order_by('date')
        
        payments = PaymentVoucher.objects.filter(
            date_filter & safe_filter
        ).order_by('date')
        
        # دمج وترتيب السندات
        cash_flow = []
        
        for receipt in receipts:
            cash_flow.append({
                'date': receipt.date,
                'type': 'receipt',
                'voucher_number': receipt.voucher_number,
                'description': receipt.description,
                'amount_in': receipt.amount,
                'amount_out': Decimal('0'),
                'safe': receipt.safe.name
            })
        
        for payment in payments:
            cash_flow.append({
                'date': payment.date,
                'type': 'payment',
                'voucher_number': payment.voucher_number,
                'description': payment.description,
                'amount_in': Decimal('0'),
                'amount_out': payment.amount,
                'safe': payment.safe.name
            })
        
        # ترتيب حسب التاريخ
        cash_flow.sort(key=lambda x: x['date'])
        
        # حساب الرصيد التراكمي
        running_balance = Decimal('0')
        for item in cash_flow:
            running_balance += item['amount_in'] - item['amount_out']
            item['balance'] = running_balance
        
        return cash_flow
    
    @staticmethod
    def transfer_between_safes(from_safe, to_safe, amount, description, user=None):
        """تحويل مبلغ بين خزنتين"""
        if amount <= 0:
            raise ValueError("مبلغ التحويل يجب أن يكون أكبر من صفر")
        
        # التحقق من الرصيد
        from_balance = TreasuryService.get_safe_balance(from_safe)
        if from_balance['balance'] < amount:
            raise ValueError("الرصيد غير كافي للتحويل")
        
        # إنشاء سند صرف من الخزنة المصدر
        payment = PaymentVoucher.objects.create(
            safe=from_safe,
            amount=amount,
            description=f"تحويل إلى {to_safe.name}: {description}",
            created_by=user
        )
        
        # إنشاء سند قبض في الخزنة المستقبلة
        receipt = ReceiptVoucher.objects.create(
            safe=to_safe,
            amount=amount,
            description=f"تحويل من {from_safe.name}: {description}",
            created_by=user
        )
        
        return {
            'payment_voucher': payment,
            'receipt_voucher': receipt
        }
    
    @staticmethod
    def get_partner_transactions(partner, from_date=None, to_date=None):
        """الحصول على معاملات الشريك"""
        transactions = []
        
        # فلترة التواريخ
        date_filter = Q()
        if from_date:
            date_filter &= Q(date__gte=from_date)
        if to_date:
            date_filter &= Q(date__lte=to_date)
        
        # سندات القبض المباشرة للشريك
        receipts = ReceiptVoucher.objects.filter(
            partner=partner
        ).filter(date_filter)
        
        for receipt in receipts:
            transactions.append({
                'date': receipt.date,
                'type': 'receipt',
                'voucher_number': receipt.voucher_number,
                'description': receipt.description,
                'debit': receipt.amount,
                'credit': Decimal('0'),
                'safe': receipt.safe.name
            })
        
        # سندات الصرف من محفظة الشريك
        try:
            partner_wallet = partner.wallet
            payments = PaymentVoucher.objects.filter(
                safe=partner_wallet
            ).filter(date_filter)
            
            for payment in payments:
                transactions.append({
                    'date': payment.date,
                    'type': 'payment',
                    'voucher_number': payment.voucher_number,
                    'description': payment.description,
                    'debit': Decimal('0'),
                    'credit': payment.amount,
                    'safe': payment.safe.name
                })
        except Safe.DoesNotExist:
            pass
        
        # ترتيب حسب التاريخ
        transactions.sort(key=lambda x: x['date'])
        
        return transactions