from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    CarViewSet,
    MyCarsView,
    index,
    rent,
    car_detail,
    auth_view,
    login_view
)

# DRF router для базових REST-шляхів
router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='car')

urlpatterns = [
    # HTML-сторінки
    path('', index, name='index'),
    path('rent/', rent, name='rent'),
    path('car/<int:car_id>/', views.car_detail, name='car_detail'),  # для перегляду
    path('car/<int:car_id>/edit/', views.car_edit, name='car_edit'),  # для редагування

    path('car/<int:car_id>/edit/', views.car_edit, name='car_edit'),
    path('car-image/<int:image_id>/delete/', views.delete_car_image, name='delete_car_image'),
    path('auth/', auth_view, name='auth'),
    path('login/', login_view, name='login'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('add-car/', views.add_car, name='add_car'),
    path('my-cars/', views.my_cars, name='my_cars'),
    path('delete-car/<int:car_id>/', views.delete_car, name='delete_car'),
    path('rent/<int:car_id>/', views.rent_car, name='rent_car'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('rental-response/<int:request_id>/', views.respond_to_rental_request, name='respond_to_rental'),
    path('chat/<int:rental_id>/', views.chat_view, name='chat_view'),
    path('send_message/<int:rental_id>/', views.send_message, name='send_message'),

    path('verify-and-pay/<int:rental_id>/', views.verify_and_pay, name='verify_and_pay'),
    path('rental/<int:rental_id>/complete/', views.complete_rental, name='complete_rental'),

    path('delete_account/', views.delete_account, name='delete_account'),


    # API endpoints
    path('api/', include(router.urls)),                     # /api/cars/
    path('api/my-cars/', MyCarsView.as_view(), name='my-cars'),  # /api/my-cars/
]