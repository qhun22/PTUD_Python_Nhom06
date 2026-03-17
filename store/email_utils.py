"""Email utilities for transactional notifications (SendGrid)."""

import os
import html
import logging
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _format_vnd(value):
    """Format number to VND style: 12.345.678 đ."""
    try:
        amount = int(value or 0)
    except Exception:
        amount = 0
    return f"{amount:,}".replace(",", ".") + " đ"


def _display_color(color_name):
    s = (color_name or "").strip()
    if " - " in s:
        suffix = s.split(" - ", 1)[1].strip()
        return suffix or s
    return s


def _absolute_image_url(url, base_url=None):
    """Return absolute URL for email images."""
    src = (url or "").strip().replace('\\\\', '/')
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http://") or src.startswith("https://"):
        return src

    # Prefer a configured public domain for email clients.
    env_root = os.getenv("APP_BASE_URL", "").strip()
    req_root = (base_url or "").strip()

    root = env_root or req_root
    if req_root and root:
        host = (urlparse(root).hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0") and env_root:
            root = env_root

    if not root:
        return ""

    if root.endswith("/"):
        root = root[:-1]
    if not src.startswith("/"):
        src = "/" + src
    return root + src


def send_order_invoice_email(order, base_url=None):
    """
    Send detailed invoice email to order.user.email via SendGrid.
    Returns True if request accepted by SendGrid, else False.
    """
    if not order or not getattr(order, "user", None):
        return False

    to_email = (getattr(order.user, "email", "") or "").strip()
    if not to_email:
        logger.warning("Order %s has no user email; skip invoice email", getattr(order, "order_code", ""))
        return False

    api_key = os.getenv("SENDGRID_API_KEY", "")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@qhun22.com")

    if not api_key:
        logger.warning("SENDGRID_API_KEY not configured; skip invoice email for %s", order.order_code)
        return False

    items_html = ""
    subtotal = 0

    for idx, item in enumerate(order.items.all(), 1):
        line_total = int((item.price or 0) * (item.quantity or 0))
        subtotal += line_total

        color = _display_color(item.color_name) or "Mặc định"
        storage = (item.storage or "").strip() or "Mặc định"

        raw_thumb = getattr(item, "thumbnail", "")
        if not raw_thumb and getattr(item, "product", None) and getattr(item.product, "image", None):
            try:
                raw_thumb = item.product.image.url
            except Exception:
                raw_thumb = ""

        img_src = _absolute_image_url(raw_thumb, base_url=base_url)
        img_html = (
            f"<img src='{html.escape(img_src)}' alt='Ảnh sản phẩm' style='width:56px;height:56px;object-fit:cover;border-radius:8px;border:1px solid #eee;'>"
            if img_src
            else "<div style='width:56px;height:56px;border-radius:8px;border:1px solid #eee;background:#fafafa;'></div>"
        )

        items_html += (
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:center;'>{idx}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:center;'>{img_html}</td>"
            f"<td style='padding:8px;border:1px solid #eee;'>{html.escape(item.product_name or 'Sản phẩm')}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:center;'>{html.escape(color)}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:center;'>{html.escape(storage)}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:center;'>{item.quantity}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:right;'>{_format_vnd(item.price)}</td>"
            f"<td style='padding:8px;border:1px solid #eee;text-align:right;font-weight:600;'>{_format_vnd(line_total)}</td>"
            f"</tr>"
        )

    customer_name = order.user.get_full_name() if hasattr(order.user, "get_full_name") else "Khách hàng"
    payment_method = order.get_payment_method_display() if hasattr(order, "get_payment_method_display") else order.payment_method
    status = order.get_status_display() if hasattr(order, "get_status_display") else order.status
    discount_amount = int(getattr(order, "discount_amount", 0) or 0)
    coupon_code = (getattr(order, "coupon_code", "") or "").strip()
    created_label = order.created_at.strftime("%d/%m/%Y %H:%M") if getattr(order, "created_at", None) else "-"

    coupon_note = f" ({html.escape(coupon_code)})" if coupon_code else ""
    discount_row = ""
    if discount_amount > 0:
        discount_row = (
            f"<tr>"
            f"<td style='padding:6px 0;color:#555;'>Giảm giá{coupon_note}</td>"
            f"<td style='padding:6px 0;text-align:right;color:#b91c1c;font-weight:600;'>- {_format_vnd(discount_amount)}</td>"
            f"</tr>"
        )

    html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:860px;margin:0 auto;padding:20px;background:#f8f9fa;color:#222;">
  <div style="background:#fff;border:1px solid #eee;border-radius:12px;padding:24px;">
    <div style="margin-bottom:14px;">
      <h2 style="margin:0;color:#111;font-size:24px;">Hóa đơn đơn hàng QHUN22</h2>
      <p style="margin:8px 0 0;color:#555;line-height:1.5;">Xin chào <strong>{html.escape(customer_name)}</strong>, cảm ơn bạn đã mua hàng tại QHUN22. Dưới đây là thông tin chi tiết đơn hàng của bạn.</p>
    </div>

    <div style="background:#fff5f5;border:1px solid #f5c2c7;border-radius:10px;padding:14px 16px;margin-bottom:16px;">
      <div style="margin-bottom:6px;"><strong>Mã đơn:</strong> {html.escape(order.order_code)}</div>
      <div style="margin-bottom:6px;"><strong>Thời gian tạo:</strong> {created_label}</div>
      <div style="margin-bottom:6px;"><strong>Phương thức thanh toán:</strong> {html.escape(payment_method)}</div>
      <div><strong>Trạng thái đơn:</strong> {html.escape(status)}</div>
    </div>

    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:14px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style='padding:8px;border:1px solid #eee;'>#</th>
          <th style='padding:8px;border:1px solid #eee;'>Ảnh</th>
          <th style='padding:8px;border:1px solid #eee;text-align:left;'>Sản phẩm</th>
          <th style='padding:8px;border:1px solid #eee;'>Màu</th>
          <th style='padding:8px;border:1px solid #eee;'>Dung lượng</th>
          <th style='padding:8px;border:1px solid #eee;'>SL</th>
          <th style='padding:8px;border:1px solid #eee;text-align:right;'>Đơn giá</th>
          <th style='padding:8px;border:1px solid #eee;text-align:right;'>Thành tiền</th>
        </tr>
      </thead>
      <tbody>
        {items_html}
      </tbody>
    </table>

    <table style="width:340px;max-width:100%;margin-left:auto;border-collapse:collapse;font-size:14px;">
      <tr>
        <td style="padding:6px 0;color:#555;">Tạm tính</td>
        <td style="padding:6px 0;text-align:right;">{_format_vnd(subtotal)}</td>
      </tr>
      {discount_row}
      <tr>
        <td style="padding:8px 0;border-top:1px solid #eee;font-weight:700;">Tổng thanh toán</td>
        <td style="padding:8px 0;border-top:1px solid #eee;text-align:right;color:#b91c1c;font-weight:700;font-size:16px;">{_format_vnd(order.total_amount)}</td>
      </tr>
    </table>

    <p style="margin:18px 0 0;color:#666;font-size:13px;line-height:1.5;">Đây là email tự động từ hệ thống QHUN22. Vui lòng không trả lời email này. Nếu cần hỗ trợ, bạn có thể liên hệ qua các kênh hỗ trợ trên website.</p>
  </div>
</div>
"""

    text_body = (
        f"Hóa đơn đơn hàng QHUN22\n"
        f"Mã đơn: {order.order_code}\n"
        f"Thời gian tạo: {created_label}\n"
        f"Phương thức thanh toán: {payment_method}\n"
        f"Trạng thái đơn: {status}\n"
        f"Tổng thanh toán: {_format_vnd(order.total_amount)}\n"
    )

    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": f"Hóa đơn đơn hàng {order.order_code} - QHUN22",
        }],
        "from": {"email": from_email},
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=12,
        )
        if resp.status_code in (200, 201, 202):
            return True
        logger.error("SendGrid invoice error %s: %s", resp.status_code, resp.text)
        return False
    except Exception:
        logger.exception("SendGrid invoice request failed for order %s", order.order_code)
        return False
