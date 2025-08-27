from django import forms
from ..models import Supplier


class SupplierForm(forms.ModelForm):
    """نموذج إدخال الموردين"""
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'company_name', 'phone', 'email', 'address',
            'supplier_type', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المورد'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الشركة (اختياري)'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف',
                'dir': 'ltr'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'البريد الإلكتروني',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'العنوان',
                'rows': 3
            }),
            'supplier_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': 'اسم المورد',
            'company_name': 'اسم الشركة',
            'phone': 'رقم الهاتف',
            'email': 'البريد الإلكتروني',
            'address': 'العنوان',
            'supplier_type': 'نوع المورد',
            'is_active': 'نشط',
        }
    
    def clean_phone(self):
        """التحقق من رقم الهاتف"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # إزالة المسافات والشرطات
            phone = phone.replace(' ', '').replace('-', '')
            # التحقق من أن الرقم يحتوي على أرقام فقط
            if not phone.replace('+', '').isdigit():
                raise forms.ValidationError('رقم الهاتف غير صالح.')
        return phone
    
    def clean(self):
        """التحقق من البيانات"""
        cleaned_data = super().clean()
        
        # التحقق من وجود اسم المورد أو اسم الشركة
        name = cleaned_data.get('name')
        company_name = cleaned_data.get('company_name')
        
        if not name and not company_name:
            raise forms.ValidationError(
                'يجب إدخال اسم المورد أو اسم الشركة على الأقل.'
            )
        
        return cleaned_data