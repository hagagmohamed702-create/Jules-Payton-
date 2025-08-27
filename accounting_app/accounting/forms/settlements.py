from django import forms
from django.utils import timezone
from ..models import Settlement, Partner, PartnersGroup


class SettlementForm(forms.ModelForm):
    """نموذج إدخال التسويات"""
    
    class Meta:
        model = Settlement
        fields = [
            'from_partner', 'to_partner', 'amount', 'settlement_date',
            'partners_group', 'notes'
        ]
        widgets = {
            'from_partner': forms.Select(attrs={
                'class': 'form-control'
            }),
            'to_partner': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'المبلغ',
                'min': '0',
                'step': '0.01'
            }),
            'settlement_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'partners_group': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'ملاحظات (اختياري)',
                'rows': 3
            }),
        }
        labels = {
            'from_partner': 'من الشريك',
            'to_partner': 'إلى الشريك',
            'amount': 'المبلغ',
            'settlement_date': 'تاريخ التسوية',
            'partners_group': 'مجموعة الشركاء',
            'notes': 'ملاحظات',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحديد تاريخ التسوية الافتراضي
        if not self.instance.pk:
            self.fields['settlement_date'].initial = timezone.now().date()
        
        # جعل الملاحظات اختيارية
        self.fields['notes'].required = False
    
    def clean_amount(self):
        """التحقق من المبلغ"""
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        
        return amount
    
    def clean(self):
        """التحقق من البيانات"""
        cleaned_data = super().clean()
        from_partner = cleaned_data.get('from_partner')
        to_partner = cleaned_data.get('to_partner')
        partners_group = cleaned_data.get('partners_group')
        
        # التحقق من أن الشريكين مختلفين
        if from_partner and to_partner and from_partner == to_partner:
            raise forms.ValidationError(
                'لا يمكن إجراء تسوية من شريك إلى نفسه.'
            )
        
        # التحقق من أن الشريكين في نفس المجموعة
        if from_partner and to_partner and partners_group:
            from_groups = from_partner.groups.all()
            to_groups = to_partner.groups.all()
            
            if partners_group not in from_groups:
                raise forms.ValidationError(
                    f'الشريك {from_partner} ليس في المجموعة {partners_group}.'
                )
            
            if partners_group not in to_groups:
                raise forms.ValidationError(
                    f'الشريك {to_partner} ليس في المجموعة {partners_group}.'
                )
        
        return cleaned_data


class CalculateSettlementsForm(forms.Form):
    """نموذج حساب التسويات"""
    
    partners_group = forms.ModelChoiceField(
        label='مجموعة الشركاء',
        queryset=PartnersGroup.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    settlement_date = forms.DateField(
        label='تاريخ التسوية',
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة معلومات للمستخدم
        self.fields['partners_group'].help_text = 'اختر المجموعة لحساب التسويات المطلوبة'