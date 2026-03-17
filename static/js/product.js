/**
 * Product Management JS
 */

// ==================== Add Modal Functions ====================
function openAddProductModal() {
    document.getElementById('addProductForm').reset();
    // Reset image preview
    document.getElementById('addImagePreviewContainer').style.display = 'none';
    document.getElementById('addImagePlaceholder').style.display = 'block';
    document.getElementById('addProductModal').style.display = 'flex';
}

function closeAddProductModal() {
    document.getElementById('addProductModal').style.display = 'none';
    document.getElementById('addProductForm').reset();
}

// ==================== Image Preview Functions ====================
function previewAddProductImage(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
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
        reader.onload = function(e) {
            document.getElementById('editImagePreview').src = e.target.result;
            document.getElementById('editImagePreviewContainer').style.display = 'block';
            document.getElementById('editImagePlaceholder').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
}

// ==================== Edit Modal Functions ====================
function openEditProductModal(id, brandId, name, imageUrl) {
    document.getElementById('editProductId').value = id;
    document.getElementById('editProductBrand').value = brandId || '';
    document.getElementById('editProductName').value = name;
    
    // Show existing image
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

// ==================== Delete Product ====================
function deleteProduct(id, name) {
    const message = 'Ban co chac muon xoa san pham "' + name + '"?';
    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            message,
            function() {
                doDeleteProduct(id);
            },
            function() {
                // User cancelled
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

// ==================== Search ====================
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

// ==================== Event Listeners ====================
document.addEventListener('DOMContentLoaded', function() {
    // Add Product Form Submit
    const addProductForm = document.getElementById('addProductForm');
    if (addProductForm) {
        addProductForm.addEventListener('submit', function(e) {
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
    
    // Edit Product Form Submit
    const editProductForm = document.getElementById('editProductForm');
    if (editProductForm) {
        editProductForm.addEventListener('submit', function(e) {
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
    
    // Close modals on outside click
    window.addEventListener('click', function(e) {
        if (e.target.id === 'addProductModal') closeAddProductModal();
        if (e.target.id === 'editProductModal') closeEditProductModal();
    });
});
