from django import forms
from django.utils import timezone
from ..models import Installment, Safe


class InstallmentPaymentForm(forms.Form):
    """نموذج دفع الأقساط"""
    
    amount = forms.DecimalField(
        label='المبلغ المدفوع',
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
        label='تاريخ الدفع',
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
        self.installment = kwargs.pop('installment', None)
        super().__init__(*args, **kwargs)
        
        if self.installment:
            # تحديد المبلغ المتبقي كقيمة افتراضية
            remaining = self.installment.amount - self.installment.paid_amount
            self.fields['amount'].initial = remaining
            self.fields['amount'].widget.attrs['max'] = str(remaining)
            
            # إضافة معلومات للمستخدم
            self.fields['amount'].help_text = f'المبلغ المتبقي: {remaining}'
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        
        if self.installment:
            remaining = self.installment.amount - self.installment.paid_amount
            if amount > remaining:
                raise forms.ValidationError(
                    f'المبلغ المدفوع ({amount}) أكبر من المتبقي ({remaining}).'
                )
        
        return amount
    
    def clean_payment_date(self):
        """التحقق من تاريخ الدفع"""
        payment_date = self.cleaned_data.get('payment_date')
        
        if payment_date > timezone.now().date():
            raise forms.ValidationError('لا يمكن تحديد تاريخ دفع في المستقبل.')
        
        return payment_date