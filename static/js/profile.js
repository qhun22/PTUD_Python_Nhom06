/**
 * Profile Page JavaScript
 * Chứa các function JS thuần (không có Django template tags)
 */

/* ==================== Sao chép mã voucher ==================== */
/**
 * Sao chép mã voucher vào clipboard
 * @param {HTMLElement} btn - Nút sao chép
 * @param {string} code - Mã voucher
 */
function copyVoucher(btn, code) {
    navigator.clipboard.writeText(code).then(function () {
        var orig = btn.innerHTML;
        btn.innerHTML = '<svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Đã sao chép';
        btn.style.borderColor = '#10b981';
        btn.style.color = '#10b981';
        if (window.QHToast) QHToast.show('Đã sao chép mã ' + code, 'success');
        setTimeout(function () {
            btn.innerHTML = orig;
            btn.style.borderColor = '#cbd5e1';
            btn.style.color = '#64748b';
        }, 2000);
    });
}

/* ==================== Token CSRF (mã xác thực) ==================== */
/**
 * Lấy CSRF token từ cookie
 * @returns {string|null} Giá trị CSRF token
 */
function getAddrCsrf() {
    var name = 'csrftoken';
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/* ==================== Dữ liệu địa chỉ ==================== */
var provincesData = [];
var districtsData = [];
var wardsData = [];

/**
 * Tải danh sách tỉnh/thành phố từ API
 */
function loadProvinces() {
    fetch('https://provinces.open-api.vn/api/p/')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            provincesData = data;
            var sel = document.getElementById('addrProvince');
            if (!sel) return;
            sel.innerHTML = '<option value="">-- Chọn Tỉnh/Thành phố --</option>';
            data.forEach(function (p) {
                sel.innerHTML += '<option value="' + p.code + '">' + p.name + '</option>';
            });
        })
        .catch(function (err) { console.error('Lỗi tải tỉnh/thành:', err); });
}

/**
 * Tải danh sách quận/huyện khi chọn tỉnh
 */
function loadDistricts() {
    var sel = document.getElementById('addrProvince');
    var distSel = document.getElementById('addrDistrict');
    var wardSel = document.getElementById('addrWard');
    distSel.innerHTML = '<option value="">-- Chọn Quận/Huyện --</option>';
    distSel.disabled = true;
    wardSel.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
    wardSel.disabled = true;

    if (!sel.value) return;

    fetch('https://provinces.open-api.vn/api/p/' + sel.value + '?depth=2')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            districtsData = data.districts || [];
            distSel.disabled = false;
            districtsData.forEach(function (d) {
                distSel.innerHTML += '<option value="' + d.code + '">' + d.name + '</option>';
            });
        })
        .catch(function (err) { console.error('Lỗi tải quận/huyện:', err); });
}

/**
 * Tải danh sách phường/xã khi chọn quận
 */
function loadWards() {
    var distSel = document.getElementById('addrDistrict');
    var wardSel = document.getElementById('addrWard');
    wardSel.innerHTML = '<option value="">-- Chọn Phường/Xã --</option>';
    wardSel.disabled = true;

    if (!distSel.value) return;

    fetch('https://provinces.open-api.vn/api/d/' + distSel.value + '?depth=2')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            wardsData = data.wards || [];
            wardSel.disabled = false;
            wardsData.forEach(function (w) {
                wardSel.innerHTML += '<option value="' + w.code + '">' + w.name + '</option>';
            });
        })
        .catch(function (err) { console.error('Lỗi tải phường/xã:', err); });
}

/* ==================== Thêm địa chỉ ==================== */
/**
 * Xử lý submit form thêm địa chỉ
 * @param {Event} e - Sự kiện submit form
 */
function submitAddress(e) {
    e.preventDefault();
    var form = document.getElementById('addAddressForm');
    var btn = document.getElementById('addrSubmitBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="ri-loader-4-line" style="margin-right:4px;"></i> Đang thêm...';

    var provinceSel = document.getElementById('addrProvince');
    var districtSel = document.getElementById('addrDistrict');
    var wardSel = document.getElementById('addrWard');

    var body = 'full_name=' + encodeURIComponent(form.full_name.value)
        + '&phone=' + encodeURIComponent(form.phone.value)
        + '&province_code=' + provinceSel.value
        + '&province_name=' + encodeURIComponent(provinceSel.options[provinceSel.selectedIndex].text)
        + '&district_code=' + districtSel.value
        + '&district_name=' + encodeURIComponent(districtSel.options[districtSel.selectedIndex].text)
        + '&ward_code=' + wardSel.value
        + '&ward_name=' + encodeURIComponent(wardSel.options[wardSel.selectedIndex].text)
        + '&detail=' + encodeURIComponent(form.detail.value)
        + '&is_default=' + (document.getElementById('addrDefault').checked ? 'true' : 'false');

    fetch('/address/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getAddrCsrf()
        },
        body: body
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                if (window.QHToast) QHToast.show(data.message, 'success');
                setTimeout(function () { location.reload(); }, 600);
            } else {
                if (window.QHToast) QHToast.show(data.message, 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="ri-add-line" style="margin-right:4px;"></i> Thêm địa chỉ';
            }
        })
        .catch(function (err) {
            console.error('Lỗi:', err);
            if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="ri-add-line" style="margin-right:4px;"></i> Thêm địa chỉ';
        });

    return false;
}

/* ==================== Xóa địa chỉ ==================== */
/**
 * Xóa địa chỉ (hiển thị confirm)
 * @param {number} id - ID địa chỉ cần xóa
 */
function deleteAddress(id) {
    if (typeof QHConfirm !== 'undefined' && QHConfirm && QHConfirm.show) {
        QHConfirm.show('Bạn có chắc muốn xóa địa chỉ này?', function () {
            doDeleteAddress(id);
        });
    } else {
        // Phương án dự phòng khi không có thư viện xác nhận
        if (confirm('Bạn có chắc muốn xóa địa chỉ này?')) {
            doDeleteAddress(id);
        }
    }
}

/**
 * Thực hiện xóa địa chỉ
 * @param {number} id - ID địa chỉ cần xóa
 */
function doDeleteAddress(id) {
    fetch('/address/delete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getAddrCsrf()
        },
        body: 'address_id=' + id
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                if (window.QHToast) QHToast.show(data.message, 'success');
                setTimeout(function () { location.reload(); }, 600);
            } else {
                if (window.QHToast) QHToast.show(data.message, 'error');
            }
        })
        .catch(function (err) {
            console.error('Lỗi:', err);
            if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
        });
}

/* ==================== Đặt địa chỉ mặc định ==================== */
/**
 * Đặt địa chỉ mặc định
 * @param {number} id - ID địa chỉ
 */
function setDefaultAddress(id) {
    fetch('/address/set-default/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getAddrCsrf()
        },
        body: 'address_id=' + id
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                if (window.QHToast) QHToast.show(data.message, 'success');
                setTimeout(function () { location.reload(); }, 600);
            } else {
                if (window.QHToast) QHToast.show(data.message, 'error');
            }
        })
        .catch(function (err) {
            console.error('Lỗi:', err);
            if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
        });
}

/* ==================== Hoàn tiền ==================== */
/**
 * Lấy cookie theo tên
 * @param {string} name - Tên cookie
 * @returns {string} Giá trị cookie
 */
function qhGetCookie(name) {
    var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
}

/**
 * Tải dữ liệu hoàn tiền (đơn cần hoàn + lịch sử)
 */
function qhLoadRefundData() {
    // Tải đơn cần hoàn tiền
    fetch('/api/refund-pending/', {
        method: 'GET',
        headers: { 'X-CSRFToken': qhGetCookie('csrftoken') }
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var listEl = document.getElementById('qh-refund-pending-list');
            if (data.orders && data.orders.length > 0) {
                var html = '<table class="qh-refund-table" style="width:100%;font-size:13px;border-collapse:collapse;">';
                html += '<thead><tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">';
                html += '<th style="padding:8px;text-align:left;font-weight:600;color:#64748b;">Mã đơn</th>';
                html += '<th style="padding:8px;text-align:left;font-weight:600;color:#64748b;">Sản phẩm</th>';
                html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">Trạng thái</th>';
                html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">Xem</th>';
                html += '</tr></thead><tbody>';
                data.orders.forEach(function (o) {
                    html += '<tr style="border-bottom:1px solid #f1f5f9;">';
                    html += '<td style="padding:8px;color:#3b82f6;font-weight:600;">' + o.order_code + '</td>';
                    html += '<td style="padding:8px;color:#1e293b;">' + (o.items.length > 0 ? o.items[0].product_name : '—') + '</td>';
                    html += '<td style="padding:8px;text-align:center;"><span class="qh-ot-badge cancelled">Chờ hoàn tiền</span></td>';
                    html += '<td style="padding:8px;text-align:center;"><button onclick="qhShowRefundDetail(\'' + o.order_code + '\')" style="padding:4px 12px;background:#3b82f6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">Xem</button></td>';
                    html += '</tr>';
                });
                html += '</tbody></table>';
                listEl.innerHTML = html;
            } else {
                listEl.innerHTML = '<p style="color:#94a3b8;font-size:14px;text-align:center;padding:20px;">Không có đơn cần hoàn tiền</p>';
            }
        })
        .catch(function (err) {
            document.getElementById('qh-refund-pending-list').innerHTML = '<p style="color:#ef4444;font-size:14px;text-align:center;padding:20px;">Lỗi tải dữ liệu</p>';
        });

    // Tải lịch sử hoàn tiền
    fetch('/api/refund-history/', {
        method: 'GET',
        headers: { 'X-CSRFToken': qhGetCookie('csrftoken') }
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var listEl = document.getElementById('qh-refund-history-list');
            if (data.orders && data.orders.length > 0) {
                var html = '';
                data.orders.forEach(function (o) {
                    var productName = o.items.length > 0 ? o.items[0].product_name : '—';
                    html += '<div style="padding:12px;background:#f8fafc;border-radius:8px;margin-bottom:8px;cursor:pointer;" onclick="qhShowRefundDetail(\'' + o.order_code + '\')">';
                    html += '<div style="display:flex;justify-content:space-between;align-items:center;">';
                    html += '<span style="color:#3b82f6;font-weight:600;font-size:13px;">' + o.order_code + '</span>';
                    html += '<span style="color:#10b981;font-weight:600;font-size:14px;">Đã hoàn ' + qhFmtVND(o.total_amount) + '</span>';
                    html += '</div>';
                    html += '<div style="color:#64748b;font-size:12px;margin-top:4px;">' + productName + '</div>';
                    html += '</div>';
                });
                listEl.innerHTML = html;
            } else {
                listEl.innerHTML = '<p style="color:#94a3b8;font-size:14px;text-align:center;padding:20px;">Chưa có lịch sử hoàn tiền</p>';
            }
        })
        .catch(function (err) {
            document.getElementById('qh-refund-history-list').innerHTML = '<p style="color:#ef4444;font-size:14px;text-align:center;padding:20px;">Lỗi tải dữ liệu</p>';
        });
}

/**
 * Hiển thị chi tiết hoàn tiền
 * @param {string} orderCode - Mã đơn hàng
 */
function qhShowRefundDetail(orderCode) {
    fetch('/api/refund-detail/' + orderCode + '/', {
        method: 'GET',
        headers: { 'X-CSRFToken': qhGetCookie('csrftoken') }
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var modal = document.getElementById('qhRefundDetailModal');
            var body = document.getElementById('qhRefundDetailBody');
            modal.classList.add('active');

            if (!data.order) {
                body.innerHTML = '<p style="color:#ef4444;text-align:center;">Không tìm thấy đơn hàng</p>';
                return;
            }

            var o = data.order;
            var html = '<table style="width:100%;font-size:13px;border-collapse:collapse;margin-bottom:16px;">';
            html += '<thead><tr style="background:#f8fafc;">';
            html += '<th style="padding:8px;text-align:left;font-weight:600;color:#64748b;">Mã đơn</th>';
            html += '<th style="padding:8px;text-align:left;font-weight:600;color:#64748b;">Sản phẩm</th>';
            html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">SL</th>';
            html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">Màu</th>';
            html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">Bộ nhớ</th>';
            html += '<th style="padding:8px;text-align:right;font-weight:600;color:#64748b;">Giá</th>';
            html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">STK</th>';
            html += '<th style="padding:8px;text-align:center;font-weight:600;color:#64748b;">Ngân hàng</th>';
            html += '</tr></thead><tbody>';

            o.items.forEach(function (item) {
                html += '<tr style="border-bottom:1px solid #f1f5f9;">';
                html += '<td style="padding:8px;color:#3b82f6;font-weight:600;">' + o.order_code + '</td>';
                html += '<td style="padding:8px;color:#1e293b;">' + item.product_name + '</td>';
                html += '<td style="padding:8px;text-align:center;color:#64748b;">' + item.quantity + '</td>';
                html += '<td style="padding:8px;text-align:center;color:#64748b;">' + (item.color_name || '—') + '</td>';
                html += '<td style="padding:8px;text-align:center;color:#64748b;">' + (item.storage || '—') + '</td>';
                html += '<td style="padding:8px;text-align:right;color:#1e293b;font-weight:600;">' + qhFmtVND(item.price) + '</td>';
                html += '<td style="padding:8px;text-align:center;color:#64748b;">' + (o.refund_account || '—') + '</td>';
                html += '<td style="padding:8px;text-align:center;color:#64748b;">' + (o.refund_bank || '—') + '</td>';
                html += '</tr>';
            });
            html += '</tbody></table>';

            html += '<div style="background:#f8fafc;padding:12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;">';
            html += '<span style="font-weight:600;color:#334155;">Tổng hoàn tiền:</span>';
            html += '<span style="font-size:18px;font-weight:700;color:#ef4444;">' + qhFmtVND(o.total_amount) + '</span>';
            html += '</div>';

            body.innerHTML = html;
        })
        .catch(function (err) {
            document.getElementById('qhRefundDetailBody').innerHTML = '<p style="color:#ef4444;text-align:center;">Lỗi tải dữ liệu</p>';
        });
}

/**
 * Đóng modal chi tiết hoàn tiền
 */
function qhCloseRefundDetail() {
    document.getElementById('qhRefundDetailModal').classList.remove('active');
}

/**
 * Đóng modal khi click bên ngoài
 * @param {Event} event - Sự kiện click
 */
function qhCloseRefundDetailOnClickOutside(event) {
    if (event.target.classList.contains('qh-modal-overlay')) {
        qhCloseRefundDetail();
    }
}

/**
 * Định dạng tiền VND
 * @param {number|string} v - Số tiền
 * @returns {string} Chuỗi tiền VND đã định dạng
 */
function qhFmtVND(v) {
    var n = parseInt(v, 10);
    if (isNaN(n)) return '0đ';
    return n.toLocaleString('vi-VN') + 'đ';
}

/* ==================== Khởi tạo khi trang tải xong ==================== */
document.addEventListener('DOMContentLoaded', function () {
    // ===== Chuyển đổi tab =====
    var tabs = document.querySelectorAll('.qh-pf-tab[data-tab]');
    var panels = document.querySelectorAll('.qh-pf-tab-panel');

    function activateTab(tabName) {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        panels.forEach(function (p) { p.classList.remove('active'); });
        var targetTab = document.querySelector('.qh-pf-tab[data-tab="' + tabName + '"]');
        var targetPanel = document.getElementById('tab-' + tabName);
        if (targetTab) targetTab.classList.add('active');
        if (targetPanel) targetPanel.classList.add('active');
        // Lưu tab hiện tại vào sessionStorage
        sessionStorage.setItem('qh_active_tab', tabName);
    }

    // Khôi phục tab từ URL hoặc sessionStorage
    var urlParams = new URLSearchParams(window.location.search);
    var tabParam = urlParams.get('tab');
    var savedTab = sessionStorage.getItem('qh_active_tab');

    // Ưu tiên: URL param > savedTab > mặc định (address)
    var activeTab = tabParam || savedTab || 'address';
    activateTab(activeTab);

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            var target = this.getAttribute('data-tab');
            activateTab(target);
        });
    });

    // ===== Phân trang lịch sử đổi mật khẩu =====
    var PW_PER_PAGE = 4;
    var pwItems = document.querySelectorAll('.qh-pf-pw-item[data-pw-index]');
    var pwPagination = document.getElementById('pwPagination');

    if (pwItems.length > 0 && pwPagination) {
        var totalPages = Math.ceil(pwItems.length / PW_PER_PAGE);

        function showPwPage(page) {
            var start = (page - 1) * PW_PER_PAGE;
            var end = start + PW_PER_PAGE;
            pwItems.forEach(function (item, i) {
                item.style.display = (i >= start && i < end) ? '' : 'none';
            });
            renderPwPagination(page);
        }

        function renderPwPagination(current) {
            if (totalPages <= 1) { pwPagination.style.display = 'none'; return; }
            var html = '';
            html += '<button class="qh-pf-pw-page-btn" data-pw-page="' + (current - 1) + '"' + (current === 1 ? ' disabled' : '') + '><i class="ri-arrow-left-s-line"></i></button>';
            for (var p = 1; p <= totalPages; p++) {
                html += '<button class="qh-pf-pw-page-btn' + (p === current ? ' active' : '') + '" data-pw-page="' + p + '">' + p + '</button>';
            }
            html += '<button class="qh-pf-pw-page-btn" data-pw-page="' + (current + 1) + '"' + (current === totalPages ? ' disabled' : '') + '><i class="ri-arrow-right-s-line"></i></button>';
            pwPagination.innerHTML = html;

            pwPagination.querySelectorAll('.qh-pf-pw-page-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    if (this.disabled) return;
                    showPwPage(parseInt(this.getAttribute('data-pw-page')));
                });
            });
        }

        showPwPage(1);
    }

    // ===== Phân trang địa chỉ =====
    var ADDR_PER_PAGE = 3;
    var addrItems = document.querySelectorAll('.qh-pf-addr-card[data-addr-index]');
    var addrPagination = document.getElementById('addrPagination');

    if (addrItems.length > 0 && addrPagination) {
        var addrTotalPages = Math.ceil(addrItems.length / ADDR_PER_PAGE);

        function showAddrPage(page) {
            var start = (page - 1) * ADDR_PER_PAGE;
            var end = start + ADDR_PER_PAGE;
            addrItems.forEach(function (item, i) {
                item.style.display = (i >= start && i < end) ? '' : 'none';
            });
            renderAddrPagination(page);
        }

        function renderAddrPagination(current) {
            if (addrTotalPages <= 1) { addrPagination.style.display = 'none'; return; }
            var html = '';
            html += '<button class="qh-pf-pw-page-btn" data-addr-page="' + (current - 1) + '"' + (current === 1 ? ' disabled' : '') + '><i class="ri-arrow-left-s-line"></i></button>';
            for (var p = 1; p <= addrTotalPages; p++) {
                html += '<button class="qh-pf-pw-page-btn' + (p === current ? ' active' : '') + '" data-addr-page="' + p + '">' + p + '</button>';
            }
            html += '<button class="qh-pf-pw-page-btn" data-addr-page="' + (current + 1) + '"' + (current === addrTotalPages ? ' disabled' : '') + '><i class="ri-arrow-right-s-line"></i></button>';
            addrPagination.innerHTML = html;

            addrPagination.querySelectorAll('.qh-pf-pw-page-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    if (this.disabled) return;
                    showAddrPage(parseInt(this.getAttribute('data-addr-page')));
                });
            });
        }

        showAddrPage(1);
    }

    // ===== Phân trang mã giảm giá =====
    var COUPON_PER_PAGE = 9;
    var couponItems = document.querySelectorAll('.qh-pf-coupon-card[data-coupon-index]');
    var couponPagination = document.getElementById('couponPagination');

    if (couponItems.length > 0 && couponPagination) {
        var couponTotalPages = Math.ceil(couponItems.length / COUPON_PER_PAGE);

        function showCouponPage(page) {
            var start = (page - 1) * COUPON_PER_PAGE;
            var end = start + COUPON_PER_PAGE;
            couponItems.forEach(function (item, i) {
                item.style.display = (i >= start && i < end) ? '' : 'none';
            });
            renderCouponPagination(page);
        }

        function renderCouponPagination(current) {
            if (couponTotalPages <= 1) { couponPagination.style.display = 'none'; return; }
            var html = '';
            html += '<button class="qh-pf-pw-page-btn" data-coupon-page="' + (current - 1) + '"' + (current === 1 ? ' disabled' : '') + '><i class="ri-arrow-left-s-line"></i></button>';
            for (var p = 1; p <= couponTotalPages; p++) {
                html += '<button class="qh-pf-pw-page-btn' + (p === current ? ' active' : '') + '" data-coupon-page="' + p + '">' + p + '</button>';
            }
            html += '<button class="qh-pf-pw-page-btn" data-coupon-page="' + (current + 1) + '"' + (current === couponTotalPages ? ' disabled' : '') + '><i class="ri-arrow-right-s-line"></i></button>';
            couponPagination.innerHTML = html;

            couponPagination.querySelectorAll('.qh-pf-pw-page-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    if (this.disabled) return;
                    showCouponPage(parseInt(this.getAttribute('data-coupon-page')));
                });
            });
        }

        showCouponPage(1);
    }

    // ===== Phân trang lịch sử đơn hàng =====
    var ORDER_PER_PAGE = 9;
    var orderItems = document.querySelectorAll('.qh-pf-order-card[data-order-index]');
    var orderPagination = document.getElementById('orderPagination');

    if (orderItems.length > 0 && orderPagination) {
        var orderTotalPages = Math.ceil(orderItems.length / ORDER_PER_PAGE);

        function showOrderPage(page) {
            var start = (page - 1) * ORDER_PER_PAGE;
            var end = start + ORDER_PER_PAGE;
            orderItems.forEach(function (item, i) {
                item.style.display = (i >= start && i < end) ? '' : 'none';
            });
            renderOrderPagination(page);
        }

        function renderOrderPagination(current) {
            if (orderTotalPages <= 1) { orderPagination.style.display = 'none'; return; }
            var html = '';
            html += '<button class="qh-pf-pw-page-btn" data-order-page="' + (current - 1) + '"' + (current === 1 ? ' disabled' : '') + '><i class="ri-arrow-left-s-line"></i></button>';
            for (var p = 1; p <= orderTotalPages; p++) {
                html += '<button class="qh-pf-pw-page-btn' + (p === current ? ' active' : '') + '" data-order-page="' + p + '">' + p + '</button>';
            }
            html += '<button class="qh-pf-pw-page-btn" data-order-page="' + (current + 1) + '"' + (current === orderTotalPages ? ' disabled' : '') + '><i class="ri-arrow-right-s-line"></i></button>';
            orderPagination.innerHTML = html;

            orderPagination.querySelectorAll('.qh-pf-pw-page-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    if (this.disabled) return;
                    showOrderPage(parseInt(this.getAttribute('data-order-page')));
                });
            });
        }

        showOrderPage(1);
    }

    // ===== Tải danh sách tỉnh/thành =====
    loadProvinces();

    // ===== Tải dữ liệu hoàn tiền khi tab được mở =====
    var allTabs = document.querySelectorAll('.qh-pf-tab[data-tab]');
    allTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var target = this.getAttribute('data-tab');
            if (target === 'refund') {
                setTimeout(qhLoadRefundData, 100);
            }
        });
    });
});
