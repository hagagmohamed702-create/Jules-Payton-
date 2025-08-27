from django import forms
from accounting.models import Contract


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = "__all__"
        widgets = {
            'contract_number': forms.TextInput(attrs={'class': 'form-input'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'contract_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'deposit': forms.NumberInput(attrs={'class': 'form-input'}),
            'installments_count': forms.NumberInput(attrs={'class': 'form-input'}),
            'contract_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'group': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }