from .models import Notification, Message

def notifications_count(request):
    if request.user.is_authenticated:
        notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

        # Виключаємо рахунок чат-повідомлень з підсумкового лічильника
        return {
            'unread_notifications_count': notifications_count,  # Тільки сповіщення
            'notifications_only_count': notifications_count  # Теж для сповіщень окремо
        }

    return {}
