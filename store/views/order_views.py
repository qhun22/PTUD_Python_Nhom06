"""
Order Views (tracking, checkout, refund, wishlist) - QHUN22 Store
Auto-generated from views.py
"""
import os
import json
import uuid
import random
import time
import traceback
import requests
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db import models
from django.db.models import Q, Count, Sum, Max
from django.utils import timezone
from django.urls import reverse
import datetime



def order_tracking(request):
    """
    Tra cứu đơn hàng - hiển thị tất cả đơn hàng của user đang đăng nhập
    (bao gồm cả đơn đã tất toán)
    Tự động hủy đơn "Chờ thanh toán" khi quá 15 phút
    """
    from store.models import Order, PendingQRPayment
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import timedelta
    
    context = {}
    if request.user.is_authenticated:
        # Tự động hủy đơn "Chờ thanh toán" quá 15 phút (VietQR)
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        
        # Lấy các đơn VietQR quá 15 phút chưa được duyệt
        expired_orders = Order.objects.filter(
            user=request.user,
            status='awaiting_payment',
            payment_method='vietqr',
            created_at__lt=fifteen_minutes_ago
        )
        
        if expired_orders.exists():
            # Lấy thông tin để cập nhật PendingQRPayment
            # Dựa vào: cùng user, cùng amount, gần thời gian tạo
            cutoff_time = timezone.now() - timedelta(minutes=15)
            
            for order in expired_orders:
                # Tìm PendingQRPayment tương ứng (cùng user, gần thời điểm tạo đơn)
                pending_qr = PendingQRPayment.objects.filter(
                    user=request.user,
                    amount=order.total_amount,
                    status='pending',
                    created_at__gte=cutoff_time
                ).first()
                
                if pending_qr:
                    pending_qr.status = 'cancelled'
                    pending_qr.save()
            
            # Hủy các đơn hàng
            expired_orders.update(status='cancelled')
        
        # Lấy tất cả đơn hàng (bao gồm cả đã tất toán)
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items').order_by('-created_at')
        
        # Phân trang 10 đơn hàng mỗi trang
        paginator = Paginator(orders, 10)
        page = request.GET.get('page', 1)
        
        try:
            orders = paginator.page(page)
        except PageNotAnInteger:
            orders = paginator.page(1)
        except EmptyPage:
            orders = paginator.page(paginator.num_pages)
        
        context['orders'] = orders
    
    return render(request, 'store/order_tracking.html', context)



@login_required
@require_POST
def cancel_order(request):
    """
    API hủy đơn hàng - chỉ cho phép hủy khi status là pending hoặc processing
    """
    import json
    from store.models import Order
    
    try:
        data = json.loads(request.body)
        order_code = data.get('order_code', '')
        refund_account = data.get('refund_account', '')
        refund_bank = data.get('refund_bank', '')
        
        order = Order.objects.get(order_code=order_code, user=request.user)
        
        if order.status not in ('pending', 'processing'):
            return JsonResponse({'success': False, 'message': 'Đơn hàng không thể hủy ở trạng thái này'})
        
        # Lưu thông tin hoàn tiền nếu có (VNPay/VietQR)
        if order.payment_method in ('vietqr', 'vnpay'):
            if refund_account:
                order.refund_account = refund_account
            if refund_bank:
                order.refund_bank = refund_bank
            # Set refund status to pending when user requests refund
            if refund_account or refund_bank:
                order.refund_status = 'pending'
        
        order.status = 'cancelled'
        order.save()
        
        return JsonResponse({'success': True, 'message': 'Đã hủy đơn hàng ' + order_code})
    
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy đơn hàng'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})



def refund_pending(request):
    """
    API lấy danh sách đơn cần hoàn tiền (đã hủy + thanh toán VNPay/VietQR + chờ hoàn tiền)
    """
    from store.models import Order
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Không được phép'}, status=401)
    
    orders = Order.objects.filter(
        user=request.user,
        status='cancelled',
        payment_method__in=['vietqr', 'vnpay'],
        refund_status='pending'
    ).prefetch_related('items')
    
    orders_data = []
    for order in orders:
        items_data = []
        for item in order.items.all():
            cn = item.color_name or ''
            if ' - ' in cn:
                cn = cn.split(' - ', 1)[1]
            items_data.append({
                'product_name': item.product_name,
                'quantity': item.quantity,
                'color_name': cn,
                'storage': item.storage,
                'price': str(item.price)
            })
        orders_data.append({
            'order_code': order.order_code,
            'total_amount': str(order.total_amount),
            'payment_method': order.payment_method,
            'refund_account': order.refund_account,
            'refund_bank': order.refund_bank,
            'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'items': items_data
        })
    
    return JsonResponse({'orders': orders_data})



def refund_history(request):
    """
    API lấy lịch sử hoàn tiền (đã hoàn tiền)
    """
    from store.models import Order
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Không được phép'}, status=401)
    
    orders = Order.objects.filter(
        user=request.user,
        status='cancelled',
        refund_status='completed'
    ).prefetch_related('items')
    
    orders_data = []
    for order in orders:
        items_data = []
        for item in order.items.all():
            items_data.append({
                'product_name': item.product_name,
                'quantity': item.quantity
            })
        orders_data.append({
            'order_code': order.order_code,
            'total_amount': str(order.total_amount),
            'refund_account': order.refund_account,
            'refund_bank': order.refund_bank,
            'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'items': items_data
        })
    
    return JsonResponse({'orders': orders_data})



def refund_detail(request, order_code):
    """
    API lấy chi tiết đơn hoàn tiền
    """
    from store.models import Order
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Không được phép'}, status=401)
    
    try:
        order = Order.objects.get(order_code=order_code, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy đơn hàng'}, status=404)
    
    items_data = []
    for item in order.items.all():
        cn = item.color_name or ''
        if ' - ' in cn:
            cn = cn.split(' - ', 1)[1]
        items_data.append({
            'product_name': item.product_name,
            'quantity': item.quantity,
            'color_name': cn,
            'storage': item.storage,
            'price': str(item.price)
        })
    
    return JsonResponse({
        'order': {
            'order_code': order.order_code,
            'total_amount': str(order.total_amount),
            'payment_method': order.payment_method,
            'refund_account': order.refund_account,
            'refund_bank': order.refund_bank,
            'refund_status': order.refund_status,
            'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'items': items_data
        }
    })



def wishlist(request):
    """
    Danh sách sản phẩm yêu thích
    Hiển thị tối đa 15 sản phẩm mỗi trang
    """
    from store.models import Wishlist

    # Lấy danh sách yêu thích của user
    wishlist = Wishlist.get_or_create_for_user(request.user)

    if wishlist:
        # Lấy các sản phẩm yêu thích, sắp xếp theo thời gian thêm gần nhất
        wishlist_products = wishlist.products.select_related('brand', 'detail').order_by('-wishlisted_by')
    else:
        wishlist_products = []

    # Phân trang - 15 sản phẩm mỗi trang
    paginator = Paginator(wishlist_products, 15)

    # Lấy số trang từ URL
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    context = {
        'products': products,
        'wishlist': wishlist,
    }
    return render(request, 'store/wishlist.html', context)



@require_POST
def wishlist_toggle(request):
    """
    API thêm/xóa sản phẩm khỏi danh sách yêu thích (AJAX)
    """
    from store.models import Wishlist, Product

    # Kiểm tra user đã đăng nhập chưa
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập để thêm yêu thích',
            'require_login': True,
        }, status=401)

    # Lấy product_id từ request
    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu product_id',
        }, status=400)

    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm không tồn tại',
        }, status=404)

    # Lấy hoặc tạo wishlist cho user
    wishlist = Wishlist.get_or_create_for_user(request.user)

    if wishlist.has_product(product):
        # Nếu đã có thì xóa (unlike)
        wishlist.remove_product(product)
        is_liked = False
        message = 'Đã xóa khỏi yêu thích'
    else:
        # Nếu chưa có thì thêm (like)
        wishlist.add_product(product)
        is_liked = True
        message = 'Đã thêm vào yêu thích'

    # Đếm tổng số sản phẩm yêu thích
    total_wishlist = wishlist.products.count()

    return JsonResponse({
        'success': True,
        'message': message,
        'is_liked': is_liked,
        'total_wishlist': total_wishlist,
    })



@login_required
def checkout_view(request):
    """
    Trang thanh toán - hiển thị sản phẩm đã chọn, địa chỉ giao hàng,
    phương thức thanh toán và tổng tiền
    """
    from store.models import Cart, Address, FolderColorImage, ProductDetail

    # Lấy danh sách item_ids từ query param
    items_param = request.GET.get('items', '')
    if not items_param:
        return redirect('store:cart_detail')

    try:
        item_ids = [int(x) for x in items_param.split(',') if x.strip()]
    except (ValueError, TypeError):
        return redirect('store:cart_detail')

    if not item_ids:
        return redirect('store:cart_detail')

    # Lấy cart và items
    cart = Cart.get_or_create_for_user(request.user)
    if not cart:
        return redirect('store:cart_detail')

    cart_items = list(
        cart.items.filter(id__in=item_ids)
        .select_related('product', 'product__brand')
        .order_by('-created_at')
    )

    if not cart_items:
        return redirect('store:cart_detail')

    # Lấy thumbnail cho từng item
    for item in cart_items:
        product = item.product
        item.color_thumbnail = ''
        item.original_price = None

        try:
            detail = ProductDetail.objects.get(product=product)
            variants = detail.variants.filter(is_active=True)

            # Tìm original_price
            current_variant = variants.filter(
                color_name=item.color_name,
                storage=item.storage
            ).first()
            if current_variant and current_variant.original_price > current_variant.price:
                item.original_price = current_variant.original_price

            # Tìm thumbnail cho màu hiện tại
            if product.brand_id:
                current_sku_variant = variants.filter(color_name=item.color_name).first()
                if current_sku_variant and current_sku_variant.sku:
                    img = FolderColorImage.objects.filter(
                        brand_id=product.brand_id,
                        sku=current_sku_variant.sku
                    ).order_by('order').first()
                    if img:
                        item.color_thumbnail = img.image.url
        except ProductDetail.DoesNotExist:
            pass

    # Địa chỉ mặc định
    default_address = Address.objects.filter(user=request.user, is_default=True).first()

    # Tính tổng
    subtotal = sum(item.price_at_add * item.quantity for item in cart_items)

    context = {
        'cart_items': cart_items,
        'default_address': default_address,
        'has_default_address': default_address is not None,
        'subtotal': subtotal,
        'total': subtotal,
        'items_param': items_param,
    }
    return render(request, 'store/checkout.html', context)



@login_required
def address_add(request):
    """
    Thêm địa chỉ mới vào sổ địa chỉ
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Yêu cầu không hợp lệ'}, status=405)
    
    from store.models import Address
    
    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    province_code = request.POST.get('province_code', '').strip()
    province_name = request.POST.get('province_name', '').strip()
    district_code = request.POST.get('district_code', '').strip()
    district_name = request.POST.get('district_name', '').strip()
    ward_code = request.POST.get('ward_code', '').strip()
    ward_name = request.POST.get('ward_name', '').strip()
    detail = request.POST.get('detail', '').strip()
    is_default = request.POST.get('is_default') == 'true'
    
    if not all([full_name, phone, province_code, province_name, district_code, district_name, ward_code, ward_name, detail]):
        return JsonResponse({'success': False, 'message': 'Vui lòng điền đầy đủ thông tin'})
    
    # Nếu đặt làm mặc định, bỏ mặc định các địa chỉ khác
    if is_default:
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    
    # Nếu chưa có địa chỉ nào, tự động đặt làm mặc định
    if not Address.objects.filter(user=request.user).exists():
        is_default = True
    
    addr = Address.objects.create(
        user=request.user,
        full_name=full_name,
        phone=phone,
        province_code=province_code,
        province_name=province_name,
        district_code=district_code,
        district_name=district_name,
        ward_code=ward_code,
        ward_name=ward_name,
        detail=detail,
        is_default=is_default,
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Thêm địa chỉ thành công!',
        'address': {
            'id': addr.id,
            'full_name': addr.full_name,
            'phone': addr.phone,
            'province_name': addr.province_name,
            'district_name': addr.district_name,
            'ward_name': addr.ward_name,
            'detail': addr.detail,
            'is_default': addr.is_default,
        }
    })



@login_required
def address_delete(request):
    """
    Xóa địa chỉ
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Yêu cầu không hợp lệ'}, status=405)
    
    from store.models import Address
    
    address_id = request.POST.get('address_id')
    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        was_default = addr.is_default
        addr.delete()
        
        # Nếu xóa địa chỉ mặc định, đặt địa chỉ đầu tiên làm mặc định
        if was_default:
            first = Address.objects.filter(user=request.user).first()
            if first:
                first.is_default = True
                first.save()
        
        return JsonResponse({'success': True, 'message': 'Xóa địa chỉ thành công!'})
    except Address.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy địa chỉ'})



@login_required
def address_set_default(request):
    """
    Đặt địa chỉ mặc định
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Yêu cầu không hợp lệ'}, status=405)
    
    from store.models import Address
    
    address_id = request.POST.get('address_id')
    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        addr.is_default = True
        addr.save()
        return JsonResponse({'success': True, 'message': 'Đã đặt làm địa chỉ mặc định!'})
    except Address.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy địa chỉ'})



@csrf_exempt
@login_required
@require_POST
def place_order(request):
    """
    Đặt hàng COD hoặc VietQR (sau khi admin duyệt).
    POST JSON: { payment_method: 'cod' | 'vietqr', items_param: '1,2,3', transfer_code: '...' (nếu vietqr) }
    """
    from store.models import Cart, Order, OrderItem, ProductDetail, FolderColorImage, PendingQRPayment
    import json
    import random as _rand
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)
    
    payment_method = data.get('payment_method', 'cod')
    items_param = data.get('items_param', '')
    transfer_code = data.get('transfer_code', '')
    
    if payment_method not in ['cod', 'vietqr', 'vnpay', 'momo']:
        return JsonResponse({'success': False, 'message': 'Phương thức thanh toán không hợp lệ'}, status=400)
    
    # Nếu VietQR, kiểm tra đã được duyệt chưa
    if payment_method == 'vietqr':
        if not transfer_code:
            return JsonResponse({'success': False, 'message': 'Thiếu mã chuyển khoản'}, status=400)
        try:
            qr = PendingQRPayment.objects.get(transfer_code=transfer_code, user=request.user, status='approved')
        except PendingQRPayment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chưa được admin xác nhận thanh toán'}, status=400)
    
    # Lấy cart items
    if not items_param:
        return JsonResponse({'success': False, 'message': 'Không có sản phẩm'}, status=400)
    
    try:
        item_ids = [int(x) for x in items_param.split(',') if x.strip()]
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Danh sách sản phẩm không hợp lệ'}, status=400)
    
    cart = Cart.get_or_create_for_user(request.user)
    if not cart:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy giỏ hàng'}, status=400)
    
    cart_items = list(cart.items.filter(id__in=item_ids).select_related('product', 'product__brand'))
    if not cart_items:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy sản phẩm trong giỏ'}, status=400)
    
    # Tính tổng tiền
    total_amount = sum(item.price_at_add * item.quantity for item in cart_items)
    
    # Xử lý mã giảm giá (7-step)
    coupon_code = data.get('coupon_code', '').strip().upper()
    discount_amount = Decimal('0')
    item_count = sum(ci.quantity for ci in cart_items)
    if coupon_code:
        from store.models import Coupon
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            # Kiểm tra target giống coupon_apply: hỗ trợ cả email edu đã xác thực
            _target_ok = False
            if coupon.target_type == 'all':
                _target_ok = True
            elif coupon.target_type == 'single':
                _user_email = request.user.email.lower() if request.user.email else ''
                _target_email = coupon.target_email.lower() if coupon.target_email else ''
                _verified_student = (getattr(request.user, 'verified_student_email', None) or '').lower()
                _verified_teacher = (getattr(request.user, 'verified_teacher_email', None) or '').lower()
                _target_ok = (
                    _user_email == _target_email or
                    _user_email == _verified_student or
                    _user_email == _verified_teacher or
                    _target_email == _verified_student or
                    _target_email == _verified_teacher
                )
            if (coupon.is_valid()
                and total_amount >= coupon.min_order_amount
                and (coupon.max_products == 0 or item_count <= coupon.max_products)
                and _target_ok):
                # Kiểm tra per-user usage
                from store.models import CouponUsage
                _user_usage = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
                if coupon.usage_limit > 0 and _user_usage >= coupon.usage_limit:
                    coupon_code = ''  # Người dùng này hết lượt
                else:
                    discount_amount = coupon.calculate_discount(total_amount)
                    CouponUsage.objects.create(coupon=coupon, user=request.user)
                    coupon.used_count += 1
                    coupon.save(update_fields=['used_count'])
            else:
                coupon_code = ''
        except Coupon.DoesNotExist:
            coupon_code = ''
    
    final_amount = total_amount - discount_amount
    
    # Tạo mã đơn hàng
    tracking_code = 'QHUN' + str(_rand.randint(10000, 99999))
    
    # Tạo Order
    order = Order.objects.create(
        user=request.user,
        order_code=tracking_code,
        total_amount=final_amount,
        coupon_code=coupon_code,
        discount_amount=discount_amount,
        payment_method=payment_method,
        status='pending' if payment_method == 'cod' else 'processing'
    )
    
    # Tạo OrderItem (stock sẽ giảm khi admin set status = delivered)
    for ci in cart_items:
        thumb_url = ''
        try:
            if ci.product and ci.product.brand_id:
                detail = ProductDetail.objects.get(product=ci.product)
                variant = detail.variants.filter(
                    is_active=True, color_name=ci.color_name
                ).first()
                if variant and variant.sku:
                    img = FolderColorImage.objects.filter(
                        brand_id=ci.product.brand_id,
                        sku=variant.sku
                    ).order_by('order').first()
                    if img:
                        thumb_url = img.image.url
            if not thumb_url and ci.product and ci.product.image:
                thumb_url = ci.product.image.url
        except Exception:
            pass
        
        OrderItem.objects.create(
            order=order,
            product=ci.product,
            product_name=ci.product.name if ci.product else 'Sản phẩm',
            color_name=ci.color_name,
            storage=ci.storage,
            quantity=ci.quantity,
            price=ci.price_at_add,
            thumbnail=thumb_url,
        )
    
    # Xóa cart items
    cart.items.filter(id__in=item_ids).delete()
    
    # Nếu VietQR, giữ lại PendingQRPayment (status='approved') để hiển thị lịch sử duyệt
    # Không xóa record — admin có thể xem lại trong tab Lịch sử
    
    if payment_method == 'cod':
        from store.telegram_utils import notify_order_success
        from store.email_utils import send_order_invoice_email
        items_info = [
            {
                'product_name': ci.product.name if ci.product else 'Sản phẩm',
                'quantity': ci.quantity,
                'storage': ci.storage,
                'color_name': ci.color_name,
            }
            for ci in cart_items
        ]
        notify_order_success(tracking_code, 'cod', items_info)
        send_order_invoice_email(order, base_url=request.build_absolute_uri('/'))
    
    return JsonResponse({
        'success': True,
        'message': 'Đặt hàng thành công!',
        'order_code': tracking_code
    })



@login_required
def order_success(request, order_code):
    """
    Trang thông báo đặt hàng thành công
    """
    from store.models import Order
    
    try:
        order = Order.objects.prefetch_related('items').get(order_code=order_code, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'Không tìm thấy đơn hàng')
        return redirect('store:home')
    
    return render(request, 'store/order_success.html', {
        'order': order,
        'order_items': order.items.all(),
    })
