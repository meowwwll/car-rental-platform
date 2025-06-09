from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение: Только владелец объекта может редактировать или удалять его.
    Для остальных - только чтение.
    """
    def has_object_permission(self, request, view, obj):
        # Разрешаем безопасные методы (GET, HEAD, OPTIONS) для всех
        if request.method in permissions.SAFE_METHODS:
            return True
        # Изменение/удаление — только если пользователь владелец
        return obj.owner == request.user.userprofile
