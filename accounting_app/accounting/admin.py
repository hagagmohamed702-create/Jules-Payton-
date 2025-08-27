from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import now

# Import models directly to ensure they're loaded
from accounting.models.partners import Partner, PartnersGroup, PartnersGroupMember
from accounting.models.safes import Safe
from accounting.models.customers import Customer
from accounting.models.suppliers import Supplier
from accounting.models.units import Unit
from accounting.models.contracts import Contract
from accounting.models.installments import Installment
from accounting.models.vouchers import ReceiptVoucher, PaymentVoucher
from accounting.models.projects import Project
from accounting.models.items_store import Item, StockMove
from accounting.models.settlements import Settlement


# Custom filter for Installment status
class InstallmentStatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('paid', 'Paid'),
            ('due', 'Due'),
            ('overdue', 'Overdue'),
        ]

    def queryset(self, request, queryset):
        today = now().date()
        if self.value() == 'paid':
            return queryset.filter(is_paid=True)
        if self.value() == 'due':
            return queryset.filter(is_paid=False, due_date__gte=today)
        if self.value() == 'overdue':
            return queryset.filter(is_paid=False, due_date__lt=today)
        return queryset


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'share_percent', 'opening_balance', 'created_at']
    list_filter = ['created_at']
    search_fields = ['code', 'name']
    ordering = ['code']


class PartnersGroupMemberInline(admin.TabularInline):
    model = PartnersGroupMember
    extra = 1


@admin.register(PartnersGroup)
class PartnersGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    inlines = [PartnersGroupMemberInline]
    search_fields = ['name']


@admin.register(Safe)
class SafeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_partner_wallet', 'partner', 'created_at']
    list_filter = ['is_partner_wallet', 'created_at']
    search_fields = ['name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'phone']
    ordering = ['code']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'created_at']
    search_fields = ['name', 'phone']
    ordering = ['name']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'unit_type', 'price_total', 'is_sold', 'created_at']
    list_filter = ['unit_type', 'is_sold', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['code']


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ('seq_no', 'due_date', 'amount', 'paid_amount', 'is_paid', 'status')
    can_delete = False

    def status(self, obj):
        if obj.is_paid:
            return 'Paid'
        if obj.due_date and obj.due_date < now().date():
            return 'Overdue'
        return 'Due'
    status.short_description = 'Status'


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['code', 'customer', 'unit', 'unit_value', 'installments_count', 'created_at']
    list_filter = ['schedule_type', 'created_at']
    search_fields = ['code', 'customer__name', 'unit__code']
    inlines = [InstallmentInline]
    ordering = ['-created_at']


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ['contract', 'seq_no', 'due_date', 'amount', 'paid_amount', 'status_colored']
    list_filter = [InstallmentStatusFilter, 'due_date']
    search_fields = ['contract__code', 'contract__customer__name']
    ordering = ['contract', 'seq_no']
    
    def status_colored(self, obj):
        # Determine status based on is_paid and due_date
        if obj.is_paid:
            status = 'PAID'
            color = 'green'
            display = 'مدفوع'
        elif obj.due_date and obj.due_date < now().date():
            status = 'LATE'
            color = 'red'
            display = 'متأخر'
        else:
            status = 'PENDING'
            color = 'orange'
            display = 'معلق'
            
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            display
        )
    status_colored.short_description = 'الحالة'


@admin.register(ReceiptVoucher)
class ReceiptVoucherAdmin(admin.ModelAdmin):
    list_display = ['voucher_number', 'date', 'amount', 'safe', 'customer', 'created_at']
    list_filter = ['date', 'safe', 'created_at']
    search_fields = ['voucher_number', 'description', 'customer__name']
    ordering = ['-date', '-created_at']


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(admin.ModelAdmin):
    list_display = ['voucher_number', 'date', 'amount', 'safe', 'supplier', 'project', 'created_at']
    list_filter = ['date', 'safe', 'project', 'created_at']
    search_fields = ['voucher_number', 'description', 'supplier__name', 'expense_head']
    ordering = ['-date', '-created_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'project_type', 'status', 'budget', 'start_date']
    list_filter = ['project_type', 'status', 'start_date']
    search_fields = ['code', 'name']
    ordering = ['-start_date']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'uom', 'unit_price', 'supplier', 'created_at']
    list_filter = ['supplier', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['code']


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ['item', 'direction', 'qty', 'project', 'date', 'created_at']
    list_filter = ['direction', 'date', 'project']
    search_fields = ['item__name', 'item__code', 'notes']
    ordering = ['-date', '-created_at']


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'period_from', 'period_to', 'project', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['notes']
    ordering = ['-period_to', '-created_at']
    readonly_fields = ['pre_balances', 'post_balances', 'details']