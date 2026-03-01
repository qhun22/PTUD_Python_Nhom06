/* ========================================================
   QHUN22 – Product Detail Page Logic
   ======================================================== */

// ========== Trạng thái ==========
let selectedColor = null;
let selectedStorage = null;
let currentImages = [];
let currentImageIndex = 0;
let autoSlideInterval = null;
let isAutoSlideActive = true;

// Trạng thái gallery lightbox
let galleryImages = [];
let galleryIndex = 0;
let galleryCurrentSku = null;

// ========== Khởi tạo ==========
document.addEventListener('DOMContentLoaded', function () {
    const firstStorageBtn = document.querySelector('.pd-storage-btn');
    if (firstStorageBtn) selectStorage(firstStorageBtn);

    const firstColorBtn = document.querySelector('.pd-color-btn');
    if (firstColorBtn) selectColor(firstColorBtn);

    updateStoragePrices();
    updateColorButtons();
    renderBottomTabs();

    if (typeof specData !== 'undefined' && specData) {
        renderSpec(specData);
        setupSpecScrollSpy();
    }

    setTimeout(function () { startAutoSlide(); }, 2000);
});

window.addEventListener('beforeunload', function () { stopAutoSlide(); });

document.addEventListener('visibilitychange', function () {
    if (document.hidden) pauseAutoSlide();
    else resumeAutoSlide();
});

// ========== Chọn dung lượng ==========
function selectStorage(btn) {
    document.querySelectorAll('.pd-storage-btn').forEach(function (b) { b.classList.remove('selected'); });
    btn.classList.add('selected');
    selectedStorage = btn.dataset.storage;
    updatePriceDisplay();
    updateStoragePrices();
}

function updateStoragePrices() {
    document.querySelectorAll('.pd-storage-btn').forEach(function (btn) {
        var storage = btn.dataset.storage;
        var v = variantsData.find(function (x) { return x.storage === storage; });
        var priceEl = btn.querySelector('.pd-storage-price');
        if (v && priceEl) priceEl.textContent = formatPrice(v.price) + ' đ';
    });
}

// ========== Chọn màu sắc ==========
function selectColor(btn) {
    document.querySelectorAll('.pd-color-btn').forEach(function (b) { b.classList.remove('selected'); });
    btn.classList.add('selected');
    selectedColor = btn.dataset.color;

    var sku = btn.dataset.sku;
    loadColorImages(sku);
    updatePriceDisplay();

    document.querySelectorAll('.pd-bottom-tab[data-color]').forEach(function (t) {
        t.classList.toggle('active', t.dataset.color === selectedColor);
    });
}

function updateColorButtons() {
    document.querySelectorAll('.pd-color-btn').forEach(function (btn, idx) {
        var sku = btn.dataset.sku;
        var thumbEl = document.getElementById('colorThumb_' + idx);
        var nameEl = btn.querySelector('.pd-color-name');

        if (colorImagesData[sku]) {
            if (thumbEl && colorImagesData[sku].images.length > 0) {
                thumbEl.innerHTML = '<img src="' + colorImagesData[sku].images[0] + '" alt="">';
            }
            if (nameEl && colorImagesData[sku].color_name) {
                nameEl.textContent = colorImagesData[sku].color_name;
            }
        }
    });
}

// ========== Thư viện ảnh ==========
function loadColorImages(sku) {
    if (colorImagesData[sku] && colorImagesData[sku].images.length > 0) {
        currentImages = colorImagesData[sku].images;
    } else {
        var fallbackImg = document.getElementById('pdMainImg').dataset.fallback || '/static/logos/sean.gif';
        currentImages = [fallbackImg];
    }
    currentImageIndex = 0;
    renderGallery();
    stopAutoSlide();
    setTimeout(function () { startAutoSlide(); }, 1000);
}

function renderGallery() {
    var mainImg = document.getElementById('pdMainImg');
    if (!mainImg || currentImages.length === 0) return;

    var newSrc = currentImages[currentImageIndex];
    // Nếu cùng ảnh, bỏ qua
    if (mainImg.src && mainImg.src.endsWith(newSrc.replace(/^.*\/\/[^\/]+/, ''))) return;

    // Fade out nhanh (150ms)
    mainImg.classList.add('pd-fade-out');
    setTimeout(function () {
        mainImg.src = newSrc;
        mainImg.onload = function () {
            mainImg.classList.remove('pd-fade-out');
            mainImg.onload = null;
        };
        // Dự phòng: nếu ảnh được cache và onload không kích hoạt
        setTimeout(function () {
            mainImg.classList.remove('pd-fade-out');
        }, 100);
    }, 150);
}

// ========== Tự động chuyển ảnh ==========
function startAutoSlide() {
    if (autoSlideInterval) clearInterval(autoSlideInterval);
    if (currentImages && currentImages.length > 1 && isAutoSlideActive) {
        autoSlideInterval = setInterval(function () {
            currentImageIndex = (currentImageIndex + 1) % currentImages.length;
            renderGallery();
        }, 3000);
    }
}

function stopAutoSlide() {
    if (autoSlideInterval) { clearInterval(autoSlideInterval); autoSlideInterval = null; }
}

function pauseAutoSlide() { isAutoSlideActive = false; stopAutoSlide(); }

function resumeAutoSlide() { isAutoSlideActive = true; startAutoSlide(); }

function prevImage() {
    if (currentImages.length === 0) return;
    pauseAutoSlide();
    setTimeout(function () { resumeAutoSlide(); }, 5000);
    currentImageIndex = (currentImageIndex - 1 + currentImages.length) % currentImages.length;
    renderGallery();
}

function nextImage() {
    if (currentImages.length === 0) return;
    pauseAutoSlide();
    setTimeout(function () { resumeAutoSlide(); }, 5000);
    currentImageIndex = (currentImageIndex + 1) % currentImages.length;
    renderGallery();
}

// ========== Hiển thị giá ==========
function updatePriceDisplay() {
    if (!selectedColor || !selectedStorage) return;

    var variant = variantsData.find(function (v) {
        return v.color_name === selectedColor && v.storage === selectedStorage;
    });
    if (!variant) return;

    document.getElementById('pdPrice').textContent = formatPrice(variant.price) + ' đ';

    var origEl = document.getElementById('pdOriginalPrice');
    if (variant.original_price > variant.price) {
        origEl.textContent = formatPrice(variant.original_price) + ' đ';
        origEl.style.display = '';
    } else {
        origEl.style.display = 'none';
    }

    // Cập nhật trạng thái nút theo tồn kho
    var cartBtn = document.querySelector('.pd-btn-cart');
    var buyBtn = document.querySelector('.pd-btn-buy');
    var stockBadge = document.getElementById('pdStockBadge');
    
    if (variant.stock_quantity <= 0) {
        // Hết hàng - hiển thị badge và disable nút
        if (cartBtn) {
            cartBtn.disabled = true;
            cartBtn.style.opacity = '0.5';
            cartBtn.style.cursor = 'not-allowed';
        }
        if (buyBtn) {
            buyBtn.disabled = true;
            buyBtn.style.opacity = '0.5';
            buyBtn.style.cursor = 'not-allowed';
        }
        if (stockBadge) {
            stockBadge.style.display = 'block';
            stockBadge.style.background = '#fee2e2';
            stockBadge.innerHTML = '<span style="color: #ef4444; font-weight: 600;">Hết hàng</span>';
        }
    } else {
        // Còn hàng - ẩn badge và enable nút
        if (cartBtn) {
            cartBtn.disabled = false;
            cartBtn.style.opacity = '1';
            cartBtn.style.cursor = 'pointer';
        }
        if (buyBtn) {
            buyBtn.disabled = false;
            buyBtn.style.opacity = '1';
            buyBtn.style.cursor = 'pointer';
        }
        if (stockBadge) {
            stockBadge.style.display = 'none';
        }
    }

    document.getElementById('pdSku').textContent = variant.sku || '-';

    var installEl = document.getElementById('pdInstallment');
    if (variant.price > 0) {
        var monthly = Math.round(variant.price / 6);
        installEl.textContent = 'Trả góp 0% thẻ TD/CTTC chỉ từ ' + formatPrice(monthly) + ' đ x 6 tháng >';
    } else {
        installEl.textContent = '';
    }
}

// ========== Tab điều hướng phía dưới ==========
function renderBottomTabs() {
    var container = document.getElementById('pdBottomTabs');
    if (!container) return;

    var html = '';
    var colorBtns = document.querySelectorAll('.pd-color-btn');

    colorBtns.forEach(function (btn) {
        var sku = btn.dataset.sku;
        var color = btn.dataset.color;
        var imgData = colorImagesData[sku];
        var thumbUrl = (imgData && imgData.images.length > 0) ? imgData.images[0] : '';
        var displayName = (imgData && imgData.color_name) ? imgData.color_name : color;

        html += '<div class="pd-bottom-tab' + (color === selectedColor ? ' active' : '') + '" data-color="' + color + '" onclick="selectColorByName(\'' + color.replace(/'/g, "\\'") + '\')">';
        html += '<div class="pd-bottom-tab-icon">';
        if (thumbUrl) html += '<img src="' + thumbUrl + '" alt="">';
        html += '</div>';
        html += '<div class="pd-bottom-tab-label">' + displayName + '</div>';
        html += '</div>';
    });

    if (typeof specData !== 'undefined' && specData) {
        html += '<div class="pd-bottom-tab" onclick="scrollToSpec()">';
        html += '<div class="pd-bottom-tab-icon"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><circle cx="12" cy="12" r="3"/></svg></div>';
        html += '<div class="pd-bottom-tab-label">Thông số kỹ thuật</div>';
        html += '</div>';
    }

    html += '<div class="pd-bottom-tab" onclick="scrollToDescription()">';
    html += '<div class="pd-bottom-tab-icon"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>';
    html += '<div class="pd-bottom-tab-label">Thông tin sản phẩm</div>';
    html += '</div>';

    html += '<div class="pd-bottom-tab" onclick="openGallery()">';
    html += '<div class="pd-bottom-tab-icon"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg></div>';
    html += '<div class="pd-bottom-tab-label">Xem chi tiết ảnh</div>';
    html += '</div>';

    container.innerHTML = html;
    var totalTabs = container.children.length;
    if (totalTabs > 0) {
        container.style.gridTemplateColumns = 'repeat(' + totalTabs + ', 1fr)';
    }
}

function selectColorByName(colorName) {
    var btn = document.querySelector('.pd-color-btn[data-color="' + colorName + '"]');
    if (btn) selectColor(btn);
}

function scrollToSpec() {
    // Mở modal thông số thay vì cuộn đến phần inline
    openSpecModal();
}

function scrollToDescription() {
    // Nếu có panel nội dung sản phẩm, mở nó (trượt từ phải như spec)
    if (typeof hasProductContent !== 'undefined' && hasProductContent) {
        openContentModal();
        return;
    }
    // Dự phòng: hiển thị mô tả inline
    var el = document.getElementById('pdDescSection');
    if (el) {
        el.style.display = 'block';
        var content = document.getElementById('pdDescContent');
        if (content && !content.innerHTML.trim()) {
            content.textContent = productDescription || 'Chưa có thông tin sản phẩm.';
        }
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// ========== Hộp xem ảnh Gallery Lightbox ==========
function openGallery() {
    var overlay = document.getElementById('pdGalleryOverlay');
    if (!overlay) return;

    buildGalleryColorTabs();

    var activeBtn = document.querySelector('.pd-color-btn.selected');
    if (activeBtn) {
        galleryCurrentSku = activeBtn.dataset.sku;
    } else {
        var firstSku = Object.keys(colorImagesData)[0];
        galleryCurrentSku = firstSku || null;
    }

    loadGalleryColor(galleryCurrentSku);
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function buildGalleryColorTabs() {
    var container = document.getElementById('pdGalleryColorTabs');
    if (!container) return;
    var html = '';
    document.querySelectorAll('.pd-color-btn').forEach(function (btn) {
        var sku = btn.dataset.sku;
        var imgData = colorImagesData[sku];
        var displayName = (imgData && imgData.color_name) ? imgData.color_name : btn.dataset.color;
        html += '<div class="pd-gallery-color-tab" data-sku="' + sku + '" onclick="switchGalleryColor(\'' + sku.replace(/'/g, "\\'") + '\')">' + displayName + '</div>';
    });
    html += '<button class="pd-gallery-close" onclick="closeGallery()">';
    html += '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
    html += '</button>';
    container.innerHTML = html;
}

function switchGalleryColor(sku) {
    galleryCurrentSku = sku;
    loadGalleryColor(sku);
}

function loadGalleryColor(sku) {
    var images = [];
    if (sku && colorImagesData[sku]) {
        images = colorImagesData[sku].images || [];
    } else {
        images = currentImages;
    }
    galleryImages = images;
    galleryIndex = 0;

    document.querySelectorAll('.pd-gallery-color-tab').forEach(function (tab) {
        tab.classList.toggle('active', tab.dataset.sku === sku);
    });

    updateGalleryMainImg();
    buildGalleryThumbs();
}

function updateGalleryMainImg() {
    var img = document.getElementById('pdGalleryMainImg');
    if (!img) return;
    if (galleryImages.length === 0) {
        img.src = '';
        img.alt = 'Chưa có ảnh';
        return;
    }
    img.classList.add('pd-slide-out');
    setTimeout(function () {
        img.src = galleryImages[galleryIndex];
        img.alt = 'Ảnh ' + (galleryIndex + 1);
        img.onload = function () {
            img.classList.remove('pd-slide-out');
        };
        setTimeout(function () {
            img.classList.remove('pd-slide-out');
        }, 600);
    }, 400);
    document.querySelectorAll('.pd-gallery-thumb').forEach(function (t, i) {
        t.classList.toggle('active', i === galleryIndex);
    });
}

function buildGalleryThumbs() {
    var container = document.getElementById('pdGalleryThumbs');
    if (!container) return;
    if (galleryImages.length === 0) {
        container.innerHTML = '<p style="color:#94a3b8;font-size:13px;">Chưa có ảnh cho màu này.</p>';
        return;
    }
    var html = '';
    galleryImages.forEach(function (url, idx) {
        html += '<div class="pd-gallery-thumb' + (idx === galleryIndex ? ' active' : '') + '" onclick="galleryGoTo(' + idx + ')">';
        html += '<img src="' + url + '" alt="" draggable="false">';
        html += '</div>';
    });
    container.innerHTML = html;
}

function galleryGoTo(idx) { galleryIndex = idx; updateGalleryMainImg(); }
function galleryPrev() { if (galleryImages.length === 0) return; galleryIndex = (galleryIndex - 1 + galleryImages.length) % galleryImages.length; updateGalleryMainImg(); }
function galleryNext() { if (galleryImages.length === 0) return; galleryIndex = (galleryIndex + 1) % galleryImages.length; updateGalleryMainImg(); }

function closeGallery() {
    var overlay = document.getElementById('pdGalleryOverlay');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}

function closeGalleryOverlay(e) {
    if (e.target === document.getElementById('pdGalleryOverlay')) closeGallery();
}

document.addEventListener('keydown', function (e) {
    var overlay = document.getElementById('pdGalleryOverlay');
    if (!overlay || !overlay.classList.contains('show')) return;
    if (e.key === 'ArrowLeft') galleryPrev();
    else if (e.key === 'ArrowRight') galleryNext();
    else if (e.key === 'Escape') closeGallery();
});

// ========== Thông số kỹ thuật (dạng FPTShop) ==========
var specGroups = []; // Nhóm thông số đã phân tích: [{name, specs: [{name, value}]}]

function parseSpecData(data) {
    var groups = [];
    if (!data) return groups;

    if (data.groups && Array.isArray(data.groups)) {
        // Định dạng cấu trúc: {groups: [{name/title, specs/items: [{name/key/label, value}]}]}
        data.groups.forEach(function (g) {
            var specs = [];
            var specArr = g.specs || g.items || [];
            if (Array.isArray(specArr)) {
                specArr.forEach(function (s) {
                    specs.push({ name: s.name || s.key || s.label || '', value: s.value || '' });
                });
            }
            groups.push({ name: g.name || g.title || '', specs: specs });
        });
    } else if (typeof data === 'object') {
        // Định dạng phẳng: {key: value} hoặc {key: {k2: v2}}
        var flatSpecs = [];
        for (var key in data) {
            if (!data.hasOwnProperty(key)) continue;
            var value = data[key];
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                var subSpecs = [];
                for (var k2 in value) {
                    if (!value.hasOwnProperty(k2)) continue;
                    subSpecs.push({ name: k2, value: value[k2] });
                }
                groups.push({ name: key, specs: subSpecs });
            } else {
                flatSpecs.push({ name: key, value: String(value) });
            }
        }
        if (flatSpecs.length > 0) {
            groups.unshift({ name: 'Thông tin chung', specs: flatSpecs });
        }
    }
    return groups;
}

function renderSpec(data) {
    specGroups = parseSpecData(data);
}

function openSpecModal() {
    var overlay = document.getElementById('pdSpecOverlay');
    if (!overlay) return;

    renderSpecTabs();
    renderSpecModalBody();

    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function renderSpecTabs() {
    var container = document.getElementById('pdSpecTabs');
    if (!container) return;

    var html = '';
    specGroups.forEach(function (group, idx) {
        html += '<div class="pd-spec-tab' + (idx === 0 ? ' active' : '') + '" data-group="' + idx + '" onclick="specTabClick(' + idx + ')">' + group.name + '</div>';
    });
    container.innerHTML = html;
}

function renderSpecModalBody() {
    var body = document.getElementById('pdSpecModalBody');
    if (!body) return;

    var html = '';
    specGroups.forEach(function (group, idx) {
        html += '<div class="pd-spec-group" id="specGroup_' + idx + '">';
        html += '<div class="pd-spec-group-title">' + group.name + '</div>';
        html += '<table>';
        group.specs.forEach(function (s) {
            var val = s.value;
            if (typeof val === 'string' && val.indexOf('\n') !== -1) {
                var lines = val.split('\n').filter(function (l) { return l.trim() !== ''; });
                val = '<ul class="pd-spec-list">' + lines.map(function (l) { return '<li>' + l.trim() + '</li>'; }).join('') + '</ul>';
            }
            html += '<tr><td>' + s.name + '</td><td>' + val + '</td></tr>';
        });
        html += '</table>';
        html += '</div>';
    });
    body.innerHTML = html;
}

function specTabClick(idx) {
    // Cập nhật tab đang active
    document.querySelectorAll('.pd-spec-tab').forEach(function (tab) {
        tab.classList.toggle('active', parseInt(tab.dataset.group) === idx);
    });

    // Cuộn đến phần nhóm thông số
    var target = document.getElementById('specGroup_' + idx);
    var body = document.getElementById('pdSpecModalBody');
    if (target && body) {
        body.scrollTo({ top: target.offsetTop - body.offsetTop, behavior: 'smooth' });
    }
}

// Cập nhật tab đang active khi cuộn
function setupSpecScrollSpy() {
    var body = document.getElementById('pdSpecModalBody');
    if (!body) return;

    body.addEventListener('scroll', function () {
        var scrollTop = body.scrollTop;
        var activeIdx = 0;

        for (var i = 0; i < specGroups.length; i++) {
            var el = document.getElementById('specGroup_' + i);
            if (el && (el.offsetTop - body.offsetTop) <= scrollTop + 60) {
                activeIdx = i;
            }
        }

        document.querySelectorAll('.pd-spec-tab').forEach(function (tab) {
            tab.classList.toggle('active', parseInt(tab.dataset.group) === activeIdx);
        });

        // Tự động cuộn tab vào vùng hiển thị
        var activeTab = document.querySelector('.pd-spec-tab.active');
        if (activeTab) {
            activeTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    });
}

function closeSpecModal(e) {
    if (e.target === document.getElementById('pdSpecOverlay')) closeSpecModalBtn();
}

function closeSpecModalBtn() {
    var overlay = document.getElementById('pdSpecOverlay');
    if (overlay) {
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Đóng modal thông số khi nhấn Escape
document.addEventListener('keydown', function (e) {
    var overlay = document.getElementById('pdSpecOverlay');
    if (overlay && overlay.classList.contains('show') && e.key === 'Escape') {
        closeSpecModalBtn();
    }
});

// ========== Tiện ích ==========
function formatPrice(value) {
    if (!value) return '0';
    return parseInt(value).toLocaleString('vi-VN').replace(/,/g, '.');
}

function buyNow() {
    // Kiểm tra đã chọn variant chưa
    if (!selectedColor || !selectedStorage) {
        if (window.QHToast) {
            QHToast.show('Vui lòng chọn màu sắc và dung lượng', 'error');
        }
        return;
    }

    // Tìm variant đã chọn
    var variant = variantsData.find(function (v) {
        return v.color_name === selectedColor && v.storage === selectedStorage;
    });

    if (!variant) {
        if (window.QHToast) {
            QHToast.show('Không tìm thấy sản phẩm', 'error');
        }
        return;
    }

    // Kiểm tra tồn kho
    if (variant.stock_quantity <= 0) {
        if (window.QHToast) {
            QHToast.show('Sản phẩm đã hết hàng!', 'error');
        }
        return;
    }

    // Gọi API thêm vào giỏ hàng rồi chuyển trang
    fetch('/cart/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: 'product_id=' + productId + '&quantity=1&color_name=' + encodeURIComponent(selectedColor) + '&color_code=' + encodeURIComponent(variant.color_code || '') + '&storage=' + encodeURIComponent(selectedStorage) + '&price=' + variant.price
    })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            if (data.success) {
                window.location.href = '/cart/';
            } else if (data.require_login) {
                if (window.QHConfirm) {
                    QHConfirm.show('Bạn cần đăng nhập để mua hàng. Chuyển đến trang đăng nhập?', function () {
                        window.location.href = '/login/';
                    });
                }
            } else {
                if (window.QHToast) {
                    QHToast.show(data.message || 'Có lỗi xảy ra', 'error');
                }
            }
        })
        .catch(function (error) {
            console.error('Error:', error);
            if (window.QHToast) {
                QHToast.show('Có lỗi xảy ra. Vui lòng thử lại.', 'error');
            }
        });
}

function updateCartBadge(count) {
    var badge = document.getElementById('qh-cart-count');
    if (badge) {
        badge.textContent = count;
    }
}

function addToCart() {
    // Lấy thông tin sản phẩm đã chọn
    if (!selectedColor || !selectedStorage) {
        if (window.QHToast) {
            QHToast.show('Vui lòng chọn màu sắc và dung lượng', 'error');
        } else {
            alert('Vui lòng chọn màu sắc và dung lượng');
        }
        return;
    }

    // Tìm variant đã chọn để lấy giá
    var variant = variantsData.find(function (v) {
        return v.color_name === selectedColor && v.storage === selectedStorage;
    });

    if (!variant) {
        if (window.QHToast) {
            QHToast.show('Không tìm thấy sản phẩm', 'error');
        } else {
            alert('Không tìm thấy sản phẩm');
        }
        return;
    }

    // Kiểm tra tồn kho
    if (variant.stock_quantity <= 0) {
        if (window.QHToast) {
            QHToast.show('Sản phẩm đã hết hàng!', 'error');
        } else {
            alert('Sản phẩm đã hết hàng!');
        }
        return;
    }

    // Gọi API thêm vào giỏ hàng
    fetch('/cart/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: 'product_id=' + productId + '&quantity=1&color_name=' + encodeURIComponent(selectedColor) + '&color_code=' + encodeURIComponent(variant.color_code || '') + '&storage=' + encodeURIComponent(selectedStorage) + '&price=' + variant.price
    })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            if (data.success) {
                // Cập nhật badge
                updateCartBadge(data.total_items);
                // Hiển thị toast
                if (window.QHToast) {
                    QHToast.show(data.message, 'success');
                } else {
                    alert(data.message);
                }
            } else if (data.require_login) {
                if (window.QHConfirm) {
                    QHConfirm.show('Bạn cần đăng nhập để thêm sản phẩm vào giỏ hàng. Chuyển đến trang đăng nhập?', function () {
                        window.location.href = '/login/';
                    });
                }
            } else {
                if (window.QHToast) {
                    QHToast.show(data.message, 'error');
                } else {
                    alert(data.message);
                }
            }
        })
        .catch(function (error) {
            console.error('Error:', error);
            if (window.QHToast) {
                QHToast.show('Có lỗi xảy ra. Vui lòng thử lại.', 'error');
            } else {
                alert('Có lỗi xảy ra. Vui lòng thử lại.');
            }
        });
}

function getCsrfToken() {
    // Lấy CSRF token từ cookie
    var name = 'csrftoken';
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ========== Panel nội dung sản phẩm (trượt từ phải, như Spec) ==========
function openContentModal() {
    var overlay = document.getElementById('pdContentOverlay');
    if (!overlay) return;
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeContentModal(e) {
    if (e.target === document.getElementById('pdContentOverlay')) closeContentModalBtn();
}

function closeContentModalBtn() {
    var overlay = document.getElementById('pdContentOverlay');
    if (overlay) {
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Đóng modal nội dung khi nhấn Escape
document.addEventListener('keydown', function (e) {
    var overlay = document.getElementById('pdContentOverlay');
    if (overlay && overlay.classList.contains('show') && e.key === 'Escape') {
        closeContentModalBtn();
    }
});
