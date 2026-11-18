from django import forms
from django.utils.translation import gettext_lazy as _
from .models import DocumentRequest, RequestType, COETemplate

class COERequestSubmissionForm(forms.ModelForm):
    class Meta:
        model = DocumentRequest
        fields = ['request_type', 'purpose']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'State the specific purpose of your request (e.g. Schengen Visa Application, Bank Home Loan Application, Credit Card Assessment)...'
            }),
        }

    def clean_purpose(self):
        purpose = self.cleaned_data.get('purpose', '').strip()
        if not purpose or len(purpose) < 5:
            raise forms.ValidationError(_("Please provide a descriptive purpose for your COE request."))
        return purpose

class COEApprovalDecisionForm(forms.Form):
    DECISION_CHOICES = [
        ('APPROVE_AUTO', _('Approve & Auto-Generate Official PDF Certificate')),
        ('APPROVE_MANUAL', _('Approve & Upload Pre-Signed PDF Document')),
        ('REJECT', _('Reject Request')),
    ]

    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Required only if rejecting the request: specify why this request cannot be approved...'
        })
    )
    signed_pdf = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        help_text=_("Required only if approving with 'Upload Pre-Signed PDF Document'.")
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        rejection_reason = cleaned_data.get('rejection_reason', '').strip()
        signed_pdf = cleaned_data.get('signed_pdf')

        if decision == 'REJECT' and not rejection_reason:
            self.add_error('rejection_reason', _("Rejection reason is mandatory when declining a request."))

        if decision == 'APPROVE_MANUAL' and not signed_pdf:
            self.add_error('signed_pdf', _("Please select a signed PDF document to fulfill this request."))

        return cleaned_data

class COETemplateForm(forms.ModelForm):
    class Meta:
        model = COETemplate
        fields = ['name', 'template_type', 'header_title', 'signatory_name', 'signatory_title', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard COE v2026'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'header_title': forms.TextInput(attrs={'class': 'form-control'}),
            'signatory_name': forms.TextInput(attrs={'class': 'form-control'}),
            'signatory_title': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
