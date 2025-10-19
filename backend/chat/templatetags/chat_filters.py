import os
from django import template

register = template.Library()

@register.filter
def filename(value):
    return os.path.basename(value)

@register.filter
def file_size_mb(value):
    """"Convert bytes to MB with 2 decimal places"""
    if value:
        return round(value / (1000 * 1000), 2)
    return 0

@register.filter
def is_recently_active(last_seen):
    if not last_seen:
        return False
    from django.utils import timezone
    return (timezone.now() - last_seen).total_seconds() < 300
