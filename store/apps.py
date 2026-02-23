"""
Cấu hình ứng dụng store cho QHUN22
"""
from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'
    verbose_name = 'Cửa hàng QHUN22'
