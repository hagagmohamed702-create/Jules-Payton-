from django.test import TestCase
from decimal import Decimal
from datetime import date
from ..models import Contract, Customer, Unit, Installment, Partner, PartnersGroup


class ContractTestCase(TestCase):
    """اختبارات العقود"""
    
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
    
    def test_contract_creation(self):
        """اختبار إنشاء عقد جديد"""
        contract = Contract.objects.create(
            code='CNT001',
            customer=self.customer,
            unit=self.unit,
            unit_value=self.unit.price_total,
            down_payment=Decimal('200000.00'),
            installments_count=60,
            schedule_type='monthly',
            start_date=date.today()
        )
        
        self.assertEqual(contract.code, 'CNT001')
        self.assertEqual(contract.unit_value, Decimal('1000000.00'))
        self.assertEqual(contract.get_remaining_amount(), Decimal('800000.00'))
    
    def test_installments_generation(self):
        """اختبار توليد الأقساط"""
        contract = Contract.objects.create(
            code='CNT002',
            customer=self.customer,
            unit=self.unit,
            unit_value=Decimal('1000000.00'),
            down_payment=Decimal('200000.00'),
            installments_count=10,
            schedule_type='monthly',
            start_date=date.today()
        )
        
        # التحقق من عدد الأقساط
        installments = contract.installments.all()
        self.assertEqual(installments.count(), 10)
        
        # التحقق من مجموع الأقساط
        total_installments = sum(inst.amount for inst in installments)
        self.assertEqual(total_installments, Decimal('800000.00'))
        
        # التحقق من قيمة القسط الواحد
        expected_installment = Decimal('80000.00')
        self.assertEqual(installments.first().amount, expected_installment)
    
    def test_installments_with_rounding(self):
        """اختبار توليد الأقساط مع التقريب"""
        contract = Contract.objects.create(
            code='CNT003',
            customer=self.customer,
            unit=self.unit,
            unit_value=Decimal('1000000.00'),
            down_payment=Decimal('100000.00'),
            installments_count=7,  # عدد لا يقسم بدون باقي
            schedule_type='monthly',
            start_date=date.today()
        )
        
        installments = contract.installments.all()
        
        # التحقق من أن مجموع الأقساط يساوي المبلغ المتبقي بالضبط
        total_installments = sum(inst.amount for inst in installments)
        expected_total = contract.unit_value - contract.down_payment
        self.assertEqual(total_installments, expected_total)
        
        # التحقق من أن آخر قسط يحتوي على الفرق
        base_amount = (expected_total / 7).quantize(Decimal('0.01'))
        last_installment = installments.last()
        
        # آخر قسط قد يكون مختلفاً قليلاً بسبب التقريب
        self.assertAlmostEqual(
            float(last_installment.amount),
            float(expected_total - (base_amount * 6)),
            places=2
        )
    
    def test_contract_validation(self):
        """اختبار التحقق من صحة بيانات العقد"""
        # محاولة إنشاء عقد بدفعة مقدمة أكبر من قيمة الوحدة
        with self.assertRaises(Exception):
            contract = Contract(
                code='CNT004',
                customer=self.customer,
                unit=self.unit,
                unit_value=Decimal('1000000.00'),
                down_payment=Decimal('1500000.00'),  # أكبر من قيمة الوحدة
                installments_count=10,
                schedule_type='monthly',
                start_date=date.today()
            )
            contract.full_clean()
    
    def test_unit_marked_as_sold(self):
        """اختبار تحديد الوحدة كمباعة عند إنشاء عقد"""
        self.assertFalse(self.unit.is_sold)
        
        contract = Contract.objects.create(
            code='CNT005',
            customer=self.customer,
            unit=self.unit,
            unit_value=self.unit.price_total,
            down_payment=Decimal('200000.00'),
            installments_count=60,
            schedule_type='monthly',
            start_date=date.today()
        )
        
        # إعادة تحميل الوحدة من قاعدة البيانات
        self.unit.refresh_from_db()
        self.assertTrue(self.unit.is_sold)