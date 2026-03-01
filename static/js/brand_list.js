/* ==================== Mở modal thêm hãng ==================== */
function openAddModal() {
    document.getElementById('addModal').classList.add('active');
}

/* ==================== Đóng modal thêm hãng ==================== */
function closeAddModal() {
    document.getElementById('addModal').classList.remove('active');
    document.getElementById('addBrandForm').reset();
}

/* ==================== Mở modal sửa hãng ==================== */
function openEditModal(id, name, desc) {
    document.getElementById('editBrandId').value = id;
    document.getElementById('editBrandName').value = name;
    document.getElementById('editBrandDesc').value = desc || '';
    document.getElementById('editModal').classList.add('active');
}

/* ==================== Đóng modal sửa hãng ==================== */
function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
    document.getElementById('editBrandForm').reset();
}

/* ==================== Đóng modal khi click bên ngoài ==================== */
document.querySelectorAll('.qh-modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.remove('active');
        }
    });
});
