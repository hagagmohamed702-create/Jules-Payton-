from django import forms
from ..models import Item, StockMove, Supplier, Project


class ItemForm(forms.ModelForm):
    """نموذج إدخال الأصناف"""
    
    class Meta:
        model = Item
        fields = [
            'code', 'name', 'description', 'unit', 'unit_price',
            'current_stock', 'minimum_stock', 'supplier'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'كود الصنف'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الصنف'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'وصف الصنف',
                'rows': 3
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الوحدة (متر، كجم، قطعة، ...)'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'سعر الوحدة',
                'min': '0',
                'step': '0.01'
            }),
            'current_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'الكمية الحالية',
                'min': '0',
                'step': '0.01'
            }),
            'minimum_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'الحد الأدنى للمخزون',
                'min': '0',
                'step': '0.01'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'code': 'كود الصنف',
            'name': 'اسم الصنف',
            'description': 'الوصف',
            'unit': 'الوحدة',
            'unit_price': 'سعر الوحدة',
            'current_stock': 'الكمية الحالية',
            'minimum_stock': 'الحد الأدنى',
            'supplier': 'المورد',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تصفية الموردين النشطين فقط
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
        self.fields['supplier'].empty_label = 'اختر المورد'
        
        # جعل بعض الحقول اختيارية
        self.fields['description'].required = False
        self.fields['supplier'].required = False
    
    def clean_code(self):
        """التحقق من الكود"""
        code = self.cleaned_data.get('code')
        if code:
            # التحقق من عدم تكرار الكود
            qs = Item.objects.filter(code__iexact=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('هذا الكود مستخدم بالفعل.')
        return code
    
    def clean(self):
        """التحقق من البيانات"""
        cleaned_data = super().clean()
        current_stock = cleaned_data.get('current_stock', 0)
        minimum_stock = cleaned_data.get('minimum_stock', 0)
        
        if minimum_stock < 0:
            raise forms.ValidationError('الحد الأدنى للمخزون لا يمكن أن يكون سالباً.')
        
        return cleaned_data


class StockMoveForm(forms.ModelForm):
    """نموذج حركة المخزون"""
    
    class Meta:
        model = StockMove
        fields = [
            'item', 'quantity', 'reference_number', 'project', 'notes'
        ]
        widgets = {
            'item': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'الكمية',
                'min': '0',
                'step': '0.01'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم المرجع (اختياري)'
            }),
            'project': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'ملاحظات (اختياري)',
                'rows': 3
            }),
        }
        labels = {
            'item': 'الصنف',
            'quantity': 'الكمية',
            'reference_number': 'رقم المرجع',
            'project': 'المشروع',
            'notes': 'ملاحظات',
        }
    
    def __init__(self, *args, **kwargs):
        self.move_type = kwargs.pop('move_type', 'in')
        super().__init__(*args, **kwargs)
        
        # تخصيص الحقول حسب نوع الحركة
        if self.move_type == 'in':
            # حركة إدخال - المشروع غير مطلوب
            self.fields['project'].required = False
            self.fields['project'].widget = forms.HiddenInput()
        else:
            # حركة إخراج - المشروع اختياري
            self.fields['project'].queryset = Project.objects.filter(
                status='in_progress'
            )
            self.fields['project'].empty_label = 'بدون مشروع'
            self.fields['project'].required = False
        
        # جعل بعض الحقول اختيارية
        self.fields['reference_number'].required = False
        self.fields['notes'].required = False
    
    def clean_quantity(self):
        """التحقق من الكمية"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity <= 0:
            raise forms.ValidationError('الكمية يجب أن تكون أكبر من صفر.')
        
        return quantity