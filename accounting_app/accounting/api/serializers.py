from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import (
    Partner, PartnersGroup, PartnersGroupMember, Safe, Customer, Supplier,
    Unit, Contract, Installment, InstallmentPayment, ReceiptVoucher, 
    PaymentVoucher, Project, Item, StockMove, Settlement, Notification
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer للمستخدمين"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class PartnerSerializer(serializers.ModelSerializer):
    """Serializer للشركاء"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Partner
        fields = ['id', 'name', 'phone', 'email', 'balance', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']


class PartnersGroupMemberSerializer(serializers.ModelSerializer):
    """Serializer لأعضاء مجموعة الشركاء"""
    partner = PartnerSerializer(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Partner.objects.all(),
        source='partner',
        write_only=True
    )
    
    class Meta:
        model = PartnersGroupMember
        fields = ['id', 'partner', 'partner_id', 'share_percentage']
        read_only_fields = ['id']


class PartnersGroupSerializer(serializers.ModelSerializer):
    """Serializer لمجموعات الشركاء"""
    members = PartnersGroupMemberSerializer(many=True, read_only=True)
    total_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PartnersGroup
        fields = ['id', 'name', 'description', 'members', 'total_percentage', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_total_percentage(self, obj):
        return sum(member.share_percentage for member in obj.members.all())


class SafeSerializer(serializers.ModelSerializer):
    """Serializer للخزائن"""
    class Meta:
        model = Safe
        fields = ['id', 'name', 'balance', 'created_at']
        read_only_fields = ['id', 'balance', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer للعملاء"""
    contracts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 
            'is_active', 'contracts_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_contracts_count(self, obj):
        return obj.contracts.count()


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer للموردين"""
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'company_name', 'phone', 'email', 
            'address', 'supplier_type', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UnitSerializer(serializers.ModelSerializer):
    """Serializer للوحدات"""
    partners_group = PartnersGroupSerializer(read_only=True)
    partners_group_id = serializers.PrimaryKeyRelatedField(
        queryset=PartnersGroup.objects.all(),
        source='partners_group',
        write_only=True,
        required=False
    )
    is_sold = serializers.SerializerMethodField()
    
    class Meta:
        model = Unit
        fields = [
            'id', 'name', 'building_number', 'unit_type', 'unit_group',
            'total_price', 'partners_group', 'partners_group_id', 
            'is_sold', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_is_sold(self, obj):
        return obj.contracts.exists()


class InstallmentSerializer(serializers.ModelSerializer):
    """Serializer للأقساط"""
    remaining_amount = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = Installment
        fields = [
            'id', 'contract', 'installment_number', 'amount', 
            'paid_amount', 'remaining_amount', 'due_date', 
            'payment_date', 'status', 'is_overdue'
        ]
        read_only_fields = ['id', 'installment_number', 'amount']
    
    def get_remaining_amount(self, obj):
        return obj.amount - obj.paid_amount
    
    def get_is_overdue(self, obj):
        from django.utils import timezone
        return obj.due_date < timezone.now().date() and obj.status != 'paid'


class ContractSerializer(serializers.ModelSerializer):
    """Serializer للعقود"""
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source='customer',
        write_only=True
    )
    unit = UnitSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        source='unit',
        write_only=True
    )
    partners_group = PartnersGroupSerializer(read_only=True)
    installments = InstallmentSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = [
            'id', 'contract_number', 'customer', 'customer_id',
            'unit', 'unit_id', 'unit_price', 'down_payment',
            'installments_count', 'installment_type', 'contract_date',
            'partners_group', 'installments', 'progress_percentage'
        ]
        read_only_fields = ['id', 'contract_number']
    
    def get_progress_percentage(self, obj):
        total = obj.unit_price
        paid = obj.down_payment + sum(i.paid_amount for i in obj.installments.all())
        return (paid / total * 100) if total > 0 else 0


class ReceiptVoucherSerializer(serializers.ModelSerializer):
    """Serializer لسندات القبض"""
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source='customer',
        write_only=True
    )
    safe = SafeSerializer(read_only=True)
    safe_id = serializers.PrimaryKeyRelatedField(
        queryset=Safe.objects.all(),
        source='safe',
        write_only=True
    )
    
    class Meta:
        model = ReceiptVoucher
        fields = [
            'id', 'voucher_number', 'customer', 'customer_id',
            'contract', 'amount', 'payment_date', 'safe', 'safe_id',
            'notes', 'is_cancelled', 'created_at'
        ]
        read_only_fields = ['id', 'voucher_number', 'is_cancelled', 'created_at']


class PaymentVoucherSerializer(serializers.ModelSerializer):
    """Serializer لسندات الصرف"""
    supplier = SupplierSerializer(read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(),
        source='supplier',
        write_only=True,
        required=False
    )
    safe = SafeSerializer(read_only=True)
    safe_id = serializers.PrimaryKeyRelatedField(
        queryset=Safe.objects.all(),
        source='safe',
        write_only=True
    )
    
    class Meta:
        model = PaymentVoucher
        fields = [
            'id', 'voucher_number', 'supplier', 'supplier_id',
            'project', 'amount', 'payment_date', 'safe', 'safe_id',
            'expense_type', 'notes', 'is_cancelled', 'created_at'
        ]
        read_only_fields = ['id', 'voucher_number', 'is_cancelled', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer للمشاريع"""
    total_expenses = serializers.SerializerMethodField()
    budget_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'project_type', 'start_date',
            'end_date', 'budget', 'total_expenses', 'budget_percentage',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_total_expenses(self, obj):
        return sum(v.amount for v in obj.payment_vouchers.filter(is_cancelled=False))
    
    def get_budget_percentage(self, obj):
        if obj.budget <= 0:
            return 0
        total_expenses = self.get_total_expenses(obj)
        return (total_expenses / obj.budget * 100)


class ItemSerializer(serializers.ModelSerializer):
    """Serializer للأصناف"""
    supplier = SupplierSerializer(read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(),
        source='supplier',
        write_only=True,
        required=False
    )
    stock_value = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'code', 'name', 'description', 'unit', 'unit_price',
            'current_stock', 'minimum_stock', 'supplier', 'supplier_id',
            'stock_value', 'is_low_stock', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_stock_value(self, obj):
        return obj.current_stock * obj.unit_price
    
    def get_is_low_stock(self, obj):
        return obj.current_stock <= obj.minimum_stock


class StockMoveSerializer(serializers.ModelSerializer):
    """Serializer لحركات المخزون"""
    item = ItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        source='item',
        write_only=True
    )
    
    class Meta:
        model = StockMove
        fields = [
            'id', 'item', 'item_id', 'move_type', 'quantity',
            'reference_number', 'project', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SettlementSerializer(serializers.ModelSerializer):
    """Serializer للتسويات"""
    from_partner = PartnerSerializer(read_only=True)
    to_partner = PartnerSerializer(read_only=True)
    partners_group = PartnersGroupSerializer(read_only=True)
    
    class Meta:
        model = Settlement
        fields = [
            'id', 'settlement_number', 'from_partner', 'to_partner',
            'amount', 'settlement_date', 'partners_group', 'status',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'settlement_number', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer للإشعارات"""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'priority', 'title',
            'message', 'link', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']