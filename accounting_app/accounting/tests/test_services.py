from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
from ..models import (
    Customer, Unit, Contract, Installment, Safe, 
    ReceiptVoucher, Partner, PartnersGroup, PartnersGroupMember
)
from ..services.installment_service import InstallmentService
from ..services.voucher_service import VoucherService
from ..services.settlement_service import SettlementService


class InstallmentServiceTest(TestCase):
    """اختبارات خدمة الأقساط"""
    
    def setUp(self):
        self.customer = Customer.objects.create(name='عميل تجريبي')
        self.unit = Unit.objects.create(
            name='وحدة تجريبية',
            total_price=Decimal('300000')
        )
        self.safe = Safe.objects.create(
            name='خزينة تجريبية',
            balance=Decimal('50000')
        )
        self.contract = Contract.objects.create(
            customer=self.customer,
            unit=self.unit,
            unit_price=Decimal('300000'),
            down_payment=Decimal('60000'),
            installments_count=6,
            installment_type='monthly'
        )
        self.contract.generate_installments()
        
    def test_process_payment(self):
        """اختبار معالجة دفعة قسط"""
        installment = self.contract.installments.first()
        initial_safe_balance = self.safe.balance
        
        # دفع القسط
        payment = InstallmentService.process_payment(
            installment=installment,
            amount=Decimal('20000'),
            payment_date=date.today(),
            safe=self.safe,
            notes='دفعة تجريبية'
        )
        
        # التحقق من تحديث القسط
        installment.refresh_from_db()
        self.assertEqual(installment.paid_amount, Decimal('20000'))
        self.assertEqual(installment.status, 'partial')
        
        # التحقق من تحديث الخزينة
        self.safe.refresh_from_db()
        self.assertEqual(
            self.safe.balance,
            initial_safe_balance + Decimal('20000')
        )
        
        # التحقق من إنشاء سند القبض
        self.assertIsNotNone(payment.receipt_voucher)
        self.assertEqual(payment.amount, Decimal('20000'))
    
    def test_get_overdue_installments(self):
        """اختبار الحصول على الأقساط المتأخرة"""
        # جعل قسط متأخر
        installment = self.contract.installments.first()
        installment.due_date = date.today() - timedelta(days=10)
        installment.save()
        
        overdue = InstallmentService.get_overdue_installments()
        self.assertIn(installment, overdue)
    
    def test_calculate_late_fees(self):
        """اختبار حساب غرامات التأخير"""
        installment = self.contract.installments.first()
        installment.due_date = date.today() - timedelta(days=30)
        installment.save()
        
        # حساب الغرامة (2% شهرياً)
        late_fee = InstallmentService.calculate_late_fees(installment, fee_percentage=2)
        expected_fee = installment.amount * Decimal('0.02')
        
        self.assertEqual(late_fee, expected_fee)


class VoucherServiceTest(TestCase):
    """اختبارات خدمة السندات"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.customer = Customer.objects.create(name='عميل تجريبي')
        self.safe = Safe.objects.create(
            name='خزينة تجريبية',
            balance=Decimal('100000')
        )
        
    def test_create_receipt_voucher(self):
        """اختبار إنشاء سند قبض"""
        initial_balance = self.safe.balance
        
        voucher = VoucherService.create_receipt_voucher(
            customer=self.customer,
            amount=Decimal('5000'),
            payment_date=date.today(),
            safe=self.safe,
            notes='سند قبض تجريبي',
            created_by=self.user
        )
        
        # التحقق من السند
        self.assertEqual(voucher.amount, Decimal('5000'))
        self.assertTrue(voucher.voucher_number.startswith('RV'))
        
        # التحقق من تحديث الخزينة
        self.safe.refresh_from_db()
        self.assertEqual(self.safe.balance, initial_balance + Decimal('5000'))
    
    def test_create_payment_voucher(self):
        """اختبار إنشاء سند صرف"""
        initial_balance = self.safe.balance
        
        voucher = VoucherService.create_payment_voucher(
            supplier=None,
            amount=Decimal('3000'),
            payment_date=date.today(),
            safe=self.safe,
            expense_type='materials',
            notes='سند صرف تجريبي',
            created_by=self.user
        )
        
        # التحقق من السند
        self.assertEqual(voucher.amount, Decimal('3000'))
        self.assertTrue(voucher.voucher_number.startswith('PV'))
        
        # التحقق من تحديث الخزينة
        self.safe.refresh_from_db()
        self.assertEqual(self.safe.balance, initial_balance - Decimal('3000'))
    
    def test_insufficient_balance(self):
        """اختبار عدم كفاية الرصيد"""
        self.safe.balance = Decimal('1000')
        self.safe.save()
        
        with self.assertRaises(ValueError):
            VoucherService.create_payment_voucher(
                supplier=None,
                amount=Decimal('2000'),
                payment_date=date.today(),
                safe=self.safe,
                created_by=self.user
            )


class SettlementServiceTest(TestCase):
    """اختبارات خدمة التسويات"""
    
    def setUp(self):
        # إنشاء شركاء
        self.partner1 = Partner.objects.create(
            name='شريك 1',
            balance=Decimal('0')
        )
        self.partner2 = Partner.objects.create(
            name='شريك 2',
            balance=Decimal('0')
        )
        
        # إنشاء مجموعة
        self.group = PartnersGroup.objects.create(
            name='مجموعة تجريبية'
        )
        
        # إضافة الأعضاء
        PartnersGroupMember.objects.create(
            group=self.group,
            partner=self.partner1,
            share_percentage=Decimal('50')
        )
        PartnersGroupMember.objects.create(
            group=self.group,
            partner=self.partner2,
            share_percentage=Decimal('50')
        )
    
    def test_calculate_partner_share(self):
        """اختبار حساب حصة الشريك"""
        # محاكاة مصروفات المجموعة
        share = SettlementService.calculate_partner_share(
            self.partner1,
            self.group
        )
        
        # مع نسبة 50%، يجب أن تكون الحصة نصف المصروفات
        self.assertEqual(share, Decimal('0'))  # لا توجد مصروفات حتى الآن
    
    def test_calculate_settlements(self):
        """اختبار حساب التسويات"""
        # محاكاة اختلاف في المصروفات
        # (يحتاج لمزيد من التطوير في الخدمة الفعلية)
        
        settlements_data = SettlementService.calculate_settlements(self.group)
        
        self.assertIn('partners', settlements_data)
        self.assertIn('settlements_needed', settlements_data)
        self.assertEqual(len(settlements_data['partners']), 2)