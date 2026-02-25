// Dashboard JavaScript

// Modal Functions
function openAddBrandModal() {
    document.getElementById('addBrandModal').style.display = 'flex';
}

function closeAddBrandModal() {
    document.getElementById('addBrandModal').style.display = 'none';
    document.getElementById('addBrandForm').reset();
}

function openEditBrandModal(id, name, desc) {
    document.getElementById('editBrandId').value = id;
    document.getElementById('editBrandName').value = name;
    document.getElementById('editBrandModal').style.display = 'flex';
}

function closeEditBrandModal() {
    document.getElementById('editBrandModal').style.display = 'none';
    document.getElementById('editBrandForm').reset();
}

// User Modal Functions
function openEditUserModal(id, email, lastName, firstName, phone) {
    document.getElementById('editUserId').value = id;
    document.getElementById('editUserEmail').value = email;
    document.getElementById('editUserLastName').value = lastName;
    document.getElementById('editUserFirstName').value = firstName;
    document.getElementById('editUserPhone').value = phone || '';
    document.getElementById('editUserModal').style.display = 'flex';
}

function closeEditUserModal() {
    document.getElementById('editUserModal').style.display = 'none';
    document.getElementById('editUserForm').reset();
}

// Delete User
function deleteUser(id, email) {
    const message = 'Bạn có chắc muốn xóa người dùng "' + email + '"?';

    QHConfirm.show(
        message,
        function () {
            doDeleteUser(id);
        },
        function () {
            // User cancelled
        }
    );
}

function doDeleteUser(id) {
    const formData = new FormData();
    formData.append('user_id', id);

    fetch(window.userDeleteUrl, {
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
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

// Search Brands - Server Side
function searchBrands(event) {
    if (event && event.key !== 'Enter') return;
    const searchTerm = document.getElementById('brandSearchInput').value.trim();

    if (searchTerm) {
        window.location.href = '?section=brands&brand_search=' + encodeURIComponent(searchTerm);
    } else {
        window.location.href = '?section=brands';
    }
}

function resetBrandSearch() {
    window.location.href = '?section=brands';
}

// Search Users - Server Side
function searchUsers(event) {
    if (event && event.key !== 'Enter') return;
    const searchTerm = document.getElementById('userSearchInput').value.trim();

    if (searchTerm) {
        window.location.href = '?section=users&user_search=' + encodeURIComponent(searchTerm);
    } else {
        window.location.href = '?section=users';
    }
}

function resetUserSearch() {
    window.location.href = '?section=users';
}

// Delete Brand
function deleteBrand(id, name) {
    const message = 'Bạn có chắc muốn xóa hãng "' + name + '"?';

    QHConfirm.show(
        message,
        function () {
            doDeleteBrand(id);
        },
        function () {
            // User cancelled
        }
    );
}

function doDeleteBrand(id) {
    const formData = new FormData();
    formData.append('brand_id', id);

    fetch(window.brandDeleteUrl, {
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
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

// Sidebar: tối đa 8 mục/trang, từ STT 9 trở đi sang trang 2
const SIDEBAR_PER_PAGE = 8;
let sidebarCurrentPage = 1;

function showSidebarPage(page) {
    const menu = document.getElementById('qhSidebarMenu');
    const paginationEl = document.getElementById('qhSidebarPagination');
    if (!menu || !paginationEl) return;
    const items = Array.from(menu.querySelectorAll('.qh-sidebar-item'));
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / SIDEBAR_PER_PAGE));
    page = Math.max(1, Math.min(page, totalPages));
    sidebarCurrentPage = page;

    const start = (page - 1) * SIDEBAR_PER_PAGE;
    const end = start + SIDEBAR_PER_PAGE;
    items.forEach((item, i) => {
        item.style.display = (i >= start && i < end) ? '' : 'none';
    });

    if (totalPages <= 1) {
        paginationEl.style.display = 'none';
        return;
    }
    paginationEl.style.display = 'flex';
    let html = '<button type="button" class="qh-sidebar-prev" ' + (page <= 1 ? 'disabled' : '') + '>Trước</button>';
    for (let p = 1; p <= totalPages; p++) {
        html += '<button type="button" class="qh-sidebar-page' + (p === page ? ' active-page' : '') + '" data-page="' + p + '">' + p + '</button>';
    }
    html += '<button type="button" class="qh-sidebar-next" ' + (page >= totalPages ? 'disabled' : '') + '>Sau</button>';
    paginationEl.innerHTML = html;

    paginationEl.querySelector('.qh-sidebar-prev').onclick = () => showSidebarPage(page - 1);
    paginationEl.querySelector('.qh-sidebar-next').onclick = () => showSidebarPage(page + 1);
    paginationEl.querySelectorAll('.qh-sidebar-page').forEach(btn => {
        btn.onclick = () => showSidebarPage(parseInt(btn.getAttribute('data-page'), 10));
    });
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', function () {
    // Lấy section từ URL hoặc mặc định là stats
    const urlParams = new URLSearchParams(window.location.search);
    const currentSection = urlParams.get('section') || 'stats';

    const menu = document.getElementById('qhSidebarMenu');
    const sidebarItems = menu ? menu.querySelectorAll('.qh-sidebar-item') : [];
    const totalPages = Math.ceil(sidebarItems.length / SIDEBAR_PER_PAGE);
    let pageToShow = 1;
    if (totalPages > 1) {
        for (let p = 1; p <= totalPages; p++) {
            const start = (p - 1) * SIDEBAR_PER_PAGE;
            for (let i = start; i < start + SIDEBAR_PER_PAGE && i < sidebarItems.length; i++) {
                if (sidebarItems[i].getAttribute('data-section') === currentSection) {
                    pageToShow = p;
                    break;
                }
            }
        }
    }
    showSidebarPage(pageToShow);

    // Cập nhật sidebar active
    sidebarItems.forEach(item => {
        const section = item.getAttribute('data-section');
        if (section === currentSection) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Hiển thị section đúng
    const statsSection = document.getElementById('stats-section');
    const usersSection = document.getElementById('users-section');
    const brandsSection = document.getElementById('brands-section');
    const productsSection = document.getElementById('products-section');
    const productImagesSection = document.getElementById('product-images-section');
    const skuSection = document.getElementById('sku-section');
    const bannerImagesSection = document.getElementById('banner-images-section');
    const productContentSection = document.getElementById('product-content-section');
    const qrApprovalSection = document.getElementById('qr-approval-section');

    if (statsSection) statsSection.style.display = (currentSection === 'stats') ? 'block' : 'none';
    if (usersSection) usersSection.style.display = (currentSection === 'users') ? 'block' : 'none';
    if (brandsSection) brandsSection.style.display = (currentSection === 'brands') ? 'block' : 'none';
    if (productsSection) productsSection.style.display = (currentSection === 'products') ? 'block' : 'none';
    if (productImagesSection) productImagesSection.style.display = (currentSection === 'product-images') ? 'block' : 'none';
    if (skuSection) {
        skuSection.style.display = (currentSection === 'sku') ? 'block' : 'none';
    }
    if (bannerImagesSection) {
        bannerImagesSection.style.display = (currentSection === 'banner-images') ? 'block' : 'none';
    }
    if (productContentSection) {
        productContentSection.style.display = (currentSection === 'product-content') ? 'block' : 'none';
    }
    if (qrApprovalSection) {
        qrApprovalSection.style.display = (currentSection === 'qr-approval') ? 'block' : 'none';
    }

    // Load SKU list if on SKU section (hoặc khi vào phần Ảnh sản phẩm để dùng dropdown SKU)
    if (currentSection === 'sku' || currentSection === 'product-images') {
        loadSkuList();
    }

    // Load QR list if on qr-approval section
    if (currentSection === 'qr-approval') {
        loadQrApprovalList();
        // Auto-refresh mỗi 30 giây
        setInterval(loadQrApprovalList, 30000);
    }

    // Add Brand Form Submit
    const addBrandForm = document.getElementById('addBrandForm');
    if (addBrandForm) {
        addBrandForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(window.brandAddUrl, {
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
                        closeAddBrandModal();
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        window.QHToast.show(data.message, 'error');
                    }
                })
                .catch(err => {
                    window.QHToast.show('Có lỗi xảy ra!', 'error');
                });
        });
    }

    // Edit Brand Form Submit
    const editBrandForm = document.getElementById('editBrandForm');
    if (editBrandForm) {
        editBrandForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(window.brandEditUrl, {
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
                        closeEditBrandModal();
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        window.QHToast.show(data.message, 'error');
                    }
                })
                .catch(err => {
                    window.QHToast.show('Có lỗi xảy ra!', 'error');
                });
        });
    }

    // Edit User Form Submit
    const editUserForm = document.getElementById('editUserForm');
    if (editUserForm) {
        editUserForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(window.userEditUrl, {
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
                        closeEditUserModal();
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        window.QHToast.show(data.message, 'error');
                    }
                })
                .catch(err => {
                    window.QHToast.show('Có lỗi xảy ra!', 'error');
                });
        });
    }

    // Close modal when clicking outside
    window.addEventListener('click', function (e) {
        if (e.target.id === 'addBrandModal') closeAddBrandModal();
        if (e.target.id === 'editBrandModal') closeEditBrandModal();
        if (e.target.id === 'editUserModal') closeEditUserModal();
        if (e.target.id === 'editSkuModal') closeEditSkuModal();
    });

    // Load SKU list on page load nếu SKU hoặc Ảnh sản phẩm đang active
    const sectionParam = urlParams.get('section');
    if (sectionParam === 'sku' || sectionParam === 'product-images') {
        loadSkuList();
    }

    // Load all products cho SKU management (giữ nguyên)
    loadAllProducts();

    // Init phần Ảnh sản phẩm
    if (sectionParam === 'product-images') {
        initProductImagesSection();
    }

    // Init phần Ảnh banner
    if (sectionParam === 'banner-images') {
        initBannerImagesSection();
    }

    // Init phần Nội dung sản phẩm
    if (sectionParam === 'product-content') {
        initProductContentSection();
    }
});

// ==================== SKU Management ====================
let allSkus = [];

function loadSkuList() {
    fetch('/products/sku/list/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allSkus = data.skus;
                renderSkuTable(allSkus);
            }
        })
        .catch(error => console.error('Error loading SKU list:', error));
}

// ==================== Product Images (Thư mục ảnh) ====================
let allImageFolderRows = [];
let allImageFolders = [];
let imageFolderPreviewImages = []; // ảnh đã upload cho màu hiện tại trong modal

function initProductImagesSection() {
    loadImageFolderRows();
}

function loadImageFolderRows() {
    fetch('/product-images/folders/list/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allImageFolderRows = data.rows || [];
                allImageFolders = data.folders || [];
                renderImageFolderTable(allImageFolderRows);
                refreshImageFolderOptions();
            }
        })
        .catch(error => {
            console.error('Error loading image folders:', error);
        });
}

function renderImageFolderTable(rows) {
    const tbody = document.getElementById('imageFolderTableBody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="padding: 40px; text-align: center; color: #64748b; font-size: 14px; font-family: 'Signika', sans-serif;">
                    Chưa có màu ảnh nào.
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    rows.forEach((row, index) => {
        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${index + 1}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif; font-weight: 500;">${row.folder_name}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${row.color_name}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${row.sku}</td>
                <td style="padding: 12px 16px;">
                    <div style="display: flex; gap: 6px;">
                        <button type="button" onclick="openAddColorImageModal(${row.folder_id || 'null'}, '${row.sku}', '${row.color_name.replace(/'/g, "\\'")}')" style="background: #dbeafe; color: #1e40af; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-family: 'Signika', sans-serif;">Quản lý</button>
                    </div>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function searchImageFolders() {
    const input = document.getElementById('imageFolderSearchInput');
    if (!input) return;
    const term = input.value.toLowerCase();
    const filtered = allImageFolderRows.filter(r => (r.folder_name || '').toLowerCase().includes(term));
    renderImageFolderTable(filtered);
}

function resetImageFolderSearch() {
    const input = document.getElementById('imageFolderSearchInput');
    if (input) input.value = '';
    renderImageFolderTable(allImageFolderRows);
}

function openAddImageFolderModal() {
    const modal = document.getElementById('addImageFolderModal');
    if (!modal) return;
    const input = document.getElementById('imageFolderNameInput');
    if (input) input.value = '';
    modal.style.display = 'flex';
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddImageFolderModal();
        }
    };
}

function closeAddImageFolderModal() {
    const modal = document.getElementById('addImageFolderModal');
    if (modal) modal.style.display = 'none';
}

function saveImageFolder() {
    const input = document.getElementById('imageFolderNameInput');
    if (!input) return;
    const name = input.value.trim();
    if (!name) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng nhập tên thư mục!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);

    fetch('/product-images/folders/create/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (window.QHToast && window.QHToast.show) {
                    window.QHToast.show(data.message, 'success');
                }
                closeAddImageFolderModal();
                loadImageFolderRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể tạo thư mục.', 'error');
            }
        })
        .catch(error => {
            console.error('Error creating image folder:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function refreshImageFolderOptions() {
    const select = document.getElementById('colorImageFolderSelect');
    if (!select) return;
    const currentValue = select.value;
    let html = '<option value="">-- Chọn thư mục --</option>';
    (allImageFolders || []).forEach(folder => {
        if (folder.id && folder.name) {
            html += `<option value="${folder.id}">${folder.name}</option>`;
        }
    });
    select.innerHTML = html;
    if (currentValue) select.value = currentValue;
}

function openAddColorImageModal(folderId = null, sku = '', colorName = '') {
    const modal = document.getElementById('addColorImageModal');
    if (!modal) return;

    const folderSelect = document.getElementById('colorImageFolderSelect');
    const brandSelect = document.getElementById('colorImageBrandSelect');
    const skuSelect = document.getElementById('colorImageSkuSelect');
    const colorInput = document.getElementById('colorImageNameInput');
    const fileNameEl = document.getElementById('colorImageFileName');
    const previewGrid = document.getElementById('colorImagePreviewGrid');

    refreshImageFolderOptions();

    if (folderId && folderSelect) {
        folderSelect.value = String(folderId);
    } else if (folderSelect) {
        folderSelect.value = '';
    }

    if (brandSelect) {
        brandSelect.value = '';
    }

    populateColorImageSkuOptions();

    if (skuSelect) {
        skuSelect.value = sku || '';
    }

    if (colorInput) {
        colorInput.value = colorName || '';
    }

    if (fileNameEl) fileNameEl.textContent = '';
    if (previewGrid) previewGrid.innerHTML = '';
    imageFolderPreviewImages = [];

    modal.style.display = 'flex';
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddColorImageModal();
        }
    };

    if (folderId && sku && colorName) {
        loadColorImageList(folderId, sku, colorName).then(images => {
            imageFolderPreviewImages = (images || []).map(img => ({ id: img.id, url: img.url }));
            renderColorImagePreview();
        });
    }
}

function closeAddColorImageModal() {
    const modal = document.getElementById('addColorImageModal');
    if (modal) modal.style.display = 'none';
}

function saveColorImageModal() {
    if (window.QHToast && window.QHToast.show) {
        window.QHToast.show('Đã lưu.', 'success');
    }
    loadImageFolderRows();
    closeAddColorImageModal();
}

function loadColorImageList(folderId, sku, colorName) {
    if (!folderId || !sku || !colorName) return Promise.resolve({ images: [] });
    const params = new URLSearchParams({ folder_id: folderId, sku: sku, color_name: colorName });
    return fetch('/product-images/color/list/?' + params.toString(), {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(response => response.json())
        .then(data => data.success && data.images ? data.images : [])
        .catch(() => []);
}

function populateColorImageSkuOptions() {
    const skuSelect = document.getElementById('colorImageSkuSelect');
    const brandSelect = document.getElementById('colorImageBrandSelect');
    if (!skuSelect) return;

    const brandId = brandSelect ? brandSelect.value : '';
    let skus = allSkus || [];
    if (brandId) {
        skus = skus.filter(s => String(s.brand_id) === String(brandId));
    }

    let html = '<option value="">-- Chọn SKU --</option>';
    skus.forEach(s => {
        const label = `${s.sku} - ${s.product_name || ''} ${s.brand_name ? '(' + s.brand_name + ')' : ''}`;
        html += `<option value="${s.sku}">${label}</option>`;
    });
    skuSelect.innerHTML = html;
}

// Khi chọn hãng trong modal màu ảnh -> lọc lại SKU
const colorImageBrandSelectEl = document.getElementById('colorImageBrandSelect');
if (colorImageBrandSelectEl) {
    colorImageBrandSelectEl.addEventListener('change', populateColorImageSkuOptions);
}

function handleColorImageFileChange(event) {
    const file = event.target.files && event.target.files[0];
    const fileNameEl = document.getElementById('colorImageFileName');
    if (fileNameEl) {
        fileNameEl.textContent = file ? file.name : '';
    }
}

function renderColorImagePreview() {
    const previewGrid = document.getElementById('colorImagePreviewGrid');
    if (!previewGrid) return;

    if (!imageFolderPreviewImages.length) {
        previewGrid.innerHTML = '';
        return;
    }

    let html = '';
    imageFolderPreviewImages.forEach((img, index) => {
        html += `
            <div style="position: relative; width: 100%; padding-top: 100%; background: #f1f5f9; border-radius: 10px; overflow: hidden;">
                <img src="${img.url}" style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;">
                <button type="button" onclick="deleteColorImage(${img.id}, ${index})" style="position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; border-radius: 999px; border: none; background: rgba(15,23,42,0.8); color: #f9fafb; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
                <div style="position: absolute; bottom: 4px; left: 4px; padding: 2px 6px; border-radius: 999px; background: rgba(15,23,42,0.75); color: #e5e7eb; font-size: 11px; font-family: 'Signika', sans-serif;">#${index + 1}</div>
            </div>
        `;
    });
    previewGrid.innerHTML = html;
}

function uploadColorImage() {
    const folderSelect = document.getElementById('colorImageFolderSelect');
    const brandSelect = document.getElementById('colorImageBrandSelect');
    const skuSelect = document.getElementById('colorImageSkuSelect');
    const colorInput = document.getElementById('colorImageNameInput');
    const fileInput = document.getElementById('colorImageFileInput');

    const folderId = folderSelect ? folderSelect.value : '';
    const brandId = brandSelect ? brandSelect.value : '';
    const sku = skuSelect ? skuSelect.value : '';
    const colorName = colorInput ? colorInput.value.trim() : '';
    const file = fileInput && fileInput.files ? fileInput.files[0] : null;

    if (!folderId || !sku || !colorName || !file) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn thư mục, hãng, SKU, màu và ảnh!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('folder_id', folderId);
    if (brandId) formData.append('brand_id', brandId);
    formData.append('sku', sku);
    formData.append('color_name', colorName);
    formData.append('image', file);

    fetch('/product-images/color/upload/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.image) {
                imageFolderPreviewImages.push({
                    id: data.image.id,
                    url: data.image.url
                });
                renderColorImagePreview();
                if (window.QHToast && window.QHToast.show) {
                    const index = imageFolderPreviewImages.length;
                    window.QHToast.show(`Đã upload thành công ảnh thứ ${index}.`, 'success');
                }
                // reset file input
                if (fileInput) fileInput.value = '';
                const fileNameEl = document.getElementById('colorImageFileName');
                if (fileNameEl) fileNameEl.textContent = '';

                // reload bảng để cập nhật dòng mới
                loadImageFolderRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload ảnh.', 'error');
            }
        })
        .catch(error => {
            console.error('Error uploading color image:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function deleteColorImage(imageId, indexInPreview) {
    if (!imageId) return;

    const formData = new FormData();
    formData.append('image_id', imageId);

    fetch('/product-images/color/delete/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (typeof indexInPreview === 'number') {
                    imageFolderPreviewImages.splice(indexInPreview, 1);
                    renderColorImagePreview();
                }
                if (window.QHToast && window.QHToast.show) {
                    window.QHToast.show(data.message || 'Đã xóa ảnh.', 'success');
                }
                loadImageFolderRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể xóa ảnh.', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting color image:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function renderSkuTable(skus) {
    const tbody = document.getElementById('skuTableBody');
    if (!tbody) return;

    if (skus.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="padding: 40px; text-align: center; color: #64748b; font-size: 14px;">
                    CHƯA CÓ SKU NÀO !
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    skus.forEach((sku, index) => {
        const date = new Date(sku.created_at).toLocaleDateString('vi-VN');
        const skuIdEscaped = String(sku.id).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const skuEscaped = (sku.sku || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const escapeHtml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        const productNameEscaped = escapeHtml(sku.product_name || '-');
        const brandDisplay = escapeHtml(sku.brand_name || '-');
        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${index + 1}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-weight: 500; font-family: 'Signika', sans-serif;">${escapeHtml(sku.sku)}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${productNameEscaped}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${brandDisplay}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${date}</td>
                <td style="padding: 12px 16px;">
                    <div style="display: flex; gap: 6px;">
                        <button type="button" onclick="editSku('${skuIdEscaped}', '${skuEscaped}')" style="background: #fef3c7; color: #b45309; border: none; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; font-family: 'Signika', sans-serif;">Sửa</button>
                        <button type="button" onclick="deleteSkuItem('${skuIdEscaped}', '${skuEscaped}')" style="background: #fee2e2; color: #dc2626; border: none; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; font-family: 'Signika', sans-serif;">Xóa</button>
                    </div>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function filterSkuByBrand() {
    const brandFilter = document.getElementById('skuBrandFilter');
    const searchInput = document.getElementById('skuSearchInput');
    if (!brandFilter || !searchInput) return;

    const brandId = brandFilter.value;
    const searchTerm = searchInput.value.toLowerCase();

    let filtered = allSkus;

    if (brandId) {
        filtered = filtered.filter(s => s.brand_id == brandId);
    }

    if (searchTerm) {
        filtered = filtered.filter(s => s.sku.toLowerCase().includes(searchTerm));
    }

    renderSkuTable(filtered);
}

function addNewSku() {
    const productId = document.getElementById('skuProductSelect').value;
    const sku = document.getElementById('newSkuInput').value.trim();

    if (!productId) {
        alert('Vui lòng chọn sản phẩm!');
        return;
    }

    if (!sku) {
        alert('Vui lòng nhập SKU!');
        return;
    }

    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('sku', sku);

    fetch('/products/sku/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.QHToast.show(data.message, 'success');
                document.getElementById('newSkuInput').value = '';
                loadSkuList();
            } else {
                window.QHToast.show(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error adding SKU:', error);
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function editSku(id, sku) {
    const modal = document.getElementById('editSkuModal');
    const input = document.getElementById('editSkuInput');
    const idInput = document.getElementById('editSkuId');
    if (!modal || !input || !idInput) return;
    idInput.value = id;
    input.value = sku || '';
    input.setAttribute('data-original', sku || '');
    input.placeholder = 'Nhập mã SKU';
    modal.style.display = 'flex';
}

function closeEditSkuModal() {
    const modal = document.getElementById('editSkuModal');
    if (modal) modal.style.display = 'none';
}

function saveEditSku() {
    const idInput = document.getElementById('editSkuId');
    const input = document.getElementById('editSkuInput');
    if (!idInput || !input) return;
    const id = idInput.value;
    const newSku = (input.value || '').trim();
    const originalSku = (input.getAttribute('data-original') || '').trim();
    if (!newSku) {
        window.QHToast.show('Vui lòng nhập mã SKU.', 'error');
        return;
    }
    if (newSku === originalSku) {
        closeEditSkuModal();
        return;
    }
    const formData = new FormData();
    formData.append('sku_id', id);
    formData.append('sku', newSku);
    fetch('/products/sku/edit/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => {
            const ct = response.headers.get('content-type') || '';
            if (ct.includes('application/json')) {
                return response.json().then(data => ({ ok: response.ok, data }));
            }
            return response.text().then(() => ({ ok: false, data: { message: 'Phản hồi không hợp lệ.' } }));
        })
        .then(({ ok, data }) => {
            if (ok && data.success) {
                window.QHToast.show(data.message || 'Đã sửa SKU.', 'success');
                closeEditSkuModal();
                loadSkuList();
            } else {
                window.QHToast.show(data.message || 'Không thể sửa SKU.', 'error');
            }
        })
        .catch(error => {
            console.error('Error editing SKU:', error);
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function deleteSkuItem(id, sku) {
    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            `Bạn có chắc muốn xóa SKU: <strong>${sku}</strong>?`,
            () => {
                performDeleteSkuItem(id);
            }
        );
    } else {
        if (confirm(`Bạn có chắc muốn xóa SKU: ${sku}?`)) {
            performDeleteSkuItem(id);
        }
    }
}

function performDeleteSkuItem(id) {
    const formData = new FormData();
    formData.append('sku_id', id);

    fetch('/products/sku/delete/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => {
            const ct = response.headers.get('content-type') || '';
            if (ct.includes('application/json')) {
                return response.json().then(data => ({ ok: response.ok, data }));
            }
            return response.text().then(() => ({ ok: false, data: { message: 'Phản hồi không hợp lệ.' } }));
        })
        .then(({ ok, data }) => {
            if (ok && data.success) {
                window.QHToast.show(data.message || 'Đã xóa SKU.', 'success');
                loadSkuList();
            } else {
                window.QHToast.show(data.message || 'Không thể xóa SKU.', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting SKU:', error);
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

// Search SKU
const skuSearchInput = document.getElementById('skuSearchInput');
if (skuSearchInput) {
    skuSearchInput.addEventListener('input', filterSkuByBrand);
}

// ==================== Add SKU Modal Functions ====================
function openAddSkuModal() {
    const modal = document.getElementById('addSkuModal');
    modal.style.display = 'flex';
    document.getElementById('addSkuBrand').value = '';
    document.getElementById('addSkuProduct').innerHTML = '<option value="">-- CHỌN HÃNG TRƯỚC NHÉ --</option>';
    document.getElementById('addSkuInput').value = '';

    // Close modal when clicking outside
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddSkuModal();
        }
    };

    // Enter key to save
    document.getElementById('addSkuInput').onkeypress = function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveSku();
        }
    };
}

function closeAddSkuModal() {
    document.getElementById('addSkuModal').style.display = 'none';
}

function loadProductsByBrand() {
    const brandId = document.getElementById('addSkuBrand').value;
    const productSelect = document.getElementById('addSkuProduct');

    if (!brandId) {
        productSelect.innerHTML = '<option value="">-- CHỌN HÃNG TRƯỚC NHÉ --</option>';
        return;
    }

    // Filter products by brand
    const products = window.allProducts || [];
    const filtered = products.filter(p => p.brand_id == brandId);

    if (filtered.length === 0) {
        productSelect.innerHTML = '<option value="">-- Không có sản phẩm --</option>';
        return;
    }

    let html = '<option value="">-- Chọn sản phẩm --</option>';
    filtered.forEach(p => {
        html += `<option value="${p.id}">${p.name}</option>`;
    });
    productSelect.innerHTML = html;
}

function saveSku() {
    const productId = document.getElementById('addSkuProduct').value;
    const sku = document.getElementById('addSkuInput').value.trim();

    if (!productId) {
        window.QHToast.show('Vui lòng chọn sản phẩm!', 'error');
        return;
    }

    if (!sku) {
        window.QHToast.show('Vui lòng nhập SKU!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('sku', sku);

    fetch('/products/sku/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.QHToast.show(data.message, 'success');
                closeAddSkuModal();
                loadSkuList();
            } else {
                window.QHToast.show(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error saving SKU:', error);
            window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function searchSku() {
    filterSkuByBrand();
}

function resetSkuSearch() {
    const skuSearchInput = document.getElementById('skuSearchInput');
    const skuBrandFilter = document.getElementById('skuBrandFilter');
    if (skuSearchInput) skuSearchInput.value = '';
    if (skuBrandFilter) skuBrandFilter.value = '';
    renderSkuTable(allSkus);
}

// Load products for SKU management
function loadAllProducts() {
    fetch('/products/list/json/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.allProducts = data.products;
            }
        })
        .catch(error => console.error('Error loading products:', error));
}

// Load products when page loads
document.addEventListener('DOMContentLoaded', function () {
    loadAllProducts();
});

// ==================== Banner Images Management ====================
let allBannerRows = [];
let bannerPreviewImages = []; // ảnh đã upload trong modal

function initBannerImagesSection() {
    loadBannerRows();
}

function loadBannerRows() {
    fetch('/banner-images/list/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allBannerRows = data.banners || [];
                renderBannerGrid(allBannerRows);
            }
        })
        .catch(error => {
            console.error('Error loading banners:', error);
        });
}

function renderBannerGrid(banners) {
    const grid = document.getElementById('bannerGrid');
    if (!grid) return;

    if (!banners || banners.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 60px 20px; text-align: center; color: #64748b; font-size: 15px; font-family: 'Signika', sans-serif;">
                Chưa có banner nào.
            </div>
        `;
        return;
    }

    // Sort banners by ID
    const sortedBanners = [...banners].sort((a, b) => (a.banner_id || 0) - (b.banner_id || 0));

    let html = '';
    sortedBanners.forEach((banner) => {
        html += `
            <div style="position: relative; background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; transition: all 0.3s ease;">
                <div style="position: relative; aspect-ratio: 3/1; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); overflow: hidden;" class="banner-image-container">
                    <img src="${banner.image_url}" alt="Banner ${banner.banner_id}" style="width: 100%; height: 100%; object-fit: contain; padding: 10px;">
                    <div class="banner-hover-overlay" style="position: absolute; inset: 0; background: rgba(0,0,0,0.4); display: none; align-items: center; justify-content: center; gap: 10px; opacity: 0; transition: opacity 0.3s;">
                        <button type="button" onclick="quickReplaceBanner(${banner.banner_id})" style="padding: 10px 20px; background: linear-gradient(135deg, #A9CCF0 0%, #8BB8E0 100%); color: #333333; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Signika', sans-serif; font-weight: 600; box-shadow: 0 2px 8px rgba(169, 204, 240, 0.5);">Tải ảnh mới</button>
                        <button type="button" onclick="deleteBannerItem(${banner.id})" style="padding: 10px 20px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Signika', sans-serif; font-weight: 600; box-shadow: 0 2px 8px rgba(239,68,68,0.4);">Xóa</button>
                    </div>
                </div>
                <div style="position: absolute; top: 10px; right: 10px; text-align: center; padding: 6px 14px; font-size: 14px; font-weight: 700; color: white; font-family: 'Signika', sans-serif; background: linear-gradient(135deg, #A9CCF0 0%, #8BB8E0 100%); border-radius: 8px; box-shadow: 0 2px 8px rgba(169, 204, 240, 0.5);">
                    Banner ${banner.banner_id}
                </div>
            </div>
        `;
    });
    grid.innerHTML = html;

    // Add hover event listeners
    document.querySelectorAll('.banner-image-container').forEach(container => {
        container.addEventListener('mouseenter', function () {
            this.querySelector('.banner-hover-overlay').style.display = 'flex';
            this.querySelector('.banner-hover-overlay').style.opacity = '1';
        });
        container.addEventListener('mouseleave', function () {
            this.querySelector('.banner-hover-overlay').style.display = 'none';
            this.querySelector('.banner-hover-overlay').style.opacity = '0';
        });
    });
}

function searchBanners() {
    const searchInput = document.getElementById('bannerSearchInput');
    if (!searchInput) return;
    const searchTerm = searchInput.value.trim();

    if (searchTerm) {
        const filtered = allBannerRows.filter(b => String(b.banner_id).includes(searchTerm));
        renderBannerGrid(filtered);
    } else {
        renderBannerGrid(allBannerRows);
    }
}

function resetBannerSearch() {
    const searchInput = document.getElementById('bannerSearchInput');
    if (searchInput) searchInput.value = '';
    renderBannerGrid(allBannerRows);
}

function openAddBannerModal() {
    const modal = document.getElementById('addBannerModal');
    if (!modal) return;

    // Reset inputs
    document.getElementById('bannerIdInput').value = '';
    document.getElementById('bannerFileInput').value = '';
    document.getElementById('bannerFileName').textContent = '';
    bannerPreviewImages = [];
    renderBannerPreview();

    modal.style.display = 'flex';
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddBannerModal();
        }
    };
}

function closeAddBannerModal() {
    const modal = document.getElementById('addBannerModal');
    if (modal) modal.style.display = 'none';
}

function handleBannerFileChange(event) {
    const file = event.target.files && event.target.files[0];
    const fileNameEl = document.getElementById('bannerFileName');
    if (fileNameEl) {
        fileNameEl.textContent = file ? file.name : '';
    }
}

function renderBannerPreview() {
    const previewGrid = document.getElementById('bannerPreviewGrid');
    if (!previewGrid) return;

    if (!bannerPreviewImages.length) {
        previewGrid.innerHTML = '';
        return;
    }

    let html = '';
    bannerPreviewImages.forEach((img, index) => {
        html += `
            <div style="position: relative; width: 100%; padding-top: 100%; background: #f1f5f9; border-radius: 10px; overflow: hidden;">
                <img src="${img.url}" style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;">
                <button type="button" onclick="deleteBannerPreview(${img.id}, ${index})" style="position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; border-radius: 999px; border: none; background: rgba(15,23,42,0.8); color: #f9fafb; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
                <div style="position: absolute; bottom: 4px; left: 4px; padding: 2px 6px; border-radius: 999px; background: rgba(15,23,42,0.75); color: #e5e7eb; font-size: 11px; font-family: 'Signika', sans-serif;">ID: ${img.banner_id}</div>
            </div>
        `;
    });
    previewGrid.innerHTML = html;
}

function uploadBanner() {
    const idInput = document.getElementById('bannerIdInput');
    const fileInput = document.getElementById('bannerFileInput');

    const bannerId = idInput ? idInput.value.trim() : '';
    const file = fileInput ? fileInput.files[0] : null;

    if (!bannerId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng nhập ID!', 'error');
        return;
    }

    if (!file) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn ảnh!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('banner_id', bannerId);
    formData.append('image', file);

    fetch('/banner-images/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.banner) {
                bannerPreviewImages.push({
                    id: data.banner.id,
                    banner_id: bannerId,
                    url: data.banner.image_url
                });
                renderBannerPreview();

                // Reset file input
                document.getElementById('bannerFileInput').value = '';
                document.getElementById('bannerFileName').textContent = '';

                const index = bannerPreviewImages.length;
                window.QHToast && window.QHToast.show && window.QHToast.show(`Đã upload thành công ảnh thứ ${index}.`, 'success');

                // Reload grid
                loadBannerRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload banner.', 'error');
            }
        })
        .catch(error => {
            console.error('Error uploading banner:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function deleteBannerPreview(imageId, indexInPreview) {
    if (!imageId) return;

    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            'Bạn có chắc muốn xóa ảnh này?',
            () => {
                performDeleteBanner(imageId, indexInPreview);
            }
        );
    } else {
        if (confirm('Bạn có chắc muốn xóa ảnh này?')) {
            performDeleteBanner(imageId, indexInPreview);
        }
    }
}

function quickReplaceBanner(bannerId) {
    // Create a temporary hidden file input and open file picker directly
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.style.display = 'none';
    document.body.appendChild(input);

    input.addEventListener('change', function () {
        var file = input.files && input.files[0];
        if (!file) {
            input.remove();
            return;
        }

        var formData = new FormData();
        formData.append('banner_id', bannerId);
        formData.append('image', file);

        fetch('/banner-images/replace/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken
            }
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    window.QHToast && window.QHToast.show && window.QHToast.show('Tải ảnh banner thành công!', 'success');
                    loadBannerRows();
                } else {
                    window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload banner.', 'error');
                }
            })
            .catch(function () {
                window.QHToast && window.QHToast.show && window.QHToast.show('Lỗi kết nối server.', 'error');
            })
            .finally(function () {
                input.remove();
            });
    });

    input.click();
}

function openEditBannerModal(bannerId) {
    // Load existing images for this banner ID first
    const existingImages = allBannerRows.filter(b => b.banner_id == bannerId);
    bannerPreviewImages = existingImages.map(b => ({
        id: b.id,
        banner_id: b.banner_id,
        url: b.image_url
    }));

    // Create a modal for editing/uploading new image
    const modal = document.createElement('div');
    modal.id = 'editBannerModal';
    modal.style.cssText = `
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1001;
    `;

    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; width: 620px; max-width: 94%; max-height: 92vh; display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 22px; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;">
                <h3 style="font-size: 18px; font-weight: 600; font-family: 'Signika', sans-serif; margin: 0;">Tải ảnh lên - ID: ${bannerId}</h3>
                <button type="button" onclick="this.closest('#editBannerModal').remove()" style="padding: 6px 12px; background: #f1f5f9; color: #334155; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-family: 'Signika', sans-serif;">Đóng</button>
            </div>
            <div style="padding: 18px 22px 4px; overflow-y: auto; flex: 1; scrollbar-width: thin; scrollbar-color: #c1c1c1 #f8fafc;">
                <div style="margin-bottom: 14px;">
                    <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #333; font-family: 'Signika', sans-serif;">Upload ảnh mới</label>
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <input type="file" id="editBannerFileInput" accept="image/*" style="display: none;" onchange="handleEditBannerFileChange(event)">
                        <button type="button" onclick="document.getElementById('editBannerFileInput').click()" style="padding: 9px 16px; background: #f1f5f9; color: #334155; border: 1px dashed #cbd5f5; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Signika', sans-serif;">Chọn ảnh</button>
                        <button type="button" onclick="uploadEditBanner(${bannerId})" style="padding: 9px 16px; background: #22c55e; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: 'Signika', sans-serif; font-weight: 500;">Tải ảnh lên</button>
                        <span id="editBannerFileName" style="font-size: 13px; color: #64748b; font-family: 'Signika', sans-serif;"></span>
                    </div>
                </div>
                <div id="editBannerPreviewGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 10px; margin-top: 10px;">
                    <!-- Thumbnails will be rendered here -->
                </div>
            </div>
            <div style="padding: 14px 22px; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 10px; flex-shrink: 0;">
                <button type="button" onclick="this.closest('#editBannerModal').remove()" style="padding: 10px 20px; background: #f1f5f9; color: #334155; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-family: 'Signika', sans-serif;">Đóng</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.onclick = function (e) {
        if (e.target === modal) {
            modal.remove();
        }
    };

    // Render existing images
    renderEditBannerPreview();
}

function handleEditBannerFileChange(event) {
    const file = event.target.files && event.target.files[0];
    const fileNameEl = document.getElementById('editBannerFileName');
    if (fileNameEl) {
        fileNameEl.textContent = file ? file.name : '';
    }
}

function renderEditBannerPreview() {
    const previewGrid = document.getElementById('editBannerPreviewGrid');
    if (!previewGrid) return;

    if (!bannerPreviewImages.length) {
        previewGrid.innerHTML = '';
        return;
    }

    let html = '';
    bannerPreviewImages.forEach((img, index) => {
        html += `
            <div style="position: relative; width: 100%; padding-top: 100%; background: #f1f5f9; border-radius: 10px; overflow: hidden;">
                <img src="${img.url}" style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;">
                <button type="button" onclick="deleteBannerItem(${img.id})" style="position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; border-radius: 999px; border: none; background: rgba(15,23,42,0.8); color: #f9fafb; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
            </div>
        `;
    });
    previewGrid.innerHTML = html;
}

function uploadEditBanner(bannerId) {
    const fileInput = document.getElementById('editBannerFileInput');
    const file = fileInput ? fileInput.files[0] : null;

    if (!file) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn ảnh!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('banner_id', bannerId);
    formData.append('image', file);

    fetch('/banner-images/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.banner) {
                bannerPreviewImages.push({
                    id: data.banner.id,
                    banner_id: bannerId,
                    url: data.banner.image_url
                });
                renderEditBannerPreview();

                // Reset file input
                document.getElementById('editBannerFileInput').value = '';
                document.getElementById('editBannerFileName').textContent = '';

                window.QHToast && window.QHToast.show && window.QHToast.show('Đã upload thành công.', 'success');

                // Reload grid
                loadBannerRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload banner.', 'error');
            }
        })
        .catch(error => {
            console.error('Error uploading banner:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function deleteBannerItem(id) {
    if (!id) return;

    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            'Bạn có chắc muốn xóa banner này?',
            () => {
                performDeleteBanner(id);
            }
        );
    } else {
        if (confirm('Bạn có chắc muốn xóa banner này?')) {
            performDeleteBanner(id);
        }
    }
}

function performDeleteBanner(id, indexInPreview = null) {
    const formData = new FormData();
    formData.append('banner_id', id);

    fetch('/banner-images/delete/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove from preview if exists
                if (typeof indexInPreview === 'number') {
                    bannerPreviewImages.splice(indexInPreview, 1);
                    renderBannerPreview();
                }
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Đã xóa banner.', 'success');
                loadBannerRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể xóa banner.', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting banner:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

// ==================== Product Content Management ====================
let allProductContentRows = [];
let productContentPreviewImages = []; // ảnh đã upload trong modal
let productContentEditorInstance = null; // CKEditor instance
let productContentEditorPromise = null; // Promise for initializing editor

// Custom CKEditor Upload Adapter (for CDN Classic build which doesn't include SimpleUploadAdapter)
class CustomUploadAdapter {
    constructor(loader) {
        this.loader = loader;
    }
    upload() {
        return this.loader.file.then(file => {
            return new Promise((resolve, reject) => {
                const formData = new FormData();
                formData.append('image', file);
                fetch('/upload-temp-image/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': window.csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.url) {
                            resolve({ default: data.url });
                        } else {
                            reject(data.message || 'Upload thất bại!');
                        }
                    })
                    .catch(err => {
                        reject('Upload ảnh thất bại: ' + err.message);
                    });
            });
        });
    }
    abort() { }
}

function CustomUploadAdapterPlugin(editor) {
    editor.plugins.get('FileRepository').createUploadAdapter = (loader) => {
        return new CustomUploadAdapter(loader);
    };
}

function initProductContentSection() {
    loadProductContentRows();
}

function loadProductContentRows() {
    fetch('/product-content/list/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            allProductContentRows = data.contents || [];
            renderProductContentTable(allProductContentRows);
        })
        .catch(error => {
            console.error('Error loading product content:', error);
        });
}

function renderProductContentTable(contents) {
    const container = document.getElementById('productContentTableContainer');
    const grid = document.getElementById('productContentGrid');
    if (container) container.style.display = 'block';
    if (grid) grid.style.display = 'none';

    const tbody = document.getElementById('productContentTableBody');
    if (!tbody) return;

    if (!contents || contents.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="padding: 40px; text-align: center; color: #64748b; font-size: 14px; font-family: 'Signika', sans-serif;">
                    Chưa có nội dung sản phẩm nào.
                </td>
            </tr>
        `;
        return;
    }

    // Sort contents by brand and product name
    const sortedContents = [...contents].sort((a, b) => {
        const brandCompare = (a.brand_name || '').localeCompare(b.brand_name || '');
        if (brandCompare !== 0) return brandCompare;
        return (a.product_name || '').localeCompare(b.product_name || '');
    });

    let html = '';
    sortedContents.forEach((content, index) => {
        // Format ngày từ created_at
        let dateStr = '-';
        if (content.created_at) {
            const date = new Date(content.created_at);
            dateStr = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
        }

        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${index + 1}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif; font-weight: 500;">${content.brand_name || '-'}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif;">${content.product_name || '-'}</td>
                <td style="padding: 12px 16px; font-size: 14px; font-family: 'Signika', sans-serif; color: #64748b;">${dateStr}</td>
                <td style="padding: 12px 16px;">
                    <div style="display: flex; gap: 6px;">
                        <button type="button" onclick="openEditProductContentModal(${content.id})" style="background: #fef3c7; color: #b45309; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-family: 'Signika', sans-serif;">Sửa</button>
                        <button type="button" onclick="quickReplaceProductContent(${content.id})" style="background: #dbeafe; color: #1e40af; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-family: 'Signika', sans-serif;">Ảnh</button>
                        <button type="button" onclick="deleteProductContentItem(${content.id})" style="background: #fee2e2; color: #dc2626; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-family: 'Signika', sans-serif;">Xóa</button>
                    </div>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function searchProductContent() {
    const searchInput = document.getElementById('productContentSearchInput');
    if (!searchInput) return;

    const searchTerm = searchInput.value.trim().toLowerCase();
    if (searchTerm) {
        const filtered = allProductContentRows.filter(c =>
            (c.brand_name && c.brand_name.toLowerCase().includes(searchTerm)) ||
            (c.product_name && c.product_name.toLowerCase().includes(searchTerm)) ||
            (c.content_text && c.content_text.toLowerCase().includes(searchTerm))
        );
        renderProductContentTable(filtered);
    } else {
        renderProductContentTable(allProductContentRows);
    }
}

function resetProductContentSearch() {
    const searchInput = document.getElementById('productContentSearchInput');
    if (searchInput) searchInput.value = '';
    renderProductContentTable(allProductContentRows);
}

function openAddProductContentModal() {
    const modal = document.getElementById('addProductContentModal');
    if (!modal) return;

    modal.style.display = 'flex';

    // Close modal when clicking outside
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddProductContentModal();
        }
    };

    // Reset form
    document.getElementById('productContentBrandSelect').value = '';
    document.getElementById('productContentProductSelect').innerHTML = '<option value="">-- Chọn hãng trước --</option>';
    productContentPreviewImages = [];
    renderProductContentPreview();

    // Initialize CKEditor 5 if not already initialized
    if (!productContentEditorInstance) {
        productContentEditorPromise = ClassicEditor.create(document.querySelector('#productContentEditor'), {
            extraPlugins: [CustomUploadAdapterPlugin],
            language: 'vi',
            toolbar: {
                items: [
                    'undo', 'redo',
                    '|',
                    'heading',
                    '|',
                    'bold', 'italic',
                    '|',
                    'bulletedList', 'numberedList',
                    '|',
                    'outdent', 'indent',
                    '|',
                    'link', 'imageUpload', 'blockQuote', 'insertTable',
                ],
                shouldNotGroupWhenFull: true
            },
            image: {
                toolbar: [
                    'imageTextAlternative',
                    'imageStyle:full',
                    'imageStyle:side'
                ]
            },
            table: {
                contentToolbar: [
                    'tableColumn',
                    'tableRow',
                    'mergeTableCells'
                ]
            },
            heading: {
                options: [
                    { model: 'paragraph', title: 'Đoạn văn', class: 'ck-heading_paragraph' },
                    { model: 'heading1', view: 'h1', title: 'Tiêu đề 1' },
                    { model: 'heading2', view: 'h2', title: 'Tiêu đề 2' },
                    { model: 'heading3', view: 'h3', title: 'Tiêu đề 3' }
                ]
            }
        }).then(editor => {
            productContentEditorInstance = editor;
            return editor;
        }).catch(error => {
            console.error('CKEditor initialization error:', error);
            return null;
        });
    } else if (productContentEditorInstance) {
        // Reset editor content
        productContentEditorInstance.setData('');
    } else if (productContentEditorPromise) {
        // Wait for promise to resolve
        productContentEditorPromise.then(editor => {
            editor.setData('');
        });
    }
}

function closeAddProductContentModal() {
    const modal = document.getElementById('addProductContentModal');
    if (modal) {
        modal.style.display = 'none';
    }

    // Reset editing state
    editingProductContentId = null;

    // Reset title
    const titleEl = modal.querySelector('h3');
    if (titleEl) titleEl.textContent = 'Thêm nội dung sản phẩm';

    // Reset save button to original function
    const saveBtn = modal.querySelector('button[onclick="saveProductContent()"]');
    if (saveBtn) {
        saveBtn.onclick = function () {
            saveProductContent();
        };
    }
}

// Load products by brand cho Product Content (returns Promise)
function loadProductsByBrand(prefix) {
    return new Promise((resolve, reject) => {
        const brandSelect = document.getElementById(prefix + 'BrandSelect');
        const productSelect = document.getElementById(prefix + 'ProductSelect');

        if (!brandSelect || !productSelect) {
            resolve();
            return;
        }

        const brandId = brandSelect.value;

        if (!brandId) {
            productSelect.innerHTML = '<option value="">-- Chọn hãng trước --</option>';
            resolve();
            return;
        }

        // Load products from API
        fetch('/products/list/json/?brand_id=' + brandId, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                const products = data.products || [];
                if (products.length === 0) {
                    productSelect.innerHTML = '<option value="">-- Không có sản phẩm --</option>';
                } else {
                    let options = '<option value="">-- Chọn sản phẩm --</option>';
                    products.forEach(product => {
                        options += `<option value="${product.id}">${product.name}</option>`;
                    });
                    productSelect.innerHTML = options;
                }
                resolve();
            })
            .catch(error => {
                console.error('Error loading products:', error);
                productSelect.innerHTML = '<option value="">-- Lỗi tải sản phẩm --</option>';
                resolve();
            });
    });
}

// Insert content tag (bold, italic, etc.)
function insertContentTag(tag) {
    const textarea = document.getElementById('productContentTextInput');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);

    let newText = '';
    let cursorOffset = 0;

    switch (tag) {
        case 'b':
            newText = '<b>' + selectedText + '</b>';
            cursorOffset = 3;
            break;
        case 'i':
            newText = '<i>' + selectedText + '</i>';
            cursorOffset = 3;
            break;
        case 'u':
            newText = '<u>' + selectedText + '</u>';
            cursorOffset = 3;
            break;
        case 'h2':
            newText = '\n<h2>' + selectedText + '</h2>\n';
            cursorOffset = 5;
            break;
        case 'h3':
            newText = '\n<h3>' + selectedText + '</h3>\n';
            cursorOffset = 5;
            break;
        case 'ul':
            newText = '\n<ul>\n<li>' + selectedText + '</li>\n</ul>\n';
            cursorOffset = 9;
            break;
        case 'ol':
            newText = '\n<ol>\n<li>' + selectedText + '</li>\n</ol>\n';
            cursorOffset = 9;
            break;
        default:
            newText = selectedText;
    }

    textarea.value = text.substring(0, start) + newText + text.substring(end);

    // Restore focus and selection
    textarea.focus();
    textarea.setSelectionRange(start + cursorOffset, start + cursorOffset + selectedText.length);
}

// Insert image into content
function insertContentImage() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.onchange = function (e) {
        const file = e.target.files[0];
        if (!file) return;

        // Upload image first
        const formData = new FormData();
        formData.append('image', file);

        fetch('/upload-temp-image/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.url) {
                    const textarea = document.getElementById('productContentTextInput');
                    if (textarea) {
                        const start = textarea.selectionStart;
                        const text = textarea.value;
                        const imgTag = '\n<img src="' + data.url + '" alt="" style="max-width: 100%; height: auto;">\n';
                        textarea.value = text.substring(0, start) + imgTag + text.substring(start);
                        textarea.focus();
                    }
                } else {
                    window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload ảnh.', 'error');
                }
            })
            .catch(error => {
                console.error('Error uploading image:', error);
                window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
            });
    };
    fileInput.click();
}

function handleProductContentFileChange(event) {
    const file = event.target.files[0];
    const fileNameEl = document.getElementById('productContentFileName');
    if (file) {
        fileNameEl.textContent = file.name;
    }
}

function renderProductContentPreview() {
    const previewGrid = document.getElementById('productContentPreviewGrid');
    if (!previewGrid) return;

    if (!productContentPreviewImages.length) {
        previewGrid.innerHTML = '';
        return;
    }

    previewGrid.innerHTML = productContentPreviewImages.map((img, index) => `
        <div style="position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; border: 2px solid #e2e8f0;">
            <img src="${img.url}" style="width: 100%; height: 100%; object-fit: cover;">
            <button type="button" onclick="deleteProductContentPreview(${img.id}, ${index})" style="position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; border-radius: 999px; border: none; background: rgba(15,23,42,0.8); color: #f9fafb; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
            <div style="position: absolute; bottom: 4px; left: 4px; padding: 2px 6px; border-radius: 999px; background: rgba(15,23,42,0.75); color: #e5e7eb; font-size: 11px; font-family: 'Signika', sans-serif;">ID: ${img.content_id}</div>
        </div>
    `).join('');
}

function saveProductContent() {
    const brandSelect = document.getElementById('productContentBrandSelect');
    const productSelect = document.getElementById('productContentProductSelect');

    const brandId = brandSelect ? brandSelect.value : '';
    const productId = productSelect ? productSelect.value : '';

    // Validate brand and product first
    if (!brandId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn hãng!', 'error');
        return;
    }

    if (!productId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn sản phẩm!', 'error');
        return;
    }

    // Get content from CKEditor
    if (productContentEditorInstance) {
        // Editor is ready, get data directly
        try {
            const contentText = productContentEditorInstance.getData();
            saveProductContentData(brandId, productId, contentText);
        } catch (e) {
            console.error('Error getting editor data:', e);
            // Fallback: try getting innerHTML from CKEditor editable area
            const editable = document.querySelector('.ck-editor__editable');
            const contentText = editable ? editable.innerHTML : '';
            saveProductContentData(brandId, productId, contentText);
        }
    } else if (productContentEditorPromise) {
        // Wait for editor to be ready
        productContentEditorPromise.then(editor => {
            if (editor) {
                const contentText = editor.getData();
                saveProductContentData(brandId, productId, contentText);
            } else {
                // Editor failed to init, try fallback
                const editable = document.querySelector('.ck-editor__editable');
                const contentText = editable ? editable.innerHTML : '';
                saveProductContentData(brandId, productId, contentText);
            }
        }).catch(error => {
            console.error('Error getting editor data:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Không thể lấy nội dung từ editor!', 'error');
        });
    } else {
        // Fallback if editor not initialized - try to find editable area
        const editable = document.querySelector('.ck-editor__editable');
        if (editable) {
            const contentText = editable.innerHTML;
            saveProductContentData(brandId, productId, contentText);
        } else {
            window.QHToast && window.QHToast.show && window.QHToast.show('Editor chưa sẵn sàng!', 'error');
        }
    }
}

function saveProductContentData(brandId, productId, contentText) {
    if (!brandId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn hãng!', 'error');
        return;
    }

    if (!productId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn sản phẩm!', 'error');
        return;
    }

    // Allow empty content (user might just want to save the product without content)
    // But we need at least some validation - check if it's just empty HTML tags
    const strippedContent = contentText.replace(/<[^>]*>/g, '').trim();
    if (!strippedContent) {
        // Content is empty or just HTML tags - this is allowed
    }

    const formData = new FormData();
    formData.append('brand_id', brandId);
    formData.append('product_id', productId);
    formData.append('content_text', contentText);

    fetch('/product-content/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    console.error('Server error:', response.status, text);
                    throw new Error('Server trả về lỗi ' + response.status);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                window.QHToast && window.QHToast.show && window.QHToast.show('Lưu nội dung thành công!', 'success');
                closeAddProductContentModal();
                loadProductContentRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể lưu nội dung.', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving product content:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show(error.message || 'Có lỗi xảy ra!', 'error');
        });
}

function deleteProductContentPreview(imageId, indexInPreview) {
    if (typeof imageId === 'number') {
        if (window.QHConfirm && window.QHConfirm.show) {
            window.QHConfirm.show(
                'Bạn có chắc muốn xóa?',
                () => {
                    performDeleteProductContent(imageId, indexInPreview);
                }
            );
        } else {
            if (confirm('Bạn có chắc muốn xóa?')) {
                performDeleteProductContent(imageId, indexInPreview);
            }
        }
    } else {
        productContentPreviewImages.splice(indexInPreview, 1);
        renderProductContentPreview();
    }
}

function quickReplaceProductContent(contentId) {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.onchange = function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('content_id', contentId);
        formData.append('image', file);

        fetch('/product-content/replace/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.csrfToken
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.QHToast && window.QHToast.show && window.QHToast.show('Tải ảnh thành công!', 'success');
                    loadProductContentRows();
                } else {
                    window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể upload ảnh.', 'error');
                }
            })
            .catch(error => {
                console.error('Error replacing product content image:', error);
                window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
            });
    };
    fileInput.click();
}

let editingProductContentId = null;

function openEditProductContentModal(contentId) {
    const modal = document.getElementById('addProductContentModal');
    if (!modal) return;

    // Close modal when clicking outside
    modal.onclick = function (e) {
        if (e.target === modal) {
            closeAddProductContentModal();
        }
    };

    // Find the content data
    const content = allProductContentRows.find(c => c.id === contentId);
    if (!content) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Không tìm thấy nội dung!', 'error');
        return;
    }

    editingProductContentId = contentId;

    modal.style.display = 'flex';

    // Set title
    const titleEl = modal.querySelector('h3');
    if (titleEl) titleEl.textContent = 'Sửa nội dung sản phẩm';

    // Set brand and product
    document.getElementById('productContentBrandSelect').value = content.brand_id;

    // Load products for selected brand
    loadProductsByBrand('productContent').then(() => {
        document.getElementById('productContentProductSelect').value = content.product_id;
    });

    // Set content text in CKEditor
    if (productContentEditorInstance) {
        // Editor already initialized — set data directly
        productContentEditorInstance.setData(content.content_text || '');
    } else if (productContentEditorPromise) {
        // Editor is still initializing — wait for it
        productContentEditorPromise.then(editor => {
            if (editor) {
                editor.setData(content.content_text || '');
            }
        });
    } else {
        // Editor not initialized yet — create it, then set data
        productContentEditorPromise = ClassicEditor.create(document.querySelector('#productContentEditor'), {
            extraPlugins: [CustomUploadAdapterPlugin],
            language: 'vi',
            toolbar: {
                items: [
                    'undo', 'redo',
                    '|',
                    'heading',
                    '|',
                    'bold', 'italic',
                    '|',
                    'bulletedList', 'numberedList',
                    '|',
                    'outdent', 'indent',
                    '|',
                    'link', 'imageUpload', 'blockQuote', 'insertTable',
                ],
                shouldNotGroupWhenFull: true
            },
            image: {
                toolbar: [
                    'imageTextAlternative',
                    'imageStyle:full',
                    'imageStyle:side'
                ]
            },
            table: {
                contentToolbar: [
                    'tableColumn',
                    'tableRow',
                    'mergeTableCells'
                ]
            },
            heading: {
                options: [
                    { model: 'paragraph', title: 'Đoạn văn', class: 'ck-heading_paragraph' },
                    { model: 'heading1', view: 'h1', title: 'Tiêu đề 1' },
                    { model: 'heading2', view: 'h2', title: 'Tiêu đề 2' },
                    { model: 'heading3', view: 'h3', title: 'Tiêu đề 3' }
                ]
            }
        }).then(editor => {
            productContentEditorInstance = editor;
            editor.setData(content.content_text || '');
            return editor;
        }).catch(error => {
            console.error('CKEditor initialization error:', error);
            return null;
        });
    }

    // Show preview image if exists
    if (content.image_url) {
        productContentPreviewImages = [{ url: content.image_url }];
        renderProductContentPreview();
    } else {
        productContentPreviewImages = [];
        renderProductContentPreview();
    }

    // Update save button to call edit function
    const saveBtn = modal.querySelector('button[onclick="saveProductContent()"]');
    if (saveBtn) {
        saveBtn.onclick = function () {
            editProductContent(contentId);
        };
    }
}

function editProductContent(contentId) {
    const brandId = document.getElementById('productContentBrandSelect').value;
    const productId = document.getElementById('productContentProductSelect').value;
    const contentText = productContentEditorInstance ? productContentEditorInstance.getData() : '';

    if (!brandId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn hãng!', 'error');
        return;
    }

    if (!productId) {
        window.QHToast && window.QHToast.show && window.QHToast.show('Vui lòng chọn sản phẩm!', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('brand_id', brandId);
    formData.append('product_id', productId);
    formData.append('content_text', contentText);

    // Add image if selected
    const fileInput = document.getElementById('productContentImageInput');
    if (fileInput && fileInput.files.length > 0) {
        formData.append('image', fileInput.files[0]);
    }

    fetch('/product-content/add/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.QHToast && window.QHToast.show && window.QHToast.show('Cập nhật nội dung thành công!', 'success');
                closeAddProductContentModal();
                loadProductContentRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể lưu nội dung.', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving product content:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

function deleteProductContentItem(id) {
    if (!id) return;

    if (window.QHConfirm && window.QHConfirm.show) {
        window.QHConfirm.show(
            'Bạn có chắc muốn xóa nội dung này?',
            () => {
                performDeleteProductContent(id);
            }
        );
    } else {
        if (confirm('Bạn có chắc muốn xóa nội dung này?')) {
            performDeleteProductContent(id);
        }
    }
}

function performDeleteProductContent(id, indexInPreview = null) {
    const formData = new FormData();
    formData.append('content_id', id);

    fetch('/product-content/delete/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove from preview if exists
                if (typeof indexInPreview === 'number') {
                    productContentPreviewImages.splice(indexInPreview, 1);
                    renderProductContentPreview();
                }
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Đã xóa nội dung.', 'success');
                loadProductContentRows();
            } else {
                window.QHToast && window.QHToast.show && window.QHToast.show(data.message || 'Không thể xóa nội dung.', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting product content:', error);
            window.QHToast && window.QHToast.show && window.QHToast.show('Có lỗi xảy ra!', 'error');
        });
}

// ==================== QR Approval ====================

var _qrDetailCurrentId = null;

function formatQrPrice(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + 'đ';
}

function loadQrApprovalList() {
    if (!window.qrListUrl) return;
    var tbody = document.getElementById('qrApprovalTableBody');
    if (!tbody) return;

    fetch(window.qrListUrl)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.success) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:40px 16px;text-align:center;color:#94a3b8;font-size:14px;">Lỗi tải dữ liệu</td></tr>';
                return;
            }
            if (data.items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:40px 16px;text-align:center;color:#94a3b8;font-size:14px;">Không có QR nào đang chờ duyệt</td></tr>';
                return;
            }
            var html = '';
            data.items.forEach(function (item) {
                html += '<tr style="border-bottom: 1px solid #f1f5f9;">'
                    + '<td style="padding:12px 16px;text-align:center;font-size:14px;color:#334155;">' + item.stt + '</td>'
                    + '<td style="padding:12px 16px;font-size:14px;color:#334155;">' + item.user_email + '</td>'
                    + '<td style="padding:12px 16px;text-align:right;font-size:14px;font-weight:600;color:#dc2626;">' + formatQrPrice(item.amount) + '</td>'
                    + '<td style="padding:12px 16px;font-size:14px;color:#334155;font-family:monospace;font-weight:600;">' + item.transfer_code + '</td>'
                    + '<td style="padding:12px 16px;font-size:13px;color:#64748b;">' + item.created_at + '</td>'
                    + '<td style="padding:12px 16px;text-align:center;">'
                    + '  <div style="display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">'
                    + '    <button onclick="openQrDetail(' + item.id + ')" style="padding:6px 12px;background:#eff6ff;color:#2563eb;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:\'Signika\',sans-serif;font-weight:500;">Xem</button>'
                    + '    <button onclick="approveQr(' + item.id + ')" style="padding:6px 12px;background:#d1fae5;color:#059669;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:\'Signika\',sans-serif;font-weight:500;">Duyệt</button>'
                    + '    <button onclick="cancelQr(' + item.id + ')" style="padding:6px 12px;background:#fee2e2;color:#dc2626;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:\'Signika\',sans-serif;font-weight:500;">Hủy</button>'
                    + '  </div>'
                    + '</td>'
                    + '</tr>';
            });
            tbody.innerHTML = html;
        })
        .catch(function () {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:40px 16px;text-align:center;color:#94a3b8;font-size:14px;">Lỗi kết nối</td></tr>';
        });
}

function openQrDetail(id) {
    if (!window.qrDetailUrl) return;
    fetch(window.qrDetailUrl + '?id=' + id)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.success) {
                window.QHToast && window.QHToast.show(data.message || 'Lỗi', 'error');
                return;
            }
            var d = data.data;
            _qrDetailCurrentId = d.id;

            var img = document.getElementById('qrDetailImage');
            if (img) img.src = d.qr_url;

            var user = document.getElementById('qrDetailUser');
            if (user) user.textContent = d.user_name;

            var email = document.getElementById('qrDetailEmail');
            if (email) email.textContent = d.user_email;

            var amount = document.getElementById('qrDetailAmount');
            if (amount) amount.textContent = formatQrPrice(d.amount);

            var code = document.getElementById('qrDetailCode');
            if (code) code.textContent = d.transfer_code;

            var time = document.getElementById('qrDetailTime');
            if (time) time.textContent = d.created_at;

            var modal = document.getElementById('qrDetailModal');
            if (modal) modal.style.display = 'flex';
        })
        .catch(function () {
            window.QHToast && window.QHToast.show('Lỗi kết nối', 'error');
        });
}

function closeQrDetailModal() {
    var modal = document.getElementById('qrDetailModal');
    if (modal) modal.style.display = 'none';
    _qrDetailCurrentId = null;
}

function approveQr(id) {
    if (!window.qrApproveUrl) return;
    if (!window.QHConfirm) {
        _doApproveQr(id);
        return;
    }
    window.QHConfirm.show('Xác nhận duyệt QR chuyển khoản này?', function () {
        _doApproveQr(id);
    });
}

function _doApproveQr(id) {
    fetch(window.qrApproveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrfToken },
        body: JSON.stringify({ id: id })
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                window.QHToast && window.QHToast.show(data.message, 'success');
                loadQrApprovalList();
                closeQrDetailModal();
            } else {
                window.QHToast && window.QHToast.show(data.message || 'Lỗi', 'error');
            }
        })
        .catch(function () {
            window.QHToast && window.QHToast.show('Lỗi kết nối', 'error');
        });
}

function cancelQr(id) {
    if (!window.qrCancelUrl) return;
    if (!window.QHConfirm) {
        _doCancelQr(id);
        return;
    }
    window.QHConfirm.show('Xác nhận hủy QR chuyển khoản này?', function () {
        _doCancelQr(id);
    });
}

function _doCancelQr(id) {
    fetch(window.qrCancelUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.csrfToken },
        body: JSON.stringify({ id: id })
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                window.QHToast && window.QHToast.show(data.message, 'success');
                loadQrApprovalList();
                closeQrDetailModal();
            } else {
                window.QHToast && window.QHToast.show(data.message || 'Lỗi', 'error');
            }
        })
        .catch(function () {
            window.QHToast && window.QHToast.show('Lỗi kết nối', 'error');
        });
}

function approveQrFromDetail() {
    if (_qrDetailCurrentId) approveQr(_qrDetailCurrentId);
}

function cancelQrFromDetail() {
    if (_qrDetailCurrentId) cancelQr(_qrDetailCurrentId);
}
