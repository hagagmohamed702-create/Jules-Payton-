from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from ..models import Customer, Unit, Contract, Safe, Partner, Supplier, Project, Item


class BaseViewTest(TestCase):
    """فئة أساسية لاختبارات الـ Views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')


class CustomerViewTest(BaseViewTest):
    """اختبارات views العملاء"""
    
    def test_customer_list_view(self):
        """اختبار عرض قائمة العملاء"""
        response = self.client.get(reverse('accounting:customer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'العملاء')
    
    def test_customer_create_view(self):
        """اختبار إنشاء عميل"""
        response = self.client.post(reverse('accounting:customer_create'), {
            'name': 'عميل جديد',
            'phone': '0501234567',
            'email': 'new@example.com',
            'is_active': True
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(name='عميل جديد').exists())
    
    def test_customer_detail_view(self):
        """اختبار عرض تفاصيل عميل"""
        customer = Customer.objects.create(name='عميل تجريبي')
        response = self.client.get(
            reverse('accounting:customer_detail', kwargs={'pk': customer.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, customer.name)


class UnitViewTest(BaseViewTest):
    """اختبارات views الوحدات"""
    
    def test_unit_list_view(self):
        """اختبار عرض قائمة الوحدات"""
        response = self.client.get(reverse('accounting:unit_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_unit_create_view(self):
        """اختبار إنشاء وحدة"""
        response = self.client.post(reverse('accounting:unit_create'), {
            'name': 'وحدة A101',
            'building_number': 'عمارة A',
            'unit_type': 'residential',
            'unit_group': 'residential',
            'total_price': '500000'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Unit.objects.filter(name='وحدة A101').exists())


class ContractViewTest(BaseViewTest):
    """اختبارات views العقود"""
    
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(name='عميل تجريبي')
        self.unit = Unit.objects.create(
            name='وحدة تجريبية',
            total_price=Decimal('600000')
        )
        self.safe = Safe.objects.create(
            name='خزينة تجريبية',
            balance=Decimal('100000')
        )
    
    def test_contract_list_view(self):
        """اختبار عرض قائمة العقود"""
        response = self.client.get(reverse('accounting:contract_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_contract_create_wizard(self):
        """اختبار معالج إنشاء العقد"""
        # الخطوة الأولى - اختيار العميل
        response = self.client.get(reverse('accounting:contract_create'))
        self.assertEqual(response.status_code, 200)
        
        # محاكاة إكمال المعالج
        session = self.client.session
        session['contract_wizard'] = {
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'down_payment': '120000',
            'installments_count': '12',
            'installment_type': 'monthly'
        }
        session.save()
        
        # تأكيد العقد
        response = self.client.post(reverse('accounting:contract_create_confirm'))
        
        # التحقق من إنشاء العقد
        self.assertTrue(Contract.objects.filter(customer=self.customer).exists())


class SafeViewTest(BaseViewTest):
    """اختبارات views الخزائن"""
    
    def test_safe_list_view(self):
        """اختبار عرض قائمة الخزائن"""
        response = self.client.get(reverse('accounting:safe_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_safe_create_view(self):
        """اختبار إنشاء خزينة"""
        response = self.client.post(reverse('accounting:safe_create'), {
            'name': 'خزينة جديدة',
            'balance': '50000'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Safe.objects.filter(name='خزينة جديدة').exists())


class ProjectViewTest(BaseViewTest):
    """اختبارات views المشاريع"""
    
    def test_project_list_view(self):
        """اختبار عرض قائمة المشاريع"""
        response = self.client.get(reverse('accounting:project_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_project_create_view(self):
        """اختبار إنشاء مشروع"""
        response = self.client.post(reverse('accounting:project_create'), {
            'name': 'مشروع جديد',
            'description': 'وصف المشروع',
            'project_type': 'construction',
            'start_date': '2024-01-01',
            'budget': '1000000',
            'status': 'planning'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(name='مشروع جديد').exists())


class ReportViewTest(BaseViewTest):
    """اختبارات views التقارير"""
    
    def test_reports_dashboard(self):
        """اختبار لوحة التقارير"""
        response = self.client.get(reverse('accounting:reports_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'التقارير')
    
    def test_installments_report(self):
        """اختبار تقرير الأقساط"""
        response = self.client.get(reverse('accounting:installments_report'))
        self.assertEqual(response.status_code, 200)
    
    def test_treasury_report(self):
        """اختبار تقرير الخزينة"""
        response = self.client.get(reverse('accounting:treasury_report'))
        self.assertEqual(response.status_code, 200)


class NotificationViewTest(BaseViewTest):
    """اختبارات views الإشعارات"""
    
    def test_notification_list_view(self):
        """اختبار عرض قائمة الإشعارات"""
        response = self.client.get(reverse('accounting:notification_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_check_new_notifications(self):
        """اختبار فحص الإشعارات الجديدة"""
        response = self.client.get(reverse('accounting:check_new_notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('unread_count', response.json())