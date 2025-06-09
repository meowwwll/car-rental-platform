from django import template

register = template.Library()

STATUS_TRANSLATIONS = {
    'pending': 'Очікує',
    'approved': 'Схвалено',
    'rejected': 'Відхилено',
    'completed': 'Завершено',
}

@register.filter
def status_uk(value):
    return STATUS_TRANSLATIONS.get(value, value)
