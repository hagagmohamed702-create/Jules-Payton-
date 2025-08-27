from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal
import random
from faker import Faker
from ...models import (
    Partner, PartnersGroup, PartnersGroupMember, Safe, Customer, Supplier,
    Unit, Contract, Installment, Project, Item, NotificationSettings
)


class Command(BaseCommand):
    help = 'يولد بيانات تجريبية للنظام'
    
    def __init__(self):
        super().__init__()
        self.fake = Faker('ar_SA')  # استخدام البيانات العربية
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='حذف البيانات الموجودة قبل إنشاء البيانات الجديدة'
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('جاري حذف البيانات الموجودة...'))
            self._clear_data()
        
        self.stdout.write(self.style.SUCCESS('جاري إنشاء البيانات التجريبية...'))
        
        with transaction.atomic():
            # إنشاء المستخدمين
            users = self._create_users()
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(users)} مستخدم'))
            
            # إنشاء الشركاء
            partners = self._create_partners(users)
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(partners)} شريك'))
            
            # إنشاء مجموعات الشركاء
            groups = self._create_partner_groups(partners)
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(groups)} مجموعة شركاء'))
            
            # إنشاء الخزائن
            safes = self._create_safes()
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(safes)} خزينة'))
            
            # إنشاء العملاء
            customers = self._create_customers()
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(customers)} عميل'))
            
            # إنشاء الموردين
            suppliers = self._create_suppliers()
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(suppliers)} مورد'))
            
            # إنشاء الوحدات
            units = self._create_units(groups)
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(units)} وحدة'))
            
            # إنشاء العقود والأقساط
            contracts = self._create_contracts(customers, units, groups)
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(contracts)} عقد'))
            
            # إنشاء المشاريع
            projects = self._create_projects()
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(projects)} مشروع'))
            
            # إنشاء أصناف المخزون
            items = self._create_items(suppliers)
            self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء {len(items)} صنف'))
            
            # إنشاء إعدادات الإشعارات
            self._create_notification_settings(users)
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء إعدادات الإشعارات'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ تم إنشاء البيانات التجريبية بنجاح!'))
        self.stdout.write(self.style.SUCCESS('يمكنك الدخول باستخدام:'))
        self.stdout.write(self.style.SUCCESS('   المستخدم: admin'))
        self.stdout.write(self.style.SUCCESS('   كلمة المرور: admin123'))
    
    def _clear_data(self):
        """حذف البيانات الموجودة"""
        models = [
            Installment, Contract, Unit, Item, Project,
            Supplier, Customer, Safe, PartnersGroupMember,
            PartnersGroup, Partner
        ]
        
        for model in models:
            model.objects.all().delete()
        
        # حذف المستخدمين ما عدا superuser
        User.objects.filter(is_superuser=False).delete()
    
    def _create_users(self):
        """إنشاء المستخدمين"""
        users = []
        
        # إنشاء مستخدم إداري
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'مدير',
                'last_name': 'النظام'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        users.append(admin_user)
        
        # إنشاء مستخدمين عاديين
        for i in range(3):
            username = f'user{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': self.fake.first_name(),
                    'last_name': self.fake.last_name()
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        
        return users
    
    def _create_partners(self, users):
        """إنشاء الشركاء"""
        partners = []
        
        partner_names = ['أحمد محمد', 'سارة أحمد', 'محمد علي', 'فاطمة عبدالله']
        
        for i, name in enumerate(partner_names):
            if i < len(users):
                partner = Partner.objects.create(
                    name=name,
                    phone=self.fake.phone_number(),
                    email=self.fake.email(),
                    balance=Decimal(random.randint(50000, 200000)),
                    user=users[i] if i < len(users) else None
                )
                partners.append(partner)
        
        return partners
    
    def _create_partner_groups(self, partners):
        """إنشاء مجموعات الشركاء"""
        groups = []
        
        # مجموعة كاملة
        group1 = PartnersGroup.objects.create(
            name='مجموعة الشركاء الرئيسية',
            description='جميع الشركاء بنسب متساوية'
        )
        
        for partner in partners:
            PartnersGroupMember.objects.create(
                group=group1,
                partner=partner,
                share_percentage=Decimal('25.00')
            )
        
        groups.append(group1)
        
        # مجموعة جزئية
        if len(partners) >= 2:
            group2 = PartnersGroup.objects.create(
                name='مجموعة المشروع الخاص',
                description='شراكة خاصة'
            )
            
            PartnersGroupMember.objects.create(
                group=group2,
                partner=partners[0],
                share_percentage=Decimal('60.00')
            )
            
            PartnersGroupMember.objects.create(
                group=group2,
                partner=partners[1],
                share_percentage=Decimal('40.00')
            )
            
            groups.append(group2)
        
        return groups
    
    def _create_safes(self):
        """إنشاء الخزائن"""
        safes = []
        
        safe_data = [
            ('الخزينة الرئيسية', Decimal('500000')),
            ('خزينة الفرع', Decimal('100000')),
            ('الخزينة الاحتياطية', Decimal('50000')),
        ]
        
        for name, balance in safe_data:
            safe = Safe.objects.create(
                name=name,
                balance=balance
            )
            safes.append(safe)
        
        return safes
    
    def _create_customers(self):
        """إنشاء العملاء"""
        customers = []
        
        for i in range(20):
            customer = Customer.objects.create(
                name=self.fake.name(),
                phone=self.fake.phone_number(),
                email=self.fake.email() if random.choice([True, False]) else '',
                address=self.fake.address() if random.choice([True, False]) else '',
                is_active=random.choice([True, True, True, False])  # 75% نشط
            )
            customers.append(customer)
        
        return customers
    
    def _create_suppliers(self):
        """إنشاء الموردين"""
        suppliers = []
        
        supplier_types = ['materials', 'services', 'equipment', 'other']
        company_names = [
            'شركة البناء المتقدم', 'مؤسسة التوريدات العامة',
            'شركة الخدمات الهندسية', 'مصنع الحديد والصلب',
            'شركة المعدات الثقيلة', 'مؤسسة المقاولات المتحدة'
        ]
        
        for i, company in enumerate(company_names):
            supplier = Supplier.objects.create(
                name=self.fake.name(),
                company_name=company,
                phone=self.fake.phone_number(),
                email=self.fake.company_email(),
                address=self.fake.address(),
                supplier_type=random.choice(supplier_types),
                is_active=True
            )
            suppliers.append(supplier)
        
        return suppliers
    
    def _create_units(self, groups):
        """إنشاء الوحدات"""
        units = []
        
        unit_types = ['residential', 'commercial', 'administrative']
        buildings = ['A', 'B', 'C']
        
        for building in buildings:
            for floor in range(1, 5):
                for unit_no in range(1, 4):
                    unit = Unit.objects.create(
                        name=f'وحدة {building}{floor}{unit_no:02d}',
                        building_number=f'عمارة {building}',
                        unit_type=random.choice(unit_types),
                        unit_group='residential' if building != 'C' else 'commercial',
                        total_price=Decimal(random.randint(300000, 800000)),
                        partners_group=random.choice(groups) if random.choice([True, False]) else None
                    )
                    units.append(unit)
        
        return units
    
    def _create_contracts(self, customers, units, groups):
        """إنشاء العقود والأقساط"""
        contracts = []
        
        # اختيار بعض الوحدات للبيع
        available_units = random.sample(units, min(15, len(units)))
        
        for i, unit in enumerate(available_units):
            if i < len(customers):
                customer = customers[i]
                
                # حساب المقدم والأقساط
                down_payment = unit.total_price * Decimal(random.randint(20, 40) / 100)
                installments_count = random.choice([12, 24, 36, 48])
                
                contract = Contract.objects.create(
                    customer=customer,
                    unit=unit,
                    unit_price=unit.total_price,
                    down_payment=down_payment,
                    installments_count=installments_count,
                    installment_type=random.choice(['monthly', 'quarterly']),
                    contract_date=timezone.now().date() - timedelta(days=random.randint(0, 365)),
                    partners_group=unit.partners_group or random.choice(groups)
                )
                
                contracts.append(contract)
                
                # إنشاء الأقساط تلقائياً سيتم من خلال signal في النموذج
        
        return contracts
    
    def _create_projects(self):
        """إنشاء المشاريع"""
        projects = []
        
        project_data = [
            ('مشروع البناء السكني أ', 'construction', Decimal('2000000')),
            ('مشروع صيانة المباني', 'maintenance', Decimal('500000')),
            ('مشروع التطوير العقاري', 'renovation', Decimal('1500000')),
            ('مشروع البنية التحتية', 'other', Decimal('3000000')),
        ]
        
        for name, ptype, budget in project_data:
            start_date = timezone.now().date() - timedelta(days=random.randint(30, 180))
            
            project = Project.objects.create(
                name=name,
                description=self.fake.paragraph(),
                project_type=ptype,
                start_date=start_date,
                end_date=start_date + timedelta(days=random.randint(90, 365)) if random.choice([True, False]) else None,
                budget=budget,
                status=random.choice(['planning', 'in_progress', 'in_progress', 'completed'])
            )
            projects.append(project)
        
        return projects
    
    def _create_items(self, suppliers):
        """إنشاء أصناف المخزون"""
        items = []
        
        item_data = [
            ('اسمنت', 'كيس', 50),
            ('حديد تسليح', 'طن', 5000),
            ('رمل', 'متر مكعب', 150),
            ('طوب أحمر', 'ألف قطعة', 300),
            ('بلاط سيراميك', 'متر مربع', 120),
            ('دهانات', 'جالون', 80),
            ('أسلاك كهربائية', 'متر', 15),
            ('مواسير PVC', 'قطعة', 25),
        ]
        
        for i, (name, unit, price) in enumerate(item_data):
            item = Item.objects.create(
                code=f'ITEM{i+1:04d}',
                name=name,
                description=f'وصف {name}',
                unit=unit,
                unit_price=Decimal(price),
                current_stock=Decimal(random.randint(10, 100)),
                minimum_stock=Decimal(random.randint(5, 20)),
                supplier=random.choice(suppliers) if suppliers else None
            )
            items.append(item)
        
        return items
    
    def _create_notification_settings(self, users):
        """إنشاء إعدادات الإشعارات"""
        for user in users:
            NotificationSettings.objects.get_or_create(
                user=user,
                defaults={
                    'notify_installment_due': True,
                    'notify_installment_overdue': True,
                    'notify_low_stock': True,
                    'notify_project_budget': True,
                    'notify_settlements': True,
                    'email_notifications': False
                }
            )