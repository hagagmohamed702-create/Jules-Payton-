from decimal import Decimal
from django.db.models import Sum, Q
from ..models import Partner, PaymentVoucher, Settlement


class SettlementService:
    """خدمة حساب التسويات بين الشركاء"""
    
    @staticmethod
    def calculate_settlement(period_from, period_to, project=None):
        """حساب التسوية المطلوبة بين الشركاء للفترة المحددة"""
        partners = Partner.objects.all()
        partners_expenses = {}
        total_expenses = Decimal('0')
        
        # فلترة المصروفات حسب الفترة والمشروع
        expense_filter = Q(date__gte=period_from, date__lte=period_to)
        if project:
            expense_filter &= Q(project=project)
        
        # حساب مصروفات كل شريك
        for partner in partners:
            # مصروفات من محفظة الشريك
            partner_expenses = Decimal('0')
            
            try:
                partner_wallet = partner.wallet
                expenses = PaymentVoucher.objects.filter(
                    safe=partner_wallet
                ).filter(expense_filter)
                
                partner_expenses = expenses.aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
            except:
                pass
            
            partners_expenses[partner.id] = {
                'partner': partner,
                'expenses': partner_expenses,
                'share_percent': partner.share_percent
            }
            total_expenses += partner_expenses
        
        # حساب المطلوب من كل شريك
        settlements = []
        for partner_id, data in partners_expenses.items():
            partner = data['partner']
            actual_expenses = data['expenses']
            share_percent = data['share_percent']
            
            # المفروض أن يتحمله الشريك
            expected_share = total_expenses * (share_percent / 100)
            
            # الفرق (موجب = يجب أن يدفع، سالب = يجب أن يستلم)
            difference = expected_share - actual_expenses
            
            settlements.append({
                'partner': partner,
                'actual_expenses': actual_expenses,
                'expected_share': expected_share,
                'difference': difference
            })
        
        # حساب التحويلات المطلوبة
        transfers = SettlementService._calculate_transfers(settlements)
        
        return {
            'period_from': period_from,
            'period_to': period_to,
            'project': project,
            'total_expenses': total_expenses,
            'settlements': settlements,
            'transfers': transfers
        }
    
    @staticmethod
    def _calculate_transfers(settlements):
        """حساب التحويلات المطلوبة بين الشركاء"""
        # فصل الشركاء الدائنين والمدينين
        creditors = []  # من يجب أن يستلموا
        debtors = []    # من يجب أن يدفعوا
        
        for settlement in settlements:
            if settlement['difference'] > 0:
                debtors.append({
                    'partner': settlement['partner'],
                    'amount': settlement['difference']
                })
            elif settlement['difference'] < 0:
                creditors.append({
                    'partner': settlement['partner'],
                    'amount': abs(settlement['difference'])
                })
        
        # ترتيب حسب المبلغ
        creditors.sort(key=lambda x: x['amount'], reverse=True)
        debtors.sort(key=lambda x: x['amount'], reverse=True)
        
        # حساب التحويلات
        transfers = []
        
        for debtor in debtors:
            remaining_debt = debtor['amount']
            
            for creditor in creditors:
                if remaining_debt <= 0:
                    break
                
                if creditor['amount'] > 0:
                    transfer_amount = min(remaining_debt, creditor['amount'])
                    
                    transfers.append({
                        'from_partner': debtor['partner'].id,
                        'from_partner_name': debtor['partner'].name,
                        'to_partner': creditor['partner'].id,
                        'to_partner_name': creditor['partner'].name,
                        'amount': transfer_amount
                    })
                    
                    remaining_debt -= transfer_amount
                    creditor['amount'] -= transfer_amount
        
        return transfers
    
    @staticmethod
    def create_settlement(period_from, period_to, project=None, notes=None, user=None):
        """إنشاء تسوية جديدة"""
        # حساب التسوية
        settlement_data = SettlementService.calculate_settlement(
            period_from, period_to, project
        )
        
        # تجهيز البيانات للحفظ
        pre_balances = {}
        post_balances = {}
        
        for item in settlement_data['settlements']:
            partner = item['partner']
            pre_balances[str(partner.id)] = float(item['actual_expenses'])
            post_balances[str(partner.id)] = float(item['expected_share'])
        
        # إنشاء التسوية
        settlement = Settlement.objects.create(
            project=project,
            period_from=period_from,
            period_to=period_to,
            pre_balances=pre_balances,
            post_balances=post_balances,
            details={
                'total_expenses': float(settlement_data['total_expenses']),
                'transfers': settlement_data['transfers']
            },
            notes=notes,
            created_by=user
        )
        
        return settlement
    
    @staticmethod
    def execute_settlement_transfers(settlement, user=None):
        """تنفيذ تحويلات التسوية"""
        from .treasury import TreasuryService
        
        if not settlement.details or 'transfers' not in settlement.details:
            return []
        
        executed_transfers = []
        
        for transfer in settlement.details['transfers']:
            from_partner = Partner.objects.get(id=transfer['from_partner'])
            to_partner = Partner.objects.get(id=transfer['to_partner'])
            amount = Decimal(str(transfer['amount']))
            
            # التحويل من محفظة الشريك المدين إلى محفظة الشريك الدائن
            try:
                from_wallet = from_partner.wallet
                to_wallet = to_partner.wallet
                
                result = TreasuryService.transfer_between_safes(
                    from_wallet,
                    to_wallet,
                    amount,
                    f"تسوية الفترة {settlement.period_from} - {settlement.period_to}",
                    user
                )
                
                executed_transfers.append({
                    'from_partner': from_partner.name,
                    'to_partner': to_partner.name,
                    'amount': amount,
                    'status': 'success',
                    'payment_voucher': result['payment_voucher'].voucher_number,
                    'receipt_voucher': result['receipt_voucher'].voucher_number
                })
            except Exception as e:
                executed_transfers.append({
                    'from_partner': from_partner.name,
                    'to_partner': to_partner.name,
                    'amount': amount,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return executed_transfers
    
    @staticmethod
    def get_partner_settlement_history(partner, limit=10):
        """الحصول على تاريخ تسويات الشريك"""
        settlements = Settlement.objects.filter(
            Q(pre_balances__has_key=str(partner.id)) | 
            Q(post_balances__has_key=str(partner.id))
        ).order_by('-created_at')[:limit]
        
        history = []
        for settlement in settlements:
            partner_id_str = str(partner.id)
            
            history.append({
                'settlement': settlement,
                'pre_balance': Decimal(str(settlement.pre_balances.get(partner_id_str, 0))),
                'post_balance': Decimal(str(settlement.post_balances.get(partner_id_str, 0))),
                'difference': Decimal(str(settlement.post_balances.get(partner_id_str, 0))) - 
                             Decimal(str(settlement.pre_balances.get(partner_id_str, 0)))
            })
        
        return history