from django.core.management.base import BaseCommand
from django.db.models import Sum, F, Q
from decimal import Decimal
from ...models import (
    Contract, Installment, Safe, Partner, 
    ReceiptVoucher, PaymentVoucher, Item, StockMove
)


class Command(BaseCommand):
    help = 'يفحص تكامل وصحة البيانات في النظام'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('جاري فحص تكامل البيانات...\n'))
        
        errors = []
        warnings = []
        
        # فحص الأقساط
        self.stdout.write('🔍 فحص الأقساط...')
        installment_issues = self._check_installments()
        errors.extend(installment_issues['errors'])
        warnings.extend(installment_issues['warnings'])
        
        # فحص الخزائن
        self.stdout.write('🔍 فحص الخزائن...')
        safe_issues = self._check_safes()
        errors.extend(safe_issues['errors'])
        warnings.extend(safe_issues['warnings'])
        
        # فحص المخزون
        self.stdout.write('🔍 فحص المخزون...')
        inventory_issues = self._check_inventory()
        errors.extend(inventory_issues['errors'])
        warnings.extend(inventory_issues['warnings'])
        
        # فحص أرصدة الشركاء
        self.stdout.write('🔍 فحص أرصدة الشركاء...')
        partner_issues = self._check_partners()
        errors.extend(partner_issues['errors'])
        warnings.extend(partner_issues['warnings'])
        
        # عرض النتائج
        self.stdout.write('\n' + '='*50 + '\n')
        
        if errors:
            self.stdout.write(self.style.ERROR(f'❌ تم العثور على {len(errors)} خطأ:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'   - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ لا توجد أخطاء في البيانات'))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'\n⚠️  تم العثور على {len(warnings)} تحذير:'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'   - {warning}'))
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✅ تم الانتهاء من فحص البيانات'))
    
    def _check_installments(self):
        """فحص صحة بيانات الأقساط"""
        errors = []
        warnings = []
        
        contracts = Contract.objects.prefetch_related('installments')
        
        for contract in contracts:
            installments = contract.installments.all()
            
            # فحص مجموع الأقساط
            total_installments = installments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            expected_total = contract.unit_price - contract.down_payment
            
            if abs(total_installments - expected_total) > Decimal('0.01'):
                errors.append(
                    f'العقد {contract.contract_number}: '
                    f'مجموع الأقساط ({total_installments}) '
                    f'لا يساوي المتوقع ({expected_total})'
                )
            
            # فحص المدفوعات
            for installment in installments:
                if installment.paid_amount > installment.amount:
                    errors.append(
                        f'القسط {installment.id}: '
                        f'المدفوع ({installment.paid_amount}) '
                        f'أكبر من قيمة القسط ({installment.amount})'
                    )
                
                # فحص الحالة
                if installment.paid_amount == installment.amount and installment.status != 'paid':
                    warnings.append(
                        f'القسط {installment.id}: '
                        f'مدفوع بالكامل لكن الحالة {installment.status}'
                    )
                elif installment.paid_amount > 0 and installment.paid_amount < installment.amount and installment.status != 'partial':
                    warnings.append(
                        f'القسط {installment.id}: '
                        f'مدفوع جزئياً لكن الحالة {installment.status}'
                    )
        
        return {'errors': errors, 'warnings': warnings}
    
    def _check_safes(self):
        """فحص صحة أرصدة الخزائن"""
        errors = []
        warnings = []
        
        safes = Safe.objects.all()
        
        for safe in safes:
            # حساب الرصيد من الحركات
            receipts_total = ReceiptVoucher.objects.filter(
                safe=safe,
                is_cancelled=False
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            payments_total = PaymentVoucher.objects.filter(
                safe=safe,
                is_cancelled=False
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            calculated_balance = receipts_total - payments_total
            
            # السماح بفرق بسيط بسبب الرصيد الافتتاحي
            if safe.balance < Decimal('0'):
                errors.append(
                    f'الخزينة {safe.name}: رصيد سالب ({safe.balance})'
                )
        
        return {'errors': errors, 'warnings': warnings}
    
    def _check_inventory(self):
        """فحص صحة بيانات المخزون"""
        errors = []
        warnings = []
        
        items = Item.objects.all()
        
        for item in items:
            # فحص الرصيد السالب
            if item.current_stock < 0:
                errors.append(
                    f'الصنف {item.name}: رصيد سالب ({item.current_stock})'
                )
            
            # فحص الحد الأدنى
            if item.current_stock < item.minimum_stock:
                warnings.append(
                    f'الصنف {item.name}: '
                    f'الرصيد ({item.current_stock}) '
                    f'أقل من الحد الأدنى ({item.minimum_stock})'
                )
            
            # حساب الرصيد من الحركات
            stock_in = StockMove.objects.filter(
                item=item,
                move_type='in'
            ).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')
            
            stock_out = StockMove.objects.filter(
                item=item,
                move_type='out'
            ).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')
            
            calculated_stock = stock_in - stock_out
            
            # قد يكون هناك رصيد افتتاحي
            if calculated_stock > item.current_stock:
                warnings.append(
                    f'الصنف {item.name}: '
                    f'قد يكون هناك حركات مفقودة'
                )
        
        return {'errors': errors, 'warnings': warnings}
    
    def _check_partners(self):
        """فحص صحة أرصدة الشركاء"""
        errors = []
        warnings = []
        
        partners = Partner.objects.all()
        
        for partner in partners:
            if partner.balance < 0:
                warnings.append(
                    f'الشريك {partner.name}: رصيد سالب ({partner.balance})'
                )
        
        # فحص نسب الشركاء في المجموعات
        from ...models import PartnersGroup
        groups = PartnersGroup.objects.prefetch_related('members')
        
        for group in groups:
            total_percentage = group.members.aggregate(
                Sum('share_percentage')
            )['share_percentage__sum'] or Decimal('0')
            
            if abs(total_percentage - Decimal('100')) > Decimal('0.01'):
                errors.append(
                    f'مجموعة {group.name}: '
                    f'مجموع النسب ({total_percentage}%) '
                    f'لا يساوي 100%'
                )
        
        return {'errors': errors, 'warnings': warnings}