from django.test import TestCase
from decimal import Decimal
from datetime import date, timedelta
from ..models import Contract, Customer, Unit, Installment, ReceiptVoucher, Safe
from ..services import InstallmentService


class InstallmentTestCase(TestCase):
    """اختبارات الأقساط"""
    
    def setUp(self):
        """إعداد البيانات الأساسية للاختبار"""
        # إنشاء عميل
        self.customer = Customer.objects.create(
            code='TEST001',
            name='عميل اختباري',
            phone='01234567890',
            is_active=True
        )
        
        # إنشاء وحدة
        self.unit = Unit.objects.create(
            code='U001',
            name='وحدة اختبارية',
            unit_type='residential',
            price_total=Decimal('1000000.00'),
            group='res'
        )
        
        # إنشاء خزنة
        self.safe = Safe.objects.create(
            name='خزنة اختبارية',
            is_partner_wallet=False
        )
        
        # إنشاء عقد
        self.contract = Contract.objects.create(
            code='CNT001',
            customer=self.customer,
            unit=self.unit,
            unit_value=Decimal('1000000.00'),
            down_payment=Decimal('100000.00'),
            installments_count=10,
            schedule_type='monthly',
            start_date=date.today() - timedelta(days=180)
        )
    
    def test_installment_payment(self):
        """اختبار سداد قسط"""
        installment = self.contract.installments.first()
        original_amount = installment.amount
        
        # إنشاء سند قبض مرتبط بالقسط
        receipt = ReceiptVoucher.objects.create(
            date=date.today(),
            amount=original_amount,
            safe=self.safe,
            description='سداد قسط',
            customer=self.customer,
            contract=self.contract,
            installment=installment
        )
        
        # إعادة تحميل القسط
        installment.refresh_from_db()
        
        # التحقق من تحديث المبلغ المدفوع والحالة
        self.assertEqual(installment.paid_amount, original_amount)
        self.assertEqual(installment.status, 'PAID')
    
    def test_partial_payment(self):
        """اختبار السداد الجزئي للقسط"""
        installment = self.contract.installments.first()
        installment_amount = installment.amount
        partial_amount = installment_amount / 2
        
        # سداد جزئي
        InstallmentService.process_payment(installment, partial_amount)
        
        self.assertEqual(installment.paid_amount, partial_amount)
        self.assertEqual(installment.get_remaining_amount(), partial_amount)
        self.assertNotEqual(installment.status, 'PAID')
    
    def test_late_installment_status(self):
        """اختبار تحديث حالة القسط المتأخر"""
        # إنشاء قسط بتاريخ استحقاق في الماضي
        late_installment = self.contract.installments.filter(
            due_date__lt=date.today()
        ).first()
        
        if late_installment:
            # التحقق من أن القسط غير المدفوع يصبح متأخراً
            InstallmentService.update_installment_status(late_installment)
            self.assertEqual(late_installment.status, 'LATE')
    
    def test_overpayment_handling(self):
        """اختبار معالجة الدفع الزائد"""
        installment = self.contract.installments.first()
        installment_amount = installment.amount
        overpayment = installment_amount + Decimal('1000.00')
        
        # محاولة دفع أكثر من قيمة القسط
        InstallmentService.process_payment(installment, overpayment)
        
        # التحقق من أن المدفوع لا يتجاوز قيمة القسط
        self.assertEqual(installment.paid_amount, installment_amount)
        self.assertEqual(installment.status, 'PAID')
    
    def test_distribute_payment_to_installments(self):
        """اختبار توزيع دفعة على عدة أقساط"""
        # الحصول على أول 3 أقساط
        installments = list(self.contract.installments.all()[:3])
        total_amount = sum(inst.amount for inst in installments)
        
        # دفع مبلغ يكفي لسداد 2.5 قسط
        payment_amount = installments[0].amount + installments[1].amount + (installments[2].amount / 2)
        
        updated_installments, remaining = InstallmentService.distribute_payment_to_installments(
            self.contract, payment_amount
        )
        
        # إعادة تحميل الأقساط
        for inst in installments:
            inst.refresh_from_db()
        
        # التحقق من سداد أول قسطين بالكامل
        self.assertEqual(installments[0].status, 'PAID')
        self.assertEqual(installments[1].status, 'PAID')
        
        # التحقق من السداد الجزئي للقسط الثالث
        self.assertEqual(installments[2].paid_amount, installments[2].amount / 2)
        self.assertNotEqual(installments[2].status, 'PAID')