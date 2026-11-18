import os
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Attendance, AttendanceStatus

class ManualAttendanceCorrectionForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['clock_in', 'clock_out', 'status', 'correction_note']
        widgets = {
            'clock_in': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'clock_out': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'correction_note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mandatory audit justification: explain reason for manual adjustment (e.g. system downtime, employee forgot to punch in, authorized off-site meeting)...'
            }),
        }

    def clean_correction_note(self):
        note = self.cleaned_data.get('correction_note', '').strip()
        if not note or len(note) < 5:
            raise forms.ValidationError(_("A descriptive audit justification is mandatory for manual attendance adjustments."))
        return note

class BiometricCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label=_("Biometric Attendance CSV"),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        help_text=_("Expected CSV format: employee_id,date,clock_in,clock_out (e.g. 00230,2026-11-18,08:02:00,17:05:00)")
    )

    def clean_csv_file(self):
        f = self.cleaned_data.get('csv_file')
        if f:
            ext = os.path.splitext(f.name)[1].lower()
            if ext != '.csv':
                raise forms.ValidationError(_("Only valid .csv files are accepted."))
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_("CSV file exceeds 10MB limit."))
        return f
