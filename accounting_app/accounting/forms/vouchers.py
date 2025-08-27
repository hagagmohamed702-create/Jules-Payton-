from django import forms
from django.utils import timezone
from ..models import ReceiptVoucher, PaymentVoucher, Customer, Supplier, Contract, Project, Safe


class ReceiptVoucherForm(forms.Form):
    """نموذج سند القبض"""
    
    customer = forms.ModelChoiceField(
        label='العميل',
        queryset=Customer.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    amount = forms.DecimalField(
        label='المبلغ',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'المبلغ',
            'min': '0',
            'step': '0.01'
        })
    )
    
    payment_date = forms.DateField(
        label='تاريخ القبض',
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    safe = forms.ModelChoiceField(
        label='الخزينة',
        queryset=Safe.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    contract = forms.ModelChoiceField(
        label='العقد',
        required=False,
        queryset=Contract.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'ملاحظات (اختياري)',
            'rows': 3
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة خيار فارغ للعقد
        self.fields['contract'].empty_label = 'بدون عقد'
        
        # تحديث قائمة العقود عند اختيار العميل
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['contract'].queryset = Contract.objects.filter(
                    customer_id=customer_id
                )
            except (ValueError, TypeError):
                pass
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        
        return amount
    
    def clean_payment_date(self):
        """التحقق من تاريخ القبض"""
        payment_date = self.cleaned_data.get('payment_date')
        
        if payment_date > timezone.now().date():
            raise forms.ValidationError('لا يمكن تحديد تاريخ قبض في المستقبل.')
        
        return payment_date


class PaymentVoucherForm(forms.Form):
    """نموذج سند الصرف"""
    
    supplier = forms.ModelChoiceField(
        label='المورد',
        required=False,
        queryset=Supplier.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    amount = forms.DecimalField(
        label='المبلغ',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'المبلغ',
            'min': '0',
            'step': '0.01'
        })
    )
    
    payment_date = forms.DateField(
        label='تاريخ الصرف',
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    safe = forms.ModelChoiceField(
        label='الخزينة',
        queryset=Safe.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    project = forms.ModelChoiceField(
        label='المشروع',
        required=False,
        queryset=Project.objects.filter(status='in_progress'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    expense_type = forms.ChoiceField(
        label='نوع المصروف',
        choices=PaymentVoucher.EXPENSE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'ملاحظات (اختياري)',
            'rows': 3
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة خيارات فارغة
        self.fields['supplier'].empty_label = 'بدون مورد'
        self.fields['project'].empty_label = 'بدون مشروع'
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        
        return amount
    
    def clean_payment_date(self):
        """التحقق من تاريخ الصرف"""
        payment_date = self.cleaned_data.get('payment_date')
        
        if payment_date > timezone.now().date():
            raise forms.ValidationError('لا يمكن تحديد تاريخ صرف في المستقبل.')
        
        return payment_date
    
    def clean(self):
        """التحقق من البيانات"""
        cleaned_data = super().clean()
        safe = cleaned_data.get('safe')
        amount = cleaned_data.get('amount')
        
        if safe and amount:
            if safe.balance < amount:
                raise forms.ValidationError(
                    f'رصيد الخزينة ({safe.balance}) غير كافي للصرف.'
                )
        
        return cleaned_data