from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import (
    Partner, PartnersGroup, PartnersGroupMember,
    Safe, Customer, Supplier, Unit, Contract,
    Installment, ReceiptVoucher, PaymentVoucher,
    Project, Item, StockMove, Settlement
)


class PartnerForm(forms.ModelForm):
    """فورم الشركاء"""
    class Meta:
        model = Partner
        fields = ['code', 'name', 'share_percent', 'opening_balance', 'notes']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود الشريك'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم الشريك'
            }),
            'share_percent': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'نسبة الشراكة %',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'الرصيد الافتتاحي',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg',
                'rows': 3,
                'placeholder': 'ملاحظات'
            })
        }


class PartnersGroupForm(forms.ModelForm):
    """فورم مجموعات الشركاء"""
    class Meta:
        model = PartnersGroup
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم المجموعة'
            })
        }


# فورم سيت لأعضاء المجموعة
PartnersGroupMemberFormSet = inlineformset_factory(
    PartnersGroup,
    PartnersGroupMember,
    fields=['partner', 'percent'],
    extra=1,
    can_delete=True,
    widgets={
        'partner': forms.Select(attrs={
            'class': 'form-select w-full rounded-lg'
        }),
        'percent': forms.NumberInput(attrs={
            'class': 'form-input w-full rounded-lg',
            'placeholder': 'النسبة %',
            'min': '0',
            'max': '100',
            'step': '0.01'
        })
    }
)


class SafeForm(forms.ModelForm):
    """فورم الخزائن والمحافظ"""
    class Meta:
        model = Safe
        fields = ['name', 'is_partner_wallet', 'partner']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم الخزنة/المحفظة'
            }),
            'is_partner_wallet': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded',
                'x-model': 'isPartnerWallet'
            }),
            'partner': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg',
                'x-show': 'isPartnerWallet',
                'x-transition': True
            })
        }


class CustomerForm(forms.ModelForm):
    """فورم العملاء"""
    class Meta:
        model = Customer
        fields = ['code', 'name', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود العميل'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم العميل'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'رقم الهاتف',
                'dir': 'ltr'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'البريد الإلكتروني',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg',
                'rows': 2,
                'placeholder': 'العنوان'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox rounded'
            })
        }


class SupplierForm(forms.ModelForm):
    """فورم الموردين"""
    class Meta:
        model = Supplier
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم المورد'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'رقم الهاتف',
                'dir': 'ltr'
            })
        }


class UnitForm(forms.ModelForm):
    """فورم الوحدات"""
    class Meta:
        model = Unit
        fields = ['code', 'name', 'building_no', 'unit_type', 'price_total', 'group', 'partners_group']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود الوحدة'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم الوحدة'
            }),
            'building_no': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'رقم المبنى'
            }),
            'unit_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'price_total': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'السعر الإجمالي',
                'step': '0.01'
            }),
            'group': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'partners_group': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            })
        }


class ContractForm(forms.ModelForm):
    """فورم العقود"""
    class Meta:
        model = Contract
        fields = [
            'code', 'customer', 'unit', 'unit_value',
            'down_payment', 'installments_count', 
            'schedule_type', 'start_date', 'partners_group'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود العقد'
            }),
            'customer': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'unit_value': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'قيمة الوحدة',
                'step': '0.01'
            }),
            'down_payment': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'الدفعة المقدمة',
                'step': '0.01'
            }),
            'installments_count': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'عدد الأقساط',
                'min': '0'
            }),
            'schedule_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'partners_group': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إظهار الوحدات غير المباعة فقط
        self.fields['unit'].queryset = Unit.objects.filter(is_sold=False)


class ReceiptVoucherForm(forms.ModelForm):
    """فورم سندات القبض"""
    class Meta:
        model = ReceiptVoucher
        fields = ['date', 'amount', 'safe', 'description', 'customer', 'partner', 'contract', 'installment']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'المبلغ',
                'step': '0.01',
                'min': '0.01'
            }),
            'safe': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg',
                'rows': 2,
                'placeholder': 'البيان'
            }),
            'customer': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'partner': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'contract': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'installment': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            })
        }


class PaymentVoucherForm(forms.ModelForm):
    """فورم سندات الصرف"""
    class Meta:
        model = PaymentVoucher
        fields = ['date', 'amount', 'safe', 'description', 'supplier', 'project', 'expense_head']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'المبلغ',
                'step': '0.01',
                'min': '0.01'
            }),
            'safe': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg',
                'rows': 2,
                'placeholder': 'البيان'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'expense_head': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'بند المصروف'
            })
        }


class ProjectForm(forms.ModelForm):
    """فورم المشاريع"""
    class Meta:
        model = Project
        fields = ['code', 'name', 'project_type', 'start_date', 'end_date', 'status', 'budget']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود المشروع'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم المشروع'
            }),
            'project_type': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'الميزانية',
                'step': '0.01',
                'min': '0'
            })
        }


class ItemForm(forms.ModelForm):
    """فورم الأصناف"""
    class Meta:
        model = Item
        fields = ['code', 'name', 'uom', 'unit_price', 'supplier']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'كود الصنف'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'اسم الصنف'
            }),
            'uom': forms.TextInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'وحدة القياس'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'سعر الوحدة',
                'step': '0.01',
                'min': '0'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            })
        }


class StockMoveForm(forms.ModelForm):
    """فورم حركات المخزن"""
    class Meta:
        model = StockMove
        fields = ['item', 'project', 'qty', 'direction', 'date', 'notes']
        widgets = {
            'item': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'placeholder': 'الكمية',
                'step': '0.01',
                'min': '0.01'
            }),
            'direction': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input w-full rounded-lg',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea w-full rounded-lg',
                'rows': 2,
                'placeholder': 'ملاحظات'
            })
        }