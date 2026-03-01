"""
Views cho ứng dụng store - QHUN22
"""
import os
import random
import time
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


def verify_turnstile(token):
    """
    Xác minh Cloudflare Turnstile token
    """
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                'response': token,
            },
            timeout=10
        )
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        print(f"Turnstile verification error: {e}")
        return False


def send_otp_view(request):
    """
    Gửi OTP qua email (AJAX)
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email missing'})
        
        # Kiểm tra email đã tồn tại chưa
        from store.models import CustomUser
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Email đã tồn tại trong hệ thống! Vui lòng sử dụng email khác.'})
        
        # Tạo OTP 5 chữ số
        otp = str(random.randint(10000, 99999))
        
        # Lưu vào session
        request.session['otp'] = otp
        request.session['otp_email'] = email
        request.session['otp_created_at'] = int(time.time())  # Thời điểm tạo OTP
        request.session['otp_expire'] = 300  # 5 phút (để tính toán sau)
        
        # Gửi email qua SendGrid
        api_key = os.getenv('SENDGRID_API_KEY', '')
        from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com')
        
        data = {
            "personalizations": [{
                "to": [{"email": email}],
                "subject": "OTP Verification - QHUN22"
            }],
            "from": {"email": from_email},
            "content": [{
                "type": "text/html",
                "value": f"<h1>Mã OTP của bạn: {otp}</h1><p>Mã có hiệu lực trong 5 phút.</p>"
            }]
        }
        
        try:
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                return JsonResponse({'status': 'success', 'message': 'OTP_SENT'})
            else:
                return JsonResponse({'status': 'error', 'message': f'Failed to send email: {response.status_code}'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def product_detail_view(request, product_id):
    """Trang chi tiết sản phẩm"""
    from store.models import Product, ProductDetail, ProductVariant, FolderColorImage, ProductSpecification, ProductContent
    from django.shortcuts import get_object_or_404
    import json
    
    product = get_object_or_404(Product, id=product_id)
    
    # Get or create product detail
    product_detail, created = ProductDetail.objects.get_or_create(product=product)
    
    # Get variants
    variants = product_detail.variants.all().order_by('storage', 'color_name')
    
    # Build unique colors (giữ thứ tự theo SKU)
    seen_colors = {}
    color_list = []
    for v in variants:
        if v.color_name not in seen_colors:
            seen_colors[v.color_name] = True
            color_list.append({
                'color_name': v.color_name,
                'color_hex': v.color_hex or '',
                'sku': v.sku or '',
            })
    
    # Build unique storages (giữ thứ tự)
    seen_storages = {}
    storage_list = []
    for v in variants:
        if v.storage not in seen_storages:
            seen_storages[v.storage] = True
            storage_list.append(v.storage)
    
    # First variant for default display
    first_variant = variants.first()
    
    # Get color images from FolderColorImage (theo brand)
    # Group by SKU -> color_name -> list of image URLs
    color_images = {}
    if product.brand_id:
        sku_list = list(set(v.sku for v in variants if v.sku))
        folder_images = FolderColorImage.objects.filter(
            brand_id=product.brand_id,
            sku__in=sku_list
        ).order_by('sku', 'order')
        
        for img in folder_images:
            key = img.sku
            if key not in color_images:
                color_images[key] = {
                    'color_name': img.color_name,
                    'sku': img.sku,
                    'images': []
                }
            color_images[key]['images'].append(img.image.url)
    
    # Convert to list for JSON (Decimal -> int để JSON serialize được)
    variants_list = []
    for v in variants:
        # Nếu variant không có stock riêng, fallback dùng Product.stock
        variant_stock = int(v.stock_quantity) if v.stock_quantity else 0
        if variant_stock == 0:
            variant_stock = product.stock
        
        variants_list.append({
            'id': v.id,
            'color_name': v.color_name,
            'color_hex': v.color_hex or '',
            'storage': v.storage,
            'price': int(v.price) if v.price is not None else 0,
            'original_price': int(v.original_price) if v.original_price is not None else 0,
            'discount_percent': int(v.discount_percent) if v.discount_percent is not None else 0,
            'sku': v.sku or '',
            'stock_quantity': variant_stock,
        })
    
    # Get specifications
    spec_data = None
    try:
        spec = ProductSpecification.objects.get(detail=product_detail)
        spec_data = spec.spec_json
    except ProductSpecification.DoesNotExist:
        pass
    
    # Get promo banner (id=72535)
    from store.models import Banner
    promo_banner = None
    try:
        promo_banner = Banner.objects.get(banner_id='72535')
    except Banner.DoesNotExist:
        pass
    
    # Get product content (nội dung SP từ admin)
    product_content = None
    try:
        product_content = ProductContent.objects.get(product=product)
    except ProductContent.DoesNotExist:
        pass
    
    # Lấy YouTube ID
    youtube_id = product_detail.youtube_id if product_detail.youtube_id else ''
    
    # --- Đánh giá sản phẩm ---
    from store.models import ProductReview, OrderItem, Order
    reviews = ProductReview.objects.filter(product=product).select_related('user')
    review_count = reviews.count()
    avg_rating = 0
    if review_count > 0:
        avg_rating = round(sum(r.rating for r in reviews) / review_count, 1)
    
    user_review = None
    can_review = False
    must_login = not request.user.is_authenticated
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        if not user_review:
            has_delivered = OrderItem.objects.filter(
                order__user=request.user,
                order__status='delivered',
                product=product
            ).exists()
            can_review = has_delivered

    # --- Sản phẩm liên quan (cùng brand, random 5, loại trừ SP hiện tại) ---
    related_products = []
    if product.brand:
        related_products = list(
            Product.objects.filter(brand=product.brand, is_active=True)
            .exclude(id=product.id)
            .select_related('detail')
            .order_by('?')[:5]
        )
    
    context = {
        'product': product,
        'product_detail': product_detail,
        'color_list': color_list,
        'storage_list': storage_list,
        'first_variant': first_variant,
        'variants_json': json.dumps(variants_list),
        'color_images_json': json.dumps(color_images),
        'spec_data_json': json.dumps(spec_data) if spec_data else 'null',
        'promo_banner': promo_banner,
        'product_content': product_content,
        'youtube_id': youtube_id,
        'reviews': reviews,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'user_review': user_review,
        'can_review': can_review,
        'must_login': must_login,
        'related_products': related_products,
        'user': request.user,  # Add user to context
        'is_authenticated': request.user.is_authenticated,  # Add is_authenticated to context
    }
    
    return render(request, 'store/product_detail.html', context)


def submit_review(request):
    """API đánh giá sản phẩm - chỉ user đã mua thành công (delivered) mới được"""
    from django.http import JsonResponse
    from store.models import Product, ProductReview, OrderItem

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Vui lòng đăng nhập'}, status=401)

    product_id = request.POST.get('product_id')
    rating = request.POST.get('rating')

    if not product_id or not rating:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin'})

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return JsonResponse({'success': False, 'message': 'Số sao không hợp lệ'})
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Số sao không hợp lệ'})

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại'})

    if ProductReview.objects.filter(user=request.user, product=product).exists():
        return JsonResponse({'success': False, 'message': 'Bạn đã đánh giá sản phẩm này rồi'})

    has_delivered = OrderItem.objects.filter(
        order__user=request.user,
        order__status='delivered',
        product=product
    ).exists()
    if not has_delivered:
        return JsonResponse({'success': False, 'message': 'Bạn cần mua và nhận hàng thành công mới được đánh giá'})

    ProductReview.objects.create(user=request.user, product=product, rating=rating)

    reviews = ProductReview.objects.filter(product=product)
    count = reviews.count()
    avg = round(sum(r.rating for r in reviews) / count, 1) if count else 0

    return JsonResponse({
        'success': True,
        'message': 'Đánh giá thành công!',
        'avg_rating': avg,
        'review_count': count,
        'user_rating': rating,
    })


def home(request):
    """
    Trang chủ của cửa hàng QHUN22
    Hiển thị danh sách sản phẩm với phân trang (tối đa 15 sản phẩm/trang)
    Sản phẩm có hàng hiển thị trước, hết hàng hiển thị sau
    """
    from store.models import Product, SiteVisit, OrderItem, Order, Banner
    
    # Tracking lượt truy cập trang chủ
    # Lấy IP của người dùng
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Lưu lượt truy cập
    SiteVisit.objects.create(
        ip_address=ip_address,
        user=request.user if request.user.is_authenticated else None
    )
    
    # Lấy tất cả sản phẩm đang hoạt động
    # Sắp xếp: có hàng trước (stock > 0), hết hàng sau
    # Sử dụng annotation để sắp xếp theo stock
    from django.db.models import Case, When, IntegerField
    
    products_list = Product.objects.filter(is_active=True).select_related('brand', 'detail').annotate(
        stock_order=Case(
            When(stock__gt=0, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by('stock_order', '-created_at')
    
    # Phân trang - 15 sản phẩm mỗi trang
    paginator = Paginator(products_list, 15)
    
    # Lấy số trang từ URL
    page = request.GET.get('page', 1)
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        # Nếu page không phải số, lấy trang đầu tiên
        products = paginator.page(1)
    except EmptyPage:
        # Nếu trang vượt quá, lấy trang cuối cùng
        products = paginator.page(paginator.num_pages)

    # Lấy danh sách sản phẩm yêu thích của user (nếu đã đăng nhập)
    wishlist_product_ids = []
    if request.user.is_authenticated:
        from store.models import Wishlist
        wishlist = Wishlist.get_or_create_for_user(request.user)
        if wishlist:
            wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))

    # Lấy top 5 sản phẩm bán chạy nhất
    # Chỉ tính các đơn hàng đã giao thành công (delivered)
    from django.db.models import Sum, F
    best_selling_products = OrderItem.objects.filter(
        order__status='delivered',
        product__is_active=True
    ).values('product__id', 'product__name', 'product__image', 'product__price', 
             'product__original_price', 'product__discount_percent', 'product__stock',
             'product__slug', 'product__brand__name').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]

    # Chuyển đổi queryset thành list với thông tin đầy đủ
    best_sellers = []
    for item in best_selling_products:
        product = Product.objects.filter(id=item['product__id']).first()
        if product:
            best_sellers.append({
                'product': product,
                'total_sold': item['total_sold']
            })

    context = {
        'products': products,
        'wishlist_product_ids': wishlist_product_ids,
        'best_sellers': best_sellers,
    }
    
    # Lấy đúng banner id=76294 cho GỢI Ý CHO BẠN
    suggest_banner = Banner.objects.filter(banner_id='76294').first()
    if suggest_banner:
        context['suggest_banner'] = suggest_banner
    # Lấy 5 sản phẩm gợi ý (ngẫu nhiên, còn hàng)
    import random
    all_active_products = list(Product.objects.filter(
        is_active=True, 
        stock__gt=0
    ).select_related('brand', 'detail'))
    if all_active_products:
        random.shuffle(all_active_products)
        context['suggest_products'] = all_active_products[:5]
    else:
        context['suggest_products'] = []
    
    return render(request, 'store/home.html', context)


def product_search(request):
    """
    Tìm kiếm và lọc sản phẩm
    - Tìm theo tên sản phẩm và tên hãng
    - Lọc theo hãng cụ thể
    """
    from store.models import Product, Brand, Wishlist
    from django.db.models import Case, When, IntegerField, Q
    
    query = request.GET.get('q', '').strip()
    brand_slug = request.GET.get('brand', '')
    
    # Lấy danh sách sản phẩm đang hoạt động
    products = Product.objects.filter(is_active=True).select_related('brand', 'detail')
    
    # Lọc theo từ khóa tìm kiếm (tên sản phẩm hoặc tên hãng)
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(brand__name__icontains=query)
        )
    
    # Lọc theo hãng nếu có
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)
    
    # Sắp xếp: có hàng trước, hết hàng sau
    products = products.annotate(
        stock_order=Case(
            When(stock__gt=0, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by('stock_order', '-created_at')
    
    # Phân trang - 15 sản phẩm mỗi trang
    paginator = Paginator(products, 15)
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Lấy danh sách sản phẩm yêu thích của user
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist = Wishlist.get_or_create_for_user(request.user)
        if wishlist:
            wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))
    
    # Lấy thông tin hãng nếu đang lọc theo hãng
    current_brand = None
    if brand_slug:
        current_brand = Brand.objects.filter(slug=brand_slug).first()
    
    context = {
        'query': query,
        'brand': brand_slug,
        'current_brand': current_brand,
        'products': products_page,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'store/search.html', context)


@require_http_methods(["GET"])
def product_list_json(request):
    """Lấy danh sách sản phẩm dạng JSON"""
    from store.models import Product
    try:
        products = Product.objects.select_related('brand').order_by('-created_at')
        
        product_list = []
        for p in products:
            product_list.append({
                'id': p.id,
                'name': p.name,
                'brand_id': p.brand.id if p.brand else None,
                'brand_name': p.brand.name if p.brand else None,
            })
        
        return JsonResponse({'success': True, 'products': product_list})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def cart_detail(request):
    """
    Chi tiết giỏ hàng
    Hiển thị các sản phẩm trong giỏ hàng
    """
    from store.models import Cart, FolderColorImage, ProductDetail, ProductVariant

    cart = Cart.get_or_create_for_user(request.user)

    if cart:
        # Lấy các item trong giỏ hàng
        cart_items = list(cart.items.select_related('product', 'product__brand').order_by('-created_at'))

        # Lấy color options cho từng item (ảnh thumbnail + tên màu)
        for item in cart_items:
            product = item.product
            item.color_options = []
            item.original_price = None
            item.color_thumbnail = ''  # Ảnh màu hiện tại

            # Lấy variants để biết các màu có sẵn
            try:
                detail = ProductDetail.objects.get(product=product)
                variants = detail.variants.filter(is_active=True)

                # Tìm original_price của variant hiện tại
                current_variant = variants.filter(
                    color_name=item.color_name,
                    storage=item.storage
                ).first()
                if current_variant and current_variant.original_price > current_variant.price:
                    item.original_price = current_variant.original_price

                # Lấy unique colors với SKU
                seen_colors = {}
                color_variants = []
                for v in variants.order_by('color_name'):
                    if v.color_name not in seen_colors:
                        seen_colors[v.color_name] = True
                        color_variants.append(v)

                # Lấy ảnh thumbnail cho từng màu từ FolderColorImage
                if product.brand_id:
                    sku_list = list(set(v.sku for v in color_variants if v.sku))
                    folder_images = {}
                    if sku_list:
                        imgs = FolderColorImage.objects.filter(
                            brand_id=product.brand_id,
                            sku__in=sku_list
                        ).order_by('sku', 'order')
                        for img in imgs:
                            if img.sku not in folder_images:
                                folder_images[img.sku] = img.image.url

                    for v in color_variants:
                        thumb = folder_images.get(v.sku, '')
                        item.color_options.append({
                            'color_name': v.color_name,
                            'sku': v.sku or '',
                            'thumbnail': thumb,
                            'is_selected': v.color_name == item.color_name,
                        })
                        # Lưu thumbnail của màu hiện tại
                        if v.color_name == item.color_name and thumb:
                            item.color_thumbnail = thumb

                # Lấy storage options cho màu hiện tại
                item.storage_options = []
                storage_variants = variants.filter(
                    color_name=item.color_name
                ).order_by('price')
                for sv in storage_variants:
                    item.storage_options.append({
                        'storage': sv.storage,
                        'price': int(sv.price),
                        'is_selected': sv.storage == item.storage,
                    })
            except ProductDetail.DoesNotExist:
                pass
    else:
        cart_items = []

    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'store/cart.html', context)


def order_tracking(request):
    """
    Tra cứu đơn hàng - hiển thị tất cả đơn hàng của user đang đăng nhập
    (bao gồm cả đơn đã tất toán)
    Có phân trang - 10 đơn/trang
    """
    from store.models import Order
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    context = {}
    if request.user.is_authenticated:
        # Lấy tất cả đơn hàng (bao gồm cả đã tất toán)
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items').order_by('-created_at')
        
        # Phân trang - 10 đơn mỗi trang
        paginator = Paginator(orders, 10)
        page = request.GET.get('page', 1)
        
        try:
            orders_page = paginator.page(page)
        except PageNotAnInteger:
            orders_page = paginator.page(1)
        except EmptyPage:
            orders_page = paginator.page(paginator.num_pages)
        
        context['orders'] = orders_page
    
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
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
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
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
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
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
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


@require_POST
def cart_add(request):
    """
    API thêm sản phẩm vào giỏ hàng (AJAX)
    """
    from store.models import Cart, CartItem, Product

    # Kiểm tra user đã đăng nhập chưa
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập để thêm vào giỏ hàng',
            'require_login': True,
        }, status=401)

    # Lấy thông tin từ request
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    color_name = request.POST.get('color_name', '')
    color_code = request.POST.get('color_code', '')
    storage = request.POST.get('storage', '')
    price = request.POST.get('price', 0)

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

    # Kiểm tra tồn kho trước khi thêm vào giỏ
    from store.models import ProductDetail
    available_stock = product.stock  # Mặc định dùng Product.stock
    
    # Nếu có color_name và storage, kiểm tra ProductVariant.stock_quantity
    if color_name and storage:
        try:
            detail = ProductDetail.objects.get(product=product)
            variant = detail.variants.filter(
                color_name=color_name,
                storage=storage,
                is_active=True
            ).first()
            if variant and variant.stock_quantity > 0:
                available_stock = variant.stock_quantity
            # Nếu variant không có stock riêng, giữ nguyên product.stock
        except ProductDetail.DoesNotExist:
            pass
    
    if available_stock <= 0:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm đã hết hàng!',
        }, status=400)
    
    if quantity > available_stock:
        return JsonResponse({
            'success': False,
            'message': f'Chỉ còn {available_stock} sản phẩm trong kho!',
        }, status=400)

    # Lấy hoặc tạo giỏ hàng cho user
    cart = Cart.get_or_create_for_user(request.user)

    # Kiểm tra xem sản phẩm đã có trong giỏ chưa (cùng màu, cùng storage)
    existing_item = CartItem.objects.filter(
        cart=cart,
        product=product,
        color_name=color_name,
        storage=storage
    ).first()

    if existing_item:
        # Kiểm tra tổng số lượng mới có vượt quá stock không
        new_quantity = existing_item.quantity + quantity
        if new_quantity > available_stock:
            return JsonResponse({
                'success': False,
                'message': f'Không thể thêm! Trong giỏ đã có {existing_item.quantity}, kho chỉ còn {available_stock} sản phẩm.',
            }, status=400)
        # Tăng số lượng
        existing_item.quantity = new_quantity
        existing_item.save()
        item = existing_item
        message = 'Đã cập nhật số lượng sản phẩm trong giỏ hàng'
    else:
        # Thêm mới
        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            color_name=color_name,
            color_code=color_code,
            storage=storage,
            price_at_add=price
        )
        message = 'Đã thêm sản phẩm vào giỏ hàng'

    # Đếm tổng số sản phẩm trong giỏ
    total_items = cart.get_total_items()

    return JsonResponse({
        'success': True,
        'message': message,
        'total_items': total_items,
        'item_quantity': item.quantity,
    })


@require_POST
def cart_remove(request):
    """
    API xóa sản phẩm khỏi giỏ hàng (AJAX)
    """
    from store.models import Cart, CartItem

    # Kiểm tra user đã đăng nhập chưa
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập',
            'require_login': True,
        }, status=401)

    # Lấy item_id từ request
    item_id = request.POST.get('item_id')
    if not item_id:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu item_id',
        }, status=400)

    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm không tồn tại trong giỏ hàng',
        }, status=404)

    cart = item.cart
    item.delete()

    # Đếm tổng số sản phẩm trong giỏ
    total_items = cart.get_total_items()

    return JsonResponse({
        'success': True,
        'message': 'Đã xóa sản phẩm khỏi giỏ hàng',
        'total_items': total_items,
    })


@require_POST
def cart_update_quantity(request):
    """
    API cập nhật số lượng sản phẩm trong giỏ hàng (AJAX)
    """
    from store.models import Cart, CartItem

    # Kiểm tra user đã đăng nhập chưa
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập',
            'require_login': True,
        }, status=401)

    # Lấy item_id và quantity từ request
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))

    if not item_id:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu item_id',
        }, status=400)

    if quantity < 1:
        return JsonResponse({
            'success': False,
            'message': 'Số lượng không được nhỏ hơn 1',
        }, status=400)

    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm không tồn tại trong giỏ hàng',
        }, status=404)

    cart = item.cart
    item.quantity = quantity
    item.save()

    # Tính lại tổng tiền
    total_price = cart.get_total_price()
    item_total = item.get_total_price()
    total_items = cart.get_total_items()

    return JsonResponse({
        'success': True,
        'message': 'Đã cập nhật số lượng',
        'total_items': total_items,
        'total_price': int(total_price),
        'item_total': int(item_total),
        'item_quantity': item.quantity,
    })


@require_POST
def cart_change_color(request):
    """
    API đổi màu sản phẩm trong giỏ hàng (AJAX)
    Cập nhật color_name, color_code và giá theo variant mới
    """
    from store.models import Cart, CartItem, ProductDetail, ProductVariant

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập',
            'require_login': True,
        }, status=401)

    item_id = request.POST.get('item_id')
    new_color = request.POST.get('color_name', '')

    if not item_id or not new_color:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu thông tin',
        }, status=400)

    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm không tồn tại trong giỏ hàng',
        }, status=404)

    # Tìm variant mới theo color + storage
    try:
        detail = ProductDetail.objects.get(product=item.product)
        new_variant = detail.variants.filter(
            color_name=new_color,
            storage=item.storage,
            is_active=True
        ).first()

        if not new_variant:
            # Nếu không tìm thấy variant cùng storage, lấy variant đầu tiên của màu đó
            new_variant = detail.variants.filter(
                color_name=new_color,
                is_active=True
            ).first()

        if new_variant:
            # Kiểm tra xem đã có item cùng product + color + storage chưa
            existing = CartItem.objects.filter(
                cart=item.cart,
                product=item.product,
                color_name=new_color,
                storage=new_variant.storage
            ).exclude(id=item.id).first()

            if existing:
                # Gộp vào item đã có
                existing.quantity += item.quantity
                existing.save()
                item.delete()
                item = existing
            else:
                item.color_name = new_color
                item.storage = new_variant.storage
                item.price_at_add = new_variant.price
                item.save()

            cart = item.cart
            total_price = cart.get_total_price()
            item_total = item.get_total_price()
            total_items = cart.get_total_items()

            # Lấy thumbnail của màu mới
            new_thumbnail = ''
            if new_variant.sku and item.product.brand_id:
                from store.models import FolderColorImage
                thumb_img = FolderColorImage.objects.filter(
                    brand_id=item.product.brand_id,
                    sku=new_variant.sku
                ).order_by('order').first()
                if thumb_img:
                    new_thumbnail = thumb_img.image.url

            return JsonResponse({
                'success': True,
                'message': f'Đã đổi sang màu {new_color}',
                'total_items': total_items,
                'total_price': int(total_price),
                'item_total': int(item_total),
                'item_price': int(new_variant.price),
                'original_price': int(new_variant.original_price) if new_variant.original_price > new_variant.price else 0,
                'new_color': new_color,
                'new_storage': new_variant.storage,
                'new_thumbnail': new_thumbnail,
            })

    except ProductDetail.DoesNotExist:
        pass

    return JsonResponse({
        'success': False,
        'message': 'Không tìm thấy biến thể phù hợp',
    }, status=400)


@require_POST
def cart_change_storage(request):
    """
    API đổi dung lượng sản phẩm trong giỏ hàng (AJAX)
    Cập nhật storage và giá theo variant mới
    """
    from store.models import Cart, CartItem, ProductDetail, ProductVariant

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng đăng nhập',
            'require_login': True,
        }, status=401)

    item_id = request.POST.get('item_id')
    new_storage = request.POST.get('storage', '')

    if not item_id or not new_storage:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu thông tin',
        }, status=400)

    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Sản phẩm không tồn tại trong giỏ hàng',
        }, status=404)

    # Tìm variant mới theo color hiện tại + storage mới
    try:
        detail = ProductDetail.objects.get(product=item.product)
        new_variant = detail.variants.filter(
            color_name=item.color_name,
            storage=new_storage,
            is_active=True
        ).first()

        if new_variant:
            # Kiểm tra xem đã có item cùng product + color + storage chưa
            existing = CartItem.objects.filter(
                cart=item.cart,
                product=item.product,
                color_name=item.color_name,
                storage=new_storage
            ).exclude(id=item.id).first()

            if existing:
                # Gộp vào item đã có
                existing.quantity += item.quantity
                existing.save()
                item.delete()
                item = existing
            else:
                item.storage = new_storage
                item.price_at_add = new_variant.price
                item.save()

            cart = item.cart
            total_price = cart.get_total_price()
            total_items = cart.get_total_items()

            return JsonResponse({
                'success': True,
                'message': f'Đã đổi sang {new_storage}',
                'total_items': total_items,
                'total_price': int(total_price),
                'item_price': int(new_variant.price),
                'original_price': int(new_variant.original_price) if new_variant.original_price > new_variant.price else 0,
                'new_storage': new_storage,
            })

    except ProductDetail.DoesNotExist:
        pass

    return JsonResponse({
        'success': False,
        'message': 'Không tìm thấy biến thể phù hợp',
    }, status=400)


def login_view(request):
    """
    Đăng nhập người dùng với Turnstile verification
    """
    # Nếu đã đăng nhập thì chuyển về trang chủ
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        # Lấy email để đăng nhập
        email = request.POST.get('username')  # Vẫn dùng field username trong form nhưng là email
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        # Tìm user theo email - CustomUser dùng email làm USERNAME_FIELD
        from store.models import CustomUser
        try:
            user_obj = CustomUser.objects.get(email=email)
            username = user_obj.username  # Sẽ là None nhưng authenticate cần
        except CustomUser.DoesNotExist:
            username = email
        
        # turnstile_token = request.POST.get('cf-turnstile-response')
        
        # Cloudflare Turnstile - Enable when deploying to production
        # if not turnstile_token:
        #     messages.error(request, 'Vui lòng xác minh bạn không phải robot!')
        #     return render(request, 'store/login.html')
        
        # # Xác minh Turnstile trước khi authenticate
        # if not verify_turnstile(turnstile_token):
        #     messages.error(request, 'Xác minh thất bại. Vui lòng thử lại!')
        #     return render(request, 'store/login.html')
        
        # Authenticate với email
        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Xử lý remember me
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
            else:
                request.session.set_expiry(0)  # Session hết khi đóng trình duyệt
            
            login(request, user)
            messages.success(request, 'Đăng nhập thành công!')
            return redirect('store:home')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')
    
    return render(request, 'store/login.html')


def profile(request):
    """
    Trang thông tin tài khoản người dùng
    """
    from store.models import Order
    from store.models import PasswordHistory
    from store.models import Address
    from django.db.models import Sum
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    context = {}
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # Phân trang: 4 đơn hàng mỗi trang
        paginator = Paginator(orders, 4)
        page = request.GET.get('page', 1)
        try:
            orders_page = paginator.page(page)
        except PageNotAnInteger:
            orders_page = paginator.page(1)
        except EmptyPage:
            orders_page = paginator.page(paginator.num_pages)
        
        # Chỉ đếm đơn đã giao thành công (không tính hủy, chờ xử lý, đang giao)
        total_orders = orders.filter(status='delivered').count()
        total_spent_raw = orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Đơn đã hoàn tiền (refund history)
        refunded_orders = orders.filter(status='cancelled', refund_status='completed')
        
        # Format total_spent for display
        total_spent = '{:,.0f}'.format(total_spent_raw).replace(',', '.')
        
        # Password change history
        password_history = PasswordHistory.objects.filter(user=request.user)
        
        # Address book
        addresses = Address.objects.filter(user=request.user)
        
        # Handle change password
        if request.method == 'POST' and request.POST.get('action') == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Mật khẩu hiện tại không đúng!')
            elif new_password != confirm_password:
                messages.error(request, 'Mật khẩu mới không khớp!')
            elif len(new_password) < 6:
                messages.error(request, 'Mật khẩu mới phải có ít nhất 6 ký tự!')
            else:
                request.user.set_password(new_password)
                request.user.save()
                # Save password change history
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                if ip and ',' in ip:
                    ip = ip.split(',')[0].strip()
                PasswordHistory.objects.create(
                    user=request.user,
                    ip_address=ip or None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Đổi mật khẩu thành công!')
                return redirect('store:profile')
        
        # Voucher khả dụng cho user
        from store.models import Coupon
        all_coupons = Coupon.objects.filter(is_active=True)
        available_coupons = []
        for cp in all_coupons:
            if cp.is_expired():
                continue
            if cp.usage_limit > 0 and cp.used_count >= cp.usage_limit:
                continue
            if cp.target_type == 'single' and cp.target_email.lower() != request.user.email.lower():
                continue
            available_coupons.append(cp)
        
        # Tìm voucher giảm 50% từ xác thực Student/Teacher
        edu_voucher = None
        is_edu_verified = request.user.is_student_verified or request.user.is_teacher_verified
        edu_voucher_status = 'none'  # none, available, used, expired
        user_email = request.user.email.lower()
        verified_email = getattr(request.user, 'verified_student_email', '') or getattr(request.user, 'verified_teacher_email', '')
        if verified_email:
            edu_voucher = Coupon.objects.filter(
                name__icontains='Student/Teacher',
                target_email__iexact=verified_email,
                is_active=True
            ).first()
            # Nếu chưa có voucher nhưng user đã xác thực, tự động tạo voucher
            if not edu_voucher and (request.user.is_student_verified or request.user.is_teacher_verified):
                import random
                import string
                voucher_code = 'EDU50' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                edu_voucher = Coupon.objects.create(
                    name=f'Ưu đãi Student/Teacher - {verified_email}',
                    code=voucher_code,
                    discount_type='percentage',
                    discount_value=50,
                    target_type='single',
                    target_email=verified_email,
                    max_products=0,
                    min_order_amount=0,
                    usage_limit=1,
                    expire_days=30,
                    is_active=True
                )
        
        # Kiểm tra trạng thái voucher
        if edu_voucher:
            if edu_voucher.used_count >= edu_voucher.usage_limit:
                edu_voucher_status = 'used'
            elif edu_voucher.is_expired():
                edu_voucher_status = 'expired'
            else:
                edu_voucher_status = 'available'
            # Nếu đã dùng hoặc hết hạn, vẫn hiển thị trong context
        elif is_edu_verified:
            edu_voucher_status = 'used'
        
        context.update({
            'is_edu_verified': is_edu_verified,
            'edu_voucher_status': edu_voucher_status,
            'orders': orders_page,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'total_spent_raw': total_spent_raw,
            'password_history': password_history,
            'addresses': addresses,
            'refunded_orders': refunded_orders,
            'available_coupons': available_coupons,
            'edu_voucher': edu_voucher,
        })
    
    return render(request, 'store/profile.html', context)


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
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)
    
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
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)
    
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
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)
    
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


def register_view(request):
    """
    Đăng ký tài khoản mới với OTP verification
    """
    # Nếu đã đăng nhập thì chuyển về trang chủ
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        otp_input = request.POST.get('otp')
        
        # Kiểm tra các trường không rỗng
        if not fullname or not email or not phone or not password or not confirm_password or not otp_input:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin!')
            return render(request, 'store/register.html')
        
        # Kiểm tra mật khẩu khớp
        if password != confirm_password:
            messages.error(request, 'Mật khẩu không khớp!')
            return render(request, 'store/register.html')
        
        # Kiểm tra OTP
        session_otp = request.session.get('otp')
        session_email = request.session.get('otp_email')
        session_created_at = request.session.get('otp_created_at', 0)
        session_expire = request.session.get('otp_expire', 300)
        
        # Kiểm tra OTP hết hạn
        if not session_otp or session_email != email or session_otp != otp_input or int(time.time()) > (session_created_at + session_expire):
            messages.error(request, 'OTP không hợp lệ hoặc đã hết hạn!')
            return render(request, 'store/register.html')
        
        # Kiểm tra email đã tồn tại chưa
        from store.models import CustomUser
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email đã được sử dụng!')
            return render(request, 'store/register.html')
        
        # Tạo user mới với email và phone
        user = CustomUser.objects.create_user(
            password=password,
            email=email,
            last_name=fullname.upper(),  # Lưu họ tên vào last_name (viết hoa)
            phone=phone
        )
        # Đảm bảo user thường không có OAuth flag
        user.is_oauth_user = False
        user.save()
        
        # Xóa OTP khỏi session
        request.session.pop('otp', None)
        request.session.pop('otp_email', None)
        request.session.pop('otp_expire', None)
        
        messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
        return redirect('store:login')
    
    return render(request, 'store/register.html')


def forgot_password_view(request):
    """
    Trang quên mật khẩu
    """
    # Nếu đã đăng nhập thì chuyển về trang chủ
    if request.user.is_authenticated:
        return redirect('store:home')
    
    return render(request, 'store/forgot_password.html')


def send_otp_forgot_password_view(request):
    """
    Gửi OTP cho quên mật khẩu (AJAX)
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email missing'})
        
        # Kiểm tra email có tồn tại trong hệ thống không
        from store.models import CustomUser
        if not CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Email không tồn tại trong hệ thống!'})
        
        # Tạo OTP 5 chữ số
        otp = str(random.randint(10000, 99999))
        
        # Lưu vào session với prefix để tránh xung đột với OTP đăng ký
        request.session['fp_otp'] = otp
        request.session['fp_otp_email'] = email
        request.session['fp_otp_created_at'] = int(time.time())
        request.session['fp_otp_expire'] = 300  # 5 phút
        
        # Gửi email qua SendGrid
        api_key = os.getenv('SENDGRID_API_KEY', '')
        from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com')
        
        data = {
            "personalizations": [{
                "to": [{"email": email}],
                "subject": "OTP Quên Mật Khẩu - QHUN22"
            }],
            "from": {"email": from_email},
            "content": [{
                "type": "text/html",
                "value": f"<h1>Mã OTP quên mật khẩu của bạn: {otp}</h1><p>Mã có hiệu lực trong 5 phút.</p><p>Nếu bạn không yêu cầu mã này, vui lòng bỏ qua.</p>"
            }]
        }
        
        try:
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                return JsonResponse({'status': 'success', 'message': 'OTP_SENT'})
            else:
                return JsonResponse({'status': 'error', 'message': f'Failed to send email: {response.status_code}'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def verify_otp_forgot_password_view(request):
    """
    Xác minh OTP cho quên mật khẩu (AJAX)
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        otp_input = request.POST.get('otp')
        
        if not email or not otp_input:
            return JsonResponse({'status': 'error', 'message': 'Missing parameters'})
        
        # Kiểm tra OTP
        session_otp = request.session.get('fp_otp')
        session_email = request.session.get('fp_otp_email')
        session_created_at = request.session.get('fp_otp_created_at', 0)
        session_expire = request.session.get('fp_otp_expire', 300)
        
        # Kiểm tra OTP hết hạn
        if not session_otp or session_email != email or session_otp != otp_input or int(time.time()) > (session_created_at + session_expire):
            return JsonResponse({'status': 'error', 'message': 'OTP không hợp lệ hoặc đã hết hạn!'})
        
        # OTP đúng, lưu trạng thái xác minh
        request.session['fp_verified'] = True
        
        return JsonResponse({'status': 'success', 'message': 'OTP verified'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def reset_password_view(request):
    """
    Đặt lại mật khẩu (AJAX)
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        
        if not email or not new_password:
            return JsonResponse({'status': 'error', 'message': 'Missing parameters'})
        
        # Kiểm tra đã xác minh OTP chưa
        if not request.session.get('fp_verified') or request.session.get('fp_otp_email') != email:
            return JsonResponse({'status': 'error', 'message': 'Vui lòng xác minh OTP trước!'})
        
        # Cập nhật mật khẩu
        from store.models import CustomUser
        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Xóa session
            request.session.pop('fp_otp', None)
            request.session.pop('fp_otp_email', None)
            request.session.pop('fp_otp_created_at', None)
            request.session.pop('fp_otp_expire', None)
            request.session.pop('fp_verified', None)
            
            return JsonResponse({'status': 'success', 'message': 'Password reset successful'})
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def dashboard_view(request):
    """
    Trang dashboard quản trị - hiển thị danh sách người dùng
    Chỉ admin (superuser) mới có thể truy cập
    """
    # Kiểm tra quyền admin
    if not request.user.is_superuser:
        messages.error(request, 'Bạn không có quyền truy cập trang này!')
        return redirect('store:profile')
    
    # Lấy danh sách tất cả người dùng
    from store.models import CustomUser, SiteVisit
    users = CustomUser.objects.all().order_by('-date_joined')
    
    # Search users
    user_search = request.GET.get('user_search', '')
    if user_search:
        users = users.filter(
            models.Q(email__icontains=user_search) | 
            models.Q(last_name__icontains=user_search) |
            models.Q(first_name__icontains=user_search)
        )
    
    # Phân trang người dùng (8 người dùng/trang)
    user_page = request.GET.get('user_page', 1)
    user_paginator = Paginator(users, 8)
    try:
        users_paginated = user_paginator.page(user_page)
    except PageNotAnInteger:
        users_paginated = user_paginator.page(1)
    except EmptyPage:
        users_paginated = user_paginator.page(user_paginator.num_pages)
    
    # Thống kê
    regular_users = users.filter(is_oauth_user=False, is_superuser=False).count()
    oauth_users = users.filter(is_oauth_user=True).count()
    
    # Tổng lượt truy cập trang chủ
    total_visits = SiteVisit.objects.count()
    
    # Sản phẩm sắp hết hàng (dưới 5 sản phẩm)
    from store.models import Product, Order, Brand
    low_stock_products_count = Product.objects.filter(stock__gt=0, stock__lt=5).count()
    
    # Danh sách hãng với số sản phẩm (cho stats)
    brands_for_stats = Brand.objects.filter(is_active=True).annotate(product_count=Count('products')).order_by('name')[:8]
    
    # Danh sách hãng cho bảng (có phân trang)
    all_brands = Brand.objects.filter(is_active=True).annotate(product_count=Count('products')).order_by('name')
    brand_search = request.GET.get('brand_search', '')
    if brand_search:
        all_brands = all_brands.filter(name__icontains=brand_search)
    
    brand_page = request.GET.get('brand_page', 1)
    brand_paginator = Paginator(all_brands, 8)
    try:
        brands_paginated = brand_paginator.page(brand_page)
    except PageNotAnInteger:
        brands_paginated = brand_paginator.page(1)
    except EmptyPage:
        brands_paginated = brand_paginator.page(brand_paginator.num_pages)
    
    # Danh sách sản phẩm (Product)
    from store.models import Product
    all_products = Product.objects.select_related('brand', 'detail').all().order_by('-created_at')
    product_search = request.GET.get('product_search', '')
    if product_search:
        all_products = all_products.filter(name__icontains=product_search)
    
    product_page = request.GET.get('product_page', 1)
    product_paginator = Paginator(all_products, 8)
    try:
        products_paginated = product_paginator.page(product_page)
    except PageNotAnInteger:
        products_paginated = product_paginator.page(1)
    except EmptyPage:
        products_paginated = product_paginator.page(product_paginator.num_pages)
    
    # Doanh thu hôm nay - tính theo giờ địa phương
    # Doanh thu tháng này
    from datetime import datetime, timedelta
    from django.db.models.functions import ExtractMonth
    from django.utils import timezone as django_timezone
    
    now = django_timezone.now()
    # Chuyển sang giờ Việt Nam trước khi lấy ngày/tháng/năm
    now_local = django_timezone.localtime(now)
    today_local = now_local.date()
    current_year = now_local.year
    current_month = now_local.month
    
    # DEBUG: In rõ ràng tháng/năm hiện tại
    print(f"=== DEBUG: Today (local): {today_local}, Year: {current_year}, Month: {current_month} ===")
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] now={now}, today_local={today_local}, current_year={current_year}, current_month={current_month}")
    
    # Lấy tất cả đơn hàng hôm nay theo giờ VN
    orders_today = Order.objects.filter(
        created_at__year=current_year,
        status__in=['processing', 'shipped', 'delivered']
    )
    
    revenue_today = 0
    for order in orders_today:
        local_created_at = django_timezone.localtime(order.created_at)
        logger.info(f"[DEBUG] order {order.id}: created_at={order.created_at}, local={local_created_at}, local.date={local_created_at.date()}")
        if local_created_at.date() == today_local:
            revenue_today += float(order.total_amount)
    
    # Lấy tất cả đơn hàng trong tháng này theo giờ địa phương
    # Chuyển đổi từng đơn hàng sang giờ VN để kiểm tra tháng
    # Lấy tất cả đơn hàng gần đây (5 năm gần nhất) để đảm bảo không bỏ sót
    orders_this_month = Order.objects.filter(
        created_at__year__gte=current_year - 1,
        status__in=['processing', 'shipped', 'delivered']
    ).order_by('-created_at')
    
    revenue_this_month = 0
    march_revenue = 0
    feb_revenue = 0
    for order in orders_this_month:
        local_created_at = django_timezone.localtime(order.created_at)
        order_month = local_created_at.month
        order_year = local_created_at.year
        
        # Debug mỗi đơn hàng
        if order_month == 3:
            march_revenue += float(order.total_amount)
            print(f"  March order: {order.id}, amount={order.total_amount}, created={local_created_at}")
        elif order_month == 2:
            feb_revenue += float(order.total_amount)
        
        if order_month == current_month and order_year == current_year:
            revenue_this_month += float(order.total_amount)
    
    print(f"=== DEBUG RESULT: revenue_this_month={revenue_this_month}, march={march_revenue}, feb={feb_revenue} ===")
    
    # TEST: Nếu tháng 3 mà không có đơn nào thì hiển thị giá trị test
    if march_revenue == 0 and feb_revenue > 0:
        print("=== WARNING: No March orders found but Feb orders exist ===")
    
    # Dữ liệu biểu đồ doanh thu năm nay
    # Lấy doanh thu từng tháng trong năm nay
    monthly_revenue = {}
    for month in range(1, 13):
        monthly_revenue[month] = 0
    
    # Query orders in current year with delivered status
    orders_current_year = Order.objects.filter(
        created_at__year=current_year,
        status__in=['processing', 'shipped', 'delivered']
    )
    
    # Lưu ý: cần chuyển về giờ địa phương trước khi lấy tháng để tránh lỗi múi giờ
    # Ví dụ: 00:30 ngày 01/03 ở VN = 17:30 ngày 28/02 UTC
    for order in orders_current_year:
        # Chuyển đổi từ UTC sang múi giờ địa phương trước khi lấy tháng
        local_created_at = django_timezone.localtime(order.created_at)
        month = local_created_at.month
        monthly_revenue[month] += float(order.total_amount)
    
    # Tính toán chiều cao biểu đồ
    max_revenue = max(monthly_revenue.values()) if max(monthly_revenue.values()) > 0 else 1
    
    month_data = []
    month_names = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
    for month in range(1, 13):
        value = monthly_revenue[month]
        # Chiều cao tối đa 280px, tối thiểu 8px
        height = int((value / max_revenue) * 280) if value > 0 else 8
        month_data.append({
            'name': month_names[month - 1],
            'value': int(value),
            'height': height,
        })
    
    context = {
        'users_paginated': users_paginated,
        'total_users': users.count(),
        'regular_users': regular_users,
        'oauth_users': oauth_users,
        'total_visits': total_visits,
        'low_stock_products_count': low_stock_products_count,
        'revenue_today': revenue_today,
        'revenue_this_month': revenue_this_month,
        'months': month_data,
        'chart_year': current_year,
        'brands': brands_for_stats,
        'brands_paginated': brands_paginated,
        'products_paginated': products_paginated,
        'products': all_products[:50],  # For SKU dropdown
    }
    return render(request, 'store/dashboard.html', context)


import re

def generate_slug(text):
    """Tạo slug từ text tiếng Việt"""
    # Remove accents
    import unicodedata
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Convert to lowercase and replace spaces with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.lower().strip('-')


@login_required
def brand_list(request):
    """Danh sách hãng sản phẩm"""
    if not request.user.is_superuser:
        messages.error(request, 'Bạn không có quyền truy cập!')
        return redirect('store:profile')
    
    from store.models import Brand
    brands = Brand.objects.all().order_by('name')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        brands = brands.filter(name__icontains=search)
    
    # Pagination (8 hãng / trang)
    brand_page = request.GET.get('brand_page', 1)
    brand_paginator = Paginator(brands, 8)
    try:
        brands_paginated = brand_paginator.page(brand_page)
    except PageNotAnInteger:
        brands_paginated = brand_paginator.page(1)
    except EmptyPage:
        brands_paginated = brand_paginator.page(brand_paginator.num_pages)
    
    context = {
        'brands_paginated': brands_paginated,
        'search': search,
    }
    return render(request, 'store/brand_list.html', context)


@login_required
@require_http_methods(["POST"])
def brand_add(request):
    """Thêm hãng mới"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Brand
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': 'Tên hãng không được để trống!'}, status=400)
    
    # Check exists
    if Brand.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Hãng đã tồn tại!'}, status=400)
    
    slug = generate_slug(name)
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Brand.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    brand = Brand.objects.create(
        name=name,
        slug=slug,
        description=description,
        is_active=True
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'Đã thêm hãng "{name}"!',
        'brand': {'id': brand.id, 'name': brand.name, 'slug': brand.slug}
    })


@login_required
@require_http_methods(["POST"])
def brand_edit(request):
    """Sửa hãng"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Brand
    brand_id = request.POST.get('brand_id')
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    
    if not name or not brand_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    # Check duplicate name (excluding current brand)
    if Brand.objects.filter(name__iexact=name).exclude(id=brand_id).exists():
        return JsonResponse({'success': False, 'message': 'Tên hãng đã tồn tại!'}, status=400)
    
    brand.name = name
    brand.description = description
    brand.slug = generate_slug(name)
    brand.save()
    
    return JsonResponse({'success': True, 'message': f'Đã cập nhật hãng "{name}"!'})


@login_required
@require_http_methods(["POST"])
def brand_delete(request):
    """Xóa hãng"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Brand
    brand_id = request.POST.get('brand_id')
    
    if not brand_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    # Check if brand has products
    if brand.products.exists():
        return JsonResponse({'success': False, 'message': 'Không thể xóa! Hãng đang có sản phẩm.'}, status=400)
    
    brand_name = brand.name
    brand.delete()
    
    return JsonResponse({'success': True, 'message': f'Đã xóa hãng "{brand_name}"!'})

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def user_edit(request):
    """Sửa thông tin người dùng"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import CustomUser
    user_id = request.POST.get('user_id')
    last_name = request.POST.get('last_name', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Người dùng không tồn tại!'}, status=404)
    
    user.last_name = last_name
    user.first_name = first_name
    user.phone = phone if phone else None
    user.save()
    
    return JsonResponse({'success': True, 'message': 'Cập nhật thông tin thành công!'})

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def user_delete(request):
    """Xóa người dùng"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import CustomUser
    user_id = request.POST.get('user_id')
    
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Người dùng không tồn tại!'}, status=404)
    
    # Không cho xóa admin
    if user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không thể xóa tài khoản admin!'}, status=400)
    
    user_email = user.email
    user.delete()
    
    return JsonResponse({'success': True, 'message': f'Đã xóa người dùng "{user_email}"!'})

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_edit(request):
    """Sửa sản phẩm (Product)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, Brand
    
    product_id = request.POST.get('product_id')
    brand_id = request.POST.get('brand')
    name = request.POST.get('name', '').strip()
    
    if not product_id or not name:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin cần thiết!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    try:
        brand = Brand.objects.get(id=brand_id) if brand_id else None
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    # Handle image upload - if new image uploaded, delete old and save new
    new_image = product.image
    new_image_file = request.FILES.get('image')
    
    if new_image_file:
        # Delete old local image
        if product.image:
            try:
                import os
                if os.path.isfile(product.image.path):
                    os.remove(product.image.path)
                product.image.delete(save=False)
            except Exception as e:
                print(f"Error deleting old image: {e}")
        new_image = new_image_file
    
    product.brand = brand
    product.name = name
    product.image = new_image
    product.save()
    
    return JsonResponse({'success': True, 'message': f'Đã cập nhật sản phẩm "{name}"!'})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_delete(request):
    """Xóa sản phẩm (Product)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product
    
    product_id = request.POST.get('product_id')
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    product_name = product.name
    product.delete()
    
    return JsonResponse({'success': True, 'message': f'Đã xóa sản phẩm "{product_name}"!'})


# ==================== Product CRUD ====================
@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_add(request):
    """Thêm sản phẩm mới"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, Brand
    import os
    
    brand_id = request.POST.get('brand')
    name = request.POST.get('name', '').strip()
    
    # Validation
    if not brand_id or not name:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin cần thiết!'}, status=400)
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    # Handle image upload
    image = request.FILES.get('image')
    
    # Generate slug from name
    from django.utils.text import slugify
    slug = slugify(name)
    
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    product = Product.objects.create(
        brand=brand,
        name=name,
        slug=slug,
        description='',
        image=image,
        is_active=True
    )
    
    return JsonResponse({'success': True, 'message': f'Đã thêm sản phẩm "{name}"!'})


# ==================== Product Detail Management ====================
@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_detail_save(request):
    """Lưu chi tiết sản phẩm (tạo/cập nhật Product và ProductDetail)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, ProductDetail, ProductVariant, FolderColorImage
    
    product_id = request.POST.get('product_id')
    original_price = request.POST.get('original_price', '0').strip()
    discount_percent = request.POST.get('discount_percent', '0').strip()
    stock = request.POST.get('stock', '0').strip()
    sku = request.POST.get('sku', '').strip()
    save_sku_only = request.POST.get('save_sku_only', 'false').strip().lower() == 'true'
    delete_sku = request.POST.get('delete_sku', 'false').strip().lower() == 'true'
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin sản phẩm!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    # Get or create ProductDetail
    detail = ProductDetail.objects.filter(product=product).first()
    
    # Handle delete SKU
    if delete_sku:
        sku_to_delete = request.POST.get('sku', '').strip()
        if not detail or not detail.sku:
            return JsonResponse({'success': False, 'message': 'Không có SKU để xóa!'}, status=400)
        
        existing_skus = detail.sku.split(',') if detail.sku else []
        if sku_to_delete in existing_skus:
            existing_skus.remove(sku_to_delete)
            detail.sku = ','.join(existing_skus)
            detail.save(update_fields=['sku'])
        
        return JsonResponse({
            'success': True, 
            'message': f'Đã xóa SKU: {sku_to_delete}!',
            'sku': detail.sku
        })
    
    # If save_sku_only, only save SKU
    if save_sku_only:
        if not sku:
            return JsonResponse({'success': False, 'message': 'Vui lòng nhập SKU!'}, status=400)
        
        if not detail:
            # Check for duplicate in case detail was just created but we have a new request
            # Create new ProductDetail
            detail = ProductDetail.objects.create(product=product, sku=sku)
        else:
            # Append SKU if not already in list (comma separated)
            existing_skus = detail.sku.split(',') if detail.sku else []
            if sku in existing_skus:
                return JsonResponse({
                    'success': False, 
                    'message': f'SKU "{sku}" đã tồn tại!',
                }, status=400)
            existing_skus.append(sku)
            detail.sku = ','.join(existing_skus)
            detail.save(update_fields=['sku'])
        
        return JsonResponse({
            'success': True, 
            'message': f'Đã lưu SKU: {sku}!',
            'sku': detail.sku
        })
    
    # Save all fields
    try:
        original_price = int(original_price) if original_price else 0
        discount_percent = int(discount_percent) if discount_percent else 0
        stock = int(stock) if stock else 0
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Giá phải là số!'}, status=400)
    
    # Calculate discounted price
    discounted_price = original_price - (original_price * discount_percent / 100)
    if discounted_price >= 5000:
        discounted_price = round(discounted_price / 5000) * 5000
    
    # Save to Product model
    product.original_price = original_price
    product.discount_percent = discount_percent
    product.price = discounted_price
    product.stock = stock
    product.save(update_fields=['original_price', 'discount_percent', 'price', 'stock'])
    
    # Save to ProductDetail model (for template display)
    if not detail:
        detail = ProductDetail.objects.create(
            product=product,
            original_price=original_price,
            discount_percent=discount_percent,
            sku=sku
        )
    else:
        detail.original_price = original_price
        detail.discount_percent = discount_percent
        if sku:
            # Append SKU if not already in list
            existing_skus = detail.sku.split(',') if detail.sku else []
            if sku not in existing_skus:
                existing_skus.append(sku)
                detail.sku = ','.join(existing_skus)
        detail.save(update_fields=['original_price', 'discount_percent', 'sku'])
    
    return JsonResponse({'success': True, 'message': f'Đã lưu thông tin sản phẩm!', 'detail_id': detail.id})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_variant_save(request):
    """Lưu biến thể sản phẩm (màu + dung lượng)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, ProductDetail, ProductVariant, FolderColorImage
    
    variant_id = request.POST.get('variant_id')
    detail_id = request.POST.get('detail_id')
    product_id = request.POST.get('product_id')
    color_name = request.POST.get('color_name', '').strip()
    color_hex = request.POST.get('color_hex', '').strip()
    storage = request.POST.get('storage', '').strip()
    original_price = request.POST.get('original_price', request.POST.get('base_price', '0')).strip()
    discount_percent = request.POST.get('discount_percent', '0').strip()
    price = request.POST.get('price', '0').strip()
    variant_sku = request.POST.get('sku', '').strip()
    stock_quantity = request.POST.get('stock_quantity', '0').strip()
    
    if not color_name or not storage:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin biến thể!'}, status=400)
    
    # Xác định ProductDetail (detail) từ detail_id hoặc product_id
    detail = None
    if detail_id:
        try:
            detail = ProductDetail.objects.get(id=detail_id)
        except ProductDetail.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chi tiết sản phẩm không tồn tại!'}, status=404)
    else:
        if not product_id:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin sản phẩm!'}, status=400)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
        detail, _ = ProductDetail.objects.get_or_create(product=product)
    
    try:
        price = int(price) if price else 0
        stock_quantity = int(stock_quantity) if stock_quantity else 0
        original_price = int(original_price) if original_price else 0
        discount_percent = min(100, max(0, int(discount_percent) if discount_percent else 0))
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Giá và số lượng phải là số!'}, status=400)
    
    if variant_id:
        # Update existing variant
        try:
            variant = ProductVariant.objects.get(id=variant_id, detail=detail)
            variant.color_name = color_name
            variant.color_hex = color_hex
            variant.storage = storage
            variant.original_price = original_price
            variant.discount_percent = discount_percent
            variant.price = price
            variant.sku = variant_sku
            variant.stock_quantity = stock_quantity
            variant.save()
            return JsonResponse({'success': True, 'message': f'Đã cập nhật biến thể "{color_name} - {storage}"!', 'variant_id': variant.id})
        except ProductVariant.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Biến thể không tồn tại!'}, status=404)
    else:
        # Create new variant
        variant, created = ProductVariant.objects.get_or_create(
            detail=detail,
            color_name=color_name,
            storage=storage,
            defaults={
                'color_hex': color_hex,
                'original_price': original_price,
                'discount_percent': discount_percent,
                'price': price,
                'sku': variant_sku,
                'stock_quantity': stock_quantity
            }
        )
        if not created:
            return JsonResponse({'success': False, 'message': 'Biến thể đã tồn tại!'}, status=400)
        return JsonResponse({'success': True, 'message': f'Đã thêm biến thể "{color_name} - {storage}"!', 'variant_id': variant.id})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_variant_delete(request):
    """Xóa biến thể sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import ProductVariant
    
    variant_id = request.POST.get('variant_id')
    
    if not variant_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        variant_name = f"{variant.color_name} - {variant.storage}"
        variant.delete()
        return JsonResponse({'success': True, 'message': f'Đã xóa biến thể "{variant_name}"!'})
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Biến thể không tồn tại!'}, status=404)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_image_upload(request):
    """Upload ảnh sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import ProductDetail, ProductVariant, ProductImage
    import os
    from django.utils.text import slugify
    from datetime import datetime
    
    detail_id = request.POST.get('detail_id')
    variant_id = request.POST.get('variant_id')
    image_type = request.POST.get('image_type', 'cover')
    
    images = request.FILES.getlist('images')
    
    if not images:
        return JsonResponse({'success': False, 'message': 'Chưa chọn ảnh!'}, status=400)
    
    # Get product detail
    detail = None
    if detail_id:
        try:
            detail = ProductDetail.objects.get(id=detail_id)
        except ProductDetail.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chi tiết sản phẩm không tồn tại!'}, status=404)
    
    # Get variant if provided
    variant = None
    if variant_id:
        try:
            variant = ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Biến thể không tồn tại!'}, status=404)
    
    # Create upload path
    product_slug = slugify(detail.product.name) if detail else slugify(variant.detail.product.name)
    year = datetime.now().year
    month = datetime.now().strftime('%m')
    
    uploaded_count = 0
    for img in images:
        # Get next order number
        max_order = ProductImage.objects.filter(detail=detail, variant=variant, image_type=image_type).aggregate(Max('order'))['order__max'] or 0
        
        # Create image record
        image = ProductImage.objects.create(
            detail=detail,
            variant=variant,
            image_type=image_type,
            image=img,
            order=max_order + 1
        )
        uploaded_count += 1
    
    return JsonResponse({'success': True, 'message': f'Đã upload {uploaded_count} ảnh!'})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_image_delete(request):
    """Xóa ảnh sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import ProductImage
    import os
    
    image_id = request.POST.get('image_id')
    
    if not image_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        img = ProductImage.objects.get(id=image_id)
        # Delete file
        if img.image:
            try:
                if os.path.isfile(img.image.path):
                    os.remove(img.image.path)
                img.image.delete(save=True)
            except Exception as e:
                print(f"Error deleting image file: {e}")
        img.delete()
        return JsonResponse({'success': True, 'message': 'Đã xóa ảnh!'})
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Ảnh không tồn tại!'}, status=404)


@login_required
@require_http_methods(["GET"])
def image_folder_list(request):
    """Danh sách màu ảnh theo thư mục (group theo thư mục + màu + SKU)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import ImageFolder, FolderColorImage

    search = request.GET.get('search', '').strip()
    brand_id = request.GET.get('brand_id', '').strip()

    try:
        images_qs = FolderColorImage.objects.select_related('folder', 'folder__brand', 'folder__product', 'brand')
        if search:
            images_qs = images_qs.filter(folder__name__icontains=search)

        # Group theo (folder, color_name, sku)
        rows_map = {}
        for img in images_qs.order_by('folder__name', 'color_name', 'sku', 'order'):
            key = (img.folder_id, img.color_name, img.sku)
            if key not in rows_map:
                rows_map[key] = {
                    'id': img.id,
                    'folder_id': img.folder_id,
                    'folder_name': img.folder.name,
                    'color_name': img.color_name,
                    'sku': img.sku,
                    'brand_id': img.brand.id if img.brand else None,
                    'brand_name': img.brand.name if img.brand else None,
                    'folder_brand_id': img.folder.brand.id if img.folder.brand else None,
                    'folder_product_id': img.folder.product.id if img.folder.product else None,
                }

        rows = list(rows_map.values())

        # Danh sách tất cả thư mục (cho dropdown)
        folders_qs = ImageFolder.objects.select_related('brand', 'product').all().order_by('-created_at')
        
        # Lọc theo brand_id nếu có
        if brand_id:
            folders_qs = folders_qs.filter(brand_id=brand_id)
        
        folders = [{
            'id': f.id, 
            'name': f.name,
            'brand_id': f.brand.id if f.brand else None,
            'brand_name': f.brand.name if f.brand else None,
            'product_id': f.product.id if f.product else None,
            'product_name': f.product.name if f.product else None
        } for f in folders_qs]

        return JsonResponse({'success': True, 'rows': rows, 'folders': folders})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def image_folder_create(request):
    """Tạo thư mục ảnh mới"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import ImageFolder, Brand, Product

    name = request.POST.get('name', '').strip()
    brand_id = request.POST.get('brand_id', '').strip()
    product_id = request.POST.get('product_id', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập tên thư mục!'}, status=400)
    
    if not brand_id:
        return JsonResponse({'success': False, 'message': 'Vui lòng chọn hãng!'}, status=400)
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Vui lòng chọn sản phẩm!'}, status=400)

    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)

    try:
        folder, created = ImageFolder.objects.get_or_create(
            name=name,
            brand=brand,
            product=product
        )
        now = timezone.now()
        year = now.year
        month = now.strftime('%m')
        dir_path = os.path.join(settings.MEDIA_ROOT, 'products', str(year), month, folder.slug)
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            return JsonResponse({'success': False, 'message': f'Không tạo được thư mục trên đĩa: {e}'}, status=500)
        if created:
            message = f'Đã tạo thư mục \"{folder.name}\" (đường dẫn: media/products/{year}/{month}/{folder.slug}/).'
        else:
            message = f'Thư mục \"{folder.name}\" đã tồn tại.'
        return JsonResponse({
            'success': True,
            'message': message,
            'folder': {
                'id': folder.id, 
                'name': folder.name, 
                'slug': folder.slug,
                'brand_id': folder.brand.id if folder.brand else None,
                'brand_name': folder.brand.name if folder.brand else None,
                'product_id': folder.product.id if folder.product else None,
                'product_name': folder.product.name if folder.product else None
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def folder_color_image_list(request):
    """Danh sách ảnh theo thư mục + SKU + màu (để hiển thị khi bấm Quản lý)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import FolderColorImage

    folder_id = request.GET.get('folder_id')
    sku = request.GET.get('sku', '').strip()
    color_name = request.GET.get('color_name', '').strip()

    if not folder_id or not sku or not color_name:
        return JsonResponse({'success': True, 'images': []})

    try:
        imgs = FolderColorImage.objects.filter(
            folder_id=folder_id,
            sku=sku,
            color_name=color_name
        ).order_by('order')

        images = [{'id': img.id, 'url': img.image.url, 'order': img.order} for img in imgs]
        return JsonResponse({'success': True, 'images': images})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def folder_color_image_upload(request):
    """
    Upload ảnh cho 1 màu + SKU trong thư mục:
    - folder_id
    - brand_id (optional)
    - sku
    - color_name
    - image (file)
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import ImageFolder, FolderColorImage, Brand

    folder_id = request.POST.get('folder_id')
    brand_id = request.POST.get('brand_id')
    sku = request.POST.get('sku', '').strip()
    color_name = request.POST.get('color_name', '').strip()
    image_file = request.FILES.get('image')

    if not folder_id or not sku or not color_name or not image_file:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin bắt buộc!'}, status=400)

    try:
        folder = ImageFolder.objects.get(id=folder_id)
    except ImageFolder.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Thư mục không tồn tại!'}, status=404)

    brand = None
    if brand_id:
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            brand = None

    # Lấy thứ tự tiếp theo trong nhóm này
    max_order = FolderColorImage.objects.filter(
        folder=folder,
        sku=sku,
        color_name=color_name
    ).aggregate(Max('order'))['order__max'] or 0

    img = FolderColorImage.objects.create(
        folder=folder,
        brand=brand,
        sku=sku,
        color_name=color_name,
        image=image_file,
        order=max_order + 1,
    )

    return JsonResponse({
        'success': True,
        'message': f'Đã upload ảnh màu \"{color_name}\"!',
        'image': {
            'id': img.id,
            'url': img.image.url,
            'order': img.order,
            'folder_name': folder.name,
            'color_name': img.color_name,
            'sku': img.sku,
        }
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def folder_color_image_delete(request):
    """Xóa 1 ảnh màu trong thư mục"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import FolderColorImage

    image_id = request.POST.get('image_id')
    if not image_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)

    try:
        img = FolderColorImage.objects.get(id=image_id)
    except FolderColorImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Ảnh không tồn tại!'}, status=404)

    # Xóa file vật lý
    try:
        if img.image and hasattr(img.image, 'path'):
            if os.path.isfile(img.image.path):
                os.remove(img.image.path)
            img.image.delete(save=False)
    except Exception:
        pass

    img.delete()
    return JsonResponse({'success': True, 'message': 'Đã xóa ảnh màu!'})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def folder_color_rename(request):
    """Đổi tên màu cho tất cả ảnh cùng folder + sku + color cũ."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import FolderColorImage

    folder_id = request.POST.get('folder_id')
    sku = request.POST.get('sku', '').strip()
    old_color = request.POST.get('old_color_name', '').strip()
    new_color = request.POST.get('new_color_name', '').strip()

    if not folder_id or not sku or not old_color or not new_color:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)

    if old_color == new_color:
        return JsonResponse({'success': True, 'message': 'Tên màu không thay đổi.'})

    updated = FolderColorImage.objects.filter(
        folder_id=folder_id,
        sku=sku,
        color_name=old_color
    ).update(color_name=new_color)

    if updated == 0:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy ảnh để cập nhật!'})

    return JsonResponse({
        'success': True,
        'message': f'Đã đổi tên màu "{old_color}" → "{new_color}" ({updated} ảnh).'
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def folder_color_row_delete(request):
    """Xóa tất cả ảnh màu theo folder + sku + color (xóa cả row)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import FolderColorImage

    folder_id = request.POST.get('folder_id')
    sku = request.POST.get('sku', '').strip()
    color_name = request.POST.get('color_name', '').strip()

    if not folder_id or not sku or not color_name:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)

    try:
        images = FolderColorImage.objects.filter(
            folder_id=folder_id,
            sku=sku,
            color_name=color_name
        )
        
        count = images.count()
        if count == 0:
            return JsonResponse({'success': False, 'message': 'Không tìm thấy ảnh nào!'}, status=404)
        
        for img in images:
            try:
                if img.image and hasattr(img.image, 'path'):
                    if os.path.isfile(img.image.path):
                        os.remove(img.image.path)
                    img.image.delete(save=False)
            except Exception:
                pass
            img.delete()
        
        return JsonResponse({'success': True, 'message': f'Đã xóa {count} ảnh màu!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_product_detail(request):
    """Lấy thông tin chi tiết sản phẩm (AJAX)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, ProductDetail, ProductVariant, FolderColorImage, ProductSpecification
    
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        product = Product.objects.select_related('detail').get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    # Ưu tiên lấy từ ProductDetail nếu có
    detail = getattr(product, 'detail', None)
    detail_id = detail.id if detail else None
    
    variants = []
    skus_with_color = []
    if detail:
        # Biến thể chi tiết (màu + dung lượng + giá)
        qs = ProductVariant.objects.filter(detail=detail).order_by('price')
        for v in qs:
            variants.append({
                'id': v.id,
                'color_name': v.color_name,
                'color_hex': v.color_hex,
                'storage': v.storage,
                'original_price': int(v.original_price),
                'discount_percent': int(v.discount_percent),
                'price': int(v.price),
                'sku': v.sku,
                'stock_quantity': v.stock_quantity,
            })
    
    # Dropdown "Chọn màu (SKU)": CHỈ lấy SKU của sản phẩm hiện tại từ ProductDetail.sku
    # Không lấy từ FolderColorImage của toàn brand để tránh hiển thị SKU sản phẩm khác
    skus_with_color = []
    
    # Lấy mapping SKU -> màu từ FolderColorImage (để lấy tên màu nếu có)
    sku_to_color = {}
    if product.brand_id:
        rows = FolderColorImage.objects.filter(brand_id=product.brand_id).order_by('sku', 'created_at')
        for row in rows:
            if row.sku and row.sku not in sku_to_color:
                sku_to_color[row.sku] = (row.color_name or '').strip()
    
    # CHỈ lấy SKU đã được thêm cho sản phẩm này trong ProductDetail.sku
    if detail and (detail.sku or '').strip():
        sku_list_raw = [x.strip() for x in (detail.sku or '').split(',') if x.strip()]
        for sku in sku_list_raw:
            color_name = sku_to_color.get(sku, '')
            skus_with_color.append({'sku': sku, 'color_name': color_name})
    
    # Lấy thông số kỹ thuật nếu có
    spec_data = None
    if detail:
        try:
            spec = ProductSpecification.objects.get(detail=detail)
            spec_data = spec.spec_json
        except ProductSpecification.DoesNotExist:
            pass
    
    # Lấy YouTube ID nếu có
    youtube_id = ''
    if detail and detail.youtube_id:
        youtube_id = detail.youtube_id
    
    return JsonResponse({
        'success': True,
        'product_name': product.name,
        'product_image': product.image.url if product.image else None,
        'product_stock': product.stock,
        'detail_id': detail_id,
        'variants': variants,
        'skus_with_color': skus_with_color,
        'spec_data': spec_data,
        'youtube_id': youtube_id,
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def save_youtube_id(request):
    """Lưu YouTube Video ID cho sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, ProductDetail
    
    product_id = request.POST.get('product_id')
    youtube_id = request.POST.get('youtube_id', '').strip()
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin sản phẩm!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    detail, created = ProductDetail.objects.get_or_create(product=product)
    detail.youtube_id = youtube_id
    detail.save(update_fields=['youtube_id'])
    
    if youtube_id:
        return JsonResponse({'success': True, 'message': f'Đã lưu YouTube ID: {youtube_id}', 'youtube_id': youtube_id})
    else:
        return JsonResponse({'success': True, 'message': 'Đã xóa YouTube ID!', 'youtube_id': ''})


# ==================== SKU Management ==
@login_required
@require_http_methods(["GET"])
def sku_list(request):
    """Lấy danh sách tất cả SKU"""
    from store.models import ProductDetail
    try:
        # Get all ProductDetails with SKU
        details = ProductDetail.objects.filter(
            sku__isnull=False, 
            sku__gt=''
        ).select_related('product__brand').order_by('-created_at')
        
        skus = []
        for detail in details:
            sku_list = detail.sku.split(',')
            for sku_item in sku_list:
                sku_item = sku_item.strip()
                if sku_item:
                    skus.append({
                        'id': f'{detail.id}_{sku_item}',  # Composite ID
                        'sku': sku_item,
                        'product_id': detail.product.id,
                        'product_name': detail.product.name,
                        'brand_id': detail.product.brand.id if detail.product.brand else None,
                        'brand_name': detail.product.brand.name if detail.product.brand else None,
                        'created_at': detail.created_at.isoformat() if detail.created_at else None
                    })
        
        return JsonResponse({'success': True, 'skus': skus})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def sku_add(request):
    """Thêm SKU mới cho sản phẩm"""
    from store.models import Product, ProductDetail
    try:
        product_id = request.POST.get('product_id')
        sku = request.POST.get('sku', '').strip()
        
        if not product_id or not sku:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
        
        product = Product.objects.get(id=product_id)
        
        # Get or create ProductDetail
        detail, created = ProductDetail.objects.get_or_create(product=product)
        
        # Check for duplicate SKU
        existing_skus = detail.sku.split(',') if detail.sku else []
        if sku in existing_skus:
            return JsonResponse({'success': False, 'message': f'SKU "{sku}" đã tồn tại!'}, status=400)
        
        # Add new SKU
        if detail.sku:
            detail.sku += f',{sku}'
        else:
            detail.sku = sku
        detail.save(update_fields=['sku'])
        
        return JsonResponse({'success': True, 'message': f'Đã thêm SKU: {sku}'})
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def sku_edit(request):
    """Sửa SKU"""
    from store.models import ProductDetail
    try:
        sku_id = request.POST.get('sku_id')
        new_sku = request.POST.get('sku', '').strip()
        
        if not sku_id or not new_sku:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
        
        # Parse composite ID - split at first underscore from right (sku might contain underscore)
        # Format: detailID_skuvalue
        last_underscore_idx = sku_id.rfind('_')
        if last_underscore_idx == -1:
            return JsonResponse({'success': False, 'message': 'ID không hợp lệ!'}, status=400)
        
        detail_id = sku_id[:last_underscore_idx]
        old_sku = sku_id[last_underscore_idx + 1:]
        
        detail = ProductDetail.objects.get(id=detail_id)
        
        # Replace SKU
        existing_skus = detail.sku.split(',') if detail.sku else []
        new_skus = []
        for s in existing_skus:
            if s.strip() == old_sku:
                new_skus.append(new_sku)
            else:
                new_skus.append(s)
        
        # Check for duplicate (exclude current one being edited)
        if new_sku in [s.strip() for s in new_skus if s.strip() != old_sku]:
            return JsonResponse({'success': False, 'message': f'SKU "{new_sku}" đã tồn tại!'}, status=400)
        
        detail.sku = ','.join(new_skus)
        detail.save(update_fields=['sku'])
        
        return JsonResponse({'success': True, 'message': f'Đã sửa SKU thành: {new_sku}'})
    except ProductDetail.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'SKU không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def sku_delete(request):
    """Xóa SKU"""
    from store.models import ProductDetail
    try:
        sku_id = request.POST.get('sku_id')
        
        if not sku_id:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
        
        # Parse composite ID - split at first underscore from right
        last_underscore_idx = sku_id.rfind('_')
        if last_underscore_idx == -1:
            return JsonResponse({'success': False, 'message': 'ID không hợp lệ!'}, status=400)
        
        detail_id = sku_id[:last_underscore_idx]
        sku_to_delete = sku_id[last_underscore_idx + 1:]
        
        detail = ProductDetail.objects.get(id=detail_id)
        
        # Remove SKU
        existing_skus = detail.sku.split(',') if detail.sku else []
        existing_skus = [s.strip() for s in existing_skus if s.strip() != sku_to_delete]
        
        detail.sku = ','.join(existing_skus)
        detail.save(update_fields=['sku'])
        
        return JsonResponse({'success': True, 'message': f'Đã xóa SKU: {sku_to_delete}'})
    except ProductDetail.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'SKU không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_specification_upload(request):
    """Upload JSON file cho Thông số kỹ thuật sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import ProductDetail, ProductSpecification
    import json
    
    try:
        detail_id = request.POST.get('detail_id')
        json_file = request.FILES.get('json_file')
        
        if not detail_id or not json_file:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin hoặc file!'}, status=400)
        
        # Validate file type
        if not json_file.name.endswith('.json'):
            return JsonResponse({'success': False, 'message': 'File phải có đuôi .json!'}, status=400)
        
        # Get ProductDetail
        detail = ProductDetail.objects.get(id=detail_id)
        
        # Read and validate JSON
        try:
            file_content = json_file.read().decode('utf-8')
            spec_data = json.loads(file_content)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'File JSON không hợp lệ!'}, status=400)
        except UnicodeDecodeError:
            return JsonResponse({'success': False, 'message': 'Mã hóa file không hợp lệ! Hãy dùng UTF-8'}, status=400)
        
        # Create or update specification
        spec, created = ProductSpecification.objects.get_or_create(detail=detail)
        spec.spec_json = spec_data
        spec.save()
        
        message = 'Tải file thông số kỹ thuật thành công!'
        return JsonResponse({
            'success': True,
            'message': message,
            'spec_id': spec.id,
            'spec_data': spec_data
        })
    
    except ProductDetail.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Chi tiết sản phẩm không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_specification_delete(request):
    """Xóa Thông số kỹ thuật sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import ProductDetail, ProductSpecification
    
    try:
        detail_id = request.POST.get('detail_id')
        if not detail_id:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
        
        detail = ProductDetail.objects.get(id=detail_id)
        
        try:
            spec = ProductSpecification.objects.get(detail=detail)
            spec.delete()
            return JsonResponse({'success': True, 'message': 'Đã xóa thông số kỹ thuật!'})
        except ProductSpecification.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Chưa có thông số kỹ thuật nào!'}, status=404)
    
    except ProductDetail.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Chi tiết sản phẩm không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


# ==================== Banner Images API ====================
def banner_list(request):
    """Lấy danh sách tất cả banner - cho phép truy cập công khai"""
    
    from store.models import Banner
    
    try:
        banners = Banner.objects.all().order_by('banner_id', '-created_at')
        banner_data = []
        for banner in banners:
            banner_data.append({
                'id': banner.id,
                'banner_id': banner.banner_id,
                'image_url': banner.image.url,
                'created_at': banner.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return JsonResponse({'success': True, 'banners': banner_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


def banner_add(request):
    """Thêm banner mới"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Banner
    
    try:
        banner_id = request.POST.get('banner_id')
        image = request.FILES.get('image')
        
        if not banner_id:
            return JsonResponse({'success': False, 'message': 'Vui lòng nhập ID!'}, status=400)
        
        if not image:
            return JsonResponse({'success': False, 'message': 'Vui lòng chọn ảnh!'}, status=400)
        
        # Tạo banner mới
        banner = Banner.objects.create(
            banner_id=banner_id,
            image=image
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Đã thêm banner ID {banner_id}!',
            'banner': {
                'id': banner.id,
                'banner_id': banner.banner_id,
                'image_url': banner.image.url
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@require_POST
def banner_replace(request):
    """Thay thế ảnh banner có cùng banner_id (đè ảnh cũ)"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Banner
    import os
    
    try:
        banner_id = request.POST.get('banner_id')
        image = request.FILES.get('image')
        
        if not banner_id:
            return JsonResponse({'success': False, 'message': 'Vui lòng nhập ID!'}, status=400)
        
        if not image:
            return JsonResponse({'success': False, 'message': 'Vui lòng chọn ảnh!'}, status=400)
        
        # Tìm banner hiện có theo banner_id
        existing = Banner.objects.filter(banner_id=banner_id).first()
        
        if existing:
            # Xóa file ảnh cũ
            if existing.image:
                old_path = existing.image.path
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            # Gán ảnh mới và lưu
            existing.image = image
            existing.save()
            banner = existing
        else:
            # Nếu chưa có thì tạo mới
            banner = Banner.objects.create(banner_id=banner_id, image=image)
        
        return JsonResponse({
            'success': True,
            'message': f'Đã thay ảnh banner ID {banner_id}!',
            'banner': {
                'id': banner.id,
                'banner_id': banner.banner_id,
                'image_url': banner.image.url
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


def banner_delete(request):
    """Xóa banner"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Banner
    import os
    
    try:
        banner_id = request.POST.get('banner_id')
        if not banner_id:
            return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
        
        # Chuyển đổi sang số nếu là số
        try:
            banner_id = int(banner_id)
            banner = Banner.objects.get(id=banner_id)
        except (ValueError, Banner.DoesNotExist):
            # Thử tìm theo banner_id string
            try:
                banner = Banner.objects.get(banner_id=str(banner_id))
            except Banner.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Banner không tồn tại!'}, status=404)
        
        banner_id_display = banner.banner_id
        
        # Xóa file ảnh khỏi server
        if banner.image:
            image_path = banner.image.path
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Lỗi khi xóa file ảnh: {e}")
        
        banner.delete()
        
        return JsonResponse({'success': True, 'message': f'Đã xóa banner ID {banner_id_display}!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


# ==================== Product Content API ====================
@csrf_exempt
@login_required
def product_content_list(request):
    """Lấy danh sách tất cả nội dung sản phẩm"""
    from store.models import ProductContent
    
    contents = ProductContent.objects.select_related('brand', 'product').all().order_by('-created_at')
    content_data = []
    for content in contents:
        content_data.append({
            'id': content.id,
            'brand_id': content.brand.id,
            'brand_name': content.brand.name,
            'product_id': content.product.id,
            'product_name': content.product.name,
            'content_text': content.content_text,
            'image_url': content.image.url if content.image else None,
            'created_at': content.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return JsonResponse({'success': True, 'contents': content_data})


@csrf_exempt
@login_required
def product_content_add(request):
    """Thêm nội dung sản phẩm mới"""
    import os
    from store.models import ProductContent, Brand, Product
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ!'}, status=400)
    
    try:
        brand_id = request.POST.get('brand_id')
        product_id = request.POST.get('product_id')
        content_text = request.POST.get('content_text', '')
        image = request.FILES.get('image')
        
        if not brand_id:
            return JsonResponse({'success': False, 'message': 'Vui lòng chọn hãng!'}, status=400)
        
        if not product_id:
            return JsonResponse({'success': False, 'message': 'Vui lòng chọn sản phẩm!'}, status=400)
        
        # Lấy brand và product
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=400)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=400)
        
        # Kiểm tra đã tồn tại chưa
        existing = ProductContent.objects.filter(brand=brand, product=product).first()
        
        if existing:
            # Cập nhật nội dung
            existing.content_text = content_text
            if image:
                # Xóa ảnh cũ nếu có
                if existing.image:
                    old_image_path = existing.image.path
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                existing.image = image
            existing.save()
            content = existing
            message = f'Đã cập nhật nội dung cho {product.name}!'
        else:
            # Tạo mới
            content = ProductContent.objects.create(
                brand=brand,
                product=product,
                content_text=content_text,
                image=image
            )
            message = f'Đã thêm nội dung cho {product.name}!'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'content': {
                'id': content.id,
                'brand_id': content.brand.id,
                'brand_name': content.brand.name,
                'product_id': content.product.id,
                'product_name': content.product.name,
                'content_text': content.content_text,
                'image_url': content.image.url if content.image else None
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'Lỗi server: {str(e)}'}, status=500)


@csrf_exempt
@login_required
def product_content_replace(request):
    """Thay thế ảnh nội dung sản phẩm"""
    import os
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ!'}, status=400)
    
    from store.models import ProductContent
    
    content_id = request.POST.get('content_id')
    image = request.FILES.get('image')
    
    if not content_id:
        return JsonResponse({'success': False, 'message': 'Vui lòng cung cấp ID!'}, status=400)
    
    if not image:
        return JsonResponse({'success': False, 'message': 'Vui lòng chọn ảnh!'}, status=400)
    
    try:
        content_id = int(content_id)
        content = ProductContent.objects.get(id=content_id)
    except (ValueError, ProductContent.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Nội dung không tồn tại!'}, status=404)
    
    # Xóa ảnh cũ nếu có
    if content.image:
        old_image_path = content.image.path
        if os.path.exists(old_image_path):
            os.remove(old_image_path)
    
    # Cập nhật ảnh mới
    content.image = image
    content.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Đã thay ảnh cho {content.product.name}!',
        'content': {
            'id': content.id,
            'content_text': content.content_text,
            'image_url': content.image.url
        }
    })


@csrf_exempt
@login_required
def product_content_delete(request):
    """Xóa nội dung sản phẩm"""
    import os
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ!'}, status=400)
    
    from store.models import ProductContent
    
    content_id = request.POST.get('content_id')
    
    if not content_id:
        return JsonResponse({'success': False, 'message': 'Vui lòng cung cấp ID!'}, status=400)
    
    try:
        content_id = int(content_id)
        content = ProductContent.objects.get(id=content_id)
    except (ValueError, ProductContent.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Nội dung không tồn tại!'}, status=404)
    
    product_name = content.product.name
    
    # Xóa ảnh nếu có
    if content.image:
        image_path = content.image.path
        if os.path.exists(image_path):
            os.remove(image_path)
    
    content.delete()
    
    return JsonResponse({'success': True, 'message': f'Đã xóa nội dung của {product_name}!'})


# ==================== Temp Image Upload ====================
@login_required
def upload_temp_image(request):
    """Upload ảnh tạm để chèn vào nội dung"""
    import os
    from django.conf import settings
    
    if request.method != 'POST':
        return JsonResponse({'error': {'message': 'Phương thức không hợp lệ!'}}, status=400)
    
    image = request.FILES.get('image') or request.FILES.get('upload')
    
    if not image:
        return JsonResponse({'error': {'message': 'Vui lòng chọn ảnh!'}}, status=400)
    
    # Validate image
    if not image.content_type.startswith('image/'):
        return JsonResponse({'error': {'message': 'File phải là ảnh!'}}, status=400)
    
    # Create temp directory if not exists
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save temp file
    from django.utils import timezone
    import uuid
    ext = os.path.splitext(image.name)[1]
    filename = f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)
    
    # Return URL 
    temp_url = f"/media/temp/{filename}"
    
    return JsonResponse({
        'url': temp_url
    })


# ==================== Pending QR Payment APIs ====================

@csrf_exempt
@login_required
@require_POST
def qr_payment_create(request):
    """
    Khách tạo QR trên checkout → lưu PendingQRPayment.
    POST: amount, transfer_code
    """
    from store.models import PendingQRPayment
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)

    amount = data.get('amount')
    transfer_code = data.get('transfer_code')

    if not amount or not transfer_code:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin'}, status=400)

    # Kiểm tra trùng mã CK
    if PendingQRPayment.objects.filter(transfer_code=transfer_code).exists():
        return JsonResponse({'success': False, 'message': 'Mã chuyển khoản đã tồn tại'}, status=400)

    qr = PendingQRPayment.objects.create(
        user=request.user,
        amount=amount,
        transfer_code=transfer_code,
    )
    return JsonResponse({'success': True, 'id': qr.id, 'message': 'Đã tạo QR thành công'})


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
    
    if payment_method not in ['cod', 'vietqr']:
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
            
            # Kiểm tra quyền sử dụng coupon (bao gồm verified student/teacher email)
            coupon_target_valid = False
            if coupon.target_type == 'all':
                coupon_target_valid = True
            else:
                user_email = request.user.email.lower()
                target_email = coupon.target_email.lower()
                verified_student = getattr(request.user, 'verified_student_email', '').lower()
                verified_teacher = getattr(request.user, 'verified_teacher_email', '').lower()
                coupon_target_valid = (user_email == target_email or 
                                      verified_student == target_email or 
                                      verified_teacher == target_email)
            
            if (coupon.is_valid()
                and total_amount >= coupon.min_order_amount
                and (coupon.max_products == 0 or item_count <= coupon.max_products)
                and coupon_target_valid):
                discount_amount = coupon.calculate_discount(total_amount)
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
    
    # Nếu VietQR, xóa pending QR
    if payment_method == 'vietqr' and transfer_code:
        PendingQRPayment.objects.filter(transfer_code=transfer_code, user=request.user).delete()
    
    if payment_method == 'cod':
        from store.telegram_utils import notify_order_success
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
    
    return JsonResponse({
        'success': True,
        'message': 'Đặt hàng thành công!',
        'order_code': tracking_code
    })


# ==================== VIETQR SEPARATE PAGE ====================

@csrf_exempt
@login_required
@require_POST
def vietqr_create_order(request):
    """
    Tạo đơn hàng VietQR (awaiting_payment) + PendingQRPayment,
    trả về URL trang thanh toán VietQR riêng.
    """
    from store.models import Cart, Order, OrderItem, ProductDetail, FolderColorImage, PendingQRPayment
    import json
    import random as _rand
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)
    
    items_param = data.get('items_param', '')
    
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
    
    total_amount = sum(item.price_at_add * item.quantity for item in cart_items)
    
    tracking_code = 'QHUN' + str(_rand.randint(10000, 99999))
    
    digits = '0123456789'
    transfer_code = 'QHUN'
    for _ in range(5):
        transfer_code += digits[_rand.randint(0, 9)]
    
    order = Order.objects.create(
        user=request.user,
        order_code=tracking_code,
        total_amount=total_amount,
        payment_method='vietqr',
        status='awaiting_payment'
    )
    
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
    
    cart.items.filter(id__in=item_ids).delete()
    
    PendingQRPayment.objects.create(
        user=request.user,
        amount=total_amount,
        transfer_code=transfer_code,
    )
    
    from store.telegram_utils import notify_payment_created
    notify_payment_created('vietqr', tracking_code, request.user.username, total_amount)
    
    return JsonResponse({
        'success': True,
        'redirect_url': '/vietqr-payment/?order=' + tracking_code + '&code=' + transfer_code,
    })


@login_required
def vietqr_payment_page(request):
    """
    Trang thanh toán VietQR riêng - hiển thị QR, timer, polling admin duyệt.
    """
    from store.models import Order, PendingQRPayment
    
    order_code = request.GET.get('order', '')
    transfer_code = request.GET.get('code', '')
    
    if not order_code or not transfer_code:
        messages.error(request, 'Thiếu thông tin thanh toán')
        return redirect('store:cart_detail')
    
    try:
        order = Order.objects.get(order_code=order_code, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'Không tìm thấy đơn hàng')
        return redirect('store:cart_detail')
    
    if order.status not in ('awaiting_payment', 'processing'):
        return redirect('store:order_success', order_code=order_code)
    
    qr = PendingQRPayment.objects.filter(
        transfer_code=transfer_code, user=request.user
    ).first()
    
    timeout_seconds = 15 * 60
    if qr and qr.created_at:
        elapsed = (timezone.now() - qr.created_at).total_seconds()
        timeout_seconds = max(0, int(15 * 60 - elapsed))
    
    if timeout_seconds <= 0 and order.status == 'awaiting_payment':
        order.status = 'cancelled'
        order.save()
        if qr:
            qr.delete()
    
    context = {
        'order': order,
        'transfer_code': transfer_code,
        'timeout_seconds': timeout_seconds,
    }
    return render(request, 'store/vietqr_payment.html', context)


@login_required
def vietqr_page_status(request):
    """
    Polling API cho trang VietQR riêng.
    GET: code, order_code
    """
    from store.models import PendingQRPayment, Order
    
    code = request.GET.get('code', '')
    order_code = request.GET.get('order_code', '')
    
    if not code:
        return JsonResponse({'success': False, 'status': 'error'})
    
    try:
        qr = PendingQRPayment.objects.get(transfer_code=code, user=request.user)
    except PendingQRPayment.DoesNotExist:
        try:
            order = Order.objects.get(order_code=order_code, user=request.user)
            if order.status in ('processing', 'pending', 'delivered'):
                return JsonResponse({'success': True, 'status': 'approved'})
        except Order.DoesNotExist:
            pass
        return JsonResponse({'success': True, 'status': 'expired'})
    
    if qr.is_expired:
        qr.delete()
        return JsonResponse({'success': True, 'status': 'expired'})
    
    if qr.status == 'approved':
        try:
            order = Order.objects.get(order_code=order_code, user=request.user)
            if order.status == 'awaiting_payment':
                order.status = 'processing'
                order.save()
                
                from store.telegram_utils import notify_order_success
                vqr_items = list(order.items.values('product_name', 'quantity', 'storage', 'color_name'))
                notify_order_success(order_code, 'vietqr', vqr_items)
        except Order.DoesNotExist:
            pass
        qr.delete()
        return JsonResponse({'success': True, 'status': 'approved'})
    
    if qr.status == 'cancelled':
        return JsonResponse({'success': True, 'status': 'cancelled'})
    
    return JsonResponse({'success': True, 'status': 'pending'})


@csrf_exempt
@login_required
@require_POST
def vietqr_expire(request):
    """
    Client báo hết thời gian → huỷ đơn + xoá QR pending.
    """
    from store.models import Order, PendingQRPayment
    import json
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False})
    
    order_code = data.get('order_code', '')
    transfer_code = data.get('transfer_code', '')
    
    if order_code:
        try:
            order = Order.objects.get(order_code=order_code, user=request.user)
            if order.status == 'awaiting_payment':
                order.status = 'cancelled'
                order.save()
        except Order.DoesNotExist:
            pass
    
    if transfer_code:
        PendingQRPayment.objects.filter(
            transfer_code=transfer_code, user=request.user
        ).delete()
    
    return JsonResponse({'success': True})


# ==================== ADMIN ORDER MANAGEMENT ====================

@login_required
def admin_order_list(request):
    """
    Admin: lấy danh sách đơn hàng (JSON API)
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Order
    
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    
    result = []
    stt = 0
    for order in orders:
        items = list(order.items.all())
        if not items:
            # Đơn không có item → vẫn hiển thị 1 dòng
            stt += 1
            result.append({
                'stt': stt,
                'id': order.id,
                'order_code': order.order_code,
                'product_name': '—',
                'quantity': 0,
                'color_name': '—',
                'storage': '—',
                'price': str(order.total_amount),
                'total_amount': str(order.total_amount),
                'status': order.status,
                'status_display': order.get_status_display(),
                'payment_method': order.payment_method,
                'refund_account': order.refund_account or '',
                'refund_bank': order.refund_bank or '',
                'refund_status': order.refund_status or '',
                'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
            })
        else:
            for item in items:
                stt += 1
                c_name = item.color_name or '—'
                if ' - ' in c_name:
                    c_name = c_name.split(' - ', 1)[1]
                result.append({
                    'stt': stt,
                    'id': order.id,
                    'order_code': order.order_code,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'color_name': c_name,
                    'storage': item.storage or '—',
                    'price': str(item.price),
                    'total_amount': str(order.total_amount),
                    'status': order.status,
                    'status_display': order.get_status_display(),
                    'payment_method': order.payment_method,
                    'refund_account': order.refund_account or '',
                    'refund_bank': order.refund_bank or '',
                    'refund_status': order.refund_status or '',
                    'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
                })
    
    return JsonResponse({'success': True, 'orders': result})


@login_required
def best_sellers_admin(request):
    """
    Admin: Trang xem thống kê sản phẩm bán chạy
    Hiển thị tất cả sản phẩm được mua nhiều nhất với chi tiết
    """
    if not request.user.is_superuser:
        messages.error(request, 'Bạn không có quyền truy cập trang này!')
        return redirect('store:home')
    
    from store.models import OrderItem, Product, Order
    from django.db.models import Sum
    
    # Lấy tất cả sản phẩm bán chạy (không giới hạn top 5)
    # Chỉ tính các đơn hàng đã giao thành công (delivered)
    best_sellers_data = OrderItem.objects.filter(
        order__status='delivered',
        product__is_active=True
    ).values(
        'product__id', 
        'product__name', 
        'product__image', 
        'product__price',
        'product__original_price', 
        'product__discount_percent', 
        'product__stock',
        'product__slug',
        'product__brand__name',
        'product__brand__id'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')

    # Chuyển đổi queryset thành list với thông tin đầy đủ
    best_sellers = []
    total_sold_all = 0
    for item in best_sellers_data:
        product = Product.objects.filter(id=item['product__id']).first()
        if product:
            best_sellers.append({
                'product': product,
                'total_sold': item['total_sold'],
                'brand_name': item['product__brand__name'],
                'brand_id': item['product__brand__id']
            })
            total_sold_all += item['total_sold']

    context = {
        'best_sellers': best_sellers,
        'total_sold_all': total_sold_all,
    }
    return render(request, 'store/best_sellers_admin.html', context)


@login_required
def best_sellers_api(request):
    """
    API: Lấy danh sách sản phẩm bán chạy (JSON)
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import OrderItem, Product
    from django.db.models import Sum
    
    best_sellers_data = OrderItem.objects.filter(
        order__status='delivered',
        product__is_active=True
    ).values(
        'product__id', 
        'product__name', 
        'product__image', 
        'product__price',
        'product__original_price', 
        'product__discount_percent', 
        'product__stock',
        'product__slug',
        'product__brand__name'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:50]

    items = []
    for item in best_sellers_data:
        product = Product.objects.filter(id=item['product__id']).first()
        if product:
            # Lấy giá
            if product.detail:
                original_price = product.detail.summary_original_price or 0
                discounted_price = product.detail.discounted_price or 0
                discount_percent = product.detail.summary_discount_percent or 0
            else:
                original_price = int(product.original_price or 0) if product.original_price else 0
                discounted_price = int(product.price) if product.price else 0
                discount_percent = product.discount_percent or 0
            
            items.append({
                'id': product.id,
                'name': product.name,
                'brand': item['product__brand__name'] or '',
                'image': product.image.url if product.image else '',
                'original_price': original_price,
                'discounted_price': discounted_price,
                'discount_percent': discount_percent,
                'stock': product.stock,
                'total_sold': item['total_sold'],
                'slug': product.slug,
            })

    return JsonResponse({'success': True, 'items': items})


@login_required
def admin_order_detail(request):
    """
    Admin: chi tiết đơn hàng (JSON API)
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Order, Address
    
    order_id = request.GET.get('id')
    if not order_id:
        return JsonResponse({'success': False, 'message': 'Thiếu ID'}, status=400)
    
    try:
        order = Order.objects.select_related('user').prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy đơn hàng'}, status=404)
    
    # Lấy địa chỉ mặc định của người đặt
    address_data = None
    try:
        addr = Address.objects.filter(user=order.user, is_default=True).first()
        if not addr:
            addr = Address.objects.filter(user=order.user).first()
        if addr:
            address_data = {
                'full_name': addr.full_name,
                'phone': addr.phone,
                'address': f"{addr.detail}, {addr.ward_name}, {addr.district_name}, {addr.province_name}",
            }
    except Exception:
        pass
    
    # Items
    items = []
    for item in order.items.all():
        color = item.color_name or ''
        if ' - ' in color:
            color = color.split(' - ', 1)[1]
        items.append({
            'product_name': item.product_name,
            'quantity': item.quantity,
            'color_name': color,
            'storage': item.storage,
            'price': str(item.price),
            'thumbnail': item.thumbnail,
        })
    
    data = {
        'id': order.id,
        'order_code': order.order_code,
        'status': order.status,
        'status_display': order.get_status_display(),
        'payment_method': order.get_payment_method_display(),
        'payment_method_key': order.payment_method,
        'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
        'total_amount': str(order.total_amount),
        'user_email': order.user.email if order.user else '—',
        'address': address_data,
        'items': items,
        'voucher': order.coupon_code if order.coupon_code else None,
        'discount_amount': str(int(order.discount_amount)) if order.discount_amount else '0',
        'refund_account': order.refund_account or '',
        'refund_bank': order.refund_bank or '',
        'refund_status': order.refund_status or '',
    }
    
    return JsonResponse({'success': True, 'order': data})


@login_required
@require_POST
def admin_order_update_status(request):
    """
    Admin: cập nhật trạng thái đơn hàng hoặc trạng thái hoàn tiền
    Khi chuyển sang 'delivered' → giảm số lượng tồn kho (HangingProduct + ProductVariant)
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    import json
    from store.models import Order, ProductDetail, HangingProduct
    
    try:
        data = json.loads(request.body)
        order_id = data.get('id')
        new_status = data.get('status')
        refund_status = data.get('refund_status')
        
        order = Order.objects.get(id=order_id)
        old_status = order.status
        
        # Cập nhật trạng thái đơn hàng
        if new_status:
            valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'message': 'Trạng thái không hợp lệ'})
            
            # Khi chuyển sang 'delivered' và trước đó chưa phải delivered → giảm stock
            if new_status == 'delivered' and old_status != 'delivered':
                for item in order.items.all():
                    if item.product:
                        # 1. Giảm stock Product.stock (hiển thị trong dashboard Treo sản phẩm)
                        try:
                            product = item.product
                            if product.stock >= item.quantity:
                                product.stock -= item.quantity
                                product.save(update_fields=['stock'])
                        except Exception:
                            pass
                        
                        # 2. Giảm stock HangingProduct (nếu có liên kết)
                        try:
                            hanging = HangingProduct.objects.filter(product=item.product).first()
                            if hanging and hanging.stock_quantity >= item.quantity:
                                hanging.stock_quantity -= item.quantity
                                hanging.save(update_fields=['stock_quantity'])
                        except Exception:
                            pass
                        
                        # 3. Giảm stock ProductVariant (match theo color + storage)
                        try:
                            detail = ProductDetail.objects.get(product=item.product)
                            variant = detail.variants.filter(
                                color_name=item.color_name,
                                storage=item.storage
                            ).first()
                            if variant and variant.stock_quantity >= item.quantity:
                                variant.stock_quantity -= item.quantity
                                variant.save(update_fields=['stock_quantity'])
                        except ProductDetail.DoesNotExist:
                            pass
            
            order.status = new_status
        
        # Cập nhật trạng thái hoàn tiền
        if refund_status is not None:
            valid_refund_statuses = ['', 'pending', 'completed']
            if refund_status not in valid_refund_statuses:
                return JsonResponse({'success': False, 'message': 'Trạng thái hoàn tiền không hợp lệ'})
            order.refund_status = refund_status
        
        order.save()
        
        return JsonResponse({'success': True, 'message': f'Đã cập nhật đơn {order.order_code}'})
    
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy đơn hàng'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def qr_payment_list(request):
    """
    Admin: lấy danh sách QR đang pending (auto-cleanup expired).
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)

    from store.models import PendingQRPayment
    # Xoá hết QR pending quá 15 phút
    PendingQRPayment.cleanup_expired()

    qrs = PendingQRPayment.objects.filter(status='pending').order_by('-created_at')
    items = []
    for idx, qr in enumerate(qrs, 1):
        items.append({
            'id': qr.id,
            'stt': idx,
            'amount': int(qr.amount),
            'transfer_code': qr.transfer_code,
            'created_at': qr.created_at.strftime('%d/%m/%Y %H:%M:%S'),
            'user_email': qr.user.email,
            'qr_url': qr.qr_url(),
        })
    return JsonResponse({'success': True, 'items': items})


@login_required
def qr_payment_detail(request):
    """
    Admin: lấy chi tiết 1 QR (ảnh, số tiền, nội dung CK).
    GET: id
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)

    from store.models import PendingQRPayment
    qr_id = request.GET.get('id')
    try:
        qr = PendingQRPayment.objects.get(id=qr_id)
    except PendingQRPayment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy QR'}, status=404)

    return JsonResponse({
        'success': True,
        'data': {
            'id': qr.id,
            'amount': int(qr.amount),
            'transfer_code': qr.transfer_code,
            'created_at': qr.created_at.strftime('%d/%m/%Y %H:%M:%S'),
            'user_email': qr.user.email,
            'user_name': qr.user.get_full_name(),
            'qr_url': qr.qr_url(),
            'status': qr.status,
        }
    })


@csrf_exempt
@login_required
@require_POST
def qr_payment_approve(request):
    """Admin duyệt QR → status = approved."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)

    from store.models import PendingQRPayment
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)

    qr_id = data.get('id')
    try:
        qr = PendingQRPayment.objects.get(id=qr_id, status='pending')
    except PendingQRPayment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy QR hoặc đã xử lý'}, status=404)

    qr.status = 'approved'
    qr.save()
    return JsonResponse({'success': True, 'message': f'Đã duyệt QR {qr.transfer_code}'})


@csrf_exempt
@login_required
@require_POST
def qr_payment_cancel(request):
    """Admin hủy QR → status = cancelled."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)

    from store.models import PendingQRPayment
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)

    qr_id = data.get('id')
    try:
        qr = PendingQRPayment.objects.get(id=qr_id, status='pending')
    except PendingQRPayment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy QR hoặc đã xử lý'}, status=404)

    qr.status = 'cancelled'
    qr.save()
    return JsonResponse({'success': True, 'message': f'Đã hủy QR {qr.transfer_code}'})


@login_required
def qr_payment_status(request):
    """
    Checkout polling: kiểm tra trạng thái QR theo transfer_code.
    GET: transfer_code
    Trả về: status = 'pending' | 'approved' | 'cancelled' | 'expired'
    """
    from store.models import PendingQRPayment
    code = request.GET.get('code', '')
    if not code:
        return JsonResponse({'success': False, 'status': 'error'})

    try:
        qr = PendingQRPayment.objects.get(transfer_code=code, user=request.user)
    except PendingQRPayment.DoesNotExist:
        # Có thể đã bị cleanup (hết 15 phút) → coi như expired
        return JsonResponse({'success': True, 'status': 'expired'})

    if qr.is_expired:
        qr.delete()
        return JsonResponse({'success': True, 'status': 'expired'})

    return JsonResponse({'success': True, 'status': qr.status})


# ==================== VNPAY PAYMENT ====================
@login_required
@require_POST
@csrf_exempt
def vnpay_create(request):
    """
    Tạo yêu cầu thanh toán VNPay
    POST: amount, order_description, items_param
    """
    from store.models import VNPayPayment
    from store.vnpay_utils import VNPayUtil
    
    try:
        amount = float(request.POST.get('amount', 0))
        order_description = request.POST.get('order_description', 'Thanh toán mua hàng QHUN22')
        items_param = request.POST.get('items_param', '')
        
        if amount <= 0:
            return JsonResponse({'success': False, 'message': 'Số tiền không hợp lệ'}, status=400)
        
        # Tạo order code
        order_code = VNPayUtil.generate_order_code()
        
        # Lấy IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Tạo bản ghi VNPay Payment
        vnpay_payment = VNPayPayment.objects.create(
            user=request.user,
            amount=Decimal(amount),
            order_code=order_code,
            status='pending'
        )
        
        # Lưu items_param vào session (để lấy lại khi VNPay redirect về)
        request.session['vnpay_items_param'] = items_param
        request.session['vnpay_order_code'] = order_code
        
        # Xây dựng URL thanh toán (return URL sạch, không chứa query params)
        return_url = request.build_absolute_uri('/vnpay/return/')
        
        # Order description chỉ dùng ASCII (tránh lỗi encoding)
        safe_description = f'Thanh toan QHUN22 - {int(amount)} VND'
        
        payment_url = VNPayUtil.build_payment_url(
            amount=amount,
            order_code=order_code,
            order_description=safe_description,
            ip_address=ip_address,
            return_url=return_url
        )
        
        from store.telegram_utils import notify_payment_created
        notify_payment_created('vnpay', order_code, request.user.username, amount)
        
        return JsonResponse({
            'success': True,
            'payment_url': payment_url,
            'order_code': order_code
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def vnpay_return(request):
    """
    Xử lý return từ VNPay sau khi thanh toán
    VNPay sẽ redirect về URL này với các tham số response
    """
    from store.models import VNPayPayment, Order, OrderItem, Cart, FolderColorImage, ProductDetail
    from store.vnpay_utils import VNPayUtil
    
    try:
        # Lấy tất cả tham số từ request (VNPay append vào return URL)
        response_data = request.GET.dict()
        order_code = response_data.get('vnp_TxnRef', '')
        
        # Lấy items_param từ session
        items_param = request.session.pop('vnpay_items_param', '')
        session_order_code = request.session.pop('vnpay_order_code', '')
        
        if not order_code:
            messages.error(request, 'Không tìm thấy mã giao dịch VNPay')
            return redirect('store:checkout')
        
        # Lấy bản ghi VNPay Payment
        try:
            vnpay_payment = VNPayPayment.objects.get(order_code=order_code)
        except VNPayPayment.DoesNotExist:
            messages.error(request, 'Không tìm thấy đơn hàng VNPay')
            return redirect('store:checkout')
        
        # Chỉ verify các tham số vnp_ (loại bỏ params không phải của VNPay)
        vnp_data = {k: v for k, v in response_data.items() if k.startswith('vnp_')}
        
        # Xác minh response từ VNPay
        is_valid, message = VNPayUtil.verify_payment_response(vnp_data)
        
        response_code = vnp_data.get('vnp_ResponseCode', '')
        transaction_no = vnp_data.get('vnp_TransactionNo', '')
        
        # Cập nhật thông tin thanh toán
        vnpay_payment.response_code = response_code
        vnpay_payment.response_message = message
        vnpay_payment.transaction_no = transaction_no
        
        if is_valid and response_code == '00':
            vnpay_payment.status = 'paid'
            vnpay_payment.paid_at = timezone.now()
            vnpay_payment.save()
            
            # Tạo mã đơn hàng QHUN + 5 số random
            import random as _rand
            tracking_code = 'QHUN' + str(_rand.randint(10000, 99999))
            
            # Tạo Order
            order = Order.objects.create(
                user=request.user,
                order_code=tracking_code,
                total_amount=vnpay_payment.amount,
                payment_method='vnpay',
                vnpay_order_code=order_code,
                status='processing'
            )
            
            # Lưu sản phẩm vào OrderItem trước khi xóa cart
            if items_param:
                try:
                    item_ids = [int(x) for x in items_param.split(',') if x.strip()]
                    cart = Cart.get_or_create_for_user(request.user)
                    if cart:
                        cart_items = cart.items.filter(id__in=item_ids).select_related('product', 'product__brand')
                        for ci in cart_items:
                            # Tìm thumbnail
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
                        # Xóa cart items sau khi đã lưu
                        cart_items.delete()
                except (ValueError, TypeError):
                    pass
            
            from store.telegram_utils import notify_order_success
            vnpay_items = list(order.items.values('product_name', 'quantity', 'storage', 'color_name'))
            notify_order_success(tracking_code, 'vnpay', vnpay_items)
            
            return redirect('store:order_success', order_code=tracking_code)
        else:
            vnpay_payment.status = 'failed'
            vnpay_payment.save()
            messages.error(request, f'Thanh toán VNPay thất bại: {message}')
            
            if items_param:
                return redirect(f'{reverse("store:checkout")}?items={items_param}')
            return redirect('store:checkout')
            
    except Exception as e:
        messages.error(request, f'Lỗi xử lý thanh toán: {str(e)}')
        return redirect('store:checkout')


@csrf_exempt
@require_http_methods(["POST"])
def vnpay_ipn(request):
    """
    Xử lý IPN (Instant Payment Notification) từ VNPay
    VNPay sẽ gửi POST request đến URL này để xác nhận thanh toán
    """
    from store.models import VNPayPayment, Order, Cart
    from store.vnpay_utils import VNPayUtil
    import json
    
    try:
        # Lấy tất cả tham số từ request
        response_data = request.POST.dict()
        order_code = response_data.get('vnp_TxnRef', '')
        
        if not order_code:
            return JsonResponse({'RspCode': '01', 'Message': 'Invalid order code'})
        
        # Lấy bản ghi VNPay Payment
        try:
            vnpay_payment = VNPayPayment.objects.get(order_code=order_code)
        except VNPayPayment.DoesNotExist:
            return JsonResponse({'RspCode': '01', 'Message': 'Order not found'})
        
        # Xác minh response từ VNPay
        is_valid, message = VNPayUtil.verify_payment_response(response_data)
        
        response_code = response_data.get('vnp_ResponseCode', '')
        transaction_no = response_data.get('vnp_TransactionNo', '')
        
        if not is_valid:
            return JsonResponse({'RspCode': '02', 'Message': message})
        
        # Cập nhật thông tin thanh toán
        vnpay_payment.transaction_no = transaction_no
        vnpay_payment.response_code = response_code
        vnpay_payment.response_message = message
        
        if response_code == '00':
            vnpay_payment.status = 'paid'
            vnpay_payment.paid_at = timezone.now()
            vnpay_payment.save()
            
            # Ghi log hoặc xử lý thêm tại đây
            # Ví dụ: Tạo Order, gửi email, v.v.
            
            return JsonResponse({'RspCode': '00', 'Message': 'Confirmed'})
        else:
            vnpay_payment.status = 'failed'
            vnpay_payment.save()
            return JsonResponse({'RspCode': '02', 'Message': f'Payment failed: {message}'})
            
    except Exception as e:
        return JsonResponse({'RspCode': '99', 'Message': str(e)})


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


def compare_view(request):
    """
    Trang so sánh sản phẩm - hiển thị thông số mỗi SP thành 1 cột
    URL: /compare/?ids=1,2,3
    """
    from store.models import Product, ProductSpecification
    import json as json_lib

    ids_param = request.GET.get('ids', '')
    if not ids_param:
        return redirect('store:home')

    try:
        ids = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
    except (ValueError, TypeError):
        return redirect('store:home')

    if not ids or len(ids) < 2:
        return redirect('store:home')

    products = list(
        Product.objects.filter(id__in=ids, is_active=True)
        .select_related('brand', 'category', 'detail')
    )

    if len(products) < 2:
        messages.error(request, 'Cần ít nhất 2 sản phẩm để so sánh')
        return redirect('store:home')

    def parse_groups(raw):
        """Parse spec_json into list of {title, items: [{label, value}]}"""
        groups = []
        if not raw:
            return groups
        if isinstance(raw, dict) and 'groups' in raw:
            raw = raw['groups']
        if isinstance(raw, list):
            for g in raw:
                title = g.get('title', '') or g.get('name', '')
                items_raw = g.get('items', []) or g.get('specs', [])
                items = []
                for item in items_raw:
                    label = item.get('label', '') or item.get('name', '') or item.get('key', '')
                    value = item.get('value', '')
                    if label:
                        items.append({'label': label, 'value': value})
                if items:
                    groups.append({'title': title, 'items': items})
        elif isinstance(raw, dict):
            items = [{'label': k, 'value': v} for k, v in raw.items()]
            if items:
                groups.append({'title': 'Thông số kỹ thuật', 'items': items})
        return groups

    compare_data = []
    for product in products:
        groups = []
        try:
            if hasattr(product, 'detail') and product.detail:
                spec_obj = ProductSpecification.objects.filter(detail=product.detail).first()
                if spec_obj and spec_obj.spec_json:
                    groups = parse_groups(spec_obj.spec_json)
        except Exception:
            pass
        compare_data.append({
            'product': product,
            'groups': groups,
        })

    context = {
        'products': products,
        'compare_data': compare_data,
    }
    return render(request, 'store/compare.html', context)


# ==================== COUPON MANAGEMENT ====================

@login_required
def coupon_list(request):
    """Lấy danh sách mã giảm giá (admin) hoặc chi tiết 1 coupon"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Coupon
    
    coupon_id = request.GET.get('id')
    if coupon_id:
        try:
            c = Coupon.objects.get(id=coupon_id)
            return JsonResponse({'success': True, 'coupon': {
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'discount_type': c.discount_type,
                'discount_value': str(c.discount_value),
                'target_type': c.target_type,
                'target_email': c.target_email,
                'max_products': c.max_products,
                'min_order_amount': str(c.min_order_amount),
                'usage_limit': c.usage_limit,
                'used_count': c.used_count,
                'expire_days': c.expire_days,
                'is_active': c.is_active,
            }})
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Không tìm thấy'}, status=404)
    
    coupons = Coupon.objects.all()
    result = []
    for c in coupons:
        result.append({
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'discount_type': c.discount_type,
            'discount_value': str(c.discount_value),
            'target_type': c.target_type,
            'target_email': c.target_email,
            'max_products': c.max_products,
            'min_order_amount': str(c.min_order_amount),
            'usage_limit': c.usage_limit,
            'used_count': c.used_count,
            'is_active': c.is_active,
            'is_valid': c.is_valid(),
            'expire_at': c.expire_at.strftime('%d/%m/%Y'),
        })
    return JsonResponse({'success': True, 'coupons': result})


@login_required
@require_POST
def coupon_add(request):
    """Thêm mã giảm giá mới"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Coupon
    
    code = request.POST.get('code', '').strip().upper()
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'message': 'Tên chương trình không được để trống'})
    if not code:
        return JsonResponse({'success': False, 'message': 'Tên mã giảm không được để trống'})
    if ' ' in code:
        return JsonResponse({'success': False, 'message': 'Mã giảm không được chứa khoảng trắng'})
    if Coupon.objects.filter(code=code).exists():
        return JsonResponse({'success': False, 'message': 'Mã giảm giá đã tồn tại'})
    
    expire_days = int(request.POST.get('expire_days', '30'))
    if expire_days < 1:
        return JsonResponse({'success': False, 'message': 'Hạn sử dụng phải ít nhất 1 ngày'})
    
    expire_at = timezone.now() + datetime.timedelta(days=expire_days)
    
    try:
        Coupon.objects.create(
            name=name,
            code=code,
            discount_type=request.POST.get('discount_type', 'percentage'),
            discount_value=Decimal(request.POST.get('discount_value', '0')),
            target_type=request.POST.get('target_type', 'all'),
            target_email=request.POST.get('target_email', ''),
            max_products=int(request.POST.get('max_products', '0')),
            min_order_amount=Decimal(request.POST.get('min_order_amount', '0')),
            usage_limit=int(request.POST.get('usage_limit', '0')),
            expire_days=expire_days,
            is_active=request.POST.get('is_active') == '1',
            expire_at=expire_at,
        )
        return JsonResponse({'success': True, 'message': 'Đã thêm mã giảm giá'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'})


@login_required
@require_POST
def coupon_edit(request):
    """Sửa mã giảm giá"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Coupon
    
    coupon_id = request.POST.get('id')
    if not coupon_id:
        return JsonResponse({'success': False, 'message': 'Thiếu ID'})
    
    try:
        c = Coupon.objects.get(id=coupon_id)
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy'})
    
    try:
        c.name = request.POST.get('name', c.name)
        c.discount_type = request.POST.get('discount_type', 'percentage')
        c.discount_value = Decimal(request.POST.get('discount_value', '0'))
        c.target_type = request.POST.get('target_type', 'all')
        c.target_email = request.POST.get('target_email', '')
        c.max_products = int(request.POST.get('max_products', '0'))
        c.min_order_amount = Decimal(request.POST.get('min_order_amount', '0'))
        c.usage_limit = int(request.POST.get('usage_limit', '0'))
        new_expire_days = int(request.POST.get('expire_days', '0'))
        if new_expire_days > 0 and new_expire_days != c.expire_days:
            c.expire_days = new_expire_days
            c.expire_at = c.created_at + datetime.timedelta(days=new_expire_days)
        c.is_active = request.POST.get('is_active') == '1'
        c.save()
        return JsonResponse({'success': True, 'message': 'Đã cập nhật mã giảm giá'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'})


@login_required
@require_POST
def coupon_delete(request):
    """Xóa mã giảm giá"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Không có quyền'}, status=403)
    
    from store.models import Coupon
    
    coupon_id = request.POST.get('id')
    if not coupon_id:
        return JsonResponse({'success': False, 'message': 'Thiếu ID'})
    
    try:
        c = Coupon.objects.get(id=coupon_id)
        c.delete()
        return JsonResponse({'success': True, 'message': 'Đã xóa mã giảm giá'})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Không tìm thấy'})


@login_required
@require_POST
def coupon_apply(request):
    """
    Áp dụng mã giảm giá - 7-step validation:
    1. Có tồn tại không?
    2. Có active không?
    3. Có hết hạn chưa?
    4. Có đúng đối tượng không?
    5. Đơn có đạt tối thiểu không?
    6. Có vượt số lượng sản phẩm không?
    7. Đã vượt số lượt chưa?
    """
    from store.models import Coupon
    import json
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dữ liệu không hợp lệ'})
    
    code = data.get('code', '').strip().upper()
    try:
        order_total = Decimal(str(data.get('order_total', 0)))
    except Exception:
        order_total = Decimal('0')
    try:
        item_count = int(data.get('item_count', 0))
    except Exception:
        item_count = 0
    
    if not code:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập mã giảm giá'})
    
    # 1. Có tồn tại không?
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Mã giảm giá không tồn tại'})
    
    # 2. Có active không?
    if not coupon.is_active:
        return JsonResponse({'success': False, 'message': 'Mã giảm giá đã bị vô hiệu hóa'})
    
    # 3. Có hết hạn chưa?
    if coupon.is_expired():
        return JsonResponse({'success': False, 'message': 'Mã giảm giá đã hết hạn'})
    
    # 4. Có đúng đối tượng không?
    if coupon.target_type == 'single':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Vui lòng đăng nhập để sử dụng mã này'})
        
        # Kiểm tra email đăng nhập hoặc email đã xác thực Student/Teacher
        user_email = request.user.email.lower()
        target_email = coupon.target_email.lower()
        
        # Cho phép sử dụng nếu email đăng nhập khớp HOẶC email đã xác thực Student/Teacher khớp
        verified_student = getattr(request.user, 'verified_student_email', '').lower()
        verified_teacher = getattr(request.user, 'verified_teacher_email', '').lower()
        
        is_valid = (user_email == target_email or 
                    verified_student == target_email or 
                    verified_teacher == target_email)
        
        if not is_valid:
            return JsonResponse({'success': False, 'message': 'Mã giảm giá không áp dụng cho tài khoản của bạn'})
    
    # 5. Đơn có đạt tối thiểu không?
    if order_total < coupon.min_order_amount:
        min_fmt = f'{int(coupon.min_order_amount):,}'.replace(',', '.')
        return JsonResponse({'success': False, 'message': f'Đơn hàng chưa đạt giá trị tối thiểu {min_fmt}đ'})
    
    # 6. Có vượt số lượng sản phẩm không?
    if coupon.max_products > 0 and item_count > coupon.max_products:
        return JsonResponse({'success': False, 'message': f'Voucher chỉ áp dụng cho tối đa {coupon.max_products} sản phẩm'})
    
    # 7. Đã vượt số lượt chưa?
    if coupon.usage_limit > 0 and coupon.used_count >= coupon.usage_limit:
        return JsonResponse({'success': False, 'message': 'Mã giảm giá đã hết lượt sử dụng'})
    
    try:
        discount = coupon.calculate_discount(order_total)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Lỗi tính toán giảm giá'})
    
    return JsonResponse({
        'success': True,
        'code': coupon.code,
        'discount': str(int(discount)),
        'discount_display': f'{int(discount):,}đ'.replace(',', '.'),
        'new_total': str(int(order_total - discount)),
        'new_total_display': f'{int(order_total - discount):,}đ'.replace(',', '.'),
        'name': coupon.name,
    })


# ── AI Chatbot ──────────────────────────────────────────────────
@csrf_exempt
@require_POST
def chatbot_api(request):
    import json as _json
    import traceback as _tb

    try:
        body = _json.loads(request.body)
        message = body.get("message", "").strip()
    except Exception:
        return JsonResponse({"message": "Tin nhắn không hợp lệ.", "suggestions": []}, status=400)

    if not message:
        return JsonResponse({"message": "Vui lòng nhập nội dung.", "suggestions": []}, status=400)

    if len(message) > 500:
        return JsonResponse({"message": "Tin nhắn quá dài, vui lòng rút gọn lại nhé!", "suggestions": []}, status=400)

    try:
        from .chatbot_service import ChatbotService
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        service = ChatbotService()
        result = service.process_message(message, user=user, session=getattr(request, "session", None))
        return JsonResponse(result)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Chatbot API error")
        if settings.DEBUG:
            return JsonResponse({
                "message": f"[DEBUG] Lỗi: {type(e).__name__}: {e}",
                "suggestions": [],
            }, status=200)
        return JsonResponse({
            "message": "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau! 🙏",
            "suggestions": ["Tư vấn chọn máy", "Gặp nhân viên"],
        }, status=200)


# ── Student/Teacher Email Verification ──────────────────────────────────────────────────
@login_required
def send_verification_code(request):
    """Gửi mã xác thực đến email .edu"""
    from store.models import EmailVerification
    from django.utils import timezone
    import random
    import string
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ'})
    
    email = request.POST.get('email', '').strip().lower()
    verification_type = request.POST.get('type', 'student')  # student or teacher
    
    if not email:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập email'})
    
    # Kiểm tra email có phải .edu.vn không
    if not email.endswith('.edu.vn'):
        return JsonResponse({'success': False, 'message': 'Vui lòng sử dụng email .edu.vn'})
    
    # Kiểm tra xem đã xác thực chưa
    user = request.user
    if verification_type == 'student':
        if user.is_student_verified:
            return JsonResponse({'success': False, 'message': 'Bạn đã xác thực Student rồi'})
    else:
        if user.is_teacher_verified:
            return JsonResponse({'success': False, 'message': 'Bạn đã xác thực Teacher rồi'})
    
    # Tạo mã xác thực 6 số
    code = ''.join(random.choices(string.digits, k=6))
    
    # Xóa các mã cũ chưa hết hạn
    EmailVerification.objects.filter(
        user=user,
        email=email,
        is_verified=False,
        expires_at__gt=timezone.now()
    ).delete()
    
    # Lưu mã mới
    verification = EmailVerification.objects.create(
        user=user,
        email=email,
        code=code,
        verification_type=verification_type
    )
    
    # Gửi email qua SendGrid API
    try:
        import os
        import requests
        
        api_key = os.getenv('SENDGRID_API_KEY', '')
        from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com')
        
        data = {
            "personalizations": [{
                "to": [{"email": email}],
                "subject": "Xac thuc Student/Teacher - QHUN22"
            }],
            "from": {"email": from_email},
            "content": [{
                "type": "text/html",
                "value": f"""
                <h1>Xin chao {user.get_full_name()},</h1>
                <p>Ma xac thuc cua ban la: <strong style="font-size: 24px; color: #667eea;">{code}</strong></p>
                <p>Ma co hieu luc trong 10 phut.</p>
                <p>Vui long khong chia se ma nay voi bat ky ai.</p>
                <p>Tran trong,<br>QHUN22 Mobile</p>
                """
            }]
        }
        
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code in [200, 201, 202]:
            return JsonResponse({
                'success': True, 
                'message': f'Ma xac thuc da gui den {email}',
                'email': email
            })
        else:
            return JsonResponse({'success': False, 'message': f'Loi gui email: {response.status_code}'})
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error sending verification email")
        from django.conf import settings
        if settings.DEBUG:
            return JsonResponse({'success': False, 'message': f'Loi gui email: {str(e)}'})
        return JsonResponse({'success': False, 'message': 'Loi gui email. Vui long thu lai sau.'})


@login_required
def verify_code(request):
    """Xác thực mã"""
    from store.models import EmailVerification, Coupon
    from django.utils import timezone
    import random
    import string
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ'})
    
    email = request.POST.get('email', '').strip().lower()
    code = request.POST.get('code', '').strip()
    
    if not email or not code:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin'})
    
    user = request.user
    
    # Tìm mã xác thực
    try:
        verification = EmailVerification.objects.get(
            user=user,
            email=email,
            code=code,
            is_verified=False
        )
    except EmailVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Mã xác thực không đúng'})
    
    # Kiểm tra hết hạn
    if not verification.is_valid():
        return JsonResponse({'success': False, 'message': 'Mã đã hết hạn. Vui lòng gửi lại mã mới.'})
    
    # Xác thực thành công
    verification.is_verified = True
    verification.save()
    
    # Cập nhật user
    if verification.verification_type == 'student':
        user.is_student_verified = True
        user.verified_student_email = email
        user.student_verified_at = timezone.now()
    else:
        user.is_teacher_verified = True
        user.verified_teacher_email = email
        user.teacher_verified_at = timezone.now()
    user.save()
    
    # Tạo voucher giảm 50% cho người dùng đã xác thực (1 lần sử dụng, 1 đơn hàng duy nhất)
    # Tạo mã voucher ngẫu nhiên
    voucher_code = 'EDU50' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Kiểm tra xem đã tạo voucher cho email này chưa
    existing_coupon = Coupon.objects.filter(
        target_email=email,
        name__icontains='Student/Teacher'
    ).first()
    
    if not existing_coupon:
        coupon = Coupon.objects.create(
            name=f'Ưu đãi Student/Teacher - {email}',
            code=voucher_code,
            discount_type='percentage',
            discount_value=50,
            target_type='single',
            target_email=email,
            max_products=0,  # Áp dụng cho tất cả sản phẩm
            min_order_amount=0,  # Không giới hạn đơn tối thiểu
            usage_limit=1,  # Chỉ sử dụng 1 lần
            expire_days=30,  # Hết hạn sau 30 ngày
            is_active=True
        )
        voucher_message = f' Mã voucher giảm 50%: {voucher_code}'
    else:
        voucher_message = f' Mã voucher: {existing_coupon.code}'
    
    return JsonResponse({
        'success': True, 
        'message': f'Xác thực thành công! Cảm ơn bạn đã xác thực.{voucher_message}',
        'type': verification.verification_type,
        'voucher_code': voucher_code if not existing_coupon else existing_coupon.code
    })
