# PHÂN TÍCH HỆ THỐNG QHUN22 - TÀI LIỆU KỸ THUẬT

## MỤC LỤC

1. [Giới thiệu hệ thống](#1-giới-thiệu-hệ-thống)
2. [Kiến trúc tổng quan](#2-kiến-trúc-tổng-quan)
3. [Phân tích cơ sở dữ liệu](#3-phân-tích-cơ-sở-dữ-liệu)
4. [Phân tích chức năng](#4-phân-tích-chức-năng)
5. [Phân tích thuật toán](#5-phân-tích-thuật-toán)
6. [Phân tích thư viện và dependency](#6-phân-tích-thư-viện-và-dependency)
7. [Hướng dẫn cài đặt và chạy](#7-hướng-dẫn-cài-đặt-và-chạy)
8. [Phân tích kiến trúc](#8-phân-tích-kiến-trúc)
9. [Kết luận](#9-kết-luận)

---

## 1. GIỚI THIỆU HỆ THỐNG

### 1.1. Tổng quan

**QHUN22** là một trang thương mại điện tử chuyên bán điện thoại di động và phụ kiện, được xây dựng trên nền tảng **Django 4.2.11**. Hệ thống cung cấp đầy đủ các tính năng cần thiết cho một cửa hàng trực tuyến:

- Quản lý sản phẩm đa dạng (iPhone, Samsung, Xiaomi,...)
- Giỏ hàng và thanh toán trực tuyến
- Tích hợp nhiều phương thức thanh toán (COD, VietQR, VNPay)
- Chatbot AI hỗ trợ khách hàng 24/7
- Quản trị đơn hàng và kho hàng
- Đánh giá sản phẩm
- Mã giảm giá (Coupon)
- Theo dõi lượt truy cập

### 1.2. Thông tin kỹ thuật

| Thông số | Giá trị |
|----------|---------|
| Framework | Django 4.2.11 |
| Database | SQLite (db.sqlite3) |
| Python | 3.x |
| Template Engine | Django Templates |
| Authentication | django-allauth + Custom Email Backend |
| Payment Gateway | VNPay, VietQR, COD |

---

## 2. KIẾN TRÚC TỔNG QUAN

### 2.1. Cấu trúc thư mục

```
qhun22/
├── config/                    # Cấu hình Django
│   ├── __init__.py
│   ├── settings.py           # Cấu hình chính
│   ├── urls.py               # URL routing chính
│   └── wsgi.py               # WSGI entry point
├── store/                    # Ứng dụng chính (main app)
│   ├── admin.py             # Cấu hình Admin
│   ├── backends.py          # Custom authentication backend
│   ├── chatbot_service.py   # AI Chatbot service
│   ├── claude_service.py    # Claude API integration
│   ├── context_processors.py # Context processors
│   ├── models.py            # Database models
│   ├── urls.py              # URL routing cho store
│   ├── views.py             # Views/Controllers
│   ├── admin.py             # Django Admin
│   ├── allauth_adapter.py   # AllAuth customization
│   ├── vnpay_utils.py      # VNPay utilities
│   ├── telegram_utils.py   # Telegram notifications
│   ├── templatetags/       # Custom template tags
│   └── management/          # Management commands
├── templates/               # HTML templates
│   ├── base.html
│   └── store/              # Store templates
├── static/                 # Static files (CSS, JS, images)
├── media/                  # Uploaded files
│   ├── banner/
│   └── products/
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── db.sqlite3             # SQLite database
```

### 2.2. Luồng khởi động ứng dụng

```
1. python manage.py runserver
   ↓
2. Load config/settings.py
   - Load .env variables
   - Setup DATABASES, INSTALLED_APPS, MIDDLEWARE
   ↓
3. Setup URL routing (config/urls.py)
   - /admin/ → Django Admin
   - /accounts/ → django-allauth
   - /vnpay/ → VNPay payment callbacks
   - / → store.urls
   ↓
4. Load store app
   - Register models
   - Load template tags
   - Setup context processors
   ↓
5. Ready to serve requests
```

### 2.3. Entry Points

| File | Mô tả |
|------|-------|
| `manage.py` | Entry point chính, chạy Django commands |
| `config/wsgi.py` | WSGI application cho production |
| `config/settings.py` | Cấu hình toàn bộ hệ thống |

---

## 3. PHÂN TÍCH CƠ SỞ DỮ LIỆU

### 3.1. Danh sách Models

| Model | Mô tả | Primary Key |
|-------|-------|-------------|
| `CustomUser` | Người dùng (mở rộng AbstractUser) | id |
| `Category` | Danh mục sản phẩm | id |
| `Brand` | Hãng sản xuất (Apple, Samsung,...) | id |
| `Product` | Sản phẩm chính | id |
| `ProductDetail` | Chi tiết sản phẩm (giá, SKU) | id |
| `ProductVariant` | Biến thể (màu, dung lượng) | id |
| `ProductSpecification` | Thông số kỹ thuật (JSON) | id |
| `ProductImage` | Hình ảnh sản phẩm | id |
| `ImageFolder` | Thư mục ảnh | id |
| `FolderColorImage` | Ảnh màu theo thư mục | id |
| `HangingProduct` | Sản phẩm treo trang chủ | id |
| `Cart` | Giỏ hàng | id |
| `CartItem` | Item trong giỏ hàng | id |
| `Wishlist` | Danh sách yêu thích | id |
| `Order` | Đơn hàng | id |
| `OrderItem` | Sản phẩm trong đơn hàng | id |
| `Address` | Địa chỉ giao hàng | id |
| `Coupon` | Mã giảm giá | id |
| `Banner` | Banner quảng cáo | id |
| `SiteVisit` | Lượt truy cập website | id |
| `ProductReview` | Đánh giá sản phẩm | id |
| `ProductContent` | Nội dung sản phẩm | id |
| `PendingQRPayment` | QR chờ duyệt (VietQR) | id |
| `VNPayPayment` | Thanh toán VNPay | id |
| `PasswordHistory` | Lịch sử đổi mật khẩu | id |

### 3.2. Quan hệ giữa các bảng

#### 3.2.1. Quan hệ 1-N (One-to-Many)

```
CustomUser (1) ──────────→ (N) Cart
CustomUser (1) ──────────→ (N) Wishlist
CustomUser (1) ──────────→ (N) Order
CustomUser (1) ──────────→ (N) Address
CustomUser (1) ──────────→ (N) ProductReview
CustomUser (1) ──────────→ (N) SiteVisit

Brand (1) ──────────────→ (N) Product
Brand (1) ──────────────→ (N) HangingProduct
Brand (1) ──────────────→ (N) ImageFolder

Category (1) ───────────→ (N) Product

Product (1) ────────────→ (N) CartItem
Product (1) ────────────→ (N) OrderItem
Product (1) ────────────→ (N) ProductReview

ProductDetail (1) ──────→ (N) ProductVariant
ProductDetail (1) ──────→ (N) ProductImage

Order (1) ──────────────→ (N) OrderItem
```

#### 3.2.2. Quan hệ 1-1 (One-to-One)

```
Product (1) ───────────→ (1) ProductDetail
ProductDetail (1) ─────→ (1) ProductSpecification
ProductVariant (1) ────→ (N) ProductImage
```

#### 3.2.3. Quan hệ N-N (Many-to-Many)

```
Wishlist (N) ─────────── (N) Product (through wishlisted_by)
```

### 3.3. Ràng buộc Logic (Constraints)

| Model | Trường | Ràng buộc |
|-------|--------|-----------|
| CustomUser | email | UNIQUE |
| CustomUser | email | REQUIRED |
| Product | slug | UNIQUE |
| ProductDetail | product | UNIQUE (OneToOne) |
| ProductVariant | detail, color_name, storage | UNIQUE together |
| ProductReview | user, product | UNIQUE together |
| Order | order_code | UNIQUE |
| Coupon | code | UNIQUE |
| ImageFolder | name, brand, product | UNIQUE together |
| PendingQRPayment | transfer_code | UNIQUE |
| VNPayPayment | order_code | UNIQUE |

### 3.4. Trạng thái dữ liệu (Status Fields)

#### Order Status
```python
STATUS_CHOICES = [
    ('awaiting_payment', 'Chờ thanh toán'),  # VietQR pending
    ('pending', 'Đã đặt hàng'),              # COD pending
    ('processing', 'Đang xử lý'),
    ('shipped', 'Đang giao'),
    ('delivered', 'Đã giao hàng'),
    ('cancelled', 'Hủy đơn'),
]
```

#### Payment Method
```python
PAYMENT_METHOD_CHOICES = [
    ('cod', 'COD'),
    ('vietqr', 'VietQR'),
    ('vnpay', 'VNPay'),
]
```

#### VNPay Payment Status
```python
STATUS_CHOICES = [
    ('pending', 'Chờ thanh toán'),
    ('paid', 'Đã thanh toán'),
    ('failed', 'Thất bại'),
    ('cancelled', 'Đã hủy'),
]
```

#### Pending QR Status
```python
STATUS_CHOICES = [
    ('pending', 'Chờ duyệt'),
    ('approved', 'Đã duyệt'),
    ('cancelled', 'Đã hủy'),
]
```

---

## 4. PHÂN TÍCH CHỨC NĂNG

### 4.1. Xác thực (Authentication)

#### 4.1.1. Đăng ký (Register)

**File**: `store/views.py` - hàm `register_view`

**Flow xử lý**:
1. Nhận POST request với email, password, name, turnstile token
2. Validate Cloudflare Turnstile token (hàm `verify_turnstile`)
3. Verify OTP từ session
4. Tạo CustomUser mới với email làm username
5. Set password sử dụng `set_password()` (Django PBKDF2)
6. Redirect về trang chủ

**Thuật toán hash mật khẩu**:
- Sử dụng Django's default: **PBKDF2 (Password-Based Key Derivation Function 2)**
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: 720,000 (Django 4.2 default)

**Import sử dụng**:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
```

#### 4.1.2. Đăng nhập (Login)

**File**: `store/views.py` - hàm `login_view`

**Authentication Backends**:
- `store.backends.EmailBackend`: Đăng nhập bằng email
- `allauth.account.auth_backends.AuthenticationBackend`: OAuth

**File**: `store/backends.py`
```python
class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Tìm user theo email
        user = User.objects.get(email=username)
        # 2. Verify password
        if user.check_password(password):
            return user
        return None
```

**Đăng nhập Google OAuth**:
- Sử dụng django-allauth
- Provider: Google OAuth2
- Auto signup: True
- Email verification: None

#### 4.1.3. Quên mật khẩu (Forgot Password)

**File**: `store/views.py`
- `forgot_password_view`: Form yêu cầu reset
- `send_otp_forgot_password_view`: Gửi OTP qua email
- `verify_otp_forgot_password_view`: Xác minh OTP
- `reset_password_view`: Đặt lại mật khẩu mới

#### 4.1.4. Phân quyền (Authorization)

| Chức năng | Quyền yêu cầu |
|-----------|---------------|
| Xem sản phẩm | Ai cũng được |
| Thêm vào giỏ | Đăng nhập |
| Thanh toán | Đăng nhập |
| Dashboard | Staff/Admin |
| Quản lý sản phẩm | Staff/Admin |
| Duyệt đơn hàng | Staff/Admin |

**Middleware kiểm tra**:
```python
@login_required
def dashboard_view(request):
    # Chỉ user đã đăng nhập mới truy cập
```

### 4.2. Quản lý sản phẩm (Product Management)

#### 4.2.1. Thêm sản phẩm

**File**: `store/views.py` - hàm `product_add`

**Flow**:
1. Nhận POST với: name, brand, category, price, stock, is_featured
2. Tạo slug từ name (`slugify(name)`)
3. Lưu vào Product model
4. Tự động tạo ProductDetail (OneToOne)

#### 4.2.2. Quản lý biến thể (Variants)

**File**: `store/views.py` - hàm `product_variant_save`

**Model**: `ProductVariant`
```python
class ProductVariant(models.Model):
    detail = ForeignKey(ProductDetail)
    color_name = CharField(max_length=50)
    color_hex = CharField(max_length=7)
    storage = CharField(max_length=20)  # 64GB, 128GB, ...
    original_price = DecimalField
    discount_percent = PositiveIntegerField
    price = DecimalField
    sku = CharField
    stock_quantity = PositiveIntegerField
```

**Tính giá sau giảm** (trong `ProductDetail.discounted_price`):
```
discounted_price = original_price - (original_price * discount_percent / 100)
discounted_price = round(discounted_price / 5000) * 5000  # Làm tròn đến 5000
```

#### 4.2.3. Upload ảnh sản phẩm

**File**: `store/views.py` - hàm `product_image_upload`

**Upload path**:
```
media/products/YYYY/MM/<folder_slug>/filename
```

**File xử lý upload**:
- `ImageField` với `upload_to` parameter
- Sử dụng Django's built-in file storage
- Validation: Image format check

#### 4.2.4. Thông số kỹ thuật (Specifications)

**Model**: `ProductSpecification`
```python
spec_json = models.JSONField(default=dict)
# Lưu trữ dạng JSON:
# {
#   "groups": [
#     {"name": "Màn hình", "items": [...]},
#     {"name": "Camera", "items": [...]}
#   ]
# }
```

### 4.3. Giỏ hàng (Cart)

#### 4.3.1. Thêm vào giỏ

**File**: `store/views.py` - hàm `cart_add`

**Flow**:
1. Nhận POST: product_id, quantity, color_name, color_code, storage
2. Lấy hoặc tạo Cart cho user (`Cart.get_or_create_for_user()`)
3. Kiểm tra sản phẩm đã có trong giỏ chưa (unique_together)
4. Nếu có: cập nhật quantity
5. Nếu không: tạo CartItem mới
6. Lưu giá tại thời điểm thêm (`price_at_add`)

**Unique constraint**:
```python
unique_together = ['cart', 'product', 'color_name', 'storage']
```

#### 4.3.2. Tính tổng tiền

**Hàm**: `Cart.get_total_price()`
```python
def get_total_price(self):
    total = 0
    for item in self.items.all():
        total += item.get_total_price()  # price_at_add * quantity
    return total
```

### 4.4. Thanh toán (Checkout & Payment)

#### 4.4.1. Checkout View

**File**: `store/views.py` - hàm `checkout_view`

**Flow**:
1. Lấy danh sách item_ids từ query param
2. Validate cart items
3. Lấy địa chỉ mặc định
4. Tính subtotal
5. Render checkout template

#### 4.4.2. Đặt hàng (Place Order)

**File**: `store/views.py` - hàm `place_order`

**Hỗ trợ thanh toán**: COD, VietQR

**Flow xử lý COD**:
```
1. Validate cart items
2. Tính tổng tiền
3. Xử lý coupon (7 bước)
4. Tạo mã đơn hàng: "QHUN" + random(10000-99999)
5. Tạo Order record
6. Tạo OrderItem records (snapshot)
7. Xóa cart items
8. Gửi Telegram notification
9. Return JSON response
```

**Xử lý Coupon** (7 bước):
```python
# 1. Kiểm tra coupon tồn tại
coupon = Coupon.objects.get(code=coupon_code)

# 2. Validate coupon
if (coupon.is_valid()
    and total_amount >= coupon.min_order_amount
    and (coupon.max_products == 0 or item_count <= coupon.max_products)
    and (coupon.target_type == 'all' or email match)):
    
    # 3. Tính discount
    discount_amount = coupon.calculate_discount(total_amount)
    
    # 4. Cập nhật used_count
    coupon.used_count += 1
    coupon.save()
```

#### 4.4.3. Thanh toán VNPay

**File**: `store/views.py` - hàm `vnpay_create`

**Utility**: `store/vnpay_utils.py`

**Flow**:
1. Tạo VNPayPayment record
2. Lưu items_param vào session
3. Build payment URL với checksum
4. Redirect đến VNPay
5. VNPay callback → `vnpay_return` view

**Thuật toán tạo checksum**:
```python
def calculate_checksum(data, secret_key):
    # 1. Sort keys
    sorted_keys = sorted(data.keys())
    
    # 2. Build hash string
    hash_data = '&'.join(
        f"{k}={urllib.parse.quote_plus(str(data[k]))}"
        for k in sorted_keys
    )
    
    # 3. HMAC SHA512
    signature = hmac.new(
        secret_key.encode(),
        hash_data.encode(),
        hashlib.sha512
    ).hexdigest()
    
    return signature
```

#### 4.4.4. Thanh toán VietQR

**File**: `store/views.py` - hàm `vietqr_create_order`

**Flow**:
1. Tạo Order với status='awaiting_payment'
2. Tạo PendingQRPayment với transfer_code (unique)
3. Build QR URL: `https://img.vietqr.io/image/{bank_id}-{account_no}-vietqr_net_2.jpg?amount={amount}&addInfo={transfer_code}`
4. Redirect đến trang thanh toán riêng

**Admin duyệt QR**:
- Admin xác nhận đã nhận tiền
- Cập nhật PendingQRPayment.status = 'approved'
- Order status = 'processing'

### 4.5. Chatbot AI

**File**: `store/chatbot_service.py`

**AI Integration**: Claude API (Anthropic)

**File**: `store/claude_service.py`

**Các intent được hỗ trợ**:
- Greeting (chào hỏi)
- List products (danh sách sản phẩm)
- Price (hỏi giá)
- Stock (hỏi tồn kho)
- Variant (hỏi màu/dung lượng)
- Spec (hỏi thông số kỹ thuật)
- Compare (so sánh sản phẩm)
- Consult (tư vấn theo ngân sách)
- Order (tra cứu đơn hàng)
- Installment (trả góp)
- Warranty (bảo hành)
- Staff (gặp nhân viên)

**Intent Detection**:
```python
# Sử dụng Regular Expression để detect intent
GREETING_PATTERNS = re.compile(r"(xin chào|chào bạn|hello|hi|...)")
PRICE_PATTERNS = re.compile(r"(giá|bao nhiêu tiền|...)")
COMPARE_PATTERNS = re.compile(r"(so sánh|vs|versus|...)")
```

### 4.6. Thống kê / Báo cáo

**File**: `store/views.py` - hàm `best_sellers_api`

**Top sản phẩm bán chạy**:
```python
best_selling_products = OrderItem.objects.filter(
    order__status='delivered',  # Chỉ đơn đã giao
    product__is_active=True
).values('product__id', 'product__name', ...).annotate(
    total_sold=Sum('quantity')
).order_by('-total_sold')[:5]
```

**Theo dõi lượt truy cập**:
```python
SiteVisit.objects.create(
    ip_address=ip_address,
    user=user if authenticated else None
)
```

### 4.7. API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/chatbot/` | POST | Chatbot AI |
| `/api/submit-review/` | POST | Đánh giá sản phẩm |
| `/api/admin/orders/` | GET | Danh sách đơn hàng (admin) |
| `/api/admin/order-update-status/` | POST | Cập nhật trạng thái đơn |
| `/api/coupons/apply/` | POST | Áp dụng mã giảm giá |
| `/api/cancel-order/` | POST | Hủy đơn hàng |
| `/qr-payment/approve/` | POST | Duyệt QR thanh toán |

---

## 5. PHÂN TÍCH THUẬT TOÁN

### 5.1. Thuật toán tìm kiếm sản phẩm

**File**: `store/views.py` - hàm `product_search`

**Phương pháp**: Query param GET với `q=keyword`

**Xử lý**:
```python
query = request.GET.get('q', '')
# Sử dụng LIKE query trong template hoặc Django Q objects
```

**Độ phức tạp**: O(n) với n là số sản phẩm trong database

### 5.2. Thuật toán lọc và sắp xếp

**Sắp xếp sản phẩm theo tồn kho**:
```python
products_list = Product.objects.filter(is_active=True).annotate(
    stock_order=Case(
        When(stock__gt=0, then=0),  # Còn hàng: ưu tiên cao nhất
        default=1,                   # Hết hàng: ưu tiên thấp
        output_field=IntegerField(),
    )
).order_by('stock_order', '-created_at')
```

**Phân trang**:
```python
paginator = Paginator(products_list, 15)  # 15 sản phẩm/trang
products = paginator.page(page)
```

### 5.3. Thuật toán tính tổng tiền

**Tính tổng giỏ hàng**:
```python
def get_total_price(self):
    total = 0
    for item in self.items.all():
        total += item.get_total_price()  # price_at_add * quantity
    return total

# Time complexity: O(n) với n là số items trong giỏ
```

**Tính giá sau giảm**:
```python
def discounted_price(self):
    if self.original_price and self.discount_percent > 0:
        discounted = self.original_price - (self.original_price * self.discount_percent / 100)
        # Round to nearest 5000
        if discounted >= 5000:
            discounted = round(discounted / 5000) * 5000
        return int(discounted)
```

### 5.4. Thuật toán phân quyền

**Phương pháp**: Django's `@login_required` decorator

```python
@login_required
def dashboard_view(request):
    # Kiểm tra user đã đăng nhập
    # Nếu chưa → redirect đến LOGIN_URL
```

**Staff check**:
```python
if request.user.is_staff:
    # Cho phép truy cập admin functions
```

### 5.5. Hash mật khẩu

**Thuật toán**: Django PBKDF2

**Cấu hình trong `settings.py`**:
```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

**Độ phức tạp**:
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: 720,000 (Django 4.2)
- Output: 256-bit hash

### 5.6. Cơ chế Session

**Sử dụng**: Django Sessions (database-backed)

**Session lưu trữ**:
- `otp`: Mã OTP đăng ký
- `otp_email`: Email nhận OTP
- `otp_created_at`: Thời điểm tạo OTP
- `vnpay_items_param`: Cart items khi redirect sang VNPay

**Session config**:
```python
# Sử dụng database session (default)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
```

---

## 6. PHÂN TÍCH THƯ VIỆN VÀ DEPENDENCY

### 6.1. Requirements.txt

```
asgiref==3.11.1        # ASGI interface cho Django
Django==4.2.11         # Web framework chính
sqlparse==0.5.5        # SQL query formatter
typing_extensions==4.15.0  # Type hints support
tzdata==2025.3         # Timezone data
django-allauth==0.63.8 # Authentication (OAuth + Email)
requests==2.31.0       # HTTP requests (VNPay, Telegram, SendGrid)
python-dotenv==1.2.1   # Load .env files
httpx==0.28.1          # Async HTTP client
```

### 6.2. Mô tả từng thư viện

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| **Django** | 4.2.11 | Web framework chính - MVC pattern |
| **django-allauth** | 0.63.8 | Authentication + OAuth (Google) |
| **requests** | 2.31.0 | HTTP client cho VNPay, Telegram, SendGrid |
| **python-dotenv** | 1.2.1 | Load biến môi trường từ .env |
| **sqlparse** | 0.5.5 | SQL query formatting |
| **asgiref** | 3.11.1 | ASGI support |
| **httpx** | 0.28.1 | Async HTTP (nếu cần) |

### 6.3. Thư viện cho từng chức năng

#### Xác thực (Authentication)
- **django-allauth**: OAuth2 (Google), Email authentication
- **Custom EmailBackend**: Đăng nhập bằng email

#### Upload file/ảnh
- **Django built-in**: `ImageField`, `FileField`
- **Validation**: Django's image validation

#### Thanh toán (Payment)
- **requests**: Gọi API VNPay
- **hashlib, hmac**: Tạo checksum cho VNPay
- **urllib.parse**: URL encoding

#### Chatbot AI
- **requests**: Gọi Claude API (Anthropic)
- **regex**: Intent detection

#### Notifications
- **requests**: Gọi Telegram Bot API

### 6.4. Middleware

**File**: `config/settings.py`

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

| Middleware | Chức năng |
|------------|-----------|
| SecurityMiddleware | HTTP security headers |
| SessionMiddleware | Quản lý session |
| CommonMiddleware | Common Django utilities |
| CsrfViewMiddleware | CSRF protection |
| AuthenticationMiddleware | User authentication |
| AccountMiddleware | AllAuth account management |
| MessageMiddleware | Flash messages |
| XFrameOptionsMiddleware | Clickjacking protection |

---

## 7. HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY

### 7.1. Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|------------|----------|
| Python | 3.8+ |
| OS | Windows / Linux / macOS |
| Database | SQLite (có sẵn) |

### 7.2. Tạo môi trường ảo

```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### 7.3. Kích hoạt môi trường ảo

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 7.4. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 7.5. Cấu hình .env

Tạo file `.env` trong thư mục gốc:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Cloudflare Turnstile (tùy chọn)
CLOUDFLARE_TURNSTILE_SITE_KEY=your-site-key
CLOUDFLARE_TURNSTILE_SECRET_KEY=your-secret-key

# Google OAuth (tùy chọn)
GOOGLE_OAUTH2_CLIENT_ID=your-client-id
GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret

# VNPay
VNPAY_TMN_CODE=981P6A3M
VNPAY_HASH_SECRET=your-hash-secret
VNPAY_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://localhost:8000/vnpay/return/
VNPAY_IPN_URL=http://localhost:8000/vnpay/ipn/

# SendGrid (cho gửi OTP email)
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@qhun22.com

# Claude AI (cho chatbot)
ANTHROPIC_API_KEY=your-anthropic-api-key

# Telegram (cho notifications)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 7.6. Migrate database

```bash
python manage.py migrate
```

### 7.7. Tạo tài khoản admin

```bash
python manage.py createsuperuser
```

**Hoặc trong code**:
```python
from store.models import CustomUser

user = CustomUser.objects.create_superuser(
    email='admin@qhun22.com',
    password='your-password'
)
```

### 7.8. Chạy server

```bash
# Development
python manage.py runserver

# Specific port
python manage.py runserver 8000
```

### 7.9. Các lệnh hữu ích

```bash
# Tạo migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Tạo static files (production)
python manage.py collectstatic

# Shell Django
python manage.py shell

# Check system
python manage.py check
```

---

## 8. PHÂN TÍCH KIẾN TRÚC

### 8.1. Mô hình kiến trúc

**Mô hình**: MVC (Model-View-Controller) - Django Pattern

| Layer | Component | Files |
|-------|-----------|-------|
| **Model** | Database Models | `store/models.py` |
| **View** | Business Logic | `store/views.py` |
| **Template** | Presentation | `templates/store/*.html` |
| **Controller** | URL Routing | `config/urls.py`, `store/urls.py` |

### 8.2. Phân tách view, logic, data

| Layer | Xử lý |
|-------|-------|
| **Models** | Database schema, relationships, business logic (properties) |
| **Views** | HTTP request/response, authentication, authorization |
| **Templates** | HTML rendering, JavaScript interactions |
| **Utils** | VNPay, Telegram, Chatbot services |

### 8.3. Điểm tốt

1. **Cấu trúc rõ ràng**: Phân tách models, views, templates, utils
2. **Custom User Model**: Sử dụng AbstractUser, không dùng username
3. **Authentication linh hoạt**: Email + OAuth (Google)
4. **Payment đa dạng**: COD, VietQR, VNPay
5. **Chatbot AI**: Tích hợp Claude API cho hỗ trợ khách hàng
6. **Notifications**: Telegram bot cho order notifications
7. **Review System**: Chỉ user đã mua mới được đánh giá
8. **Coupon System**: Hỗ trợ nhiều loại giảm giá

### 8.4. Điểm cần cải thiện

1. **Database**: SQLite không phù hợp cho production
   - Nên chuyển sang PostgreSQL

2. **Không có API RESTful đầy đủ**
   - Hiện tại chỉ có một số API endpoints
   - Nên sử dụng Django REST Framework

3. **Frontend**: Sử dụng jQuery + vanilla JS
   - Nên xem xét React/Vue cho scalability

4. **Caching**: Chưa có caching
   - Nên thêm Redis cho session/cache

5. **Security**:
   - Thiếu rate limiting
   - Nên thêm 2FA

6. **Error handling**: Chưa đồng nhất
   - Nên có centralized error handling

7. **Testing**: Chưa có unit tests
   - Nên viết tests cho critical functions

8. **Logging**: Cơ bản
   - Nên cải thiện logging cho production

---

## 9. KẾT LUẬN

### 9.1. Tổng kết

Hệ thống **QHUN22** là một ứng dụng thương mại điện tử hoàn chỉnh được xây dựng trên Django 4.2.11 với đầy đủ các tính năng cần thiết cho một cửa hàng điện thoại trực tuyến:

- ✅ Quản lý sản phẩm đa dạng
- ✅ Giỏ hàng và thanh toán
- ✅ Đa phương thức thanh toán (COD, VietQR, VNPay)
- ✅ Chatbot AI hỗ trợ khách hàng
- ✅ Hệ thống đánh giá và đánh giá sản phẩm
- ✅ Mã giảm giá và khuyến mãi
- ✅ Dashboard quản trị

### 9.2. Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| Backend | Django 4.2.11 |
| Database | SQLite |
| Authentication | django-allauth |
| AI | Claude API (Anthropic) |
| Payment | VNPay, VietQR, COD |
| Notifications | Telegram Bot |

### 9.3. Khuyến nghị phát triển

1. **Ngắn hạn**:
   - Thêm unit tests
   - Cải thiện error handling
   - Thêm logging

2. **Trung hạn**:
   - Chuyển sang PostgreSQL
   - Thêm Redis caching
   - Xây dựng REST API với DRF

3. **Dài hạn**:
   - Tách monolith thành microservices
   - Thêm mobile app
   - Tích hợp more payment methods

---

**Tài liệu được tạo**: 2026-02-28  
**Phiên bản**: 1.0  
**Dự án**: QHUN22 Mobile Shop
