from django import forms
from django.utils import timezone
from ..models import Project, Supplier, Safe, PaymentVoucher


class ProjectForm(forms.ModelForm):
    """نموذج إدخال المشاريع"""
    
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'project_type', 'start_date',
            'end_date', 'budget', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المشروع'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'وصف المشروع',
                'rows': 4
            }),
            'project_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'الميزانية المخصصة',
                'min': '0',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'name': 'اسم المشروع',
            'description': 'الوصف',
            'project_type': 'نوع المشروع',
            'start_date': 'تاريخ البداية',
            'end_date': 'تاريخ النهاية',
            'budget': 'الميزانية',
            'status': 'الحالة',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحديد تاريخ البداية الافتراضي
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
    
    def clean(self):
        """التحقق من البيانات"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                'تاريخ النهاية لا يمكن أن يكون قبل تاريخ البداية.'
            )
        
        return cleaned_data
    
    def clean_budget(self):
        """التحقق من الميزانية"""
        budget = self.cleaned_data.get('budget')
        if budget and budget <= 0:
            raise forms.ValidationError('الميزانية يجب أن تكون أكبر من صفر.')
        return budget


class ProjectExpenseForm(forms.Form):
    """نموذج إضافة مصروف للمشروع"""
    
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
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # إضافة خيار فارغ للمورد
        self.fields['supplier'].empty_label = 'بدون مورد'
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        
        return amount
    
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