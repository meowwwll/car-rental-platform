from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Car(models.Model):
    owner = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='cars',
        verbose_name="Власник"
    )
    brand = models.CharField(max_length=50, verbose_name="Марка")
    model = models.CharField(max_length=50, verbose_name="Модель")
    year = models.PositiveIntegerField(verbose_name="Рік випуску")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Місто розташування авто")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Ціна за день")
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=0, verbose_name="Ціна за годину")
    description = models.TextField(blank=True, null=True, verbose_name="Опис авто")

    fuel_type = models.CharField(
        max_length=20,
        choices=[
            ('petrol', 'Бензин'),
            ('diesel', 'Дизель'),
            ('electric', 'Електро'),
            ('hybrid', 'Гібрид'),
        ],
        default='petrol',
        verbose_name="Тип пального"
    )
    transmission = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Механіка'),
            ('automatic', 'Автомат'),
            ('cvt', 'Варіатор'),
        ],
        default='manual',
        verbose_name="Коробка передач"
    )
    seats = models.PositiveSmallIntegerField(default=4, verbose_name="Кількість місць")

    class Meta:
        verbose_name = "Авто"
        verbose_name_plural = "Автомобілі"
        ordering = ['brand', 'model']

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"

    def save(self, *args, **kwargs):
        if (self.price_per_hour is None or self.price_per_hour == 0) and self.price_per_day:
            self.price_per_hour = round(self.price_per_day / 24, 2)

        super().save(*args, **kwargs)

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="images", verbose_name="Авто")
    image = models.ImageField(upload_to='cars/', blank=True, null=True, verbose_name="Фото авто")

    class Meta:
        verbose_name = "Фото авто"
        verbose_name_plural = "Фото автомобілів"

    def __str__(self):
        return f"Фото для {self.car.brand} {self.car.model}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Акаунт користувача")
    full_name = models.CharField(max_length=255, verbose_name="ПІБ")
    driver_license_series = models.CharField(max_length=10, verbose_name="Серія ПВ")
    driver_license_number = models.CharField(max_length=10, verbose_name="Номер ПВ")
    birth_date = models.DateField(verbose_name="Дата народження власника ПВ")
    selfie = models.ImageField(upload_to='faces/', blank=True, null=True, verbose_name="Фото для Face ID")
    email = models.EmailField(blank=True, null=True, verbose_name="Електронна пошта")

    class Meta:
        verbose_name = "Профіль користувача"
        verbose_name_plural = "Профілі користувачів"
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

class CarRentalRequest(models.Model):
    car = models.ForeignKey('Car', on_delete=models.CASCADE, related_name='rental_requests')
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rental_requests')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_unlocked = models.BooleanField(default=False)

    STATUS_CHOICES = [
        ('pending', 'Очікує підтвердження'),
        ('approved', 'Підтверджено'),
        ('rejected', 'Відхилено'),
        ('cancelled', 'Скасовано'),
        ('completed', 'Завершено'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.renter} → {self.car} ({self.start_datetime} - {self.end_datetime})"

    def clean(self):
        if self.start_datetime >= self.end_datetime:
            raise ValidationError("Дата завершення має бути пізніше дати початку.")


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    rental_request = models.ForeignKey('CarRentalRequest', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сповіщення для {self.user.username}"


class Message(models.Model):
    rental_request = models.ForeignKey('CarRentalRequest', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Від {self.sender.username} для {self.rental_request.id} о {self.timestamp.strftime('%d.%m.%Y %H:%M')}"
