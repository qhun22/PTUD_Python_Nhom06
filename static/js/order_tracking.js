/* ========================================================
   QHUN22 – Order Tracking Page JavaScript
   ======================================================== */

/* ========== Biến toàn cục ========== */
var _otCurrentCode = null;
var _otConfirmCallback = null;
var _otCancelData = { orderCode: null, btn: null };

/* ========== Lọc đơn hàng ========== */
/**
 * Lọc đơn hàng theo trạng thái
 * @param {string} status - Trạng thái cần lọc ('all', 'pending', 'processing', etc.)
 */
function filterOtOrders(status) {
    var rows = document.querySelectorAll('#otTableBody tr[data-status]');
    var stt = 0;
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        if (status === 'all' || r.getAttribute('data-status') === status) {
            r.style.display = '';
            stt++;
            var sttCell = r.querySelector('.stt');
            if (sttCell) sttCell.textContent = stt;
        } else {
            r.style.display = 'none';
        }
    }
    // Cập nhật nút active
    var btns = document.querySelectorAll('.qh-ot-filter-btn');
    btns.forEach(function(b) {
        if (b.getAttribute('data-filter') === status) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
}

/* ========== Modal Chi tiết đơn hàng ========== */
/**
 * Mở modal chi tiết đơn hàng
 * @param {string} code - Mã đơn hàng
 */
function openOtDetail(code) {
    _otCurrentCode = code;
    var modal = document.getElementById('otDetailModal');
    var body = document.getElementById('otDetailBody');
    var footer = document.getElementById('otDetailFooter');
    modal.classList.add('show');

    var o = OT_ORDERS[code];
    if (!o) {
        body.innerHTML = '<p style="text-align:center;color:#ef4444;">Không tìm thấy đơn hàng</p>';
        footer.innerHTML = '';
        return;
    }

    var html = '';

    // Danh sách sản phẩm
    html += '<div style="margin-bottom: 16px;">';
    html += '<h4 style="font-size:14px;font-weight:600;color:#334155;margin:0 0 10px;">Sản phẩm</h4>';
    o.items.forEach(function(item) {
        html += '<div style="display:flex; gap:12px; align-items:center; padding:10px 0; border-bottom:1px solid #f1f5f9;">';
        // Ảnh thumbnail
        if (item.thumbnail) {
            html += '<img src="' + escOtHtml(item.thumbnail) + '" alt="" style="width:56px; height:56px; border-radius:8px; object-fit:cover; flex-shrink:0; background:#f8fafc;">';
        } else {
            html += '<div style="width:56px; height:56px; border-radius:8px; background:#f1f5f9; display:flex; align-items:center; justify-content:center; flex-shrink:0; color:#94a3b8;">';
            html += '<svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg></div>';
        }
        // Thông tin
        html += '<div style="flex:1; min-width:0;">';
        html += '<div style="font-size:14px; font-weight:600; color:#1e293b; margin-bottom:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + escOtHtml(item.product_name) + '</div>';
        html += '<div style="font-size:12px; color:#64748b;">';
        if (item.color_name && item.color_name !== '—') html += 'Màu: ' + escOtHtml(item.color_name);
        if (item.storage && item.storage !== '—') html += ' &nbsp;|&nbsp; ' + escOtHtml(item.storage);
        html += ' &nbsp;|&nbsp; SL: ' + item.quantity;
        html += '</div></div>';
        // Giá
        html += '<div style="flex-shrink:0; text-align:right; font-size:14px; font-weight:700; color:#1e293b;">' + fmtOtVND(item.price) + '</div>';
        html += '</div>';
    });
    html += '</div>';

    // Thông tin đơn hàng
    html += '<div class="qh-ot-detail-block">';
    html += '<div class="qh-ot-info-grid">';
    html += otInfoRow('Mã đơn hàng', '<span style="color:#3b82f6;font-weight:600;font-family:monospace;">' + escOtHtml(o.order_code) + '</span>');
    html += otInfoRow('Hình thức TT', otPayBadge(o.payment_method, o.payment_display));
    html += otInfoRow('Ngày đặt', escOtHtml(o.created_at));

    // Mã giảm giá
    if (o.coupon_code) {
        html += otInfoRow('Voucher đã dùng', '<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:4px; font-weight:600; font-size:12px; letter-spacing:0.5px;">' + escOtHtml(o.coupon_code) + '</span>');
        html += otInfoRow('Chiết khấu', '<span style="color:#dc2626; font-weight:600;">-' + fmtOtVND(o.discount_amount) + '</span>');
    }

    // Trạng thái
    var statusHtml = '';
    if (o.status === 'cancelled' && o.refund_status === 'pending') {
        statusHtml = '<span class="qh-ot-badge refunding">Chờ hoàn tiền</span>';
    } else if (o.status === 'cancelled' && o.refund_status === 'completed') {
        statusHtml = '<span class="qh-ot-badge delivered">Đã tất toán</span>';
    } else if (o.status === 'cancelled') {
        statusHtml = '<span class="qh-ot-badge cancelled">Đã hủy</span>';
    } else {
        statusHtml = '<span class="qh-ot-badge ' + o.status + '">' + escOtHtml(o.status_display) + '</span>';
    }
    html += otInfoRow('Trạng thái', statusHtml);
    html += '</div>';
    html += '<div class="qh-ot-total-row">';
    html += '<span style="font-size:14px;font-weight:600;color:#334155;">Tổng cộng</span>';
    html += '<span style="font-size:18px;font-weight:700;color:#ef4444;">' + fmtOtVND(o.total_amount) + '</span>';
    html += '</div></div>';

    body.innerHTML = html;

    // Footer: nút hủy nếu đơn đang chờ/xử lý
    footer.innerHTML = '';
    if (o.status === 'pending' || o.status === 'processing') {
        var cancelBtn = document.createElement('button');
        cancelBtn.className = 'qh-ot-modal-cancel-btn';
        cancelBtn.innerHTML = '<i class="ri-close-circle-line"></i> Hủy đơn hàng';
        cancelBtn.onclick = function() { cancelOtOrder(o.order_code, cancelBtn, o.payment_method); };
        footer.appendChild(cancelBtn);
    }
}

/**
 * Đóng modal chi tiết đơn hàng
 */
function closeOtDetail() {
    document.getElementById('otDetailModal').classList.remove('show');
    _otCurrentCode = null;
}

/**
 * Đóng modal khi click bên ngoài
 * @param {Event} event - Sự kiện click
 */
function closeOtDetailOnClickOutside(event) {
    if (event.target.classList.contains('qh-ot-modal-overlay')) {
        closeOtDetail();
    }
}

/* ========== Modal Xác nhận ========== */
/**
 * Hiển thị modal xác nhận
 * @param {string} message - Nội dung thông báo
 * @param {Function} callback - Hàm callback khi xác nhận
 */
function showOtConfirm(message, callback) {
    document.getElementById('otConfirmText').textContent = message;
    document.getElementById('otConfirmModal').classList.add('show');
    _otConfirmCallback = callback;
    document.getElementById('otConfirmBtn').onclick = function() {
        closeOtConfirm();
        if (_otConfirmCallback) _otConfirmCallback();
    };
}

/**
 * Đóng modal xác nhận
 */
function closeOtConfirm() {
    document.getElementById('otConfirmModal').classList.remove('show');
    _otConfirmCallback = null;
}

/* ========== Hàm hỗ trợ ========== */
/**
 * Escape HTML để tránh XSS
 * @param {string} s - Chuỗi cần escape
 * @returns {string} Chuỗi đã escape
 */
function escOtHtml(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
}

/**
 * Định dạng tiền tệ Việt Nam
 * @param {string|number} v - Số tiền
 * @returns {string} Chuỗi đã định dạng
 */
function fmtOtVND(v) {
    var n = parseInt(v, 10);
    if (isNaN(n)) return '0đ';
    return n.toLocaleString('vi-VN') + 'đ';
}

/**
 * Tạo hàng thông tin cho grid
 * @param {string} label - Nhãn
 * @param {string} value - Giá trị
 * @returns {string} HTML của hàng
 */
function otInfoRow(label, value) {
    return '<span class="qh-ot-info-label">' + label + '</span><span class="qh-ot-info-value">' + value + '</span>';
}

/**
 * Tạo badge cho phương thức thanh toán
 * @param {string} key - Khóa phương thức
 * @param {string} display - Tên hiển thị
 * @returns {string} HTML của badge
 */
function otPayBadge(key, display) {
    var cls = {cod: 'pending', vietqr: 'processing', vnpay: 'shipped'};
    return '<span class="qh-ot-badge ' + (cls[key] || '') + '">' + escOtHtml(display) + '</span>';
}

/**
 * Lấy giá trị cookie
 * @param {string} name - Tên cookie
 * @returns {string} Giá trị cookie
 */
function getCookie(name) {
    var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
}

/* ========== Hủy đơn hàng ========== */
/**
 * Hủy đơn hàng - hiển thị modal xác nhận hoặc modal hoàn tiền
 * @param {string} orderCode - Mã đơn hàng
 * @param {HTMLElement} btn - Nút bấm
 * @param {string} paymentMethod - Phương thức thanh toán
 */
function cancelOtOrder(orderCode, btn, paymentMethod) {
    _otCancelData = { orderCode: orderCode, btn: btn };

    // COD - thanh toán khi nhận hàng: hủy bình thường
    if (paymentMethod === 'cod') {
        QHConfirm.show(
            'Bạn có chắc muốn hủy đơn hàng ' + orderCode + '?',
            function() {
                doCancelOtOrder(orderCode, btn);
            }
        );
        return;
    }

    // VNPay/VietQR - cần nhập thông tin hoàn tiền
    document.getElementById('otRefundAccount').value = '';
    document.getElementById('otRefundBank').value = '';
    document.getElementById('otRefundModal').classList.add('show');
}

/**
 * Đóng modal hoàn tiền
 */
function closeOtRefundModal() {
    document.getElementById('otRefundModal').classList.remove('show');
}

/**
 * Gửi yêu cầu hoàn tiền
 */
function submitOtRefund() {
    var account = document.getElementById('otRefundAccount').value.trim();
    var bank = document.getElementById('otRefundBank').value.trim();

    if (!account) {
        QHToast.show('Vui lòng nhập số tài khoản', 'error');
        return;
    }
    if (!bank) {
        QHToast.show('Vui lòng nhập tên ngân hàng', 'error');
        return;
    }

    closeOtRefundModal();
    doCancelOtOrder(_otCancelData.orderCode, _otCancelData.btn, { account: account, bank: bank });
}

/**
 * Thực hiện hủy đơn hàng (gọi API)
 * @param {string} orderCode - Mã đơn hàng
 * @param {HTMLElement} btn - Nút bấm
 * @param {Object} refundInfo - Thông tin hoàn tiền (tùy chọn)
 */
function doCancelOtOrder(orderCode, btn, refundInfo) {
    btn.disabled = true;
    btn.innerHTML = '<i class="ri-loader-2-line"></i> Đang hủy...';

    var bodyData = { order_code: orderCode };
    if (refundInfo) {
        bodyData.refund_account = refundInfo.account;
        bodyData.refund_bank = refundInfo.bank;
    }

    fetch('/api/cancel-order/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(bodyData)
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            QHToast.success('Đã hủy đơn hàng và yêu cầu hoàn tiền thành công!');
            location.reload();
        } else {
            QHToast.show(data.message || 'Có lỗi xảy ra', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="ri-close-circle-line"></i> Hủy đơn hàng';
        }
    })
    .catch(function(err) {
        console.error(err);
        QHToast.show('Có lỗi xảy ra khi hủy đơn', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="ri-close-circle-line"></i> Hủy đơn hàng';
    });
}
