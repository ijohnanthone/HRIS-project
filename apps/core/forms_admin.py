from django import forms
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import CustomUser, UserRole

class AdminUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Initial Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter temporary password or leave blank for default'}),
        required=False,
        help_text=_("Defaults to HRequest2026! if left blank.")
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'role', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@hrequest.com'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        if not pwd:
            return 'HRequest2026!'
        return pwd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if user.role == UserRole.SUPER_ADMIN:
            user.is_staff = True
            user.is_superuser = True
        elif user.role in [UserRole.HR_ADMIN, UserRole.HR_STAFF]:
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()
        return user

class AdminUserRoleForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['role', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        min_length=8,
        required=True
    )
