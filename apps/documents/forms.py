from django import forms
from django.utils.translation import gettext_lazy as _
from .models import EmployeeDocument, DocumentCategory

class EmployeeDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ['title', 'category', 'file', 'is_confidential']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Signed Employment Agreement 2026'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file:
            # Enforce max file size: 15MB
            max_size = 15 * 1024 * 1024
            if uploaded_file.size > max_size:
                raise forms.ValidationError(_("File size exceeds 15MB limit."))
        return uploaded_file
