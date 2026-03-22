"""
Cấu hình Django Admin cho ứng dụng store
"""
from django.contrib import admin
from store.models import VNPayPayment, ProductReview, UserBrowseLog, HotSaleProduct


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['created_at']


@admin.register(VNPayPayment)
class VNPayPaymentAdmin(admin.ModelAdmin):
    list_display = ['order_code', 'user', 'amount', 'status', 'transaction_no', 'created_at', 'paid_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_code', 'transaction_no', 'user__email']
    readonly_fields = ['order_code', 'transaction_no', 'response_code', 'response_message', 'created_at', 'updated_at', 'paid_at']


@admin.register(UserBrowseLog)
class UserBrowseLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'product', 'brand', 'viewed_at']
    list_filter = ['brand', 'viewed_at']
    search_fields = ['user__email', 'ip_address', 'product__name', 'brand__name']
    readonly_fields = ['viewed_at']
    date_hierarchy = 'viewed_at'


@admin.register(HotSaleProduct)
class HotSaleProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'sort_order', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['product__name']
    list_editable = ['sort_order', 'is_active']
    ordering = ['sort_order', '-created_at']
