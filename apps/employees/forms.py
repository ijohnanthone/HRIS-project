from django import forms
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Department, Position
from apps.accounts.models import CustomUser, UserRole
from .models import Employee, EmploymentType, EmployeeStatus, WorkLocation

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
    work_location = forms.ChoiceField(
        label=_("Work Location / Site"),
        choices=WorkLocation.choices,
        initial=WorkLocation.HEADQUARTERS,
        widget=forms.Select(attrs={'class': 'form-select'})
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
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'employee.name@hrequest.com'})
    )
    password = forms.CharField(
        label=_("Login Password"),
        widget=forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'Set login password for this employee'}),
        min_length=6
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


class EmployeeEditForm(forms.ModelForm):
    work_email = forms.EmailField(
        label=_("Company Login Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Employee
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'department',
            'position',
            'manager',
            'employment_type',
            'status',
            'work_location',
            'hire_date',
            'probation_end_date',
            'birth_date',
            'phone_number',
            'personal_email',
            'emergency_contact_name',
            'emergency_contact_phone',
            'avatar_data',
        ]
        widgets = {
            'avatar_data': forms.HiddenInput(attrs={'id': 'id_avatar_data'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'work_location': forms.Select(attrs={'class': 'form-select'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'probation_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'personal_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['position'].queryset = Position.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            self.fields['manager'].queryset = Employee.objects.exclude(pk=self.instance.pk).order_by('first_name', 'last_name')
            self.fields['manager'].required = False
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['work_email'].initial = self.instance.user.email

    def clean_work_email(self):
        email = self.cleaned_data.get('work_email', '').strip().lower()
        qs = CustomUser.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk and self.instance.user_id:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError(_("Another user account already uses this login email."))
        return email
