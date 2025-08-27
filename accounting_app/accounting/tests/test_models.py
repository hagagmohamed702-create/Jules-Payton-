from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
from ..models import (
    Partner, PartnersGroup, PartnersGroupMember, Safe, Customer,
    Supplier, Unit, Contract, Installment, Project, Item
)


class PartnerModelTest(TestCase):
    """اختبارات نموذج الشريك"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_create_partner(self):
        """اختبار إنشاء شريك"""
        partner = Partner.objects.create(
            name='أحمد محمد',
            phone='0501234567',
            email='ahmad@example.com',
            balance=Decimal('100000'),
            user=self.user
        )
        
        self.assertEqual(partner.name, 'أحمد محمد')
        self.assertEqual(partner.balance, Decimal('100000'))
        self.assertEqual(str(partner), 'أحمد محمد')


class PartnersGroupModelTest(TestCase):
    """اختبارات نموذج مجموعة الشركاء"""
    
    def setUp(self):
        self.partner1 = Partner.objects.create(
            name='شريك 1',
            balance=Decimal('50000')
        )
        self.partner2 = Partner.objects.create(
            name='شريك 2',
            balance=Decimal('50000')
        )
        
    def test_create_partners_group(self):
        """اختبار إنشاء مجموعة شركاء"""
        group = PartnersGroup.objects.create(
            name='المجموعة الأولى',
            description='مجموعة تجريبية'
        )
        
        # إضافة أعضاء
        PartnersGroupMember.objects.create(
            group=group,
            partner=self.partner1,
            share_percentage=Decimal('60')
        )
        PartnersGroupMember.objects.create(
            group=group,
            partner=self.partner2,
            share_percentage=Decimal('40')
        )
        
        self.assertEqual(group.members.count(), 2)
        self.assertEqual(group.get_total_percentage(), Decimal('100'))


class SafeModelTest(TestCase):
    """اختبارات نموذج الخزينة"""
    
    def test_create_safe(self):
        """اختبار إنشاء خزينة"""
        safe = Safe.objects.create(
            name='الخزينة الرئيسية',
            balance=Decimal('100000')
        )
        
        self.assertEqual(safe.name, 'الخزينة الرئيسية')
        self.assertEqual(safe.balance, Decimal('100000'))
        self.assertTrue(safe.is_active)


class CustomerModelTest(TestCase):
    """اختبارات نموذج العميل"""
    
    def test_create_customer(self):
        """اختبار إنشاء عميل"""
        customer = Customer.objects.create(
            name='محمد علي',
            phone='0551234567',
            email='mohamed@example.com',
            address='الرياض'
        )
        
        self.assertEqual(customer.name, 'محمد علي')
        self.assertTrue(customer.is_active)
        self.assertEqual(str(customer), 'محمد علي')


class UnitModelTest(TestCase):
    """اختبارات نموذج الوحدة"""
    
    def test_create_unit(self):
        """اختبار إنشاء وحدة"""
        unit = Unit.objects.create(
            name='وحدة A101',
            building_number='عمارة A',
            unit_type='residential',
            unit_group='residential',
            total_price=Decimal('500000')
        )
        
        self.assertEqual(unit.name, 'وحدة A101')
        self.assertEqual(unit.total_price, Decimal('500000'))
        self.assertFalse(unit.is_sold())


class ContractModelTest(TestCase):
    """اختبارات نموذج العقد"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            name='عميل تجريبي'
        )
        self.unit = Unit.objects.create(
            name='وحدة تجريبية',
            total_price=Decimal('600000')
        )
        
    def test_create_contract(self):
        """اختبار إنشاء عقد"""
        contract = Contract.objects.create(
            customer=self.customer,
            unit=self.unit,
            unit_price=Decimal('600000'),
            down_payment=Decimal('120000'),
            installments_count=24,
            installment_type='monthly',
            contract_date=date.today()
        )
        
        self.assertEqual(contract.unit_price, Decimal('600000'))
        self.assertEqual(contract.installment_amount, Decimal('20000'))
        self.assertTrue(contract.contract_number.startswith('CON'))
    
    def test_generate_installments(self):
        """اختبار توليد الأقساط"""
        contract = Contract.objects.create(
            customer=self.customer,
            unit=self.unit,
            unit_price=Decimal('600000'),
            down_payment=Decimal('120000'),
            installments_count=12,
            installment_type='monthly',
            contract_date=date.today()
        )
        
        # توليد الأقساط
        contract.generate_installments()
        
        self.assertEqual(contract.installments.count(), 12)
        
        # التحقق من قيمة كل قسط
        for installment in contract.installments.all():
            self.assertEqual(installment.amount, Decimal('40000'))


class InstallmentModelTest(TestCase):
    """اختبارات نموذج القسط"""
    
    def setUp(self):
        self.customer = Customer.objects.create(name='عميل')
        self.unit = Unit.objects.create(
            name='وحدة',
            total_price=Decimal('300000')
        )
        self.contract = Contract.objects.create(
            customer=self.customer,
            unit=self.unit,
            unit_price=Decimal('300000'),
            down_payment=Decimal('60000'),
            installments_count=6,
            installment_type='monthly'
        )
        
    def test_installment_status(self):
        """اختبار حالة القسط"""
        installment = Installment.objects.create(
            contract=self.contract,
            installment_number=1,
            amount=Decimal('40000'),
            due_date=date.today() + timedelta(days=30)
        )
        
        # قسط غير مدفوع
        self.assertEqual(installment.status, 'pending')
        self.assertFalse(installment.is_overdue())
        
        # دفع جزئي
        installment.paid_amount = Decimal('20000')
        installment.save()
        self.assertEqual(installment.status, 'partial')
        
        # دفع كامل
        installment.paid_amount = Decimal('40000')
        installment.save()
        self.assertEqual(installment.status, 'paid')


class ProjectModelTest(TestCase):
    """اختبارات نموذج المشروع"""
    
    def test_create_project(self):
        """اختبار إنشاء مشروع"""
        project = Project.objects.create(
            name='مشروع البناء',
            description='مشروع تجريبي',
            project_type='construction',
            start_date=date.today(),
            budget=Decimal('1000000'),
            status='planning'
        )
        
        self.assertEqual(project.name, 'مشروع البناء')
        self.assertEqual(project.budget, Decimal('1000000'))
        self.assertEqual(project.get_duration_days(), 0)


class ItemModelTest(TestCase):
    """اختبارات نموذج الصنف"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='مورد تجريبي',
            supplier_type='materials'
        )
        
    def test_create_item(self):
        """اختبار إنشاء صنف"""
        item = Item.objects.create(
            code='ITEM001',
            name='اسمنت',
            unit='كيس',
            unit_price=Decimal('50'),
            current_stock=Decimal('100'),
            minimum_stock=Decimal('20'),
            supplier=self.supplier
        )
        
        self.assertEqual(item.name, 'اسمنت')
        self.assertEqual(item.current_stock, Decimal('100'))
        self.assertFalse(item.is_low_stock())
        
        # اختبار المخزون المنخفض
        item.current_stock = Decimal('15')
        item.save()
        self.assertTrue(item.is_low_stock())