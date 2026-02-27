/* ========================================
   QHUN22 - Checkout Page JS
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ==================== Config ==================== */
    var BANK_ID = 'TCB';
    var ACCOUNT_NO = '22100588888888';
    var ACCOUNT_NAME = 'TRUONG QUANG HUY';
    var QR_TIMEOUT = 15 * 60; // 15 phút (giây)

    var totalAmount = window.QH_CHECKOUT_TOTAL || 0;
    var qrTimerInterval = null;
    var qrPollInterval = null;
    var currentTransferCode = null;
    var vietqrPaid = false;

    /* ==================== Elements ==================== */
    var payOpts = document.querySelectorAll('.qh-checkout-pay-opt:not(.disabled)');
    var payText = document.getElementById('checkoutPayText');
    var summaryPayMethod = document.getElementById('summaryPayMethod');
    var summaryTotalEl = document.querySelector('.qh-checkout-summary-row.total .qh-checkout-summary-val');

    // QR elements
    var qrBox = document.getElementById('vietqrBox');
    var qrContent = document.getElementById('vietqrContent');
    var qrSuccess = document.getElementById('vietqrSuccess');
    var qrImage = document.getElementById('vietqrImage');
    var qrAmount = document.getElementById('vietqrAmount');
    var qrCode = document.getElementById('vietqrCode');
    var qrTimer = document.getElementById('vietqrTimer');

    /* ==================== Helpers ==================== */
    function formatPrice(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + 'đ';
    }

    function generateTransferCode() {
        var digits = '0123456789';
        var code = 'QHUN';
        for (var i = 0; i < 5; i++) {
            code += digits.charAt(Math.floor(Math.random() * digits.length));
        }
        return code;
    }

    function buildQrUrl(amount, transferCode) {
        return 'https://img.vietqr.io/image/' + BANK_ID + '-' + ACCOUNT_NO + '-vietqr_net_2.jpg'
            + '?amount=' + amount
            + '&addInfo=' + encodeURIComponent(transferCode)
            + '&accountName=' + encodeURIComponent(ACCOUNT_NAME);
    }

    /* ==================== Timer ==================== */
    function startTimer() {
        stopTimer();
        var remaining = QR_TIMEOUT;
        updateTimerDisplay(remaining);
        qrTimerInterval = setInterval(function () {
            remaining--;
            if (remaining <= 0) {
                stopTimer();
                hideQrBox();
                if (window.QHToast) {
                    QHToast.show('Hết thời gian thanh toán QR. Vui lòng thử lại.', 'error');
                }
                return;
            }
            updateTimerDisplay(remaining);
        }, 1000);
    }

    function stopTimer() {
        if (qrTimerInterval) {
            clearInterval(qrTimerInterval);
            qrTimerInterval = null;
        }
    }

    function updateTimerDisplay(seconds) {
        var m = Math.floor(seconds / 60);
        var s = seconds % 60;
        if (qrTimer) {
            qrTimer.textContent = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }
    }

    /* ==================== QR Box ==================== */
    function showQrBox() {
        if (!qrBox) return;
        var transferCode = generateTransferCode();

        // Set QR image
        if (qrImage) {
            qrImage.src = buildQrUrl(totalAmount, transferCode);
        }
        // Set amount
        if (qrAmount) {
            qrAmount.textContent = formatPrice(totalAmount);
        }
        // Set transfer code
        if (qrCode) {
            qrCode.textContent = transferCode;
        }
        // Reset states
        if (qrContent) qrContent.style.display = '';
        if (qrSuccess) qrSuccess.style.display = 'none';

        qrBox.style.display = '';
        startTimer();
        currentTransferCode = transferCode;

        // POST to server → lưu PendingQRPayment
        if (window.QH_QR_CREATE_URL && window.QH_CSRF_TOKEN) {
            fetch(QH_QR_CREATE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': QH_CSRF_TOKEN
                },
                body: JSON.stringify({
                    amount: totalAmount,
                    transfer_code: transferCode
                })
            })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    console.log('[QR Create]', data);
                    if (data.success) {
                        // Bắt đầu polling trạng thái
                        startPolling();
                    }
                })
                .catch(function (err) {
                    console.error('[QR Create Error]', err);
                });
        }
    }

    function hideQrBox() {
        if (qrBox) qrBox.style.display = 'none';
        stopTimer();
        stopPolling();
    }

    /* ==================== QR Status Polling ==================== */
    function startPolling() {
        stopPolling();
        if (!currentTransferCode || !window.QH_QR_STATUS_URL) return;
        qrPollInterval = setInterval(function () {
            fetch(QH_QR_STATUS_URL + '?code=' + encodeURIComponent(currentTransferCode))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.success) return;
                    if (data.status === 'approved') {
                        onQrApproved();
                    } else if (data.status === 'cancelled') {
                        onQrCancelled();
                    } else if (data.status === 'expired') {
                        onQrExpired();
                    }
                })
                .catch(function () { });
        }, 3000); // mỗi 3 giây
    }

    function stopPolling() {
        if (qrPollInterval) {
            clearInterval(qrPollInterval);
            qrPollInterval = null;
        }
    }

    function onQrApproved() {
        vietqrPaid = true;
        stopTimer();
        stopPolling();

        // Hiển thị trạng thái thành công
        if (qrContent) qrContent.style.display = 'none';
        if (qrSuccess) qrSuccess.style.display = '';

        // Thêm verified checkmark vào VIETQR option
        var vietqrOpt = document.querySelector('[data-pay-type="vietqr"]');
        if (vietqrOpt) vietqrOpt.classList.add('verified');

        // Cập nhật tổng tiền = 0đ
        if (summaryTotalEl) summaryTotalEl.textContent = '0đ';

        if (window.QHToast) {
            QHToast.show('Thanh toán chuyển khoản đã được admin xác nhận!', 'success');
        }
    }

    function onQrCancelled() {
        stopTimer();
        stopPolling();
        hideQrBox();

        // Bỏ verified
        var vietqrOpt = document.querySelector('[data-pay-type="vietqr"]');
        if (vietqrOpt) vietqrOpt.classList.remove('verified');

        if (summaryTotalEl) summaryTotalEl.textContent = formatPrice(totalAmount);

        if (window.QHToast) {
            QHToast.show('QR chuyển khoản đã bị admin từ chối. Vui lòng thử lại.', 'error');
        }
    }

    function onQrExpired() {
        stopTimer();
        stopPolling();
        hideQrBox();

        if (window.QHToast) {
            QHToast.show('QR đã hết hạn (15 phút). Vui lòng thử lại.', 'error');
        }
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

            // Deselect all
            document.querySelectorAll('.qh-checkout-pay-opt').forEach(function (o) {
                o.classList.remove('selected');
                o.classList.remove('verified');
            });

            // Select this
            this.classList.add('selected');

            // COD → verified immediately, hide QR, restore total
            if (payType === 'cod') {
                this.classList.add('verified');
                hideQrBox();
                // Restore total if switching back from paid vietqr
                if (summaryTotalEl) {
                    summaryTotalEl.textContent = formatPrice(totalAmount);
                }
            }
            // VIETQR → show QR box
            else if (payType === 'vietqr') {
                if (vietqrPaid) {
                    // Đã thanh toán trước đó → hiển thị lại trạng thái success
                    this.classList.add('verified');
                    if (qrBox) qrBox.style.display = '';
                    if (qrContent) qrContent.style.display = 'none';
                    if (qrSuccess) qrSuccess.style.display = '';
                    if (summaryTotalEl) summaryTotalEl.textContent = '0đ';
                } else {
                    showQrBox();
                    if (summaryTotalEl) {
                        summaryTotalEl.textContent = formatPrice(totalAmount);
                    }
                }
            }
            // VNPAY → hide QR, restore total
            else if (payType === 'vnpay') {
                hideQrBox();
                if (summaryTotalEl) {
                    summaryTotalEl.textContent = formatPrice(totalAmount);
                }
            }

            updatePaySelection(this);
        });
    });

    // Set default selection (COD)
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
                    // Redirect sang VNPay sandbox
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

            // Chặn nếu chọn vietqr nhưng chưa được admin duyệt
            if (payType === 'vietqr' && !vietqrPaid) {
                if (window.QHToast) {
                    QHToast.show('Vui lòng chờ admin xác nhận thanh toán chuyển khoản', 'error');
                }
                return;
            }

            // VNPAY → chuyển hướng sang cổng thanh toán VNPay
            if (payType === 'vnpay') {
                initiateVNPayPayment();
                return;
            }

            // COD hoặc VietQR → đặt hàng trực tiếp
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
            items_param: window.QH_CHECKOUT_ITEMS_PARAM || ''
        };

        if (payType === 'vietqr' && currentTransferCode) {
            requestData.transfer_code = currentTransferCode;
        }

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
