import os
from django import forms
from django.utils.translation import gettext_lazy as _
from apps.employees.models import Employee
from .models import PayslipRecord, PayrollPeriod, PayslipStatus

class PayslipUploadForm(forms.ModelForm):
    class Meta:
        model = PayslipRecord
        fields = [
            'employee',
            'payroll_period',
            'payslip_file',
            'total_salary',
            'status',
            'is_replacement',
            'replacement_note'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'payroll_period': forms.Select(attrs={'class': 'form-select'}),
            'payslip_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
            'total_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 16436.00', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_replacement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'replacement_note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Required only if replacing an existing payslip (e.g. recalculation of overtime, tax adjustment)...'
            }),
        }

    def clean_payslip_file(self):
        f = self.cleaned_data.get('payslip_file')
        if f:
            ext = os.path.splitext(f.name)[1].lower()
            if ext != '.pdf':
                raise forms.ValidationError(_("Payslip document must be in PDF format (.pdf)."))
            if f.size > 15 * 1024 * 1024:
                raise forms.ValidationError(_("Payslip file size exceeds 15MB limit."))
        return f

    def clean(self):
        cleaned_data = super().clean()
        emp = cleaned_data.get('employee')
        period = cleaned_data.get('payroll_period')
        is_replacement = cleaned_data.get('is_replacement')
        replacement_note = cleaned_data.get('replacement_note', '').strip()

        if emp and period:
            existing = PayslipRecord.objects.filter(employee=emp, payroll_period=period).first()
            if existing:
                if not is_replacement:
                    raise forms.ValidationError(
                        _("A payslip for this employee and payroll period already exists. "
                          "To replace it, check 'Authorized Replacement' and enter a justification note.")
                    )
                elif not replacement_note:
                    self.add_error('replacement_note', _("An audit justification note is mandatory when replacing an existing payslip."))

        return cleaned_data

class PayrollPeriodForm(forms.ModelForm):
    class Meta:
        model = PayrollPeriod
        fields = ['label', 'period_month', 'period_year', 'is_active']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. December 2026'}),
            'period_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'period_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2035}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
