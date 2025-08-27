from django import forms
from accounting.models import Safe

class SafeForm(forms.ModelForm):
    class Meta:
        model = Safe
        fields = "__all__"