from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
import random
from ...models import (
    Partner, PartnersGroup, PartnersGroupMember,
    Safe, Customer, Supplier, Unit, Contract,
    ReceiptVoucher, PaymentVoucher, Project,
    Item, StockMove
)


class Command(BaseCommand):
    help = 'Seed database with demo data'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Creating demo data...')
            
            # Create superuser if not exists
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
                self.stdout.write(self.style.SUCCESS('Created superuser: admin/admin123'))
            
            # Create Partners
            partners = []
            partner1 = Partner.objects.create(
                code='P001',
                name='أحمد محمد',
                share_percent=Decimal('50.00'),
                opening_balance=Decimal('100000.00'),
                notes='شريك مؤسس'
            )
            partners.append(partner1)
            
            partner2 = Partner.objects.create(
                code='P002',
                name='محمود علي',
                share_percent=Decimal('50.00'),
                opening_balance=Decimal('100000.00'),
                notes='شريك مؤسس'
            )
            partners.append(partner2)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(partners)} partners'))
            
            # Create Partners Group
            group = PartnersGroup.objects.create(name='مجموعة الشركاء المؤسسين')
            
            PartnersGroupMember.objects.create(
                group=group,
                partner=partner1,
                percent=Decimal('50.00')
            )
            
            PartnersGroupMember.objects.create(
                group=group,
                partner=partner2,
                percent=Decimal('50.00')
            )
            
            self.stdout.write(self.style.SUCCESS('Created partners group'))
            
            # Create Safes
            main_safe = Safe.objects.create(
                name='الخزنة الرئيسية',
                is_partner_wallet=False
            )
            
            partner1_wallet = Safe.objects.create(
                name=f'محفظة {partner1.name}',
                is_partner_wallet=True,
                partner=partner1
            )
            
            partner2_wallet = Safe.objects.create(
                name=f'محفظة {partner2.name}',
                is_partner_wallet=True,
                partner=partner2
            )
            
            self.stdout.write(self.style.SUCCESS('Created safes and wallets'))
            
            # Create Customers
            customers = []
            customer_names = [
                'عبد الرحمن أحمد',
                'فاطمة محمد',
                'يوسف إبراهيم',
                'مريم خالد',
                'عمر حسن'
            ]
            
            for i, name in enumerate(customer_names, 1):
                customer = Customer.objects.create(
                    code=f'C{i:03d}',
                    name=name,
                    phone=f'010{random.randint(10000000, 99999999)}',
                    email=f'customer{i}@example.com',
                    address=f'القاهرة - مدينة نصر - شارع {i}',
                    is_active=True
                )
                customers.append(customer)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(customers)} customers'))
            
            # Create Suppliers
            suppliers = []
            supplier_names = [
                'شركة الأسمنت المصرية',
                'مؤسسة الحديد والصلب',
                'شركة السيراميك الحديثة'
            ]
            
            for name in supplier_names:
                supplier = Supplier.objects.create(
                    name=name,
                    phone=f'02{random.randint(10000000, 99999999)}'
                )
                suppliers.append(supplier)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(suppliers)} suppliers'))
            
            # Create Units
            units = []
            buildings = ['A', 'B', 'C']
            
            for building in buildings:
                for floor in range(1, 6):
                    for apt in range(1, 5):
                        unit_code = f'{building}{floor:02d}{apt:02d}'
                        unit = Unit.objects.create(
                            code=unit_code,
                            name=f'شقة {unit_code}',
                            building_no=building,
                            unit_type='residential',
                            price_total=Decimal(random.randint(800000, 1500000)),
                            group='res',
                            partners_group=group,
                            is_sold=False
                        )
                        units.append(unit)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(units)} units'))
            
            # Create Contracts
            contracts = []
            for i in range(min(3, len(customers), len(units))):
                contract = Contract.objects.create(
                    code=f'CNT{date.today().year}{i+1:04d}',
                    customer=customers[i],
                    unit=units[i],
                    unit_value=units[i].price_total,
                    down_payment=units[i].price_total * Decimal('0.20'),
                    installments_count=60,
                    schedule_type='monthly',
                    start_date=date.today() - timedelta(days=180),
                    partners_group=group
                )
                contracts.append(contract)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(contracts)} contracts with installments'))
            
            # Create Project
            project = Project.objects.create(
                code='PRJ001',
                name='مشروع بناء عمارة سكنية',
                project_type='build',
                start_date=date.today() - timedelta(days=365),
                status='ongoing',
                budget=Decimal('5000000.00')
            )
            
            self.stdout.write(self.style.SUCCESS('Created project'))
            
            # Create Items
            items = []
            item_data = [
                ('ITM001', 'أسمنت', 'شيكارة', '65.00', suppliers[0]),
                ('ITM002', 'حديد تسليح', 'طن', '18000.00', suppliers[1]),
                ('ITM003', 'رمل', 'متر مكعب', '150.00', None),
                ('ITM004', 'زلط', 'متر مكعب', '200.00', None),
                ('ITM005', 'سيراميك', 'متر مربع', '120.00', suppliers[2])
            ]
            
            for code, name, uom, price, supplier in item_data:
                item = Item.objects.create(
                    code=code,
                    name=name,
                    uom=uom,
                    unit_price=Decimal(price),
                    supplier=supplier
                )
                items.append(item)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(items)} items'))
            
            # Create Stock Moves
            stock_moves = []
            
            # IN movements
            for item in items[:3]:
                move = StockMove.objects.create(
                    item=item,
                    qty=Decimal(random.randint(50, 200)),
                    direction='IN',
                    date=date.today() - timedelta(days=random.randint(30, 90)),
                    notes='شراء مواد'
                )
                stock_moves.append(move)
            
            # OUT movements
            for item in items[:2]:
                move = StockMove.objects.create(
                    item=item,
                    project=project,
                    qty=Decimal(random.randint(10, 50)),
                    direction='OUT',
                    date=date.today() - timedelta(days=random.randint(1, 30)),
                    notes='صرف للمشروع'
                )
                stock_moves.append(move)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(stock_moves)} stock movements'))
            
            # Create Receipt Vouchers
            receipts = []
            
            # Down payments for contracts
            for contract in contracts:
                if contract.down_payment > 0:
                    receipt = ReceiptVoucher.objects.create(
                        date=contract.created_at.date(),
                        amount=contract.down_payment,
                        safe=main_safe,
                        description=f'دفعة مقدمة - عقد {contract.code}',
                        customer=contract.customer,
                        contract=contract
                    )
                    receipts.append(receipt)
            
            # Some installment payments
            for contract in contracts:
                installments = contract.installments.filter(status='PENDING')[:3]
                for installment in installments:
                    receipt = ReceiptVoucher.objects.create(
                        date=date.today() - timedelta(days=random.randint(1, 30)),
                        amount=installment.amount,
                        safe=main_safe,
                        description=f'سداد قسط {installment.seq_no} - عقد {contract.code}',
                        customer=contract.customer,
                        contract=contract,
                        installment=installment
                    )
                    receipts.append(receipt)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(receipts)} receipt vouchers'))
            
            # Create Payment Vouchers
            payments = []
            
            # Supplier payments
            for supplier in suppliers:
                payment = PaymentVoucher.objects.create(
                    date=date.today() - timedelta(days=random.randint(1, 60)),
                    amount=Decimal(random.randint(10000, 50000)),
                    safe=main_safe,
                    description=f'دفعة لحساب {supplier.name}',
                    supplier=supplier,
                    expense_head='مشتريات مواد'
                )
                payments.append(payment)
            
            # Project expenses
            expense_heads = [
                'أجور عمال',
                'نقل مواد',
                'كهرباء ومياه',
                'إيجار معدات',
                'مصاريف إدارية'
            ]
            
            for head in expense_heads:
                payment = PaymentVoucher.objects.create(
                    date=date.today() - timedelta(days=random.randint(1, 90)),
                    amount=Decimal(random.randint(5000, 20000)),
                    safe=main_safe,
                    description=f'{head} - {project.name}',
                    project=project,
                    expense_head=head
                )
                payments.append(payment)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(payments)} payment vouchers'))
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n=== Demo Data Created Successfully ==='))
            self.stdout.write(f'Partners: {Partner.objects.count()}')
            self.stdout.write(f'Customers: {Customer.objects.count()}')
            self.stdout.write(f'Units: {Unit.objects.count()}')
            self.stdout.write(f'Contracts: {Contract.objects.count()}')
            self.stdout.write(f'Receipts: {ReceiptVoucher.objects.count()}')
            self.stdout.write(f'Payments: {PaymentVoucher.objects.count()}')
            self.stdout.write('\nYou can now login with: admin/admin123')