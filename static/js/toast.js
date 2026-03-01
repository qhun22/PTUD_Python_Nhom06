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
        
        // Thêm icon dựa trên loại thông báo
        const icon = type === 'success' 
            ? '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
            : '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        
        toast.innerHTML = `
            <span class="qh-toast-icon">${icon}</span>
            <span class="qh-toast-text">${message}</span>
        `;

        // Thêm vào container
        container.appendChild(toast);

        // Force reflow để animation hoạt động
        toast.offsetHeight;

        // Thêm class show để tạo hiệu ứng hiển thị mượt mà
        toast.classList.add('qh-toast-show');

        // Tự động ẩn sau 3 giây
        setTimeout(() => {
            toast.classList.remove('qh-toast-show');
            toast.classList.add('qh-toast-hide');
            
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
};

// Gán vào window để có thể gọi từ template
window.QHToast = QHToast;
