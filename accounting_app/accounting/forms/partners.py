from django import forms
from django.forms import inlineformset_factory
from accounting.models import Partner, PartnersGroup, PartnersGroupMember

class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = "__all__"

class PartnersGroupForm(forms.ModelForm):
    class Meta:
        model = PartnersGroup
        fields = "__all__"

class PartnersGroupMemberForm(forms.ModelForm):
    class Meta:
        model = PartnersGroupMember
        fields = "__all__"

PartnersGroupMemberFormSet = inlineformset_factory(
    parent_model=PartnersGroup,
    model=PartnersGroupMember,
    fields="__all__",
    extra=1,
    can_delete=True,
)