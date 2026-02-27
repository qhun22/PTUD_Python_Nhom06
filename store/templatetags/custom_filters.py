"""
Custom template filters for QHUN22
"""
from django import template

register = template.Library()

@register.filter
def format_price(value):
    """
    Format price with dot notation: 1000000 -> 1.000.000
    """
    if value is None:
        return '0'
    
    try:
        value = int(value)
    except (ValueError, TypeError):
        return '0'
    
    return '{:,}'.format(value).replace(',', '.')

@register.filter
def format_price_with_unit(value):
    """
    Format price with dot notation and 'đ' unit: 1000000 -> 1.000.000đ
    """
    if value is None:
        return '0đ'
    
    try:
        value = int(value)
    except (ValueError, TypeError):
        return '0đ'
    
    return '{:,}đ'.format(value).replace(',', '.')

@register.filter
def color_only(value):
    """
    Strip SKU prefix from color name: 'T3W8P - Trắng' -> 'Trắng'
    """
    if not value or value == '—':
        return value
    if ' - ' in str(value):
        return str(value).split(' - ', 1)[1]
    return value

@register.filter
def filter_refunded(orders):
    """
    Lọc đơn hàng đã hoàn tiền (cancelled + refund_status = 'completed')
    """
    return [o for o in orders if o.status == 'cancelled' and o.refund_status == 'completed']