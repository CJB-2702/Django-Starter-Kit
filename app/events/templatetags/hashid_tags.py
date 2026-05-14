from django import template
from app.utils.hashids import encode_id as _encode_id

register = template.Library()


@register.filter
def encode_id(pk):
    """Encode an integer PK to a hashid string. Usage: {{ event.pk|encode_id }}"""
    if pk is None:
        return ""
    return _encode_id(int(pk))
