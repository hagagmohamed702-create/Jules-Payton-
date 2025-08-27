from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import Settlement, Partner, PartnersGroup, PaymentVoucher, ReceiptVoucher


class SettlementService:
    """خدمة إدارة التسويات بين الشركاء"""
    
    @staticmethod
    def calculate_partner_expenses(partner, partners_group, date_from=None, date_to=None):
        """حساب مصروفات الشريك في مجموعة معينة"""
        
        # المصروفات المباشرة (سندات الصرف)
        payment_vouchers = PaymentVoucher.objects.filter(
            created_by=partner.user
        )
        
        if date_from:
            payment_vouchers = payment_vouchers.filter(payment_date__gte=date_from)
        if date_to:
            payment_vouchers = payment_vouchers.filter(payment_date__lte=date_to)
        
        total_expenses = sum(v.amount for v in payment_vouchers)
        
        return total_expenses
    
    @staticmethod
    def calculate_partner_share(partner, partners_group):
        """حساب حصة الشريك من إجمالي المصروفات"""
        
        # الحصول على نسبة الشريك في المجموعة
        membership = partners_group.members.filter(partner=partner).first()
        if not membership:
            return Decimal('0')
        
        share_percentage = membership.share_percentage
        
        # حساب إجمالي المصروفات للمجموعة
        total_group_expenses = Decimal('0')
        for member in partners_group.members.all():
            partner_expenses = SettlementService.calculate_partner_expenses(
                member.partner,
                partners_group
            )
            total_group_expenses += partner_expenses
        
        # حساب الحصة المستحقة
        partner_share = (share_percentage / 100) * total_group_expenses
        
        return partner_share
    
    @staticmethod
    def calculate_settlements(partners_group):
        """حساب التسويات المطلوبة بين الشركاء"""
        
        settlements_data = {
            'partners': [],
            'settlements_needed': [],
            'total_expenses': Decimal('0')
        }
        
        # حساب المصروفات والحصص لكل شريك
        for member in partners_group.members.all():
            partner = member.partner
            actual_expenses = SettlementService.calculate_partner_expenses(
                partner,
                partners_group
            )
            expected_share = SettlementService.calculate_partner_share(
                partner,
                partners_group
            )
            
            difference = actual_expenses - expected_share
            
            settlements_data['partners'].append({
                'partner': partner,
                'share_percentage': member.share_percentage,
                'actual_expenses': actual_expenses,
                'expected_share': expected_share,
                'difference': difference
            })
            
            settlements_data['total_expenses'] += actual_expenses
        
        # حساب التسويات المطلوبة
        creditors = [p for p in settlements_data['partners'] if p['difference'] > 0]
        debtors = [p for p in settlements_data['partners'] if p['difference'] < 0]
        
        # ترتيب حسب المبلغ
        creditors.sort(key=lambda x: x['difference'], reverse=True)
        debtors.sort(key=lambda x: x['difference'])
        
        # إنشاء التسويات
        for creditor in creditors:
            remaining = creditor['difference']
            
            for debtor in debtors:
                if remaining <= 0:
                    break
                
                debt = abs(debtor['difference'])
                if debt <= 0:
                    continue
                
                amount = min(remaining, debt)
                
                settlements_data['settlements_needed'].append({
                    'from_partner': debtor['partner'],
                    'to_partner': creditor['partner'],
                    'amount': amount
                })
                
                remaining -= amount
                debtor['difference'] += amount
        
        return settlements_data
    
    @staticmethod
    @transaction.atomic
    def create_settlements(partners_group, created_by):
        """إنشاء التسويات تلقائياً"""
        
        settlements_data = SettlementService.calculate_settlements(partners_group)
        settlements = []
        
        for settlement_data in settlements_data['settlements_needed']:
            settlement = Settlement.objects.create(
                from_partner=settlement_data['from_partner'],
                to_partner=settlement_data['to_partner'],
                amount=settlement_data['amount'],
                partners_group=partners_group,
                settlement_date=timezone.now().date(),
                status='pending',
                created_by=created_by,
                notes=f'تسوية تلقائية لمجموعة {partners_group.name}'
            )
            settlements.append(settlement)
        
        return settlements
    
    @staticmethod
    @transaction.atomic
    def execute_settlement(settlement):
        """تنفيذ التسوية"""
        
        if settlement.status != 'pending':
            raise ValueError('هذه التسوية تم تنفيذها مسبقاً')
        
        # تحديث أرصدة الشركاء
        settlement.from_partner.balance -= settlement.amount
        settlement.from_partner.save()
        
        settlement.to_partner.balance += settlement.amount
        settlement.to_partner.save()
        
        # تحديث حالة التسوية
        settlement.status = 'completed'
        settlement.save()
        
        return settlement
    
    @staticmethod
    def get_partner_settlement_balance(partner, partners_group=None):
        """حساب رصيد التسويات للشريك"""
        
        # التسويات المستلمة
        received = Settlement.objects.filter(
            to_partner=partner,
            status='completed'
        )
        
        # التسويات المدفوعة
        paid = Settlement.objects.filter(
            from_partner=partner,
            status='completed'
        )
        
        if partners_group:
            received = received.filter(partners_group=partners_group)
            paid = paid.filter(partners_group=partners_group)
        
        total_received = sum(s.amount for s in received)
        total_paid = sum(s.amount for s in paid)
        
        return total_received - total_paid