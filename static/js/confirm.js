/**
 * QHUN22 Mobile - Confirmation Dialog
 * Hộp thoại xác nhận với màu sắc brand QHUN22
 */

const QHConfirm = {
    /**
     * Hiển thị hộp thoại xác nhận
     * @param {string} message - Nội dung xác nhận
     * @param {function} onConfirm - Hàm callback khi người dùng xác nhận
     * @param {function} onCancel - Hàm callback khi người dùng hủy
     */
    show: function(message, onConfirm, onCancel = null) {
        // Tạo modal container
        const modal = document.createElement('div');
        modal.className = 'qh-modal active';
        modal.innerHTML = `
            <div class="qh-modal-content">
                <h3 class="qh-modal-title">Xác nhận</h3>
                <p class="qh-modal-text">${message}</p>
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button class="qh-btn qh-btn-cancel" style="background: #E0E0E0; color: #333;">Hủy</button>
                    <button class="qh-btn qh-btn-primary">Xác nhận</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Xử lý sự kiện
        const confirmBtn = modal.querySelector('.qh-btn-primary');
        const cancelBtn = modal.querySelector('.qh-btn-cancel');

        confirmBtn.addEventListener('click', () => {
            modal.remove();
            if (onConfirm) onConfirm();
        });

        cancelBtn.addEventListener('click', () => {
            modal.remove();
            if (onCancel) onCancel();
        });

        // Đóng khi click bên ngoài
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                if (onCancel) onCancel();
            }
        });
    }
};
