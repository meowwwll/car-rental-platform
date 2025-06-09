from django.contrib import admin
from .models import Car, CarImage, UserProfile

# Инлайн-отображение фото машины
class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 4

# Админка для машин
class CarAdmin(admin.ModelAdmin):
    inlines = [CarImageInline]
    list_display = ('brand', 'model', 'year', 'city', 'owner')  # Показываем владельца
    search_fields = ('brand', 'model', 'owner__full_name')

# Админка для профиля пользователя
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'driver_license_series', 'driver_license_number', 'birth_date')
    search_fields = ('full_name', 'email', 'driver_license_series', 'driver_license_number')

# Регистрация моделей
admin.site.register(Car, CarAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
