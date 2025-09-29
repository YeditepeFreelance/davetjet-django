# -*- coding: utf-8 -*-

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from .models import Profile, User, language_choices  # adjust path if needed

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'timezone']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'phone_number': forms.TextInput(attrs={'class': 'input'}),
            'timezone': forms.TextInput(attrs={'class': 'input'}),
        }

class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'full_name', 'company_name', 'bio', 'profile_picture', 'language',
            'location', 'date_of_birth', 'website'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'input'}),
            'company_name': forms.TextInput(attrs={'class': 'input'}),
            'bio': forms.Textarea(attrs={'class': 'input'}),
            'profile_picture': forms.FileInput(attrs={'class': 'input'}),
            'language': forms.Select(attrs={'class': 'input'}),
            'location': forms.TextInput(attrs={'class': 'input'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'website': forms.URLInput(attrs={'class': 'input'}),
        }

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Kullanici Adi',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Sifre',
            'class': 'form-control'
        })
    )



class CustomRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Ad', 'class': 'form-control'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Soyad', 'class': 'form-control'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Kullanici Adi', 'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'E-posta', 'class': 'form-control'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Sifre', 'class': 'form-control'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Sifre (tekrar)', 'class': 'form-control'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Telefon Numarasi', 'class': 'form-control'})
    )

    profile_picture = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 
            'password1', 'password2', 'phone_number','profile_picture'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Şifreler eşleşmiyor.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')

        if commit:
            user.save()

            # Create or update profile
            profile, created = Profile.objects.get_or_create(user=user)

            # Only update profile_picture if provided
            profile_picture = self.cleaned_data.get('profile_picture')
            if profile_picture:
                profile.profile_picture = profile_picture

            profile.save()

            user.profile = profile
            user.save()

        return user