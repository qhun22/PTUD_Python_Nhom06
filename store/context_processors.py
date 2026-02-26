"""
Context processors cho QHUN22
"""
from django.conf import settings


def qhun22_context(request):
    """
    Thêm các biến global vào context của template
    """
    context = {
        'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', ''),
    }

    # Thêm thông tin người dùng nếu đã đăng nhập
    if request.user.is_authenticated:
        context['user_display_name'] = request.user.get_full_name()
        context['user_short_name'] = request.user.get_short_name()
        context['user_email'] = request.user.email
        context['user_phone'] = request.user.phone
        context['is_oauth_user'] = getattr(request.user, 'is_oauth_user', False)

        # Thêm số lượng wishlist
        from store.models import Wishlist
        wishlist = Wishlist.get_or_create_for_user(request.user)
        if wishlist:
            context['wishlist_count'] = wishlist.products.count()
        else:
            context['wishlist_count'] = 0

        # Thêm số lượng giỏ hàng
        from store.models import Cart
        cart = Cart.get_or_create_for_user(request.user)
        if cart:
            context['cart_count'] = cart.get_total_items()
        else:
            context['cart_count'] = 0

        # Thêm số lượng đơn hàng
        from store.models import Order
        context['order_count'] = Order.objects.filter(user=request.user).count()
    else:
        context['wishlist_count'] = 0
        context['cart_count'] = 0
        context['order_count'] = 0

    return context
