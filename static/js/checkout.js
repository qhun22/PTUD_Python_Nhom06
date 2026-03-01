/* ========================================
   QHUN22 - Checkout Page JS
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ==================== Config ==================== */
    var totalAmount = window.QH_CHECKOUT_TOTAL || 0;
    var discountAmount = 0; // Track discount amount

    /* ==================== Elements ==================== */
    var payOpts = document.querySelectorAll('.qh-checkout-pay-opt:not(.disabled)');
    var payText = document.getElementById('checkoutPayText');
    var summaryPayMethod = document.getElementById('summaryPayMethod');
    var summaryTotalEl = document.querySelector('.qh-checkout-summary-row.total .qh-checkout-summary-val');

    /* ==================== Helpers ==================== */
    function formatPrice(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + 'đ';
    }

    /* ==================== Payment Selection ==================== */
    function updatePaySelection(opt) {
        var label = opt.getAttribute('data-pay-label');
        if (payText && label) {
            payText.innerHTML = 'Bạn đang chọn hình thức thanh toán <strong>' + label + '</strong>';
        }
        var shortLabel = opt.getAttribute('data-pay-short');
        if (summaryPayMethod && shortLabel) {
            summaryPayMethod.textContent = shortLabel;
        }
    }

    payOpts.forEach(function (opt) {
        opt.addEventListener('click', function () {
            var payType = this.getAttribute('data-pay-type');

            document.querySelectorAll('.qh-checkout-pay-opt').forEach(function (o) {
                o.classList.remove('selected');
                o.classList.remove('verified');
            });

            this.classList.add('selected');

            if (payType === 'cod') {
                this.classList.add('verified');
            }

            if (summaryTotalEl) {
                summaryTotalEl.textContent = formatPrice(totalAmount);
            }

            updatePaySelection(this);
        });
    });

    var defaultSelected = document.querySelector('.qh-checkout-pay-opt.selected');
    if (defaultSelected) {
        updatePaySelection(defaultSelected);
    }

    /* ==================== VNPay Payment ==================== */
    function initiateVNPayPayment() {
        var submitBtn = document.getElementById('checkoutSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang chuyển hướng đến VNPay...';
        }

        var formData = new FormData();
        formData.append('amount', totalAmount);
        formData.append('order_description', 'Thanh toan QHUN22 - ' + totalAmount + ' VND');
        formData.append('items_param', window.QH_CHECKOUT_ITEMS_PARAM || '');

        fetch(window.QH_VNPAY_CREATE_URL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': QH_CSRF_TOKEN
            },
            body: formData
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success && data.payment_url) {
                    window.location.href = data.payment_url;
                } else {
                    if (window.QHToast) {
                        QHToast.show(data.message || 'Lỗi tạo thanh toán VNPay', 'error');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'ĐẶT HÀNG';
                    }
                }
            })
            .catch(function (err) {
                console.error('[VNPay Create Error]', err);
                if (window.QHToast) {
                    QHToast.show('Lỗi kết nối đến VNPay. Vui lòng thử lại.', 'error');
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'ĐẶT HÀNG';
                }
            });
    }

    /* ==================== VietQR → Redirect to Separate Page ==================== */
    function initiateVietQRPayment() {
        var submitBtn = document.getElementById('checkoutSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang tạo đơn hàng...';
        }

        fetch(window.QH_VIETQR_CREATE_ORDER_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': QH_CSRF_TOKEN
            },
            body: JSON.stringify({
                items_param: window.QH_CHECKOUT_ITEMS_PARAM || ''
            })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success && data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    if (window.QHToast) {
                        QHToast.show(data.message || 'Lỗi tạo đơn hàng VietQR', 'error');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'ĐẶT HÀNG';
                    }
                }
            })
            .catch(function (err) {
                console.error('[VietQR Create Error]', err);
                if (window.QHToast) {
                    QHToast.show('Lỗi kết nối. Vui lòng thử lại.', 'error');
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'ĐẶT HÀNG';
                }
            });
    }

    /* ==================== Place Order ==================== */
    var submitBtn = document.getElementById('checkoutSubmitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function () {
            var selected = document.querySelector('.qh-checkout-pay-opt.selected');
            if (!selected) {
                if (window.QHToast) {
                    QHToast.show('Vui lòng chọn phương thức thanh toán', 'error');
                }
                return;
            }
            var payType = selected.getAttribute('data-pay-type');

            if (payType === 'vnpay') {
                initiateVNPayPayment();
                return;
            }

            if (payType === 'vietqr') {
                initiateVietQRPayment();
                return;
            }

            placeOrder(payType);
        });
    }

    function placeOrder(payType) {
        var submitBtn = document.getElementById('checkoutSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang xử lý...';
        }

        var requestData = {
            payment_method: payType,
            items_param: window.QH_CHECKOUT_ITEMS_PARAM || '',
            coupon_code: window.QH_APPLIED_COUPON || ''
        };

        fetch(window.QH_PLACE_ORDER_URL || '/order/place/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': QH_CSRF_TOKEN
            },
            body: JSON.stringify(requestData)
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    if (window.QHToast) {
                        QHToast.show('Đặt hàng thành công!', 'success');
                    }
                    window.location.href = '/order/success/' + data.order_code + '/';
                } else {
                    if (window.QHToast) {
                        QHToast.show(data.message || 'Lỗi đặt hàng', 'error');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'ĐẶT HÀNG';
                    }
                }
            })
            .catch(function (err) {
                console.error('[Place Order Error]', err);
                if (window.QHToast) {
                    QHToast.show('Lỗi kết nối. Vui lòng thử lại.', 'error');
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'ĐẶT HÀNG';
                }
            });
    }

});

function applyCoupon() {
    var input = document.getElementById('couponInput');
    var msg = document.getElementById('couponMessage');
    var code = (input.value || '').trim().toUpperCase();
    
    if (!code) {
        if (window.QHToast) QHToast.show('Vui lòng nhập mã giảm giá', 'error');
        return;
    }
    
    var btn = document.getElementById('couponApplyBtn');
    btn.disabled = true;
    btn.textContent = 'Đang kiểm tra...';
    
    fetch(window.QH_COUPON_APPLY_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.QH_CSRF_TOKEN
        },
        body: JSON.stringify({
            code: code,
            order_total: window.QH_CHECKOUT_TOTAL,
            item_count: window.QH_ITEM_COUNT || 0
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.success) {
            msg.style.display = 'block';
            msg.style.color = '#16a34a';
            msg.textContent = 'Áp dụng thành công!';
            if (window.QHToast) QHToast.show('Đã áp dụng mã giảm giá thành công!', 'success');
            
            window.QH_APPLIED_COUPON = data.code;
            window.QH_DISCOUNT_AMOUNT = parseInt(data.discount);
            discountAmount = parseInt(data.discount); // Update discount tracker
            totalAmount = totalAmount - discountAmount; // Update total with discount
            
            var voucherEl = document.getElementById('summaryVoucher');
            var discountEl = document.getElementById('summaryDiscount');
            var totalEl = document.getElementById('summaryTotal');
            
            if (voucherEl) voucherEl.textContent = data.code;
            if (discountEl) discountEl.textContent = '-' + data.discount_display;
            if (totalEl) totalEl.textContent = data.new_total_display;
            
            input.disabled = true;
            btn.textContent = 'Đã áp dụng';
            btn.style.background = '#10b981';
        } else {
            if (window.QHToast) QHToast.show(data.message || 'Mã không hợp lệ', 'error');
            msg.style.display = 'block';
            msg.style.color = '#dc2626';
            msg.textContent = data.message || 'Mã không hợp lệ';
            btn.disabled = false;
            btn.textContent = 'Áp dụng';
        }
    })
    .catch(function() {
        if (window.QHToast) QHToast.show('Lỗi kết nối, vui lòng thử lại', 'error');
        btn.disabled = false;
        btn.textContent = 'Áp dụng';
    });
}
