from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
from ..models import (
    Safe, Customer, ReceiptVoucher, PaymentVoucher,
    Contract, Unit, Installment
)


class DashboardTestCase(TestCase):
    """اختبارات لوحة التحكم"""
    
    def setUp(self):
        """إعداد البيانات الأساسية للاختبار"""
        # إنشاء مستخدم للاختبار
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء عميل الاختبار
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # إنشاء خزنة
        self.safe = Safe.objects.create(
            name='الخزنة الرئيسية',
            is_partner_wallet=False
        )
        
        # إنشاء بعض العملاء
        for i in range(5):
            Customer.objects.create(
                code=f'C{i+1:03d}',
                name=f'عميل {i+1}',
                phone=f'0123456789{i}',
                is_active=True
            )
    
    def test_dashboard_access(self):
        """اختبار الوصول إلى لوحة التحكم"""
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لوحة التحكم')
    
    def test_dashboard_requires_login(self):
        """اختبار أن لوحة التحكم تتطلب تسجيل الدخول"""
        self.client.logout()
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_kpi_calculations(self):
        """اختبار حسابات مؤشرات الأداء الرئيسية"""
        # إنشاء سندات قبض
        for i in range(3):
            ReceiptVoucher.objects.create(
                date=date.today(),
                amount=Decimal('10000.00'),
                safe=self.safe,
                description=f'سند قبض {i+1}'
            )
        
        # إنشاء سندات صرف
        for i in range(2):
            PaymentVoucher.objects.create(
                date=date.today(),
                amount=Decimal('5000.00'),
                safe=self.safe,
                description=f'سند صرف {i+1}'
            )
        
        response = self.client.get(reverse('accounting:dashboard'))
        
        # التحقق من القيم المحسوبة
        self.assertEqual(response.context['total_receipts'], Decimal('30000.00'))
        self.assertEqual(response.context['total_payments'], Decimal('10000.00'))
        self.assertEqual(response.context['net_balance'], Decimal('20000.00'))
    
    def test_dashboard_late_installments_count(self):
        """اختبار حساب عدد الأقساط المتأخرة"""
        # إنشاء عميل ووحدة
        customer = Customer.objects.first()
        unit = Unit.objects.create(
            code='U001',
            name='وحدة اختبارية',
            unit_type='residential',
            price_total=Decimal('1000000.00'),
            group='res'
        )
        
        # إنشاء عقد
        contract = Contract.objects.create(
            code='CNT001',
            customer=customer,
            unit=unit,
            unit_value=unit.price_total,
            down_payment=Decimal('0'),
            installments_count=3,
            schedule_type='monthly',
            start_date=date(2023, 1, 1)  # تاريخ قديم
        )
        
        # تحديث حالة الأقساط لتصبح متأخرة
        from ..services import InstallmentService
        InstallmentService.update_all_installments_status()
        
        response = self.client.get(reverse('accounting:dashboard'))
        
        # يجب أن يكون هناك 3 أقساط متأخرة
        self.assertEqual(response.context['late_installments_count'], 3)
    
    def test_dashboard_statistics(self):
        """اختبار إحصائيات لوحة التحكم"""
        # إنشاء وحدات
        for i in range(10):
            Unit.objects.create(
                code=f'U{i+1:03d}',
                name=f'وحدة {i+1}',
                unit_type='residential',
                price_total=Decimal('500000.00'),
                group='res',
                is_sold=(i < 3)  # أول 3 وحدات مباعة
            )
        
        response = self.client.get(reverse('accounting:dashboard'))
        
        # التحقق من الإحصائيات
        self.assertEqual(response.context['total_customers'], 5)
        self.assertEqual(response.context['available_units'], 7)
    
    def test_dashboard_recent_transactions(self):
        """اختبار عرض آخر المعاملات"""
        # إنشاء سندات قبض
        receipts = []
        for i in range(15):
            receipt = ReceiptVoucher.objects.create(
                date=date.today(),
                amount=Decimal('1000.00'),
                safe=self.safe,
                description=f'سند قبض {i+1}'
            )
            receipts.append(receipt)
        
        response = self.client.get(reverse('accounting:dashboard'))
        
        # يجب عرض آخر 10 سندات فقط
        recent_receipts = response.context['recent_receipts']
        self.assertEqual(len(recent_receipts), 10)
        
        # التحقق من الترتيب (الأحدث أولاً)
        self.assertEqual(
            recent_receipts[0].voucher_number,
            receipts[-1].voucher_number
        )