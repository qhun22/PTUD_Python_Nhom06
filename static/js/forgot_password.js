/**
 * QHUN22 Mobile - Forgot Password JavaScript
 * Xử lý chức năng quên mật khẩu
 */

// Các URL endpoint
const FORGOT_PASSWORD_URLS = {
    sendOtp: '/send-otp-forgot-password/',
    verifyOtp: '/verify-otp-forgot-password/',
    resetPassword: '/reset-password/'
};

// Ẩn/hiện mật khẩu
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Lấy CSRF token
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Hiển thị thông báo toast
function showToast(message, type = 'success') {
    if (window.QHToast) {
        window.QHToast.show(message, type);
    }
}

// Các phần tử DOM
const emailInput = document.getElementById('email');
const otpBtn = document.getElementById('otpBtn');
const otpMessage = document.getElementById('otpMessage');
const otpForm = document.getElementById('otpForm');
const resetPasswordForm = document.getElementById('resetPasswordForm');

let countdownInterval;

// Khởi tạo khi DOM đã sẵn sàng
document.addEventListener('DOMContentLoaded', function() {
    if (emailInput && otpBtn) {
        initEmailStep();
    }
    if (otpForm) {
        initOtpStep();
    }
    if (resetPasswordForm) {
        initResetPasswordStep();
    }
});

// Bước 1: Xác thực email và gửi OTP
function initEmailStep() {
    emailInput.addEventListener('input', function() {
        const email = this.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        otpBtn.disabled = !emailRegex.test(email);
        if (otpMessage) {
            otpMessage.style.display = 'none';
        }
    });

    otpBtn.addEventListener('click', function() {
        const email = emailInput.value.trim();
        
        otpBtn.disabled = true;
        otpBtn.textContent = 'Đang gửi...';
        
        fetch(FORGOT_PASSWORD_URLS.sendOtp, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: 'email=' + encodeURIComponent(email)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('Đã gửi mã OTP về email của bạn!', 'success');
                showStep2(email);
            } else {
                showToast(data.message || 'Gửi OTP thất bại!', 'error');
                otpBtn.disabled = false;
                otpBtn.textContent = 'Gửi mã';
            }
        })
        .catch(error => {
            showToast('Đã xảy ra lỗi. Vui lòng thử lại!', 'error');
            otpBtn.disabled = false;
            otpBtn.textContent = 'Gửi mã';
        });
    });
}

// Hiển thị Bước 2
function showStep2(email) {
    document.getElementById('step1-form').classList.add('qh-hidden');
    document.getElementById('step2-form').classList.remove('qh-hidden');
    document.getElementById('step1').classList.remove('active');
    document.getElementById('step1').classList.add('completed');
    document.getElementById('step2').classList.add('active');
    
    document.getElementById('hiddenEmail').value = email;
    
    startCountdown();
}

// Bước 2: Xác thực OTP
function initOtpStep() {
    otpForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('hiddenEmail').value;
        const otp = document.getElementById('otp').value;
        
        fetch(FORGOT_PASSWORD_URLS.verifyOtp, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: 'email=' + encodeURIComponent(email) + '&otp=' + encodeURIComponent(otp)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStep3(email);
            } else {
                showToast(data.message || 'OTP không hợp lệ!', 'error');
            }
        })
        .catch(error => {
            showToast('Đã xảy ra lỗi. Vui lòng thử lại!', 'error');
        });
    });

    // Nút gửi lại OTP
    const resendBtn = document.getElementById('resendOtpBtn');
    if (resendBtn) {
        resendBtn.addEventListener('click', function() {
            const email = document.getElementById('hiddenEmail').value;
            
            this.disabled = true;
            this.textContent = 'Đang gửi lại...';
            
            fetch(FORGOT_PASSWORD_URLS.sendOtp, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCsrfToken()
                },
                body: 'email=' + encodeURIComponent(email)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('Mã OTP đã được gửi lại!', 'success');
                    this.textContent = 'Gửi lại mã OTP';
                    startCountdown();
                } else {
                    showToast(data.message || 'Gửi lại OTP thất bại!', 'error');
                    this.disabled = false;
                }
            })
            .catch(error => {
                showToast('Đã xảy ra lỗi. Vui lòng thử lại!', 'error');
                this.disabled = false;
            });
        });
    }
}

// Đếm ngược thời gian
function startCountdown() {
    let timeLeft = 300; // 5 minutes
    const countdownEl = document.getElementById('countdown');
    const resendBtn = document.getElementById('resendOtpBtn');
    
    if (resendBtn) {
        resendBtn.disabled = true;
    }
    
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    countdownInterval = setInterval(function() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        
        if (countdownEl) {
            countdownEl.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
        }
        
        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
            if (countdownEl) {
                countdownEl.textContent = '0:00';
            }
            if (resendBtn) {
                resendBtn.disabled = false;
            }
        }
        
        timeLeft--;
    }, 1000);
}

// Hiển thị Bước 3
function showStep3(email) {
    document.getElementById('step2-form').classList.add('qh-hidden');
    document.getElementById('step3-form').classList.remove('qh-hidden');
    document.getElementById('step2').classList.remove('active');
    document.getElementById('step2').classList.add('completed');
    document.getElementById('step3').classList.add('active');
    
    document.getElementById('resetEmail').value = email;
    
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
}

// Bước 3: Đặt lại mật khẩu
function initResetPasswordStep() {
    resetPasswordForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('resetEmail').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Xác thực mật khẩu
        if (newPassword.length < 6) {
            showToast('Mật khẩu phải có ít nhất 6 ký tự!', 'error');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showToast('Mật khẩu không khớp!', 'error');
            return;
        }
        
        fetch(FORGOT_PASSWORD_URLS.resetPassword, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: 'email=' + encodeURIComponent(email) + '&new_password=' + encodeURIComponent(newPassword)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('Đổi mật khẩu thành công!', 'success');
                setTimeout(function() {
                    window.location.href = '/login/';
                }, 2000);
            } else {
                showToast(data.message || 'Đổi mật khẩu thất bại!', 'error');
            }
        })
        .catch(error => {
            showToast('Đã xảy ra lỗi. Vui lòng thử lại!', 'error');
        });
    });
}
