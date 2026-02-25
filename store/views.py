"""
Views cho ứng dụng store - QHUN22
"""
import os
import random
import time
import requests
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
        variants_list.append({
            'id': v.id,
            'color_name': v.color_name,
            'color_hex': v.color_hex or '',
            'storage': v.storage,
            'price': int(v.price) if v.price is not None else 0,
            'original_price': int(v.original_price) if v.original_price is not None else 0,
            'discount_percent': int(v.discount_percent) if v.discount_percent is not None else 0,
            'sku': v.sku or '',
            'stock_quantity': int(v.stock_quantity) if v.stock_quantity is not None else 0,
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
    }
    
    return render(request, 'store/product_detail.html', context)


def home(request):
    """
    Trang chủ của cửa hàng QHUN22
    Hiển thị danh sách sản phẩm với phân trang (tối đa 15 sản phẩm/trang)
    Sản phẩm có hàng hiển thị trước, hết hàng hiển thị sau
    """
    from store.models import Product, SiteVisit
    
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

    context = {
        'products': products,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'store/home.html', context)


def product_search(request):
    """
    Tìm kiếm sản phẩm
    """
    query = request.GET.get('q', '')
    context = {
        'query': query,
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
    Tra cứu đơn hàng - hiển thị đơn hàng của user đang đăng nhập
    """
    from store.models import Order
    
    context = {}
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        context['orders'] = orders
    
    return render(request, 'store/order_tracking.html', context)


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
        # Tăng số lượng
        existing_item.quantity += quantity
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
    
    context = {}
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        total_orders = orders.count()
        total_spent_raw = orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        
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
        
        context.update({
            'orders': orders,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'total_spent_raw': total_spent_raw,
            'password_history': password_history,
            'addresses': addresses,
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
    
    # Doanh thu hôm nay
    today = timezone.now().date()
    revenue_today = Order.objects.filter(
        created_at__date=today,
        status__in=['processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Doanh thu tháng này
    from datetime import datetime
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_this_month = Order.objects.filter(
        created_at__gte=start_of_month,
        status__in=['processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Dữ liệu biểu đồ doanh thu năm 2026 (12 tháng)
    # Hiện tại: 23/02/2026 - Tất cả tháng có chiều cao bằng nhau khi chưa có dữ liệu
    month_data = [
        {'name': 'T1', 'value': 0, 'height': 10},
        {'name': 'T2', 'value': 0, 'height': 10},
        {'name': 'T3', 'value': 0, 'height': 10},
        {'name': 'T4', 'value': 0, 'height': 10},
        {'name': 'T5', 'value': 0, 'height': 10},
        {'name': 'T6', 'value': 0, 'height': 10},
        {'name': 'T7', 'value': 0, 'height': 10},
        {'name': 'T8', 'value': 0, 'height': 10},
        {'name': 'T9', 'value': 0, 'height': 10},
        {'name': 'T10', 'value': 0, 'height': 10},
        {'name': 'T11', 'value': 0, 'height': 10},
        {'name': 'T12', 'value': 0, 'height': 10},
    ]
    
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


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_edit(request):
    """Sửa sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product, Brand
    import os
    
    product_id = request.POST.get('product_id')
    brand_id = request.POST.get('brand')
    name = request.POST.get('name', '').strip()
    
    if not product_id or not brand_id or not name:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin cần thiết!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    try:
        brand = Brand.objects.get(id=brand_id)
    except Brand.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hãng không tồn tại!'}, status=404)
    
    try:
        price = int(price)
        original_price = int(original_price) if original_price else None
        stock = int(stock) if stock else 0
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Giá và số lượng phải là số!'}, status=400)
    
    # Handle image upload - if new image uploaded, delete old and save new
    new_image = request.FILES.get('image')
    
    if new_image:
        # Delete old image
        if product.image:
            try:
                if os.path.isfile(product.image.path):
                    os.remove(product.image.path)
                product.image.delete(save=True)
            except Exception as e:
                print(f"Error deleting old image: {e}")
    
    product.brand = brand
    product.name = name
    if new_image:
        product.image = new_image
    product.save()
    
    return JsonResponse({'success': True, 'message': f'Đã cập nhật sản phẩm "{name}"!'})


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def product_delete(request):
    """Xóa sản phẩm"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
    from store.models import Product
    import os
    
    product_id = request.POST.get('product_id')
    
    if not product_id:
        return JsonResponse({'success': False, 'message': 'Thiếu thông tin!'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Sản phẩm không tồn tại!'}, status=404)
    
    # Delete image file
    if product.image:
        try:
            if os.path.isfile(product.image.path):
                os.remove(product.image.path)
            product.image.delete(save=True)
        except Exception as e:
            print(f"Error deleting image: {e}")
    
    product_name = product.name
    product.delete()
    
    return JsonResponse({'success': True, 'message': f'Đã xóa sản phẩm "{product_name}"!'})


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

    try:
        images_qs = FolderColorImage.objects.select_related('folder', 'brand')
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
                    'brand_name': img.brand.name if img.brand else None,
                }

        rows = list(rows_map.values())

        # Danh sách tất cả thư mục (cho dropdown), không phụ thuộc search
        folders_qs = ImageFolder.objects.all().order_by('-created_at')
        folders = [{'id': f.id, 'name': f.name} for f in folders_qs]

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

    from store.models import ImageFolder

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập tên thư mục!'}, status=400)

    try:
        # Tự sinh slug từ name (trong model)
        folder, created = ImageFolder.objects.get_or_create(name=name)
        # Tạo thư mục vật lý: media/products/YYYY/MM/<slug>/
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
            'folder': {'id': folder.id, 'name': folder.name, 'slug': folder.slug}
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
        # Không chặn xóa record nếu xóa file lỗi
        pass

    img.delete()
    return JsonResponse({'success': True, 'message': 'Đã xóa ảnh màu!'})


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
    
    # Dropdown "Chọn màu (SKU)": lấy SKU + màu từ Ảnh sản phẩm (FolderColorImage) theo hãng
    # để luôn có dữ liệu dù ProductDetail.sku còn trống
    sku_to_color = {}
    if product.brand_id:
        # Mỗi SKU lấy 1 màu từ Ảnh sản phẩm (FolderColorImage)
        rows = FolderColorImage.objects.filter(brand_id=product.brand_id).order_by('sku', 'created_at')
        for row in rows:
            if row.sku and row.sku not in sku_to_color:
                sku_to_color[row.sku] = (row.color_name or '').strip()
    skus_with_color = [{'sku': sku, 'color_name': color} for sku, color in sku_to_color.items()]
    # Nếu ProductDetail đã có SKU thì giữ thứ tự đó và đảm bảo có trong list
    if detail and (detail.sku or '').strip():
        sku_list_raw = [x.strip() for x in (detail.sku or '').split(',') if x.strip()]
        existing_skus = {s['sku'] for s in skus_with_color}
        for s in sku_list_raw:
            if s not in existing_skus:
                skus_with_color.append({'sku': s, 'color_name': sku_to_color.get(s, '')})
                existing_skus.add(s)
    
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
    """Lấy danh sách tất cả banner"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)
    
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