# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.utils.html import escapejs
from django.http import JsonResponse
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib.auth import logout
from django.core.mail import send_mail

from django.views.decorators.http import require_POST

from deepface import DeepFace
from django.core.files.storage import default_storage
import os
import logging


# Django REST Framework imports
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Local app imports
from .models import Car, UserProfile, CarImage, CarRentalRequest, Notification, Message
from .serializers import CarSerializer
from .permissions import IsOwnerOrReadOnly
from django.contrib.auth.decorators import login_required
from .forms import CarForm, CarImageForm, RegistrationForm, CarRentalRequestForm
import requests
from datetime import timedelta
from decimal import Decimal

# -------------------------------
# API Views
# -------------------------------

class CarViewSet(viewsets.ModelViewSet):
    """Список всіх машин та створення нової (з прив’язкою до власника)."""
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user.userprofile)


class MyCarsView(generics.ListAPIView):
    """Список машин, доданих поточним користувачем."""
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Car.objects.filter(owner=self.request.user.userprofile)

# -------------------------------
# Web Views
# -------------------------------

def index(request):
    cars = Car.objects.all()
    return render(request, 'main/index.html', {'cars': cars})


def rent(request):
    query = request.GET.get('q')
    sort_option = request.GET.get('sort')

    cars = Car.objects.all()

    if query:
        cars = cars.filter(
            Q(brand__icontains=query) | Q(model__icontains=query)
        )

    # Сортування
    sort_mapping = {
        'price_asc': ['price_per_hour', 'price_per_day'],
        'price_desc': ['-price_per_hour', '-price_per_day'],
        'year_asc': ['year'],
        'year_desc': ['-year'],
        'brand_asc': ['brand'],
        'brand_desc': ['-brand'],
    }

    if sort_option in sort_mapping:
        cars = cars.order_by(*sort_mapping[sort_option])

    cars = cars.prefetch_related('images')

    car_map_data = [
        {
            "brand": car.brand,
            "model": car.model,
            "city": car.city
        }
        for car in cars if car.city
    ]

    return render(request, 'main/rent.html', {
        'cars': cars,
        'car_map_data': car_map_data,
        'query': query,
        'sort': sort_option,
    })


def add_car(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            car_form = CarForm(request.POST)
            images = request.FILES.getlist('images')  # Получаем список загруженных изображений

            if car_form.is_valid():
                car = car_form.save(commit=False)
                car.owner = request.user.userprofile

                # Просто сохраняем машину
                car.save()

                # Сохраняем изображения
                for image in images:
                    CarImage.objects.create(car=car, image=image)

                return redirect('index')

        else:
            car_form = CarForm()

        return render(request, 'main/add_car.html', {
            'car_form': car_form,
        })

    else:
        # Неавторизованный пользователь — показываем сообщение
        return render(request, 'main/add_car.html', {
            'auth_required': True
        })

def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    return render(request, 'main/car_detail.html', {'car': car})


def auth_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or '/'

    form = RegistrationForm()  # ← Ініціалізація за замовчуванням

    if request.method == 'POST':
        if 'register' in request.POST:
            form = RegistrationForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Реєстрація успішна. Увійдіть.')
                return redirect('auth')
            else:
                messages.error(request, 'Помилка при реєстрації.')
        elif 'login' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(next_url)
            else:
                messages.error(request, 'Невірні дані для входу.')
                # форма реєстрації не потрібна, але для шаблону її треба передати
                form = RegistrationForm()  # ← додатково тут, якщо хочеш перевизначити явно

    return render(request, 'main/auth.html', {
        'form': form,
        'next': next_url
    })

@login_required
def profile_view(request):
    profile = request.user.userprofile

    if request.method == 'POST':
        new_email = request.POST.get('email')
        if new_email:
            request.user.email = new_email
            request.user.save()

        new_selfie = request.FILES.get('selfie')
        if new_selfie:
            profile.selfie = new_selfie
            profile.save()

        messages.success(request, "Зміни збережено.")

    # ІСТОРІЯ ОРЕНД
    rented_cars = CarRentalRequest.objects.filter(renter=request.user).select_related('car').order_by('-created_at')
    given_cars = CarRentalRequest.objects.filter(car__owner=profile)

    return render(request, 'main/profile.html', {
        'user': request.user,
        'profile': profile,
        'rented_cars': rented_cars,
        'given_cars': given_cars,
    })


def logout_view(request):
    logout(request)
    return redirect('index')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user:
                login(request, user)
                return redirect('index')  # или 'profile', если хочешь
            else:
                messages.error(request, "Неправильний email або пароль.")
        except User.DoesNotExist:
            messages.error(request, "Користувача не знайдено.")
    return render(request, 'main/auth.html')

@login_required
def my_cars(request):
    cars = Car.objects.filter(owner=request.user.userprofile)
    return render(request, 'main/my_cars.html', {'cars': cars})

@login_required
def delete_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, owner=request.user.userprofile)

    if request.method == 'POST':
        car.delete()
        messages.success(request, "Авто успішно видалено.")
        return redirect('my_cars')

    return HttpResponseForbidden("Неможливо виконати цю дію.")


@login_required
def car_edit(request, car_id):
    car = get_object_or_404(Car, id=car_id, owner=request.user.userprofile)
    images = car.images.all()

    if request.method == 'POST':
        car_form = CarForm(request.POST, instance=car)
        new_images = request.FILES.getlist('images')

        if car_form.is_valid():
            car_form.save()

            # Додаємо нові зображення
            for image in new_images:
                CarImage.objects.create(car=car, image=image)

            # Видалення обраних зображень (ID передаються з hidden inputs або JS)
            to_delete = request.POST.getlist('delete_images')
            if to_delete:
                CarImage.objects.filter(id__in=to_delete, car=car).delete()

            messages.success(request, "Інформацію оновлено!")
            return redirect('car_edit', car_id=car.id)

    else:
        car_form = CarForm(instance=car)

    return render(request, 'main/car_edit.html', {
        'car': car,
        'car_form': car_form,
        'images': images,
    })


@login_required
def delete_car_image(request, image_id):
    image = get_object_or_404(CarImage, id=image_id)

    # Перевірка, що користувач є власником авто
    if image.car.owner != request.user.userprofile:
        return HttpResponseForbidden("Ви не можете видалити це фото.")

    if request.method == 'POST':
        image.delete()
        messages.success(request, "Фото успішно видалено.")

    return redirect('car_edit', car_id=image.car.id)



@login_required
def rent_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if car.owner.user == request.user:
        messages.error(request, "Ви не можете орендувати власне авто.")
        return redirect('car_detail', car_id=car.id)

    if request.method == 'POST':
        form = CarRentalRequestForm(request.POST)

        if form.is_valid():
            rental = form.save(commit=False)
            rental.car = car
            rental.renter = request.user

            # 🔍 Проверка, занято ли авто на этот период
            existing = CarRentalRequest.objects.filter(
                car=car,
                status__in=['pending', 'approved'],
                start_datetime__lt=rental.end_datetime,
                end_datetime__gt=rental.start_datetime
            ).exists()

            if existing:
                messages.error(request, "Цей автомобіль вже орендовано на вказаний період.")
                return render(request, 'main/rent_car.html', {
                    'form': form,
                    'car': car
                })

            delta = rental.end_datetime - rental.start_datetime
            hours = delta.total_seconds() / 3600

            if hours <= 0:
                messages.error(request, "Дата завершення повинна бути пізніше за дату початку.")
                return render(request, 'main/rent_car.html', {
                    'form': form,
                    'car': car
                })

            days = int(hours // 24)
            remaining_hours = hours % 24

            price_per_day = Decimal(car.price_per_day)
            price_per_hour = Decimal(car.price_per_hour)
            days_decimal = Decimal(days)
            remaining_hours_decimal = Decimal(remaining_hours)

            # 💰 Розрахунок ціни
            rental.total_price = days_decimal * price_per_day + remaining_hours_decimal * price_per_hour

            rental.save()  # ✅ Зберігаємо, якщо все гаразд

            owner_user = car.owner.user
            send_notification(owner_user, f"Новий запит на оренду вашого авто «{car}»", rental_request=rental)

            send_email_notification(
                subject="Новий запит на оренду вашого авто",
                message=f"Користувач {request.user.username} надіслав запит на оренду авто: {car}.",
                recipient_email=owner_user.email
            )

            messages.success(request, "Запит на оренду надіслано власнику авто.")
            return redirect('car_detail', car_id=car.id)

            # TODO: Надіслати email або повідомлення власнику авто


    else:
        form = CarRentalRequestForm()

    return render(request, 'main/rent_car.html', {
        'form': form,
        'car': car
    })


def send_notification(user, message, rental_request=None):
    Notification.objects.create(
        user=user,
        message=message,
        rental_request=rental_request
    )


@login_required
def chat_view(request, rental_id):
    rental = get_object_or_404(CarRentalRequest, id=rental_id)

    if request.user != rental.renter and request.user != rental.car.owner.user:
        return redirect('notifications')  # захист: тільки учасники чату

    messages = Message.objects.filter(rental_request=rental).order_by('timestamp')

    chat_with = rental.car.owner.user.username if request.user == rental.renter else rental.renter.username

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                rental_request=rental,
                sender=request.user,
                content=content
            )
            return redirect('chat_view', rental_id=rental.id)

    # Отметить сообщения как прочитанные
    Message.objects.filter(
        rental_request=rental,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    return render(request, 'main/chat.html', {
        'rental': rental,
        'messages': messages,
        'chat_with': chat_with,
        'is_chat_page': True,
    })

@login_required
def send_message(request, rental_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        rental_request = CarRentalRequest.objects.get(id=rental_id)

        # Створення нового повідомлення
        message = Message.objects.create(
            sender=request.user,
            rental_request=rental_request,
            content=content
        )

        # Отримувач
        receiver = rental_request.renter if request.user == rental_request.car.owner.user else rental_request.car.owner.user

        # Якщо це перше непрочитане повідомлення — надсилаємо email
        unread_count = Message.objects.filter(
            rental_request=rental_request,
            is_read=False,
            sender=request.user
        ).count()

        if unread_count == 1:
            send_email_notification(
                subject="Нове повідомлення в чаті CarSwap",
                message=f"У вас нове повідомлення в чаті щодо авто «{rental_request.car}».",
                recipient_email=receiver.email
            )

        # Повернення даних для оновлення чату через AJAX
        return JsonResponse({
            'success': True,
            'sender': message.sender.username,
            'content': message.content,
            'timestamp': message.timestamp.strftime('%d.%m.%Y %H:%M'),
        })

    return JsonResponse({'success': False}, status=400)

@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    for n in notifications:
        rental = n.rental_request
        if rental:
            # Подсчёт сообщений от другого пользователя, которые ещё не прочитаны
            n.unread_count = rental.messages.filter(
                is_read=False
            ).exclude(sender=request.user).count()

    notifications.update(is_read=True)
    return render(request, 'main/notifications.html', {
        'notifications': notifications
    })

@login_required
def respond_to_rental_request(request, request_id):
    rental_request = get_object_or_404(
        CarRentalRequest,
        id=request_id,
        car__owner__user=request.user
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if rental_request.status != 'pending':
            messages.warning(request, "Цей запит вже оброблено.")
            return redirect('notifications')

        if action == "approve":
            rental_request.status = 'approved'
            message = f"Ваш запит на оренду авто «{rental_request.car}» підтверджено."
            messages.success(request, "Запит підтверджено.")
        elif action == "reject":
            rental_request.status = 'rejected'
            message = f"Ваш запит на оренду авто «{rental_request.car}» відхилено."
            messages.success(request, "Запит відхилено.")
        else:
            messages.error(request, "Невідома дія.")
            return redirect('notifications')

        rental_request.save()

        # Надсилаємо орендарю сповіщення
        send_notification(rental_request.renter, message, rental_request=rental_request)
        send_email_notification(
            subject="Статус вашого запиту на оренду",
            message=message,
            recipient_email=rental_request.renter.email
        )

    return redirect('notifications')


logger = logging.getLogger(__name__)
#
# @login_required
# def unlock_car(request, rental_id):
#     rental = get_object_or_404(CarRentalRequest, id=rental_id)
#
#     # 🔒 Захист — тільки орендар і статус має бути approved
#     if rental.renter != request.user:
#         messages.error(request, 'У вас немає доступу до цього запиту.')
#         return redirect('notifications')
#
#     if rental.status != 'approved':
#         messages.error(request, 'Цей запит ще не підтверджений.')
#         return redirect('notifications')
#
#     if rental.is_unlocked:
#         messages.info(request, 'Авто вже розблоковане.')
#         return redirect('notifications')
#
#     if request.method == 'POST':
#         uploaded_file = request.FILES.get('photo')
#         if not uploaded_file:
#             messages.error(request, 'Фото не надано.')
#             return redirect('notifications')
#
#         path_uploaded = default_storage.save('temp_uploaded.jpg', uploaded_file)
#         reference_photo_path = request.user.userprofile.selfie.path
#
#         try:
#             result = DeepFace.verify(
#                 img1_path=reference_photo_path,
#                 img2_path=default_storage.path(path_uploaded),
#                 model_name='Facenet',
#                 enforce_detection=True
#             )
#             if result['verified']:
#                 rental.is_unlocked = True
#                 rental.save()
#                 messages.success(request, 'Обличчя підтверджено, авто розблоковано.')
#             else:
#                 messages.error(request, 'Обличчя не співпало. Доступ заборонено.')
#
#         except Exception as e:
#             logger.exception("Помилка при розпізнаванні обличчя")
#             messages.error(request, f'Помилка при розпізнаванні: {str(e)}')
#
#         default_storage.delete(path_uploaded)
#         return redirect('notifications')
#

@login_required
def verify_and_pay(request, rental_id):
    rental = get_object_or_404(CarRentalRequest, id=rental_id)

    # Перевірка доступу
    if rental.renter != request.user or rental.status != 'approved':
        messages.error(request, 'У вас немає доступу до цього запиту.')
        return redirect('notifications')

    if rental.is_unlocked:
        messages.info(request, 'Авто вже розблоковане.')
        return redirect('notifications')

    if request.method == 'POST':
        # Перевірка, чи користувач пройшов верифікацію
        if 'photo' in request.FILES:
            uploaded_file = request.FILES['photo']
            path_uploaded = default_storage.save('temp_uploaded.jpg', uploaded_file)
            reference_photo_path = request.user.userprofile.selfie.path

            try:
                result = DeepFace.verify(
                    img1_path=reference_photo_path,
                    img2_path=default_storage.path(path_uploaded),
                    model_name='Facenet',
                    enforce_detection=True
                )
                if result['verified']:
                    request.session['face_verified'] = True  # тимчасове збереження стану
                    messages.success(request, 'Обличчя підтверджено. Тепер оплатіть оренду.')
                else:
                    messages.error(request, 'Обличчя не співпало. Доступ заборонено.')

            except Exception as e:
                logger.exception("Помилка при розпізнаванні обличчя")
                messages.error(request, f'Помилка при розпізнаванні: {str(e)}')

            default_storage.delete(path_uploaded)
            return redirect('verify_and_pay', rental_id=rental.id)

        # Обробка оплати
        elif request.POST.get('pay') and request.session.get('face_verified'):
            rental.is_unlocked = True
            rental.save()
            request.session.pop('face_verified', None)
            messages.success(request, 'Оренду оплачено, авто розблоковано.')
            return redirect('notifications')

        else:
            messages.error(request, 'Спочатку пройдіть верифікацію обличчя.')
            return redirect('verify_and_pay', rental_id=rental.id)

    return render(request, 'main/verify_and_pay.html', {'rental': rental})

@login_required
def complete_rental(request, rental_id):
    rental = get_object_or_404(CarRentalRequest, id=rental_id)

    if request.user != rental.renter:
        messages.error(request, "У вас немає прав для завершення цієї оренди.")
        return redirect('notifications')

    if rental.status == 'completed':
        messages.info(request, "Ця оренда вже завершена.")
        return redirect('notifications')

    if not rental.is_unlocked:
        messages.warning(request, "Авто ще не було розблоковано.")
        return redirect('notifications')

    rental.status = 'completed'
    rental.save()

    messages.success(request, "Оренду успішно завершено.")
    return redirect('notifications')


@require_POST
@login_required
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect('index')


def send_email_notification(subject, message, recipient_email):
    send_mail(
        subject,
        message,
        'carswapcompany@gmail.com',  # або DEFAULT_FROM_EMAIL
        [recipient_email],
        fail_silently=False
    )