from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from ..models import Customer, Unit, Safe, Partner, Supplier, Project, Item


class BaseAPITest(TestCase):
    """فئة أساسية لاختبارات API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            password='apipass123'
        )
        self.client.force_authenticate(user=self.user)


class CustomerAPITest(BaseAPITest):
    """اختبارات API العملاء"""
    
    def test_list_customers(self):
        """اختبار قائمة العملاء"""
        Customer.objects.create(name='عميل 1')
        Customer.objects.create(name='عميل 2')
        
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_create_customer(self):
        """اختبار إنشاء عميل"""
        data = {
            'name': 'عميل جديد',
            'phone': '0501234567',
            'email': 'new@example.com',
            'is_active': True
        }
        
        response = self.client.post('/api/customers/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)
    
    def test_retrieve_customer(self):
        """اختبار عرض عميل"""
        customer = Customer.objects.create(name='عميل تجريبي')
        
        response = self.client.get(f'/api/customers/{customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'عميل تجريبي')
    
    def test_update_customer(self):
        """اختبار تحديث عميل"""
        customer = Customer.objects.create(name='عميل قديم')
        
        data = {'name': 'عميل محدث'}
        response = self.client.patch(f'/api/customers/{customer.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'عميل محدث')
    
    def test_delete_customer(self):
        """اختبار حذف عميل"""
        customer = Customer.objects.create(name='عميل للحذف')
        
        response = self.client.delete(f'/api/customers/{customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Customer.objects.count(), 0)


class UnitAPITest(BaseAPITest):
    """اختبارات API الوحدات"""
    
    def test_list_units(self):
        """اختبار قائمة الوحدات"""
        Unit.objects.create(name='وحدة 1', total_price=Decimal('500000'))
        Unit.objects.create(name='وحدة 2', total_price=Decimal('600000'))
        
        response = self.client.get('/api/units/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_available_units(self):
        """اختبار الوحدات المتاحة"""
        Unit.objects.create(name='وحدة متاحة', total_price=Decimal('500000'))
        
        response = self.client.get('/api/units/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class SafeAPITest(BaseAPITest):
    """اختبارات API الخزائن"""
    
    def test_list_safes(self):
        """اختبار قائمة الخزائن"""
        Safe.objects.create(name='خزينة 1', balance=Decimal('50000'))
        Safe.objects.create(name='خزينة 2', balance=Decimal('100000'))
        
        response = self.client.get('/api/safes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_safe_transactions(self):
        """اختبار حركات الخزينة"""
        safe = Safe.objects.create(name='خزينة', balance=Decimal('50000'))
        
        response = self.client.get(f'/api/safes/{safe.id}/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('receipts', response.data)
        self.assertIn('payments', response.data)


class ProjectAPITest(BaseAPITest):
    """اختبارات API المشاريع"""
    
    def test_list_projects(self):
        """اختبار قائمة المشاريع"""
        Project.objects.create(
            name='مشروع 1',
            budget=Decimal('1000000'),
            status='planning'
        )
        
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_project_expenses(self):
        """اختبار مصروفات المشروع"""
        project = Project.objects.create(
            name='مشروع',
            budget=Decimal('1000000')
        )
        
        response = self.client.get(f'/api/projects/{project.id}/expenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class ItemAPITest(BaseAPITest):
    """اختبارات API الأصناف"""
    
    def test_list_items(self):
        """اختبار قائمة الأصناف"""
        Item.objects.create(
            code='ITEM001',
            name='صنف 1',
            unit='قطعة',
            unit_price=Decimal('100'),
            current_stock=Decimal('50')
        )
        
        response = self.client.get('/api/items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_low_stock_items(self):
        """اختبار الأصناف منخفضة المخزون"""
        Item.objects.create(
            code='ITEM002',
            name='صنف منخفض',
            unit='قطعة',
            unit_price=Decimal('50'),
            current_stock=Decimal('5'),
            minimum_stock=Decimal('10')
        )
        
        response = self.client.get('/api/items/low_stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class NotificationAPITest(BaseAPITest):
    """اختبارات API الإشعارات"""
    
    def test_list_notifications(self):
        """اختبار قائمة الإشعارات"""
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_notification_summary(self):
        """اختبار ملخص الإشعارات"""
        response = self.client.get('/api/notifications/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('unread', response.data)


class AuthenticationAPITest(TestCase):
    """اختبارات المصادقة في API"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_unauthenticated_request(self):
        """اختبار طلب غير مصدق"""
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_authenticated_request(self):
        """اختبار طلب مصدق"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)