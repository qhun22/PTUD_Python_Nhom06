/**
 * JavaScript quản lý sản phẩm
 */

// ==================== Các hàm Modal thêm sản phẩm ====================
function openAddProductModal() {
    document.getElementById('addProductForm').reset();
    // Đặt lại xem trước ảnh
    document.getElementById('addImagePreviewContainer').style.display = 'none';
    document.getElementById('addImagePlaceholder').style.display = 'block';
    document.getElementById('addProductModal').style.display = 'flex';
}

function closeAddProductModal() {
    document.getElementById('addProductModal').style.display = 'none';
    document.getElementById('addProductForm').reset();
}

// ==================== Các hàm xem trước ảnh ====================
function previewAddProductImage(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('addImagePreview').src = e.target.result;
            document.getElementById('addImagePreviewContainer').style.display = 'block';
            document.getElementById('addImagePlaceholder').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

function previewEditProductImage(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('editImagePreview').src = e.target.result;
            document.getElementById('editImagePreviewContainer').style.display = 'block';
            document.getElementById('editImagePlaceholder').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

// ==================== Các hàm Modal sửa sản phẩm ====================
function openEditProductModal(id, brandId, name, imageUrl) {
    document.getElementById('editProductId').value = id;
    document.getElementById('editProductBrand').value = brandId || '';
    document.getElementById('editProductName').value = name;

    // Hiển thị ảnh hiện có
    const previewContainer = document.getElementById('editImagePreviewContainer');
    const placeholder = document.getElementById('editImagePlaceholder');
    const preview = document.getElementById('editImagePreview');

    if (imageUrl) {
        preview.src = imageUrl;
        previewContainer.style.display = 'block';
        placeholder.style.display = 'none';
    } else {
        previewContainer.style.display = 'none';
        placeholder.style.display = 'block';
    }

    document.getElementById('editProductModal').style.display = 'flex';
}

function closeEditProductModal() {
    document.getElementById('editProductModal').style.display = 'none';
    document.getElementById('editProductForm').reset();
}

// ==================== Xóa sản phẩm ====================
function deleteProduct(id, name) {
    const message = 'Ban co chac muon xoa san pham "' + name + '"?';
    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            message,
            function () {
                doDeleteProduct(id);
            },
            function () {
                // Người dùng đã hủy
            }
        );
    } else {
        if (confirm(message)) {
            doDeleteProduct(id);
        }
    }
}

function doDeleteProduct(id) {
    const formData = new FormData();
    formData.append('product_id', id);

    fetch(window.productDeleteUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.QHToast.show(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                window.QHToast.show(data.message, 'error');
            }
        })
        .catch(err => {
            window.QHToast.show('Co loi xay ra!', 'error');
        });
}

// ==================== Tìm kiếm ====================
function searchProducts(event) {
    if (event && event.key !== 'Enter') return;
    const searchTerm = document.getElementById('productSearchInput').value.trim();
    const url = new URL(window.location.href);
    if (searchTerm) {
        url.searchParams.set('product_search', searchTerm);
    } else {
        url.searchParams.delete('product_search');
    }
    window.location.href = url.toString();
}

function resetProductSearch() {
    const url = new URL(window.location.href);
    url.searchParams.delete('product_search');
    window.location.href = url.toString();
}

// ==================== Trình lắng nghe sự kiện ====================
document.addEventListener('DOMContentLoaded', function () {
    // Gửi form thêm sản phẩm
    const addProductForm = document.getElementById('addProductForm');
    if (addProductForm) {
        addProductForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(window.productAddUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': window.csrfToken
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        window.QHToast.show(data.message, 'success');
                        closeAddProductModal();
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        window.QHToast.show(data.message, 'error');
                    }
                })
                .catch(err => {
                    window.QHToast.show('Co loi xay ra!', 'error');
                });
        });
    }

    // Gửi form sửa sản phẩm
    const editProductForm = document.getElementById('editProductForm');
    if (editProductForm) {
        editProductForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(window.productEditUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': window.csrfToken
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        window.QHToast.show(data.message, 'success');
                        closeEditProductModal();
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        window.QHToast.show(data.message, 'error');
                    }
                })
                .catch(err => {
                    window.QHToast.show('Co loi xay ra!', 'error');
                });
        });
    }

    // Đóng modal khi click bên ngoài
    window.addEventListener('click', function (e) {
        if (e.target.id === 'addProductModal') closeAddProductModal();
        if (e.target.id === 'editProductModal') closeEditProductModal();
    });
});
