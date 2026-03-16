# QHUN22 - Cửa hàng điện thoại di động

## Mục lục

1. [Giới thiệu](#giới-thiệu)
2. [Công nghệ](#công-nghệ)
3. [Cấu trúc dự án](#cấu-trúc-dự-án)
4. [Models (Database)](#models-database)
5. [Views và URLs](#views-và-urls)
6. [Templates](#templates)
7. [Static Files](#static-files)
8. [Chức năng chính](#chức-năng-chính)
9. [Hướng dẫn cài đặt](#hướng-dẫn-cài-đặt)
10. [Cấu hình thanh toán](#cấu-hình-thanh-toán)
11. [Cấu hình AI Chatbot](#cấu-hình-ai-chatbot)

---

## Giới thiệu

**QHUN22** là website thương mại điện tử di động hoàn chỉnh được viết bằng **Django** (Python). Website cung cấp đầy đủ tính năng cho một cửa hàng điện thoại online:

- Hiển thị sản phẩm, tìm kiếm, lọc theo hãng
- Giỏ hàng và đặt hàng
- Nhiều phương thức thanh toán (COD, VietQR, VNPay, MoMo)
- Chatbot AI hỗ trợ khách hàng 24/7
- Quản lý đơn hàng, sản phẩm, người dùng
- Mã giảm giá, đánh giá sản phẩm
- Blog sản phẩm

---

## Công nghệ

| Thành phần | Công nghệ sử dụng |
|------------|---------------------|
| Backend | Python 3.10+ (khuyến nghị 3.11), Django 4.2.x |
| Database | SQLite3 (development), PostgreSQL (production) |
| Authentication | django-allauth |
| Payment | VNPay API, VietQR, MoMo, COD |
| AI | Claude API (Anthropic) |
| Frontend | HTML, CSS, JavaScript |
| OAuth | Google Login |

---

## Cấu trúc dự án

```
qhun22/
├── config/                    # Cấu hình Django
│   ├── __init__.py
│   ├── settings.py          # Cấu hình chính
│   ├── urls.py              # URL routing chính
│   └── wsgi.py
├── store/                    # Ứng dụng chính
│   ├── migrations/          # Database migrations
│   ├── views/               # Views (theo chức năng)
│   │   ├── __init__.py
│   │   ├── auth_views.py    # Đăng nhập, đăng ký
│   │   ├── admin_views.py   # Dashboard admin
│   │   ├── product_views.py # Sản phẩm
│   │   ├── cart_views.py    # Giỏ hàng
│   │   ├── order_views.py   # Đơn hàng
│   │   ├── payment_views.py # Thanh toán
│   │   ├── blog_views.py    # Blog
│   │   ├── coupon_views.py  # Mã giảm giá
│   │   └── chatbot_views.py # AI Chatbot
│   ├── templatetags/        # Template tags tùy chỉnh
│   ├── management/          # Custom commands
│   ├── models.py            # Tất cả database models
│   ├── urls.py              # URL routing
│   ├── admin.py             # Django Admin config
│   ├── apps.py
│   ├── context_processors.py # Context processors
│   ├── backends.py          # Authentication backends
│   ├── allauth_adapter.py   # Allauth adapter
│   ├── vnpay_utils.py       # VNPay utilities
│   ├── momo_utils.py        # MoMo utilities
│   ├── telegram_utils.py    # Telegram notifications
│   ├── chatbot_service.py    # Chatbot AI service
│   └── claude_service.py    # Claude API service
├── templates/                # HTML templates
│   ├── base.html            # Base template
│   └── store/               # Store templates
├── static/                  # Static files
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript files
│   ├── logos/               # Website logos
│   └── videos/              # Video files
├── media/                   # User uploaded files
│   ├── products/            # Product images
│   ├── brands/              # Brand logos
│   ├── banner/              # Banner images
│   └── blog/                # Blog images
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
└── db.sqlite3               # SQLite database
```

---

## Models (Database)

### 1. User & Authentication

#### CustomUser
- **Mô tả**: Custom User Model - đăng nhập bằng email
- **Trường chính**:
  - `email` - Email (unique, làm username)
  - `phone` - Số điện thoại
  - `username` - Đã bỏ, giữ để tương thích allauth
  - `is_oauth_user` - Đánh dấu user đăng nhập bằng OAuth
  - `is_student_verified` - Xác thực sinh viên
  - `is_teacher_verified` - Xác thực giáo viên
  - `verified_student_email` - Email sinh viên đã xác thực
  - `verified_teacher_email` - Email giáo viên đã xác thực

#### PasswordHistory
- **Mô tả**: Lưu lịch sử đổi mật khẩu
- **Trường**: user, changed_at, ip_address, user_agent

#### EmailVerification
- **Mô tả**: Lưu mã xác thực email .edu (Student/Teacher)
- **Trường**: user, email, code, is_verified, verification_type

---

### 2. Products

#### Category
- **Mô tả**: Danh mục sản phẩm
- **Trường**: name, slug, description, created_at

#### Brand
- **Mô tả**: Hãng sản phẩm (Apple, Samsung, Xiaomi...)
- **Trường**: name, slug, description, logo, is_active

#### Product
- **Mô tả**: Sản phẩm điện thoại
- **Trường**: name, slug, brand, category, price, original_price, discount_percent, image, stock, is_featured, is_active

#### ProductDetail
- **Mô tả**: Chi tiết sản phẩm - OneToOne với Product
- **Trường**: 
  - product (OneToOne)
  - original_price, discount_percent
  - sku (SKU tổng)
  - youtube_id (Video ID)
  - description
  - is_active

#### ProductVariant
- **Mô tả**: Biến thể sản phẩm theo màu sắc và dung lượng
- **Trường**: 
  - detail (ForeignKey to ProductDetail)
  - color_name, color_hex
  - storage (64GB, 128GB...)
  - original_price, discount_percent, price
  - sku, stock_quantity
  - is_active
- **Unique**: detail, color_name, storage

#### ProductSpecification
- **Mô tả**: Thông số kỹ thuật - lưu JSON
- **Trường**: detail (OneToOne), spec_json (JSONField)

#### ProductImage
- **Mô tả**: Hình ảnh sản phẩm
- **Trường**: detail, variant, image_type (cover/marketing/variant_thumbnail/variant_main...), image, order

#### ImageFolder
- **Mô tả**: Thư mục ảnh riêng để quản lý ảnh theo thư mục
- **Trường**: name, slug, brand, product

#### FolderColorImage
- **Mô tả**: Ảnh màu theo thư mục
- **Trường**: folder, brand, sku, color_name, image, order

#### HangingProduct
- **Mô tả**: Sản phẩm treo hiển thị trên trang chủ
- **Trường**: brand, product, name, image_url/image_local, original_price, discount_percent, installment_0_percent, is_active

---

### 3. Shopping

#### Wishlist
- **Mô tả**: Danh sách yêu thích của user
- **Trường**: user, products (ManyToMany to Product)

#### Cart
- **Mô tả**: Giỏ hàng của user
- **Trường**: user

#### CartItem
- **Mô tả**: Item trong giỏ hàng
- **Trường**: cart, product, quantity, color_name, color_code, storage, price_at_add

---

### 4. Orders

#### Order
- **Mô tả**: Đơn hàng
- **Trường**:
  - user, order_code (unique)
  - total_amount
  - payment_method (cod/vietqr/vnpay/momo)
  - vnpay_order_code, momo_order_code
  - coupon_code, discount_amount
  - status: awaiting_payment → pending → processing → shipped → delivered / cancelled
  - refund_account, refund_bank, refund_status

#### OrderItem
- **Mô tả**: Sản phẩm trong đơn hàng (snapshot)
- **Trường**: order, product, product_name, color_name, storage, quantity, price, thumbnail

#### Address
- **Mô tả**: Sổ địa chỉ giao hàng
- **Trường**: user, full_name, phone, province_code, province_name, district_code, district_name, ward_code, ward_name, detail, is_default

---

### 5. Payments

#### PendingQRPayment
- **Mô tả**: QR chuyển khoản chờ duyệt (VietQR)
- **Trường**: user, amount, transfer_code, status (pending/approved/cancelled)
- **Tự động xóa** sau 15 phút nếu không duyệt

#### VNPayPayment
- **Mô tả**: Lưu thông tin thanh toán VNPay
- **Trường**: user, amount, order_code, transaction_no, transaction_status, status, response_code, response_message, pay_method

---

### 6. Reviews & Content

#### ProductReview
- **Mô tả**: Đánh giá sản phẩm (chỉ user đã mua mới được đánh giá)
- **Trường**: user, product (unique together), rating (1-5), comment, images (JSON)
- **Unique**: user, product

#### ProductContent
- **Mô tả**: Nội dung sản phẩm theo hãng
- **Trường**: brand, product, content_text, image

#### BlogPost
- **Mô tả**: Bài viết blog sản phẩm
- **Trường**: title, summary, content, image, is_active

#### Banner
- **Mô tả**: Banner trang chủ
- **Trường**: banner_id, image

---

### 7. Coupons & Marketing

#### Coupon
- **Mô tả**: Mã giảm giá
- **Trường**:
  - code (unique)
  - discount_type (percentage/fixed)
  - discount_value
  - target_type (all/single)
  - target_email
  - max_products (0 = không giới hạn)
  - min_order_amount
  - usage_limit (per user)
  - expire_days, expire_at
  - is_active

#### CouponUsage
- **Mô tả**: Lịch sử dùng voucher
- **Trường**: coupon, user, used_at

---

### 8. Analytics & Newsletter

#### SiteVisit
- **Mô tả**: Theo dõi lượt truy cập website
- **Trường**: visit_time, ip_address, user

#### Newsletter
- **Mô tả**: Đăng ký nhận tin tư vấn & ưu đãi
- **Trường**: user (nullable), email, phone, is_active

---

## Views và URLs

### Trang khách hàng

| URL | View | Mô tả |
|-----|------|-------|
| `/` | `home` | Trang chủ |
| `/product/<id>/` | `product_detail_view` | Chi tiết sản phẩm |
| `/compare/` | `compare_view` | So sánh sản phẩm |
| `/products/search/` | `product_search` | Tìm kiếm sản phẩm |
| `/products/autocomplete/` | `product_autocomplete` | Autocomplete tìm kiếm |
| `/cart/` | `cart_detail` | Giỏ hàng |
| `/cart/add/` | `cart_add` | Thêm vào giỏ |
| `/cart/remove/` | `cart_remove` | Xóa khỏi giỏ |
| `/cart/update/` | `cart_update_quantity` | Cập nhật số lượng |
| `/cart/change-color/` | `cart_change_color` | Đổi màu |
| `/cart/change-storage/` | `cart_change_storage` | Đổi dung lượng |
| `/checkout/` | `checkout_view` | Thanh toán |
| `/order-tracking/` | `order_tracking` | Tra cứu đơn hàng |
| `/order/success/<code>/` | `order_success` | Đặt hàng thành công |
| `/wishlist/` | `wishlist` | Danh sách yêu thích |
| `/wishlist/toggle/` | `wishlist_toggle` | Toggle yêu thích |
| `/login/` | `login_view` | Đăng nhập |
| `/register/` | `register_view` | Đăng ký |
| `/profile/` | `profile` | Thông tin user |
| `/forgot-password/` | `forgot_password_view` | Quên mật khẩu |

### Thanh toán

| URL | View | Mô tả |
|-----|------|-------|
| `/order/place/` | `place_order` | Đặt hàng (COD/VietQR) |
| `/qr-payment/create/` | `qr_payment_create` | Tạo QR thanh toán |
| `/qr-payment/list/` | `qr_payment_list` | Danh sách QR |
| `/vietqr/create-order/` | `vietqr_create_order` | Tạo VietQR |
| `/vietqr-payment/` | `vietqr_payment_page` | Trang thanh toán VietQR |
| `/vnpay/create/` | `vnpay_create` | Tạo thanh toán VNPay |
| `/vnpay/return/` | `vnpay_return` | VNPay return URL |
| `/momo/create/` | `momo_create` | Tạo thanh toán MoMo |
| `/momo/return/` | `momo_return` | MoMo return URL |

### Address Management

| URL | View | Mô tả |
|-----|------|-------|
| `/address/add/` | `address_add` | Thêm địa chỉ |
| `/address/delete/` | `address_delete` | Xóa địa chỉ |
| `/address/set-default/` | `address_set_default` | Đặt mặc định |

### API Endpoints

| URL | View | Mô tả |
|-----|------|-------|
| `/api/submit-review/` | `submit_review` | Gửi đánh giá |
| `/api/cancel-order/` | `cancel_order` | Hủy đơn |
| `/api/refund-pending/` | `refund_pending` | Yêu cầu hoàn tiền |
| `/api/refund-history/` | `refund_history` | Lịch sử hoàn tiền |
| `/api/chatbot/` | `chatbot_api` | AI Chatbot |
| `/api/autocomplete/` | `product_autocomplete` | Autocomplete |
| `/api/products/filter/` | `product_filter_json` | Lọc sản phẩm |

### Admin Dashboard

| URL | View | Mô tả |
|-----|------|-------|
| `/dashboard/` | `dashboard_view` | Dashboard admin |
| `/dashboard/order-detail/` | `dashboard_order_detail` | Chi tiết đơn hàng |
| `/dashboard/product-detail/` | `dashboard_product_detail` | Chi tiết sản phẩm |
| `/brands/` | `brand_list` | Danh sách hãng |
| `/brands/add/` | `brand_add` | Thêm hãng |
| `/brands/edit/` | `brand_edit` | Sửa hãng |
| `/brands/delete/` | `brand_delete` | Xóa hãng |
| `/users/detail/` | `user_detail_json` | Chi tiết user |
| `/users/add/` | `user_add` | Thêm user |
| `/users/edit/` | `user_edit` | Sửa user |
| `/users/delete/` | `user_delete` | Xóa user |
| `/products/add/` | `product_add` | Thêm sản phẩm |
| `/products/edit/` | `product_edit` | Sửa sản phẩm |
| `/products/delete/` | `product_delete` | Xóa sản phẩm |
| `/products/detail/save/` | `product_detail_save` | Lưu chi tiết SP |
| `/products/variant/save/` | `product_variant_save` | Lưu biến thể |
| `/products/specification/upload/` | `product_specification_upload` | Upload thông số |
| `/products/image/upload/` | `product_image_upload` | Upload ảnh |
| `/banner-images/add/` | `banner_add` | Thêm banner |
| `/banner-images/replace/` | `banner_replace` | Thay banner |
| `/banner-images/delete/` | `banner_delete` | Xóa banner |
| `/blog-posts/list/` | `blog_list` | Danh sách blog |
| `/blog-posts/add/` | `blog_add` | Thêm blog |
| `/best-sellers/` | `best_sellers_admin` | Sản phẩm bán chạy |
| `/export/month/` | `export_revenue_month` | Xuất doanh thu tháng |
| `/export/year/` | `export_revenue_year` | Xuất doanh thu năm |
| `/reviews/list/` | `review_list` | Danh sách đánh giá |
| `/api/admin/orders/` | `admin_order_list` | DS đơn hàng (API) |
| `/api/admin/order-update-status/` | `admin_order_update_status` | Cập nhật trạng thái |
| `/api/coupons/` | `coupon_list` | Danh sách coupon |
| `/api/coupons/add/` | `coupon_add` | Thêm coupon |

---

## Templates

```
templates/
├── base.html                    # Base template (Header, Footer, Navigation)
└── store/
    ├── home.html                # Trang chủ
    ├── product_detail.html      # Chi tiết sản phẩm
    ├── search.html             # Kết quả tìm kiếm
    ├── cart.html               # Giỏ hàng
    ├── checkout.html           # Thanh toán
    ├── wishlist.html           # Yêu thích
    ├── login.html              # Đăng nhập
    ├── register.html           # Đăng ký
    ├── profile.html            # Thông tin user
    ├── dashboard.html          # Admin dashboard
    ├── order_tracking.html     # Tra cứu đơn hàng
    ├── order_success.html      # Đặt hàng thành công
    ├── payment_success.html    # Thanh toán thành công
    ├── payment_error.html      # Thanh toán lỗi
    ├── vietqr_payment.html     # Trang thanh toán VietQR
    ├── forgot_password.html    # Quên mật khẩu
    ├── compare.html            # So sánh sản phẩm
    ├── brand_list.html         # Danh sách hãng
    ├── best_sellers_admin.html # Admin sản phẩm bán chạy
    └── partials/
        ├── pagination.html     # Phân trang
        └── product_list.html   # Danh sách sản phẩm
```

---

## Static Files

```
static/
├── css/
│   ├── style.css              # Main stylesheet
│   ├── base.css               # Base styles
│   ├── home.css               # Homepage styles
│   ├── cart.css               # Cart styles
│   ├── checkout.css           # Checkout styles
│   ├── login.css              # Login styles
│   ├── register.css           # Register styles
│   ├── search.css             # Search styles
│   ├── product_detail.css     # Product detail styles
│   ├── wishlist.css           # Wishlist styles
│   ├── profile.css            # Profile styles
│   ├── order_tracking.css     # Order tracking styles
│   ├── order_success.css      # Order success styles
│   ├── compare.css            # Compare styles
│   ├── brand_list.css         # Brand list styles
│   ├── banner.css             # Banner styles
│   ├── chatbot.css            # Chatbot styles
│   ├── contact-bar.css        # Contact bar styles
│   ├── forgot_password.css    # Forgot password styles
│   └── vietqr_payment.css     # VietQR payment styles
├── js/
│   ├── toast.js               # Toast notifications
│   ├── confirm.js             # Confirm dialogs
│   ├── home.js                # Homepage scripts
│   ├── cart.js                # Cart scripts
│   ├── checkout.js            # Checkout scripts
│   ├── login.js               # Login scripts
│   ├── register.js            # Register scripts
│   ├── product.js             # Product scripts
│   ├── product_detail.js      # Product detail scripts
│   ├── pd_page.js             # Product page scripts
│   ├── compare.js             # Compare scripts
│   ├── chatbot.js             # Chatbot scripts
│   ├── banner.js              # Banner management
│   ├── profile.js             # Profile scripts
│   ├── order_tracking.js      # Order tracking scripts
│   ├── order_success.js       # Order success scripts
│   ├── forgot_password.js     # Forgot password scripts
│   ├── dashboard.js          # Admin dashboard scripts
│   └── brand_list.js          # Brand list scripts
├── logos/
│   ├── sean.gif
│   └── seanfavi.jpg
└── videos/
    └── README.txt
```

---

## Chức năng chính

### Cho khách hàng

1. **Xem sản phẩm** - Danh sách sản phẩm theo danh mục, hãng
2. **Tìm kiếm** - Tìm kiếm với autocomplete, lọc theo hãng, giá
3. **So sánh sản phẩm** - So sánh các sản phẩm cùng loại
4. **Giỏ hàng** - Thêm/xóa/cập nhật số lượng, đổi màu/dung lượng
5. **Yêu thích** - Lưu sản phẩm yêu thích
6. **Đặt hàng** - Với nhiều phương thức thanh toán
7. **Theo dõi đơn hàng** - Xem trạng thái đơn hàng
8. **Đánh giá sản phẩm** - Chỉ sau khi mua thành công
9. **Chat với AI** - Chatbot tư vấn sản phẩm 24/7
10. **Đăng nhập** - Email + Google OAuth
11. **Quên mật khẩu** - Reset qua OTP SMS

### Cho Admin

1. **Quản lý sản phẩm** - Thêm/sửa/xóa sản phẩm, biến thể, hình ảnh
2. **Quản lý danh mục** - Thêm/sửa/xóa danh mục
3. **Quản lý hãng** - Thêm/sửa/xóa hãng sản xuất
4. **Quản lý đơn hàng** - Xem, cập nhật trạng thái
5. **Quản lý người dùng** - Thêm/sửa/xóa user
6. **Quản lý mã giảm giá** - Tạo và quản lý coupon
7. **Quản lý banner** - Thêm/sửa/xóa banner trang chủ
8. **Quản lý blog** - Viết và quản lý bài viết
9. **Quản lý đánh giá** - Xem/xóa đánh giá
10. **Thống kê** - Sản phẩm bán chạy, doanh thu
11. **Xuất Excel** - Báo cáo doanh thu tháng/năm

---

## Hướng dẫn cài đặt

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|---------|-----------|
| Python | **3.10 trở lên** (3.11 khuyến nghị) |
| pip | 23.0 trở lên |
| OS | Windows / Linux / macOS |

### Các bước cài đặt

#### Bước 1: Tạo môi trường ảo

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

#### Bước 2: Cài thư viện

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Bước 3: Tạo file `.env`

Tạo file `.env` trong thư mục gốc:

```env
# Django
SECRET_KEY=mã-bảo-mật-dự-án
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# VNPay (tùy chọn)
VNPAY_TMN_CODE=
VNPAY_HASH_SECRET=mã-hash-secret
VNPAY_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://localhost:8000/vnpay/return/

# Cloudflare Turnstile
CLOUDFLARE_TURNSTILE_SITE_KEY=site-key
CLOUDFLARE_TURNSTILE_SECRET_KEY=secret-key

# Google OAuth (tùy chọn)
GOOGLE_OAUTH2_CLIENT_ID=client-id
GOOGLE_OAUTH2_CLIENT_SECRET=client-secret

# Claude API (cho chatbot)
ANTHROPIC_API_KEY=api-key-của-anthropic
```

#### Bước 4: Tạo database

```bash
python manage.py migrate
```

#### Bước 5: Tạo tài khoản admin

```bash
python manage.py createsuperuser
```

#### Bước 6: Chạy server

```bash
python manage.py runserver
```

Truy cập website: **http://127.0.0.1:8000/**

---

## Cấu hình thanh toán

### VNPay (tùy chọn)

Để sử dụng VNPay trong production:

1. Đăng ký tài khoản VNPay
2. Lấy mã TmnCode và HashSecret
3. Cập nhật vào file `.env`

Trong development, có thể dùng sandbox của VNPay.

### MoMo

Cấu hình MoMo trong settings.py:

```python
MOMO_ENDPOINT = 'https://test-payment.momo.vn/v2/gateway/api/create'
MOMO_PARTNER_CODE = 'MOMO'
MOMO_ACCESS_KEY = 'access-key'
MOMO_SECRET_KEY = 'secret-key'
```

### VietQR

Cấu hình ngân hàng trong settings.py:

```python
BANK_ID = 'BIDV'
BANK_ACCOUNT_NO = '1234567890'
BANK_ACCOUNT_NAME = 'QHUN22'
```

---

## Cấu hình AI Chatbot

Chatbot sử dụng **Claude API** của Anthropic.

### Bước 1: Đăng ký Anthropic

1. Truy cập https://www.anthropic.com/
2. Tạo tài khoản và lấy API key

### Bước 2: Cấu hình

Thêm vào file `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Bước 3: Kiểm tra

Nếu không cấu hình, chatbot sẽ hiển thị thông báo lỗi nhưng website vẫn hoạt động bình thường.

---

## Ghi chú

- Cho production, nên chuyển sang **PostgreSQL**
- Một số tính năng (VNPay, Claude API) cần cấu hình thêm mới hoạt động
- File `db.sqlite3` đã có sẵn sản phẩm mẫu để test

---

## Liên hệ

- Email: qhun22@gmail.com
- Website: qhun22.com

---

Tài liệu được viết bởi Quang Huy Truong
