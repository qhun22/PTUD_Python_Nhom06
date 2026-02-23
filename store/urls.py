"""
URL configuration cho ứng dụng store
"""
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Trang chủ
    path('', views.home, name='home'),
    # Tìm kiếm sản phẩm
    path('products/search/', views.product_search, name='product_search'),
    # Giỏ hàng
    path('cart/', views.cart_detail, name='cart_detail'),
    # Tra cứu đơn hàng
    path('order-tracking/', views.order_tracking, name='order_tracking'),
    # Yêu thích
    path('wishlist/', views.wishlist, name='wishlist'),
    # Tài khoản
    path('login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
]
