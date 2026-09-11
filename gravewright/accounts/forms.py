from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class RegistrationForm(forms.Form):
    name = forms.CharField(min_length=2, max_length=80)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(min_length=12, max_length=256, strip=False,
                               widget=forms.PasswordInput)

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])


class LoginForm(forms.Form):
    email = forms.CharField(max_length=254)
    password = forms.CharField(min_length=1, max_length=256, strip=False,
                               widget=forms.PasswordInput)

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])


class AccountUpdateForm(forms.Form):
    name = forms.CharField(min_length=2, max_length=80)
    currentPassword = forms.CharField(max_length=256, strip=False, required=False,
                                      widget=forms.PasswordInput)
    newPassword = forms.CharField(min_length=12, max_length=256, strip=False,
                                  required=False, widget=forms.PasswordInput)


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
