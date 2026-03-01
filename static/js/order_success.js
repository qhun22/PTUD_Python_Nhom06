/* ========================================================
   QHUN22 – Order Success Page JavaScript
   ======================================================== */

/* ========== Xử lý khi đã sao chép ========== */
/**
 * Xử lý sau khi sao chép mã đơn hàng
 * @param {HTMLElement} btn - Nút bấm
 */
function doCopied(btn) {
    var ic = btn.querySelector('i');
    var origText = btn.innerHTML;
    if (ic) ic.className = 'ri-check-line';
    btn.childNodes[btn.childNodes.length - 1].textContent = ' Đã sao chép!';
    btn.style.borderColor = '#10b981';
    btn.style.background = '#d1fae5';
    if (window.QHToast) QHToast.show('Đã sao chép mã đơn hàng!', 'success');
    setTimeout(function() {
        btn.innerHTML = origText;
        btn.style.borderColor = '';
        btn.style.background = '';
    }, 2000);
}

/* ========== Hiệu ứng confetti ========== */
/**
 * Tạo hiệu ứng confetti khi trang tải xong
 */
function initConfetti() {
    var c = document.getElementById('successCard');
    if (!c) return;

    var cls = ['#A9CCF0', '#D3BAFF', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];
    for (var i = 0; i < 30; i++) {
        (function(n) {
            setTimeout(function() {
                var d = document.createElement('div');
                d.className = 'qh-confetti';
                d.style.left = (Math.random() * 100) + '%';
                d.style.top = '-10px';
                d.style.background = cls[Math.floor(Math.random() * cls.length)];
                d.style.animationDelay = (Math.random() * 0.5) + 's';
                d.style.animationDuration = (1.5 + Math.random()) + 's';
                d.style.width = (5 + Math.random() * 6) + 'px';
                d.style.height = (5 + Math.random() * 6) + 'px';
                c.appendChild(d);
                setTimeout(function() { d.remove(); }, 3000);
            }, n * 60);
        })(i);
    }
}

// Khởi tạo confetti khi DOM đã sẵn sàng
document.addEventListener('DOMContentLoaded', function() {
    initConfetti();
});
