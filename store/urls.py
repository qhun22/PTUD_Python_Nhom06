"""
URL configuration cho ứng dụng store
"""
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Trang chủ
    path('', views.home, name='home'),
    # Chi tiết sản phẩm
    path('product/<int:product_id>/', views.product_detail_view, name='product_detail'),
    # Tìm kiếm sản phẩm
    path('products/search/', views.product_search, name='product_search'),
    # Giỏ hàng
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/update/', views.cart_update_quantity, name='cart_update_quantity'),
    path('cart/change-color/', views.cart_change_color, name='cart_change_color'),
    path('cart/change-storage/', views.cart_change_storage, name='cart_change_storage'),

    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    # Tra cứu đơn hàng
    path('order-tracking/', views.order_tracking, name='order_tracking'),
    # Yêu thích
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    # Tài khoản
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('profile/', views.profile, name='profile'),
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    # Quản lý hãng
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/add/', views.brand_add, name='brand_add'),
    path('brands/edit/', views.brand_edit, name='brand_edit'),
    path('brands/delete/', views.brand_delete, name='brand_delete'),
    # Quản lý người dùng
    path('users/edit/', views.user_edit, name='user_edit'),
    path('users/delete/', views.user_delete, name='user_delete'),
    # Quan ly san pham
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/', views.product_edit, name='product_edit'),
    path('products/delete/', views.product_delete, name='product_delete'),
    # Chi tiet san pham
    path('products/detail/save/', views.product_detail_save, name='product_detail_save'),
    path('products/detail/get/', views.get_product_detail, name='get_product_detail'),
    path('products/variant/save/', views.product_variant_save, name='product_variant_save'),
    path('products/variant/delete/', views.product_variant_delete, name='product_variant_delete'),
    path('products/specification/upload/', views.product_specification_upload, name='product_specification_upload'),
    path('products/specification/delete/', views.product_specification_delete, name='product_specification_delete'),
    path('products/youtube/save/', views.save_youtube_id, name='save_youtube_id'),
    path('products/image/upload/', views.product_image_upload, name='product_image_upload'),
    path('products/image/delete/', views.product_image_delete, name='product_image_delete'),
    # Product image folders management
    path('product-images/folders/list/', views.image_folder_list, name='image_folder_list'),
    path('product-images/folders/create/', views.image_folder_create, name='image_folder_create'),
    path('product-images/color/list/', views.folder_color_image_list, name='folder_color_image_list'),
    path('product-images/color/upload/', views.folder_color_image_upload, name='folder_color_image_upload'),
    path('product-images/color/delete/', views.folder_color_image_delete, name='folder_color_image_delete'),
    path('product-images/color/row-delete/', views.folder_color_row_delete, name='folder_color_row_delete'),
    # Temp Image Upload
    path('upload-temp-image/', views.upload_temp_image, name='upload_temp_image'),
    # Banner Images Management
    path('banner-images/list/', views.banner_list, name='banner_list'),
    path('banner-images/add/', views.banner_add, name='banner_add'),
    path('banner-images/replace/', views.banner_replace, name='banner_replace'),
    path('banner-images/delete/', views.banner_delete, name='banner_delete'),
    # Product Content Management
    path('product-content/list/', views.product_content_list, name='product_content_list'),
    path('product-content/add/', views.product_content_add, name='product_content_add'),
    path('product-content/replace/', views.product_content_replace, name='product_content_replace'),
    path('product-content/delete/', views.product_content_delete, name='product_content_delete'),
    # Product List JSON
    path('products/list/json/', views.product_list_json, name='product_list_json'),
    # SKU Management
    path('products/sku/list/', views.sku_list, name='sku_list'),
    path('products/sku/add/', views.sku_add, name='sku_add'),
    path('products/sku/edit/', views.sku_edit, name='sku_edit'),
    path('products/sku/delete/', views.sku_delete, name='sku_delete'),
    # Quen mat khau
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('send-otp-forgot-password/', views.send_otp_forgot_password_view, name='send_otp_forgot_password'),
    path('verify-otp-forgot-password/', views.verify_otp_forgot_password_view, name='verify_otp_forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    # Address Book
    path('address/add/', views.address_add, name='address_add'),
    path('address/delete/', views.address_delete, name='address_delete'),
    path('address/set-default/', views.address_set_default, name='address_set_default'),

    # Place Order (COD/VietQR)
    path('order/place/', views.place_order, name='place_order'),
    
    # QR Payment
    path('qr-payment/create/', views.qr_payment_create, name='qr_payment_create'),
    path('qr-payment/list/', views.qr_payment_list, name='qr_payment_list'),
    path('qr-payment/detail/', views.qr_payment_detail, name='qr_payment_detail'),
    path('qr-payment/approve/', views.qr_payment_approve, name='qr_payment_approve'),
    path('qr-payment/status/', views.qr_payment_status, name='qr_payment_status'),
    path('qr-payment/cancel/', views.qr_payment_cancel, name='qr_payment_cancel'),

    # VNPay Payment
    path('vnpay/create/', views.vnpay_create, name='vnpay_create'),

    # Order Success
    path('order/success/<str:order_code>/', views.order_success, name='order_success'),
    
    # Cancel Order API
    path('api/cancel-order/', views.cancel_order, name='cancel_order'),
    
    # Refund APIs
    path('api/refund-pending/', views.refund_pending, name='refund_pending'),
    path('api/refund-history/', views.refund_history, name='refund_history'),
    path('api/refund-detail/<str:order_code>/', views.refund_detail, name='refund_detail'),

    # Product Review
    path('api/submit-review/', views.submit_review, name='submit_review'),

    # Admin Order Management
    path('api/admin/orders/', views.admin_order_list, name='admin_order_list'),
    path('api/admin/order-detail/', views.admin_order_detail, name='admin_order_detail'),
    path('api/admin/order-update-status/', views.admin_order_update_status, name='admin_order_update_status'),
]
