from decimal import Decimal
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.text import slugify


class CustomUserManager(UserManager):
    """Custom Manager cho CustomUser - không cần username"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email là bắt buộc')
        email = self.normalize_email(email)
        
        # Loại bỏ username khỏi extra_fields nếu có
        extra_fields.pop('username', None)
        
        # Tự động tạo username từ email nếu không được cung cấp
        # Lấy phần trước @ của email
        username = email.split('@')[0]
        extra_fields['username'] = username[:150]  # Django limit
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # Loại bỏ username
        extra_fields.pop('username', None)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser phải có is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser phải có is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom User Model cho QHUN22
    - Bỏ username, chỉ dùng email để đăng nhập
    - Thêm số điện thoại
    - Sử dụng last_name làm Họ tên đầy đủ
    - Hỗ trợ cả đăng ký thường và OAuth (Google)
    """
    username = models.CharField(max_length=150, null=True, blank=True)  # Giữ field cho allauth tương thích
    email = models.EmailField(unique=True)  # Email là unique identifier
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Số điện thoại')
    
    # Sử dụng last_name làm tên đầy đủ (Họ tên)
    # Bỏ first_name
    
    # Trường để đánh dấu nguồn đăng ký
    is_oauth_user = models.BooleanField(default=False, verbose_name='Người dùng OAuth')
    
    # Trường xác thực Student - Teacher
    is_student_verified = models.BooleanField(default=False, verbose_name='Đã xác thực Student')
    verified_student_email = models.EmailField(blank=True, default='', verbose_name='Email Student đã xác thực')
    student_verified_at = models.DateTimeField(null=True, blank=True, verbose_name='Ngày xác thực Student')
    is_teacher_verified = models.BooleanField(default=False, verbose_name='Đã xác thực Teacher')
    verified_teacher_email = models.EmailField(blank=True, default='', verbose_name='Email Teacher đã xác thực')
    teacher_verified_at = models.DateTimeField(null=True, blank=True, verbose_name='Ngày xác thực Teacher')
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'  # Dùng email để đăng nhập
    REQUIRED_FIELDS = []  # Không yêu cầu fields khác khi tạo superuser
    
    class Meta:
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """
        Lấy tên đầy đủ của người dùng
        - Nếu có last_name thì dùng last_name (cả regular và OAuth users)
        - Nếu không có thì dùng email (bỏ @domain)
        """
        if self.last_name:
            return self.last_name.strip()
        # Fallback: lấy phần trước @ của email
        if self.email:
            return self.email.split('@')[0]
        return 'Người dùng'
    
    def get_short_name(self):
        """Lấy tên ngắn (dùng cho chào hỏi)"""
        full_name = self.get_full_name()
        # Nếu là tên đầy đủ có nhiều từ, lấy từ cuối cùng (họ)
        # Nếu chỉ là một từ, dùng từ đó
        names = full_name.split()
        return names[-1] if names else 'Khách'


class Category(models.Model):
    """Danh mục sản phẩm"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Tên danh mục')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Mô tả')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    """Hãng sản phẩm (Apple, Samsung, Xiaomi, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Tên hãng')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Mô tả')
    logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name='Logo')
    is_active = models.BooleanField(default=True, verbose_name='Hoạt động')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Hãng sản phẩm'
        verbose_name_plural = 'Hãng sản phẩm'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class HangingProduct(models.Model):
    """Sản phẩm treo (hiển trang chủ thị trên)"""
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='hanging_products', verbose_name='Hãng sản xuất', null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='hanging_products', verbose_name='Sản phẩm liên kết')
    name = models.CharField(max_length=200, verbose_name='Tên sản phẩm')
    image_url = models.URLField(blank=True, null=True, verbose_name='URL Ảnh bên ngoài')
    image_local = models.ImageField(upload_to='hanging_products/', blank=True, null=True, verbose_name='Ảnh sản phẩm')
    original_price = models.DecimalField(max_digits=15, decimal_places=0, verbose_name='Giá gốc (VNĐ)')
    discount_percent = models.PositiveIntegerField(default=0, verbose_name='% Giảm giá')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='Số lượng trong kho')
    installment_0_percent = models.BooleanField(default=False, verbose_name='Trả góp 0%')
    is_active = models.BooleanField(default=True, verbose_name='Hiển thị')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sản phẩm treo'
        verbose_name_plural = 'Sản phẩm treo'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProductDetail(models.Model):
    """Chi tiết sản phẩm - giá, SKU, biến thể (màu, dung lượng)"""
    product = models.OneToOneField('Product', on_delete=models.CASCADE, related_name='detail', verbose_name='Sản phẩm')
    
    # Giá
    original_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá gốc (VNĐ)')
    discount_percent = models.PositiveIntegerField(default=0, verbose_name='% Giảm giá')
    
    @property
    def discounted_price(self):
        """Giá sau giảm - tính từ giá gốc và % giảm"""
        if self.original_price and self.discount_percent > 0:
            discounted = self.original_price - (self.original_price * self.discount_percent / 100)
            # Round to nearest 5000
            if discounted >= 5000:
                discounted = round(discounted / 5000) * 5000
            return int(discounted)
        # If no discount, get min variant price
        min_price = self.get_min_price()
        if min_price > 0:
            return min_price
        return self.original_price if self.original_price else 0

    @property
    def summary_original_price(self):
        """
        Giá gốc hiển thị trên dashboard:
        - Nếu đã nhập giá gốc tổng thì dùng luôn
        - Nếu không, lấy original_price nhỏ nhất từ các biến thể
        """
        if self.original_price:
            return int(self.original_price)
        agg = self.variants.aggregate(models.Min('original_price'))
        value = agg.get('original_price__min') if agg else None
        return int(value) if value else 0

    @property
    def summary_discount_percent(self):
        """
        % giảm giá hiển thị trên dashboard:
        - Nếu đã nhập % giảm tổng thì dùng luôn
        - Nếu không, lấy % giảm của biến thể có giá sau giảm nhỏ nhất
        """
        if self.discount_percent:
            return int(self.discount_percent)
        cheapest = self.variants.order_by('price').first()
        return int(cheapest.discount_percent) if cheapest and cheapest.discount_percent else 0
    
    def get_min_price(self):
        """Lấy giá nhỏ nhất từ các biến thể"""
        min_price = self.variants.aggregate(models.Min('price'))['price__min']
        return min_price if min_price else 0
    
    # SKU tổng
    sku = models.CharField(max_length=100, blank=True, verbose_name='SKU chung')
    
    # YouTube Video ID
    youtube_id = models.CharField(max_length=50, blank=True, default='', verbose_name='YouTube Video ID')
    
    # Mô tả
    description = models.TextField(blank=True, verbose_name='Mô tả')
    
    is_active = models.BooleanField(default=True, verbose_name='Hiển thị')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chi tiết sản phẩm'
        verbose_name_plural = 'Chi tiết sản phẩm'

    def __str__(self):
        return f"Chi tiết: {self.product.name}"


class ProductVariant(models.Model):
    """Biến thể sản phẩm theo màu sắc và dung lượng"""
    detail = models.ForeignKey(ProductDetail, on_delete=models.CASCADE, related_name='variants', verbose_name='Chi tiết sản phẩm')
    
    # Thông tin biến thể
    color_name = models.CharField(max_length=50, verbose_name='Tên màu')
    color_hex = models.CharField(max_length=7, blank=True, verbose_name='Mã màu (hex)')
    storage = models.CharField(max_length=20, verbose_name='Dung lượng')  # ví dụ: 64GB, 128GB
    
    # Giá và SKU
    original_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá gốc (VNĐ)')
    discount_percent = models.PositiveIntegerField(default=0, verbose_name='% Giảm giá')
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá sau giảm (VNĐ)')
    sku = models.CharField(max_length=100, blank=True, verbose_name='SKU biến thể')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='Số lượng trong kho')
    
    is_active = models.BooleanField(default=True, verbose_name='Còn hàng')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Biến thể sản phẩm'
        verbose_name_plural = 'Biến thể sản phẩm'
        unique_together = ['detail', 'color_name', 'storage']

    def __str__(self):
        return f"{self.detail.product.name} - {self.color_name} - {self.storage}"


class ProductSpecification(models.Model):
    """Thông số kỹ thuật sản phẩm - lưu JSON"""
    detail = models.OneToOneField(ProductDetail, on_delete=models.CASCADE, related_name='specification', verbose_name='Chi tiết sản phẩm')
    
    # Lưu JSON dạng text
    spec_json = models.JSONField(default=dict, blank=True, verbose_name='Thông số kỹ thuật (JSON)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Thông số kỹ thuật sản phẩm'
        verbose_name_plural = 'Thông số kỹ thuật sản phẩm'
    
    def __str__(self):
        return f"Specs: {self.detail.product.name}"


class ProductImage(models.Model):
    """Hình ảnh sản phẩm"""
    IMAGE_TYPES = [
        ('cover', 'Ảnh đại diện'),
        ('marketing', 'Ảnh marketing/banner'),
        ('variant_thumbnail', 'Ảnh màu (thumbnail)'),
        ('variant_main', 'Ảnh màu (chính)'),
        ('variant_gallery', 'Ảnh màu (gallery)'),
        ('variant_detail', 'Ảnh màu (chi tiết)'),
    ]
    
    detail = models.ForeignKey(ProductDetail, on_delete=models.CASCADE, related_name='images', verbose_name='Chi tiết sản phẩm', null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images', verbose_name='Biến thể', null=True, blank=True)
    
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='cover', verbose_name='Loại ảnh')
    image = models.ImageField(upload_to='products/', verbose_name='Ảnh')
    order = models.PositiveIntegerField(default=0, verbose_name='Thứ tự')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hình ảnh sản phẩm'
        verbose_name_plural = 'Hình ảnh sản phẩm'
        ordering = ['order']

    def __str__(self):
        return f"{self.image_type} - {self.detail.product.name if self.detail else self.variant.detail.product.name}"


def image_folder_upload_path(instance, filename):
    """
    Đường dẫn lưu ảnh thư mục riêng:
    media/products/YYYY/MM/<folder_slug>/filename
    """
    from datetime import datetime
    import os

    now = datetime.now()
    year = now.year
    month = now.strftime('%m')
    folder_slug = instance.folder.slug
    return os.path.join('products', str(year), month, folder_slug, filename)


class ImageFolder(models.Model):
    """Thư mục ảnh riêng để quản lý ảnh sản phẩm theo thư mục"""
    name = models.CharField(max_length=150, verbose_name='Thư mục ảnh')
    slug = models.SlugField(max_length=150, verbose_name='Slug thư mục')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True, related_name='image_folders', verbose_name='Hãng')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=True, blank=True, related_name='image_folders', verbose_name='Sản phẩm')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'store_imagefolder'
        verbose_name = 'Thư mục ảnh'
        verbose_name_plural = 'Thư mục ảnh'
        ordering = ['-created_at']
        unique_together = ['name', 'brand', 'product']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FolderColorImage(models.Model):
    """
    Ảnh màu theo thư mục:
    - Mỗi bản ghi là 1 ảnh thuộc 1 màu + SKU trong 1 thư mục
    """
    folder = models.ForeignKey(ImageFolder, on_delete=models.CASCADE, related_name='images', verbose_name='Thư mục ảnh')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='folder_images', verbose_name='Hãng')
    sku = models.CharField(max_length=100, verbose_name='SKU')
    color_name = models.CharField(max_length=100, verbose_name='Màu sản phẩm')
    image = models.ImageField(upload_to=image_folder_upload_path, verbose_name='Ảnh')
    order = models.PositiveIntegerField(default=0, verbose_name='Thứ tự')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'store_foldercolorimage'
        verbose_name = 'Ảnh màu theo thư mục'
        verbose_name_plural = 'Ảnh màu theo thư mục'
        ordering = ['folder__name', 'color_name', 'order']

    def __str__(self):
        return f"{self.folder.name} - {self.color_name} - {self.sku}"


class Product(models.Model):
    """Sản phẩm điện thoại"""
    name = models.CharField(max_length=200, verbose_name='Tên sản phẩm')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Slug')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Hãng')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Danh mục')
    description = models.TextField(blank=True, default='', verbose_name='Mô tả')
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá (VNĐ)')
    original_price = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True, verbose_name='Giá gốc')
    discount_percent = models.PositiveIntegerField(default=0, verbose_name='% Giảm giá')
    image = models.ImageField(upload_to='products/%Y/%m/', blank=True, null=True, verbose_name='Hình ảnh')
    stock = models.PositiveIntegerField(default=0, verbose_name='Số lượng trong kho')
    is_featured = models.BooleanField(default=False, verbose_name='Sản phẩm nổi bật')
    is_active = models.BooleanField(default=True, verbose_name='Hiển thị')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Sản phẩm'
        verbose_name_plural = 'Sản phẩm'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_discount_percent(self):
        """Tính phần trăm giảm giá"""
        if self.original_price and self.original_price > self.price:
            return int((self.original_price - self.price) / self.original_price * 100)
        return 0


class Wishlist(models.Model):
    """
    Danh sách yêu thích của người dùng
    Lưu trữ các sản phẩm mà người dùng đã thích (trái tim đỏ)
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlists', verbose_name='Người dùng')
    products = models.ManyToManyField(Product, related_name='wishlisted_by', verbose_name='Sản phẩm yêu thích')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        db_table = 'store_wishlist'
        verbose_name = 'Danh sách yêu thích'
        verbose_name_plural = 'Danh sách yêu thích'

    def __str__(self):
        return f"Wishlist của {self.user.email}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Lấy hoặc tạo wishlist cho user"""
        if not user.is_authenticated:
            return None
        wishlist, created = cls.objects.get_or_create(user=user)
        return wishlist

    def add_product(self, product):
        """Thêm sản phẩm vào wishlist"""
        if not self.products.filter(id=product.id).exists():
            self.products.add(product)
            return True
        return False

    def remove_product(self, product):
        """Xóa sản phẩm khỏi wishlist"""
        if self.products.filter(id=product.id).exists():
            self.products.remove(product)
            return True
        return False

    def has_product(self, product):
        """Kiểm tra sản phẩm có trong wishlist không"""
        return self.products.filter(id=product.id).exists()


class Cart(models.Model):
    """
    Giỏ hàng của người dùng
    Lưu trữ các sản phẩm mà người dùng đã thêm vào giỏ hàng
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='carts', verbose_name='Người dùng')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        db_table = 'store_cart'
        verbose_name = 'Giỏ hàng'
        verbose_name_plural = 'Giỏ hàng'

    def __str__(self):
        return f"Giỏ hàng của {self.user.email}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Lấy hoặc tạo giỏ hàng cho user"""
        if not user.is_authenticated:
            return None
        cart, created = cls.objects.get_or_create(user=user)
        return cart

    def get_total_price(self):
        """Tính tổng tiền giỏ hàng"""
        total = 0
        for item in self.items.all():
            total += item.get_total_price()
        return total

    def get_total_items(self):
        """Tính tổng số sản phẩm trong giỏ"""
        total = 0
        for item in self.items.all():
            total += item.quantity
        return total


class CartItem(models.Model):
    """
    Item trong giỏ hàng - lưu sản phẩm, màu, số lượng và giá tại thời điểm thêm
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='Giỏ hàng')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items', verbose_name='Sản phẩm')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Số lượng')
    color_name = models.CharField(max_length=50, blank=True, verbose_name='Tên màu')
    color_code = models.CharField(max_length=20, blank=True, verbose_name='Mã màu')
    storage = models.CharField(max_length=20, blank=True, verbose_name='Dung lượng')
    price_at_add = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá khi thêm')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày thêm')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        db_table = 'store_cartitem'
        verbose_name = 'Item giỏ hàng'
        verbose_name_plural = 'Items giỏ hàng'
        unique_together = ['cart', 'product', 'color_name', 'storage']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self):
        """Tính thành tiền = giá x số lượng"""
        return self.price_at_add * self.quantity


class SiteVisit(models.Model):
    """
    Model theo dõi lượt truy cập website
    Mỗi lần vào trang chủ (click logo hoặc refresh) tính là 1 lượt
    """
    visit_time = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian truy cập')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Địa chỉ IP')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits', verbose_name='Người dùng')
    
    class Meta:
        verbose_name = 'Lượt truy cập'
        verbose_name_plural = 'Lượt truy cập'
        ordering = ['-visit_time']
    
    def __str__(self):
        return f"Visit at {self.visit_time.strftime('%Y-%m-%d %H:%M')}"


class Order(models.Model):
    """
    Model đơn hàng để theo dõi doanh thu
    """
    STATUS_CHOICES = [
        ('awaiting_payment', 'Chờ thanh toán'),
        ('pending', 'Đã đặt hàng'),
        ('processing', 'Đang xử lý'),
        ('shipped', 'Đang giao'),
        ('delivered', 'Đã giao hàng'),
        ('cancelled', 'Hủy đơn'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'COD'),
        ('vietqr', 'VietQR'),
        ('vnpay', 'VNPay'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders', verbose_name='Khách hàng')
    order_code = models.CharField(max_length=20, unique=True, verbose_name='Mã đơn hàng')
    total_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Tổng tiền')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod', verbose_name='Phương thức TT')
    vnpay_order_code = models.CharField(max_length=50, blank=True, null=True, verbose_name='Mã VNPay')
    coupon_code = models.CharField(max_length=50, blank=True, default='', verbose_name='Mã giảm giá')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Số tiền giảm')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Trạng thái')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    
    # Thông tin hoàn tiền
    refund_account = models.CharField(max_length=50, blank=True, null=True, verbose_name='Số tài khoản hoàn tiền')
    refund_bank = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ngân hàng hoàn tiền')
    REFUND_STATUS_CHOICES = [
        ('', 'Chưa yêu cầu'),
        ('pending', 'Chờ hoàn tiền'),
        ('completed', 'Đã hoàn tiền'),
    ]
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, blank=True, default='', verbose_name='Trạng thái hoàn tiền')
    
    class Meta:
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_code}"


class OrderItem(models.Model):
    """
    Sản phẩm trong đơn hàng - snapshot tại thời điểm mua
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Đơn hàng')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name='Sản phẩm')
    product_name = models.CharField(max_length=255, verbose_name='Tên sản phẩm')
    color_name = models.CharField(max_length=50, blank=True, verbose_name='Màu')
    storage = models.CharField(max_length=20, blank=True, verbose_name='Dung lượng')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Số lượng')
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Đơn giá')
    thumbnail = models.CharField(max_length=500, blank=True, verbose_name='Ảnh thumbnail URL')

    class Meta:
        verbose_name = 'Sản phẩm đơn hàng'
        verbose_name_plural = 'Sản phẩm đơn hàng'

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    def get_total_price(self):
        return self.price * self.quantity


class Banner(models.Model):
    """
    Model lưu trữ ảnh banner với ID riêng
    """
    banner_id = models.CharField(max_length=50, verbose_name='ID Banner')
    image = models.ImageField(upload_to='banner/%Y/%m/', verbose_name='Ảnh Banner')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    
    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Banner'
        ordering = ['banner_id', '-created_at']
    
    def __str__(self):
        return f"Banner {self.banner_id}"


class Address(models.Model):
    """
    Sổ địa chỉ giao hàng của người dùng
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses', verbose_name='Người dùng')
    full_name = models.CharField(max_length=255, verbose_name='Họ tên')
    phone = models.CharField(max_length=20, verbose_name='Số điện thoại')
    province_code = models.CharField(max_length=10, verbose_name='Mã tỉnh/thành')
    province_name = models.CharField(max_length=100, verbose_name='Tỉnh/Thành phố')
    district_code = models.CharField(max_length=10, verbose_name='Mã quận/huyện')
    district_name = models.CharField(max_length=100, verbose_name='Quận/Huyện')
    ward_code = models.CharField(max_length=10, verbose_name='Mã phường/xã')
    ward_name = models.CharField(max_length=100, verbose_name='Phường/Xã')
    detail = models.CharField(max_length=500, verbose_name='Địa chỉ chi tiết')
    is_default = models.BooleanField(default=False, verbose_name='Địa chỉ mặc định')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        verbose_name = 'Địa chỉ'
        verbose_name_plural = 'Địa chỉ'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.detail}, {self.ward_name}, {self.district_name}, {self.province_name}"


class PasswordHistory(models.Model):
    """
    Lưu lịch sử đổi mật khẩu của người dùng
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='password_history', verbose_name='Người dùng')
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian đổi')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='Địa chỉ IP')
    user_agent = models.CharField(max_length=500, blank=True, verbose_name='Trình duyệt')

    class Meta:
        verbose_name = 'Lịch sử đổi mật khẩu'
        verbose_name_plural = 'Lịch sử đổi mật khẩu'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.user.email} - {self.changed_at.strftime('%d/%m/%Y %H:%M')}"


class PendingQRPayment(models.Model):
    """
    QR chuyển khoản chờ duyệt.
    Khi khách chọn VietQR trên checkout, 1 bản ghi được tạo ở đây.
    Admin duyệt / hủy trên dashboard.
    Sau 15 phút không duyệt → tự xóa (cleanup khi load danh sách).
    """
    STATUS_CHOICES = [
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancelled', 'Đã hủy'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pending_qr_payments', verbose_name='Khách hàng')
    amount = models.DecimalField(max_digits=15, decimal_places=0, verbose_name='Số tiền')
    transfer_code = models.CharField(max_length=20, unique=True, verbose_name='Nội dung CK')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Trạng thái')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo QR')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')

    class Meta:
        verbose_name = 'QR chờ duyệt'
        verbose_name_plural = 'QR chờ duyệt'
        ordering = ['-created_at']

    def __str__(self):
        return f"QR {self.transfer_code} - {self.amount}"

    @staticmethod
    def cleanup_expired():
        """Xóa tất cả QR pending quá 15 phút"""
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=15)
        PendingQRPayment.objects.filter(status='pending', created_at__lt=cutoff).delete()

    @property
    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.status == 'pending' and self.created_at < timezone.now() - timedelta(minutes=15)

    def qr_url(self):
        """Build VietQR URL"""
        import urllib.parse
        bank_id = 'TCB'
        account_no = '22100588888888'
        account_name = 'TRUONG QUANG HUY'
        return (
            f'https://img.vietqr.io/image/{bank_id}-{account_no}-vietqr_net_2.jpg'
            f'?amount={int(self.amount)}'
            f'&addInfo={urllib.parse.quote(self.transfer_code)}'
            f'&accountName={urllib.parse.quote(account_name)}'
        )


class VNPayPayment(models.Model):
    """
    Model lưu trữ thông tin thanh toán VNPay
    """
    STATUS_CHOICES = [
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('failed', 'Thất bại'),
        ('cancelled', 'Đã hủy'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='vnpay_payments', verbose_name='Khách hàng')
    amount = models.DecimalField(max_digits=15, decimal_places=0, verbose_name='Số tiền')
    order_code = models.CharField(max_length=50, unique=True, verbose_name='Mã đơn hàng VNPay')
    transaction_no = models.CharField(max_length=50, blank=True, null=True, verbose_name='Mã giao dịch VNPay')
    transaction_status = models.CharField(max_length=20, blank=True, null=True, verbose_name='Mã trạng thái VNPay')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Trạng thái')
    response_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='Response code VNPay')
    response_message = models.CharField(max_length=255, blank=True, null=True, verbose_name='Response message VNPay')
    pay_method = models.CharField(max_length=50, blank=True, null=True, verbose_name='Phương thức thanh toán')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Ngày cập nhật')
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name='Thời gian thanh toán')

    class Meta:
        verbose_name = 'Thanh toán VNPay'
        verbose_name_plural = 'Thanh toán VNPay'
        ordering = ['-created_at']

    def __str__(self):
        return f"VNPay {self.order_code} - {self.amount}đ - {self.status}"


class ProductReview(models.Model):
    """Đánh giá sản phẩm - chỉ user đã mua thành công mới được đánh giá, mỗi user 1 lần/sản phẩm"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews', verbose_name='Người dùng')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Sản phẩm')
    rating = models.PositiveIntegerField(verbose_name='Số sao (1-5)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày đánh giá')

    class Meta:
        verbose_name = 'Đánh giá sản phẩm'
        verbose_name_plural = 'Đánh giá sản phẩm'
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} - {self.rating} sao"


class ProductContent(models.Model):
    """
    Model lưu trữ nội dung sản phẩm theo hãng và sản phẩm
    """
    brand = models.ForeignKey('store.Brand', on_delete=models.CASCADE, related_name='product_contents', verbose_name='Hãng')
    product = models.ForeignKey('store.Product', on_delete=models.CASCADE, related_name='product_contents', verbose_name='Sản phẩm')
    content_text = models.TextField(blank=True, verbose_name='Nội dung text')
    image = models.ImageField(upload_to='product_content/%Y/%m/', blank=True, verbose_name='Ảnh minh họa')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    
    class Meta:
        verbose_name = 'Nội dung sản phẩm'
        verbose_name_plural = 'Nội dung sản phẩm'
        ordering = ['-created_at']
        unique_together = ['brand', 'product']
    
    def __str__(self):
        return f"Nội dung - {self.product.name}"


class Coupon(models.Model):
    """Mã giảm giá"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Giảm %'),
        ('fixed', 'Giảm số tiền'),
    ]
    TARGET_TYPE_CHOICES = [
        ('all', 'Mọi người'),
        ('single', '1 người'),
    ]
    
    name = models.CharField(max_length=255, default='', verbose_name='Tên chương trình')
    code = models.CharField(max_length=50, unique=True, verbose_name='Tên mã giảm')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage', verbose_name='Kiểu giảm giá')
    discount_value = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Giá trị giảm')
    target_type = models.CharField(max_length=10, choices=TARGET_TYPE_CHOICES, default='all', verbose_name='Đối tượng')
    target_email = models.EmailField(blank=True, default='', verbose_name='Email áp dụng')
    max_products = models.PositiveIntegerField(default=0, verbose_name='Giới hạn sản phẩm', help_text='Số SP tối đa được áp dụng. 0 = không giới hạn')
    min_order_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='Đơn tối thiểu')
    usage_limit = models.PositiveIntegerField(default=0, verbose_name='Giới hạn lượt dùng (mỗi người)', help_text='Số lần mỗi người dùng được tối đa. 0 = không giới hạn')
    used_count = models.PositiveIntegerField(default=0, verbose_name='Đã sử dụng')
    expire_days = models.PositiveIntegerField(default=30, verbose_name='Hạn sử dụng (ngày)')
    is_active = models.BooleanField(default=True, verbose_name='Còn sử dụng')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    expire_at = models.DateTimeField(verbose_name='Ngày hết hạn', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Mã giảm giá'
        verbose_name_plural = 'Mã giảm giá'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        if not self.expire_at:
            from django.utils import timezone
            import datetime
            self.expire_at = timezone.now() + datetime.timedelta(days=self.expire_days)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        from django.utils import timezone
        if not self.expire_at:
            return True
        return timezone.now() > self.expire_at
    
    def is_valid(self):
        if not self.is_active:
            return False
        if self.is_expired():
            return False
        # Lưu ý: usage_limit là giới hạn per-user, được kiểm tra riêng qua CouponUsage
        return True
    
    def calculate_discount(self, order_total):
        if order_total < self.min_order_amount:
            return Decimal('0')
        if self.discount_type == 'percentage':
            discount = order_total * self.discount_value / Decimal('100')
        else:
            discount = self.discount_value
        return min(discount, order_total)


class CouponUsage(models.Model):
    """
    Lưu lịch sử dụng voucher theo từng user.
    Đảm bảo kiểm tra giới hạn per-user (usage_limit).
    """
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages', verbose_name='Mã giảm')
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='coupon_usages', verbose_name='Người dùng')
    used_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời điểm dùng')

    class Meta:
        verbose_name = 'Lịch sử dụng voucher'
        verbose_name_plural = 'Lịch sử dụng voucher'
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.user} dùng {self.coupon.code}"


class EmailVerification(models.Model):
    """Model lưu mã xác thực email .edu"""
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField(verbose_name='Email xác thực')
    code = models.CharField(max_length=6, verbose_name='Mã xác thực')
    is_verified = models.BooleanField(default=False, verbose_name='Đã xác thực')
    verification_type = models.CharField(max_length=20, choices=[
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ], verbose_name='Loại xác thực')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')
    expires_at = models.DateTimeField(verbose_name='Thời gian hết hạn')
    
    class Meta:
        verbose_name = 'Xác thực email'
        verbose_name_plural = 'Xác thực email'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {self.verification_type}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            import datetime
            self.expires_at = timezone.now() + datetime.timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        from django.utils import timezone
        return not self.is_verified and timezone.now() < self.expires_at
