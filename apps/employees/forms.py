from django import forms
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Department, Position
from apps.accounts.models import CustomUser, UserRole
from .models import Employee, EmploymentType, EmployeeStatus

class OnboardingStep1Form(forms.Form):
    first_name = forms.CharField(
        label=_("First Name"),
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Chris'})
    )
    middle_name = forms.CharField(
        label=_("Middle Name (Optional)"),
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. M.'})
    )
    last_name = forms.CharField(
        label=_("Last Name"),
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Glasser'})
    )
    birth_date = forms.DateField(
        label=_("Date of Birth"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    phone_number = forms.CharField(
        label=_("Contact Phone"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 019-3382'})
    )
    work_location = forms.CharField(
        label=_("Work Location"),
        max_length=100,
        initial='New York',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. New York'})
    )

class OnboardingStep2Form(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label=_("Department"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    position = forms.ModelChoiceField(
        queryset=Position.objects.filter(is_active=True),
        label=_("Job Title / Position"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    employment_type = forms.ChoiceField(
        choices=EmploymentType.choices,
        label=_("Classification"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    hire_date = forms.DateField(
        label=_("Hire Date"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    probation_end_date = forms.DateField(
        label=_("Probation End Date (Optional)"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

class OnboardingStep3Form(forms.Form):
    work_email = forms.EmailField(
        label=_("Company Login Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'chris.glasser@company.com'})
    )
    password = forms.CharField(
        label=_("Initial Temporary Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        initial='HRequest2026!'
    )
    role = forms.ChoiceField(
        choices=UserRole.choices,
        initial=UserRole.EMPLOYEE,
        label=_("System RBAC Role"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_work_email(self):
        email = self.cleaned_data.get('work_email', '').lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user account with this work email already exists."))
        return email

class OnboardingStep4Form(forms.Form):
    employee_id_number = forms.CharField(
        label=_("Employee ID Number"),
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 00240'})
    )
    emergency_contact_name = forms.CharField(
        label=_("Emergency Contact Name"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Jane Glasser'})
    )
    emergency_contact_phone = forms.CharField(
        label=_("Emergency Contact Phone"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 018-9921'})
    )

    def clean_employee_id_number(self):
        id_num = self.cleaned_data.get('employee_id_number', '').strip()
        if Employee.objects.filter(employee_id_number=id_num).exists():
            raise forms.ValidationError(_("An employee with this ID number already exists."))
        return id_num
