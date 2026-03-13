"""
Product Views (home, detail, search, compare) - QHUN22 Store
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
    }
    
    return render(request, 'store/product_detail.html', context)



def submit_review(request):
    """API đánh giá sản phẩm - chỉ user đã mua thành công (delivered) mới được"""
    from django.http import JsonResponse
    from store.models import Product, ProductReview, OrderItem

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Phương thức không được phép'}, status=405)
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
    )
    
    # Bộ lọc: theo hãng
    selected_brand = request.GET.get('brand', '').strip()
    if selected_brand:
        products_list = products_list.filter(brand__slug=selected_brand)
    
    # Bộ lọc: theo khoảng giá - SỬ DỤNG discounted_price từ ProductDetail
    selected_price_range = request.GET.get('price_range', '').strip()
    price_ranges = {
        '0-2': (0, 2000000),
        '2-4': (2000000, 4000000),
        '4-7': (4000000, 7000000),
        '7-13': (7000000, 13000000),
        '13-20': (13000000, 20000000),
        '20-999': (20000000, None),
    }
    if selected_price_range in price_ranges:
        min_p, max_p = price_ranges[selected_price_range]
        # Lọc theo giá thực tế hiển thị trên card:
        # 1) Giá giảm từ ProductDetail (nếu có)
        # 2) Giá gốc ProductDetail
        # 3) Giá nhỏ nhất của biến thể
        # 4) Product.price (fallback cuối)
        products_list = products_list.annotate(
            _variant_min_price=models.Min('detail__variants__price'),
            _discounted_price=models.Case(
                models.When(
                    detail__original_price__gt=0,
                    detail__discount_percent__gt=0,
                    then=models.F('detail__original_price') - (models.F('detail__original_price') * models.F('detail__discount_percent') / 100)
                ),
                models.When(
                    detail__original_price__gt=0,
                    then=models.F('detail__original_price')
                ),
                models.When(
                    _variant_min_price__gt=0,
                    then=models.F('_variant_min_price')
                ),
                default=models.F('price'),
                output_field=models.DecimalField(max_digits=15, decimal_places=0)
            )
        )
        if max_p is not None:
            products_list = products_list.filter(_discounted_price__gte=min_p, _discounted_price__lt=max_p)
        else:
            products_list = products_list.filter(_discounted_price__gte=min_p)
    
    # Sắp xếp theo giá
    selected_sort_price = request.GET.get('sort_price', '').strip()
    
    if selected_sort_price == 'asc':
        products_list = products_list.order_by('stock_order', 'price')
    elif selected_sort_price == 'desc':
        products_list = products_list.order_by('stock_order', '-price')
    else:
        # Default: Random display (có hàng trước, sau đó hết hàng)
        # Split thành 2 group, random mỗi group riêng, sau đó ghép lại
        from django.db.models import Case, When, FloatField
        
        # Dùng 30 phút làm seed để random consistent mỗi 30 phút
        # Sau mỗi 30 phút random khác lần
        import random
        import datetime
        now = datetime.datetime.now()
        # Tính slot 30 phút: (hour * 60 + minute) // 30
        time_slot = (now.hour * 60 + now.minute) // 30
        seed_str = f"{now.date()}_{time_slot}"
        random.seed(seed_str)
        
        # Split: có hàng (stock_order = 0) và hết hàng (stock_order = 1)
        in_stock = products_list.filter(stock__gt=0)
        out_of_stock = products_list.filter(stock__lte=0)
        
        # Random trong mỗi group riêng
        in_stock_ids = list(in_stock.values_list('id', flat=True))
        out_of_stock_ids = list(out_of_stock.values_list('id', flat=True))
        
        random.shuffle(in_stock_ids)
        random.shuffle(out_of_stock_ids)
        
        # Ghép lại bằng cách tạo preserve order instruction
        all_ids = in_stock_ids + out_of_stock_ids
        
        # Dùng Case/When để preserve order theo list ID
        if all_ids:
            # Tạo Case statement để preserve order
            preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(all_ids)], output_field=IntegerField())
            products_list = products_list.filter(id__in=all_ids).annotate(preserved_pos=preserved_order).order_by('preserved_pos')
        else:
            products_list = products_list.order_by('stock_order')
    
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
        'selected_brand': selected_brand,
        'selected_price_range': selected_price_range,
        'selected_sort_price': selected_sort_price,
    }
    
    # Lấy danh sách brands cho header và featured brands
    from store.models import Brand
    context['brands'] = Brand.objects.filter(is_active=True).order_by('name')
    
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
    Tìm kiếm sản phẩm theo từ khóa hoặc hãng
    """
    from store.models import Product, Brand
    
    query = request.GET.get('q', '')
    brand_slug = request.GET.get('brand', '')
    
    # Khởi tạo query sản phẩm
    products = Product.objects.select_related('brand', 'detail').filter(is_active=True)
    
    current_brand = None
    
    # Lọc theo hãng nếu có
    if brand_slug:
        try:
            current_brand = Brand.objects.get(slug=brand_slug, is_active=True)
            products = products.filter(brand=current_brand)
        except Brand.DoesNotExist:
            pass
    
    # Lọc theo từ khóa tìm kiếm nếu có
    if query:
        # Tìm kiếm trong tên sản phẩm hoặc mô tả
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(brand__name__icontains=query)
        )
    
    # Sắp xếp theo ngày tạo (mới nhất trước)
    products = products.order_by('-created_at')
    
    # Phân trang
    paginator = Paginator(products, 20)  # 20 sản phẩm mỗi trang
    page_number = request.GET.get('page')
    products_paginated = paginator.get_page(page_number)
    
    # Lấy danh sách sản phẩm trong wishlist của user
    wishlist_product_ids = []
    if request.user.is_authenticated:
        from store.models import Wishlist
        wishlist = Wishlist.get_or_create_for_user(request.user)
        if wishlist:
            wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))
    
    context = {
        'query': query,
        'brand': brand_slug,
        'current_brand': current_brand,
        'products': products_paginated,
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


@require_http_methods(["GET"])
def product_filter_json(request):
    """
    API lọc sản phẩm bằng AJAX - trả về HTML danh sách sản phẩm
    """
    from django.template.loader import render_to_string
    from store.models import Product, Wishlist

    # Lấy các tham số lọc
    selected_brand = request.GET.get('brand', '').strip()
    selected_price_range = request.GET.get('price_range', '').strip()
    selected_sort_price = request.GET.get('sort_price', '').strip()
    page = request.GET.get('page', 1)

    # Build query sản phẩm
    products_list = Product.objects.filter(is_active=True).select_related('brand', 'detail')

    # Lọc theo hãng
    if selected_brand:
        products_list = products_list.filter(brand__slug=selected_brand)

    # Lọc theo khoảng giá - SỬ DỤNG discounted_price từ ProductDetail
    price_ranges = {
        '0-2': (0, 2000000),
        '2-4': (2000000, 4000000),
        '4-7': (4000000, 7000000),
        '7-13': (7000000, 13000000),
        '13-20': (13000000, 20000000),
        '20-999': (20000000, None),
    }

    if selected_price_range in price_ranges:
        min_p, max_p = price_ranges[selected_price_range]
        # Lọc theo giá thực tế hiển thị trên card:
        # 1) Giá giảm từ ProductDetail (nếu có)
        # 2) Giá gốc ProductDetail
        # 3) Giá nhỏ nhất của biến thể
        # 4) Product.price (fallback cuối)
        products_list = products_list.annotate(
            _variant_min_price=models.Min('detail__variants__price'),
            _discounted_price=models.Case(
                models.When(
                    detail__original_price__gt=0,
                    detail__discount_percent__gt=0,
                    then=models.F('detail__original_price') - (models.F('detail__original_price') * models.F('detail__discount_percent') / 100)
                ),
                models.When(
                    detail__original_price__gt=0,
                    then=models.F('detail__original_price')
                ),
                models.When(
                    _variant_min_price__gt=0,
                    then=models.F('_variant_min_price')
                ),
                default=models.F('price'),
                output_field=models.DecimalField(max_digits=15, decimal_places=0)
            )
        )
        if max_p is not None:
            products_list = products_list.filter(_discounted_price__gte=min_p, _discounted_price__lt=max_p)
        else:
            products_list = products_list.filter(_discounted_price__gte=min_p)

    # Sắp xếp
    from django.db.models import Case, When, IntegerField
    products_list = products_list.annotate(
        stock_order=Case(
            When(stock__gt=0, then=0),
            default=1,
            output_field=IntegerField(),
        )
    )

    if selected_sort_price == 'asc':
        products_list = products_list.order_by('stock_order', 'price')
    elif selected_sort_price == 'desc':
        products_list = products_list.order_by('stock_order', '-price')
    else:
        # Default: Random display giống hàm home
        import random
        import datetime
        
        # Dùng 30 phút làm seed để random consistent mỗi 30 phút
        now = datetime.datetime.now()
        time_slot = (now.hour * 60 + now.minute) // 30
        seed_str = f"{now.date()}_{time_slot}"
        random.seed(seed_str)
        
        in_stock_ids = list(products_list.filter(stock__gt=0).values_list('id', flat=True))
        out_of_stock_ids = list(products_list.filter(stock__lte=0).values_list('id', flat=True))
        
        random.shuffle(in_stock_ids)
        random.shuffle(out_of_stock_ids)
        
        all_ids = in_stock_ids + out_of_stock_ids
        
        if all_ids:
            preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(all_ids)], output_field=IntegerField())
            products_list = products_list.filter(id__in=all_ids).annotate(preserved_pos=preserved_order).order_by('preserved_pos')
        else:
            products_list = products_list.order_by('stock_order')

    # Phân trang - 15 sản phẩm mỗi trang
    paginator = Paginator(products_list, 15)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Lấy wishlist của user
    wishlist_product_ids = []
    if request.user and request.user.is_authenticated:
        wishlist = Wishlist.get_or_create_for_user(request.user)
        if wishlist:
            wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))

    # Render HTML cho danh sách sản phẩm
    products_html = render_to_string('store/products_fragment.html', {
        'products': products,
        'wishlist_product_ids': wishlist_product_ids,
    })

    # Render HTML cho phân trang
    pagination_html = render_to_string('store/pagination_fragment.html', {
        'page_obj': products,
        'paginator': paginator,
    })

    return JsonResponse({
        'success': True,
        'products_html': products_html,
        'pagination_html': pagination_html,
        'total_products': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': products.number,
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


def _newsletter_parse_contact(contact):
    """Trả về (email, phone) — một trong hai có giá trị, cái kia None."""
    contact = (contact or '').strip()
    if not contact:
        return None, None
    if '@' in contact:
        return contact, None
    phone = ''.join(filter(str.isdigit, contact))
    if len(phone) >= 10:
        return None, phone
    return None, None


@require_POST
def newsletter_subscribe(request):
    """Đăng ký nhận tư vấn & ưu đãi. User đăng nhập: lưu user_id + email/phone; Guest: lưu email/phone. Gửi Telegram."""
    from store.models import Newsletter
    from store.telegram_utils import notify_newsletter_subscribe

    contact = request.POST.get('contact', '').strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def err(msg):
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect('store:home')

    def ok(msg):
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
        return redirect('store:home')

    # --- User đã đăng nhập: dùng thông tin user, có thể ghi đè bằng contact nếu nhập ---
    if request.user.is_authenticated:
        user = request.user
        # Tránh đăng ký trùng: mỗi user chỉ một bản ghi active
        existing = Newsletter.objects.filter(user=user, is_active=True).first()
        if existing:
            return err('Bạn đã đăng ký nhận tin rồi.')

        email, phone = _newsletter_parse_contact(contact)
        # Nếu guest không nhập, lấy từ user
        if not email and not phone:
            email = getattr(user, 'email', None) or ''
            if email:
                email = email.strip()
            # Số điện thoại từ profile nếu có
            phone = getattr(user, 'phone', None) or ''
            if isinstance(phone, str):
                phone = ''.join(filter(str.isdigit, phone)) or None
            else:
                phone = None
        if not email and not phone:
            return err('Vui lòng nhập email hoặc số điện thoại.')

        newsletter = Newsletter(user=user, email=email or None, phone=phone or None)
        newsletter.save()

        created_str = timezone.localtime(newsletter.created_at).strftime('%d/%m/%Y %H:%M')
        notify_newsletter_subscribe(True, user.get_full_name() or user.email or str(user), created_str)
        return ok('Đăng ký thành công! Cảm ơn bạn đã quan tâm.')

    # --- Guest ---
    if not contact:
        return err('Vui lòng nhập email hoặc số điện thoại.')

    email, phone = _newsletter_parse_contact(contact)
    if not email and not phone:
        return err('Email hoặc số điện thoại không hợp lệ.')

    if email and Newsletter.objects.filter(email=email, is_active=True).exists():
        return err('Email này đã được đăng ký.')
    if phone and Newsletter.objects.filter(phone=phone, is_active=True).exists():
        return err('Số điện thoại này đã được đăng ký.')

    newsletter = Newsletter(email=email, phone=phone)
    newsletter.save()

    created_str = timezone.localtime(newsletter.created_at).strftime('%d/%m/%Y %H:%M')
    display = email or phone
    notify_newsletter_subscribe(False, display, created_str)
    return ok('Đăng ký thành công! Cảm ơn bạn đã quan tâm.')
