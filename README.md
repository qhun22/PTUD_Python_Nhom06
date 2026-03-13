# QHUN22 - Cửa hàng điện thoại

## Giới thiệu

Website cung cấp đầy đủ tính năng cho một cửa hàng điện thoại online:

- Hiển thị sản phẩm, tìm kiếm, lọc theo hãng
- Giỏ hàng và đặt hàng
- Nhiều phương thức thanh toán (COD, VietQR, VNPay)
- Chatbot AI hỗ trợ khách hàng 24/7
- Quản lý đơn hàng, sản phẩm, người dùng
- Mã giảm giá, đánh giá sản phẩm

## Công nghệ

| Thành phần | Công nghệ sử dụng |
|------------|---------------------|
| Backend | Python **3.10+** (khuyến nghị 3.11), Django 4.2.x |
| Database | SQLite3 |
| Authentication | django-allauth |
| Payment | VNPay API, VietQR, COD |
| AI | Claude API (Anthropic) |
| Frontend | HTML, CSS, JavaScript |

## Cấu trúc thư mục

```
qhun22/
├── config/              # Cấu hình Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── store/               # Ứng dụng chính
│   ├── models.py       # Database models
│   ├── views.py        # Logic xử lý
│   ├── urls.py         # URL routing
│   ├── admin.py        # Cấu hình admin
│   ├── chatbot_service.py  # Chatbot AI
│   └── ...
├── templates/          # HTML templates
├── static/             # CSS, JS, hình ảnh
├── media/              # File upload
├── manage.py
└── requirements.txt
```

## Hướng dẫn cài đặt

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|---------|----------|
| Python | **3.10 trở lên** (3.11 khuyến nghị) |
| pip | 23.0 trở lên |
| OS | Windows / Linux / macOS |

> **Lưu ý quan trọng:** Dự án dùng `>=` cho tất cả package thay vì `==` để tránh xung đột version giữa các máy. Không cần cài đúng version như người share — chỉ cần Python 3.10+.

### Cách nhanh nhất (Windows)

Chạy file `qhun22.bat` → chọn **[0] Cài đặt lần đầu** — script sẽ tự động:

- Kiểm tra Python
- Tạo môi trường ảo (`venv`)
- Nâng cấp `pip`
- Cài tất cả thư viện
- Chạy database migration

### Cài đặt thủ công (mọi OS)

### Bước 1: Tạo môi trường ảo

Tạo môi trường Python riêng biệt để không ảnh hưởng đến các dự án khác:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Bước 2: Nâng cấp pip và cài thư viện

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Ghi chú về tzdata:** Trên Linux/macOS không cần `tzdata` vì hệ thống đã có. File `requirements.txt` đã xử lý tự động với điều kiện `sys_platform == "win32"`.

### Bước 3: Cấu hình biến môi trường

Tạo file `.env` trong thư mục gốc với nội dung:

```env
# Django
SECRET_KEY=mã-bảo-mật-dự-án
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# VNPay (nếu sử dụng)
VNPAY_TMN_CODE=
VNPAY_HASH_SECRET=mã-hash-secret
VNPAY_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://localhost:8000/vnpay/return/

# Cloudflare Turnstile (chống bot)
CLOUDFLARE_TURNSTILE_SITE_KEY=site-key
CLOUDFLARE_TURNSTILE_SECRET_KEY=secret-key

# Google OAuth (nếu sử dụng)
GOOGLE_OAUTH2_CLIENT_ID=client-id
GOOGLE_OAUTH2_CLIENT_SECRET=client-secret

# Claude API (cho chatbot)
ANTHROPIC_API_KEY=api-key-của-anthropic
```

### Bước 4: Tạo database

```bash
python manage.py migrate
```

### Bước 5: Tạo tài khoản admin

```bash
python manage.py createsuperuser
```

Nhập email và mật khẩu theo hướng dẫn. Tài khoản này sẽ được sử dụng để truy cập trang quản trị /admin/

### Bước 6: Khởi động server

```bash
python manage.py runserver
```

Truy cập website tại: <http://127.0.0.1:8000/>

## Xử lý lỗi thường gặp khi cài đặt

| Lỗi | Nguyên nhân | Giải pháp |
|-----|------------|----------|
| `No module named 'openpyxl'` | Package bị thiếu trong venv cũ | `pip install openpyxl` |
| `tzdata` conflict trên Linux | Hệ thống không cần tzdata | Bỏ qua, dòng có `sys_platform` sẽ tự skip |
| `typing_extensions` error | Python < 3.10 | Nâng cấp Python lên 3.10+ |
| `django-allauth` import error | Version không tương thích | `pip install -U django-allauth` |
| `.env not found` | Chưa tạo file .env | Tạo file `.env` theo mẫu ở trên |

## Tài khoản mẫu

Sau khi chạy `createsuperuser`, bạn có thể đăng nhập với tài khoản admin tại:

- URL: /admin/
- Email: no data
- Mật khẩu: no data

## Các chức năng chính

### Cho khách hàng

- Xem sản phẩm, tìm kiếm, lọc theo hãng
- Thêm vào giỏ hàng, cập nhật số lượng
- Thêm sản phẩm yêu thích
- Đặt hàng với nhiều phương thức thanh toán
- Theo dõi trạng thái đơn hàng
- Đánh giá sản phẩm (chỉ sau khi mua thành công)
- Chat với chatbot để được tư vấn

### Cho admin

- Quản lý sản phẩm (thêm, sửa, xóa)
- Quản lý danh mục, hãng sản xuất
- Quản lý đơn hàng, cập nhật trạng thái
- Quản lý người dùng
- Tạo và quản lý mã giảm giá
- Xem thống kê sản phẩm bán chạy
- Quản lý banner quảng cáo

## Cấu hình VNPay (tùy chọn)

Nếu muốn sử dụng VNPay trong môi trường production, cần:

1. Đăng ký tài khoản VNPay
2. Lấy mã TmnCode và HashSecret từ VNPay
3. Cập nhật vào file .env

Trong môi trường development, có thể sử dụng sandbox của VNPay.

## Cấu hình chatbot AI

Chatbot sử dụng Claude API của Anthropic. Để kích hoạt:

1. Đăng ký tài khoản Anthropic
2. Lấy API key
3. Thêm vào file .env: ANTHROPIC_API_KEY

Nếu không cấu hình, chatbot sẽ hiển thị thông báo lỗi nhưng website vẫn hoạt động bình thường.

## Ghi chú

- Cho production, nên chuyển sang PostgreSQL
- Một số tính năng (VNPay, Claude API) cần cấu hình thêm mới hoạt động
- File db.sqlite3 đã có sẵn sản phẩm mẫu để test

## Liên hệ

- Email: <qhun22@gmail.com>
- Website: qhun22.com

---

Tài liệu được viết bởi Quang Huy Truong
