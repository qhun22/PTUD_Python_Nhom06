/**
 * QHUN22 Mobile - Toast Notifications
 * Hiển thị thông báo toast với màu sắc brand QHUN22
 */

const QHToast = {
    /**
     * Hiển thị thông báo thành công
     * @param {string} message - Nội dung thông báo
     */
    success: function(message) {
        this.show(message, 'success');
    },

    /**
     * Hiển thị thông báo lỗi
     * @param {string} message - Nội dung thông báo lỗi
     */
    error: function(message) {
        this.show(message, 'error');
    },

    /**
     * Hiển thị thông báo
     * @param {string} message - Nội dung thông báo
     * @param {string} type - Loại thông báo (success/error)
     */
    show: function(message, type = 'success') {
        // Tạo container nếu chưa có
        let container = document.querySelector('.qh-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'qh-toast-container';
            document.body.appendChild(container);
        }

        // Tạo toast element
        const toast = document.createElement('div');
        toast.className = `qh-toast qh-toast-${type}`;
        toast.innerHTML = `
            <span>${message}</span>
        `;

        // Thêm vào container
        container.appendChild(toast);

        // Tự động ẩn sau 3 giây
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
};

// Thêm animation slideOut
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
