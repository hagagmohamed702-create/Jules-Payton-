from django import forms
from ..models import Unit, PartnersGroup


class UnitForm(forms.ModelForm):
    """نموذج إدخال الوحدات"""
    
    class Meta:
        model = Unit
        fields = [
            'name', 'building_number', 'unit_type', 'unit_group',
            'total_price', 'partners_group'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الوحدة'
            }),
            'building_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم العمارة'
            }),
            'unit_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'unit_group': forms.Select(attrs={
                'class': 'form-control'
            }),
            'total_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'السعر الإجمالي',
                'min': '0',
                'step': '0.01'
            }),
            'partners_group': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'name': 'اسم الوحدة',
            'building_number': 'رقم العمارة',
            'unit_type': 'نوع الوحدة',
            'unit_group': 'المجموعة',
            'total_price': 'السعر الإجمالي',
            'partners_group': 'مجموعة الشركاء',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص الحقول
        self.fields['partners_group'].queryset = PartnersGroup.objects.all()
        self.fields['partners_group'].empty_label = 'اختر مجموعة الشركاء'
        
        # جعل مجموعة الشركاء اختيارية
        self.fields['partners_group'].required = False
    
    def clean_total_price(self):
        """التحقق من السعر"""
        total_price = self.cleaned_data.get('total_price')
        if total_price and total_price <= 0:
            raise forms.ValidationError('السعر يجب أن يكون أكبر من صفر.')
        return total_price