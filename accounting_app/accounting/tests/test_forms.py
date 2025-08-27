from django.test import TestCase
from decimal import Decimal
from datetime import date
from ..models import Safe, Supplier, Customer, Unit, Contract, Installment
from ..forms.units import UnitForm
from ..forms.suppliers import SupplierForm
from ..forms.installments import InstallmentPaymentForm
from ..forms.projects import ProjectForm, ProjectExpenseForm
from ..forms.vouchers import ReceiptVoucherForm, PaymentVoucherForm


class UnitFormTest(TestCase):
    """اختبارات نموذج الوحدة"""
    
    def test_valid_unit_form(self):
        """اختبار نموذج صالح"""
        form_data = {
            'name': 'وحدة A101',
            'building_number': 'عمارة A',
            'unit_type': 'residential',
            'unit_group': 'residential',
            'total_price': '500000'
        }
        
        form = UnitForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_price(self):
        """اختبار سعر غير صالح"""
        form_data = {
            'name': 'وحدة',
            'building_number': 'عمارة',
            'unit_type': 'residential',
            'unit_group': 'residential',
            'total_price': '-1000'
        }
        
        form = UnitForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_price', form.errors)


class SupplierFormTest(TestCase):
    """اختبارات نموذج المورد"""
    
    def test_valid_supplier_form(self):
        """اختبار نموذج صالح"""
        form_data = {
            'name': 'مورد جديد',
            'phone': '0501234567',
            'supplier_type': 'materials',
            'is_active': True
        }
        
        form = SupplierForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_phone(self):
        """اختبار رقم هاتف غير صالح"""
        form_data = {
            'name': 'مورد',
            'phone': 'abc123',
            'supplier_type': 'materials',
            'is_active': True
        }
        
        form = SupplierForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
    
    def test_missing_name_and_company(self):
        """اختبار عدم وجود اسم أو شركة"""
        form_data = {
            'phone': '0501234567',
            'supplier_type': 'materials',
            'is_active': True
        }
        
        form = SupplierForm(data=form_data)
        self.assertFalse(form.is_valid())


class InstallmentPaymentFormTest(TestCase):
    """اختبارات نموذج دفع القسط"""
    
    def setUp(self):
        self.safe = Safe.objects.create(
            name='خزينة',
            balance=Decimal('50000')
        )
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
            installments_count=6
        )
        self.installment = Installment.objects.create(
            contract=self.contract,
            installment_number=1,
            amount=Decimal('40000'),
            due_date=date.today()
        )
    
    def test_valid_payment_form(self):
        """اختبار دفعة صالحة"""
        form_data = {
            'amount': '20000',
            'payment_date': date.today(),
            'safe': self.safe.id,
            'notes': 'دفعة جزئية'
        }
        
        form = InstallmentPaymentForm(data=form_data, installment=self.installment)
        self.assertTrue(form.is_valid())
    
    def test_amount_exceeds_remaining(self):
        """اختبار مبلغ يتجاوز المتبقي"""
        form_data = {
            'amount': '50000',
            'payment_date': date.today(),
            'safe': self.safe.id
        }
        
        form = InstallmentPaymentForm(data=form_data, installment=self.installment)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_future_payment_date(self):
        """اختبار تاريخ دفع مستقبلي"""
        from datetime import timedelta
        future_date = date.today() + timedelta(days=7)
        
        form_data = {
            'amount': '10000',
            'payment_date': future_date,
            'safe': self.safe.id
        }
        
        form = InstallmentPaymentForm(data=form_data, installment=self.installment)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_date', form.errors)


class ProjectFormTest(TestCase):
    """اختبارات نموذج المشروع"""
    
    def test_valid_project_form(self):
        """اختبار نموذج مشروع صالح"""
        form_data = {
            'name': 'مشروع جديد',
            'description': 'وصف المشروع',
            'project_type': 'construction',
            'start_date': date.today(),
            'budget': '1000000',
            'status': 'planning'
        }
        
        form = ProjectForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_end_date_before_start(self):
        """اختبار تاريخ نهاية قبل البداية"""
        from datetime import timedelta
        
        form_data = {
            'name': 'مشروع',
            'project_type': 'construction',
            'start_date': date.today(),
            'end_date': date.today() - timedelta(days=7),
            'budget': '1000000',
            'status': 'planning'
        }
        
        form = ProjectForm(data=form_data)
        self.assertFalse(form.is_valid())


class VoucherFormTest(TestCase):
    """اختبارات نماذج السندات"""
    
    def setUp(self):
        self.safe = Safe.objects.create(
            name='خزينة',
            balance=Decimal('100000')
        )
        self.customer = Customer.objects.create(name='عميل')
        self.supplier = Supplier.objects.create(
            name='مورد',
            supplier_type='materials'
        )
    
    def test_valid_receipt_voucher_form(self):
        """اختبار سند قبض صالح"""
        form_data = {
            'customer': self.customer.id,
            'amount': '5000',
            'payment_date': date.today(),
            'safe': self.safe.id,
            'notes': 'سند قبض'
        }
        
        form = ReceiptVoucherForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_payment_voucher_insufficient_balance(self):
        """اختبار سند صرف برصيد غير كافي"""
        self.safe.balance = Decimal('1000')
        self.safe.save()
        
        form_data = {
            'supplier': self.supplier.id,
            'amount': '2000',
            'payment_date': date.today(),
            'safe': self.safe.id,
            'expense_type': 'materials'
        }
        
        form = PaymentVoucherForm(data=form_data)
        self.assertFalse(form.is_valid())