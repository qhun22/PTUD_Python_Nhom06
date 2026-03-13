"""
store.views package
Re-exports tất cả views để urls.py không cần thay đổi.
"""
from .admin_views import admin_order_detail, admin_order_list, admin_order_update_status, banner_add, banner_delete, banner_list, banner_replace, best_sellers_admin, best_sellers_api, brand_add, brand_delete, brand_edit, brand_list, dashboard_order_detail, dashboard_product_detail, dashboard_view, export_revenue_month, export_revenue_year, folder_color_image_delete, folder_color_image_list, folder_color_image_upload, folder_color_rename, folder_color_row_delete, generate_slug, get_product_detail, image_folder_create, image_folder_delete, image_folder_list, product_add, product_content_add, product_content_delete, product_content_list, product_content_replace, product_delete, product_detail_save, product_edit, product_image_delete, product_image_upload, product_specification_delete, product_specification_upload, product_variant_delete, product_variant_save, save_youtube_id, sku_add, sku_delete, sku_edit, sku_list, upload_temp_image, user_add, user_delete, user_detail_json, user_edit
from .auth_views import forgot_password_view, login_view, profile, register_view, reset_password_view, send_otp_forgot_password_view, send_otp_view, send_verification_code, verify_code, verify_otp_forgot_password_view, verify_turnstile
from .cart_views import cart_add, cart_change_color, cart_change_storage, cart_detail, cart_remove, cart_update_quantity
from .chatbot_views import chatbot_api
from .coupon_views import coupon_add, coupon_apply, coupon_delete, coupon_edit, coupon_list
from .order_views import address_add, address_delete, address_set_default, cancel_order, checkout_view, order_success, order_tracking, place_order, refund_detail, refund_history, refund_pending, wishlist, wishlist_toggle
from .payment_views import qr_payment_approve, qr_payment_cancel, qr_payment_create, qr_payment_detail, qr_payment_list, qr_payment_status, vietqr_create_order, vietqr_expire, vietqr_page_status, vietqr_payment_page, vnpay_create, vnpay_ipn, vnpay_return
from .product_views import compare_view, home, newsletter_subscribe, product_detail_view, product_filter_json, product_list_json, product_search, submit_review
