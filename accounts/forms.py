# accounts/forms.py

import base64
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.forms import ClearableFileInput

from accounts.models import Address, NotificationSettings, Subscription, Profile


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password1') != cd.get('password2'):
            raise forms.ValidationError('Пароли не совпадают.')
        return cd.get('password2')


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class CustomClearableFileInput(ClearableFileInput):
    clear_checkbox_label = ''
    initial_text = ''
    input_text = 'Изменить'
    clear_checkbox_checked = False
    template_name = 'accounts/custom_clearable_file_input.html'


class ProfileForm(forms.ModelForm):
    # Добавляем скрытое поле для данных об обрезанном изображении
    cropped_avatar = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Profile
        # Поле 'address' удалено, так как в модели Profile его нет.
        fields = [
            'avatar', 'bio', 'birth_date', 'phone_number',
            'twitter', 'facebook', 'instagram', 'linkedin',
            'receive_newsletters', 'receive_notifications'
        ]
        widgets = {
            'avatar': CustomClearableFileInput(attrs={
                'accept': 'image/*',
                'style': 'display:none;'
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^\+?1?\d{9,15}$', phone):
            raise forms.ValidationError(
                "Номер телефона должен быть в формате +999999999. До 15 цифр."
            )
        return phone

    def clean_twitter(self):
        twitter = self.cleaned_data.get('twitter')
        if twitter and not re.match(
            r'^https?://(www\.)?twitter\.com/[\w-]+/?$', twitter
        ):
            raise forms.ValidationError("Некорректный URL Twitter.")
        return twitter

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        # Дополнительная валидация, если требуется
        return avatar

    def clean_cropped_avatar(self):
        cropped_avatar = self.cleaned_data.get('cropped_avatar')
        # Дополнительная валидация, если требуется
        return cropped_avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        cropped_avatar = self.cleaned_data.get('cropped_avatar')
        if cropped_avatar:
            try:
                format_str, imgstr = cropped_avatar.split(';base64,')
                ext = format_str.split('/')[-1]
                data = ContentFile(
                    base64.b64decode(imgstr),
                    name=f'cropped_avatar.{ext}'
                )
                profile.avatar = data
            except Exception:
                raise forms.ValidationError("Ошибка обработки изображения.")
        if commit:
            profile.save()
        return profile


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['address_line1', 'address_line2', 'city', 'postal_code', 'country', 'is_default']
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = ['email_notifications', 'sms_notifications', 'push_notifications']
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['category']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
