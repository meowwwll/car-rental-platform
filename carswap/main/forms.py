from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Car, CarImage, CarRentalRequest
from django.core.exceptions import ValidationError
from django.forms.widgets import DateInput
import requests
import imghdr
from bs4 import BeautifulSoup  # Для парсингу HTML


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Підтвердження паролю")

    class Meta:
        model = UserProfile
        fields = ['full_name', 'driver_license_series', 'driver_license_number', 'birth_date', 'selfie', 'email']
        widgets = {
            'birth_date': DateInput(attrs={'type': 'date', 'placeholder': 'Напр. 1999-12-31'}),
        }
        labels = {
            'birth_date': 'Дата народження',
        }

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise ValidationError("Паролі не співпадають")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        series = cleaned_data.get('driver_license_series')
        number = cleaned_data.get('driver_license_number')
        birth_date = cleaned_data.get('birth_date')
        selfie = cleaned_data.get('selfie')
        full_name = cleaned_data.get('full_name')
        email = cleaned_data.get('email')

        if not full_name or not full_name.strip():
            self.add_error('full_name', "Введіть повне ім’я.")


        if email and User.objects.filter(username=email).exists():
            self.add_error('email', "Користувач з такою електронною поштою вже існує.")


        if not selfie:
            self.add_error('selfie', "Додайте фото з посвідченням особи (селфі).")
        else:
            if selfie.content_type not in ['image/jpeg', 'image/png']:
                self.add_error('selfie', "Допустимі лише зображення JPG або PNG.")

            elif imghdr.what(selfie) not in ['jpeg', 'png']:
                self.add_error('selfie', "Завантажте справжнє зображення (JPG або PNG).")

        if series and number:
            if UserProfile.objects.filter(driver_license_series=series, driver_license_number=number).exists():
                self._errors.pop('__all__', None)
                raise ValidationError("Профіль з такою серією і номером водійського посвідчення вже існує.")


        # Онлайн-перевірка ПВ через HSC
        if series and number and birth_date:
            url = "https://opendata.hsc.gov.ua/check-driver-license/"
            payload = {
                "seria": series,
                "number": number,
                "birthday_system": birth_date.strftime('%Y-%m-%d')
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://opendata.hsc.gov.ua/check-driver-license/",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            try:
                session = requests.Session()
                response = session.post(url, data=payload, headers=headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)

                if "ПОМИЛКА ВВОДУ ДАНИХ" in text:
                    raise ValidationError("Посвідчення водія не знайдено. Перевірте правильність даних.")
                elif "Результат перевірки посвідчення водія" not in text:
                    raise ValidationError("Неможливо перевірити посвідчення. Спробуйте пізніше.")
            except requests.RequestException:
                raise ValidationError("Помилка під час перевірки посвідчення. Спробуйте пізніше.")


    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['email'],  # логін по email
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email']
        )
        profile = super().save(commit=False)
        profile.user = user
        if commit:
            profile.save()
        return user


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['brand', 'model', 'year', 'city', 'price_per_day', 'price_per_hour', 'description', 'fuel_type', 'transmission', 'seats']
        # Пример для добавления аттрибутов к полям
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'price_per_day': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', }),
            'fuel_type': forms.Select(attrs={'class': 'form-select'}),
            'transmission': forms.Select(attrs={'class': 'form-select'}),
            'seats': forms.NumberInput(attrs={'class': 'form-control'}),
        }



class CarImageForm(forms.ModelForm):
    class Meta:
        model = CarImage
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем класс form-control для поля загрузки изображения
        self.fields['image'].widget.attrs.update({'class': 'form-control'})



class CarRentalRequestForm(forms.ModelForm):
    class Meta:
        model = CarRentalRequest
        fields = ['start_datetime', 'end_datetime']
        labels = {
            'start_datetime': 'Початок оренди авто',
            'end_datetime': 'Кінець оренди авто',
        }
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
