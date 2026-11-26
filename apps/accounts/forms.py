from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

class EmailAuthenticationForm(forms.Form):
    """
    Styled login form requiring email and password.
    """
    email = forms.EmailField(
        label=_("Work Email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'name@company.com',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    _("Invalid email or password. Please verify your credentials and try again."),
                    code='invalid_login',
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    _("This account is currently deactivated. Please contact your HR administrator."),
                    code='inactive',
                )
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class EmployeeContactSelfServiceForm(forms.Form):
    """
    Allows employees to update only their personal contact & emergency details
    without modifying HR-controlled official employment records.
    """
    phone_number = forms.CharField(
        label=_("Contact Phone"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 917 000 0000'})
    )
    personal_email = forms.EmailField(
        label=_("Personal Email"),
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'personal@example.com'})
    )
    emergency_contact_name = forms.CharField(
        label=_("Emergency Contact Name"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'})
    )
    emergency_contact_phone = forms.CharField(
        label=_("Emergency Contact Phone"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 917 000 0000'})
    )


class HRequestPasswordChangeForm(PasswordChangeForm):
    """
    Bootstrap-styled password change form for logged-in users.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'role', 'is_active')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'role', 'is_active', 'is_staff', 'is_superuser')
