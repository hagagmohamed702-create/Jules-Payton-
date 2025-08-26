from django.test import TestCase
from decimal import Decimal
from datetime import date
from ..models import Safe, Customer, Supplier, ReceiptVoucher, PaymentVoucher
from ..services import TreasuryService


class VoucherTestCase(TestCase):
    """اختبارات السندات"""
    
    def setUp(self):
        """إعداد البيانات الأساسية للاختبار"""
        # إنشاء خزنة
        self.safe = Safe.objects.create(
            name='الخزنة الرئيسية',
            is_partner_wallet=False
        )
        
        # إنشاء عميل
        self.customer = Customer.objects.create(
            code='C001',
            name='عميل اختباري',
            phone='01234567890'
        )
        
        # إنشاء مورد
        self.supplier = Supplier.objects.create(
            name='مورد اختباري',
            phone='01234567890'
        )
    
    def test_receipt_voucher_creation(self):
        """اختبار إنشاء سند قبض"""
        receipt = ReceiptVoucher.objects.create(
            date=date.today(),
            amount=Decimal('5000.00'),
            safe=self.safe,
            description='إيداع نقدي',
            customer=self.customer
        )
        
        self.assertIsNotNone(receipt.voucher_number)
        self.assertTrue(receipt.voucher_number.startswith('RV-'))
        self.assertEqual(receipt.amount, Decimal('5000.00'))
    
    def test_payment_voucher_creation(self):
        """اختبار إنشاء سند صرف"""
        payment = PaymentVoucher.objects.create(
            date=date.today(),
            amount=Decimal('3000.00'),
            safe=self.safe,
            description='دفعة للمورد',
            supplier=self.supplier,
            expense_head='مشتريات'
        )
        
        self.assertIsNotNone(payment.voucher_number)
        self.assertTrue(payment.voucher_number.startswith('PV-'))
        self.assertEqual(payment.amount, Decimal('3000.00'))
    
    def test_safe_balance_calculation(self):
        """اختبار حساب رصيد الخزنة"""
        # الرصيد الأولي يجب أن يكون صفر
        initial_balance = TreasuryService.get_safe_balance(self.safe)
        self.assertEqual(initial_balance['balance'], Decimal('0'))
        
        # إضافة سند قبض
        ReceiptVoucher.objects.create(
            date=date.today(),
            amount=Decimal('10000.00'),
            safe=self.safe,
            description='إيداع',
            customer=self.customer
        )
        
        # الرصيد يجب أن يزيد
        balance_after_receipt = TreasuryService.get_safe_balance(self.safe)
        self.assertEqual(balance_after_receipt['receipts'], Decimal('10000.00'))
        self.assertEqual(balance_after_receipt['balance'], Decimal('10000.00'))
        
        # إضافة سند صرف
        PaymentVoucher.objects.create(
            date=date.today(),
            amount=Decimal('3000.00'),
            safe=self.safe,
            description='صرف',
            supplier=self.supplier
        )
        
        # الرصيد يجب أن ينقص
        final_balance = TreasuryService.get_safe_balance(self.safe)
        self.assertEqual(final_balance['payments'], Decimal('3000.00'))
        self.assertEqual(final_balance['balance'], Decimal('7000.00'))
    
    def test_voucher_number_sequence(self):
        """اختبار تسلسل أرقام السندات"""
        # إنشاء عدة سندات قبض
        receipts = []
        for i in range(3):
            receipt = ReceiptVoucher.objects.create(
                date=date.today(),
                amount=Decimal('1000.00'),
                safe=self.safe,
                description=f'سند {i+1}'
            )
            receipts.append(receipt)
        
        # التحقق من التسلسل
        self.assertEqual(receipts[0].voucher_number, 'RV-000001')
        self.assertEqual(receipts[1].voucher_number, 'RV-000002')
        self.assertEqual(receipts[2].voucher_number, 'RV-000003')
        
        # نفس الشيء لسندات الصرف
        payments = []
        for i in range(2):
            payment = PaymentVoucher.objects.create(
                date=date.today(),
                amount=Decimal('500.00'),
                safe=self.safe,
                description=f'سند صرف {i+1}'
            )
            payments.append(payment)
        
        self.assertEqual(payments[0].voucher_number, 'PV-000001')
        self.assertEqual(payments[1].voucher_number, 'PV-000002')
    
    def test_safe_balance_with_date_filter(self):
        """اختبار حساب رصيد الخزنة مع فلترة التواريخ"""
        from datetime import timedelta
        
        # سند قبض قديم
        ReceiptVoucher.objects.create(
            date=date.today() - timedelta(days=30),
            amount=Decimal('5000.00'),
            safe=self.safe,
            description='إيداع قديم'
        )
        
        # سند قبض حديث
        ReceiptVoucher.objects.create(
            date=date.today(),
            amount=Decimal('3000.00'),
            safe=self.safe,
            description='إيداع حديث'
        )
        
        # الرصيد الكامل
        full_balance = TreasuryService.get_safe_balance(self.safe)
        self.assertEqual(full_balance['balance'], Decimal('8000.00'))
        
        # الرصيد لليوم فقط
        today_balance = TreasuryService.get_safe_balance(
            self.safe,
            from_date=date.today(),
            to_date=date.today()
        )
        self.assertEqual(today_balance['balance'], Decimal('3000.00'))