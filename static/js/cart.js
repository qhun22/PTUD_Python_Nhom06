/* ==================== CSRF Token (mã xác thực) ==================== */
function getCsrfToken() {
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

/* ==================== Định dạng giá tiền ==================== */
function formatPrice(value) {
    if (!value) return '0';
    return parseInt(value).toLocaleString('vi-VN').replace(/,/g, '.');
}

/* ==================== Badge giỏ hàng ==================== */
function updateCartBadge(count) {
    var badge = document.getElementById('qh-cart-count');
    if (badge) badge.textContent = count;
}

/* ==================== Chọn tất cả / Checkbox ==================== */
function toggleSelectAll(checkbox) {
    var items = document.querySelectorAll('.cart-item-check');
    items.forEach(function(item) {
        item.checked = checkbox.checked;
    });
    updateSelectedCount();
}

function updateSelectedCount() {
    var checked = document.querySelectorAll('.cart-item-check:checked');
    var total = document.querySelectorAll('.cart-item-check').length;
    document.getElementById('selectedCount').textContent = checked.length;
    document.getElementById('selectAll').checked = (checked.length === total && total > 0);
    
    var selectedTotal = 0;
    var productListHtml = '';
    
    checked.forEach(function(cb, idx) {
        var itemId = cb.getAttribute('data-item-id');
        var priceEl = document.getElementById('itemPrice_' + itemId);
        var qtyInput = document.getElementById('qtyInput_' + itemId);
        var nameEl = document.querySelector('.qh-cart-item[data-item-id="' + itemId + '"] .qh-cart-item-name');
        
        if (priceEl && qtyInput) {
            var priceText = priceEl.textContent.replace(/[.\sđ]/g, '');
            var price = parseInt(priceText) || 0;
            var quantity = parseInt(qtyInput.value) || 1;
            selectedTotal += price * quantity;
        }
        
        var prodName = nameEl ? nameEl.textContent.trim() : 'Sản phẩm';
        var qty = qtyInput ? qtyInput.value : '1';
        productListHtml += '<div style="padding: 8px 0; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">'
            + '<span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; color:#334155;">' + prodName + '</span>'
            + '<span style="flex-shrink:0; font-size:12px; color:#94a3b8; margin-left:8px;">x' + qty + '</span>'
            + '</div>';
    });
    
    var listEl = document.getElementById('summaryProductList');
    if (listEl) {
        if (checked.length === 0) {
            listEl.innerHTML = '<p style="color:#94a3b8; font-style:italic;">Chưa chọn sản phẩm nào</p>';
        } else {
            listEl.innerHTML = productListHtml;
        }
    }
    
    document.getElementById('summaryTotal').textContent = formatPrice(selectedTotal) + ' đ';
}

/* ==================== Xóa các sản phẩm đã chọn ==================== */
function deleteSelected() {
    var checked = document.querySelectorAll('.cart-item-check:checked');
    if (checked.length === 0) {
        if (window.QHToast) {
            QHToast.show('Vui lòng chọn sản phẩm cần xóa', 'error');
        }
        return;
    }
    QHConfirm.show('Bạn có chắc muốn xóa ' + checked.length + ' sản phẩm đã chọn?', function() {
        var promises = [];
        checked.forEach(function(cb) {
            var itemId = cb.getAttribute('data-item-id');
            promises.push(
                fetch('/cart/remove/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: 'item_id=' + itemId
                })
            );
        });
        Promise.all(promises).then(function() {
            location.reload();
        });
    });
}

/* ==================== Dropdown màu sắc ==================== */
function toggleColorDropdown(el) {
    var dropdown = el.closest('.qh-cart-color-dropdown');
    var itemId = dropdown.getAttribute('data-item-id');

    // Đóng tất cả các dropdown màu khác
    document.querySelectorAll('.qh-cart-color-dropdown.open').forEach(function(d) {
        if (d !== dropdown) d.classList.remove('open');
    });

    // Đóng tất cả các dropdown dung lượng
    document.querySelectorAll('.qh-cart-storage-dropdown.open').forEach(function(d) {
        d.classList.remove('open');
    });

    dropdown.classList.toggle('open');
}

// Đóng dropdown khi click bên ngoài
document.addEventListener('click', function(e) {
    if (!e.target.closest('.qh-cart-color-dropdown')) {
        document.querySelectorAll('.qh-cart-color-dropdown.open').forEach(function(d) {
            d.classList.remove('open');
        });
    }
    if (!e.target.closest('.qh-cart-storage-dropdown')) {
        document.querySelectorAll('.qh-cart-storage-dropdown.open').forEach(function(d) {
            d.classList.remove('open');
        });
    }
});

/* ==================== Thay đổi màu sắc ==================== */
function changeColor(btn, itemId, colorName) {
    // Phản hồi trực quan
    var options = document.getElementById('colorOptions_' + itemId);
    options.querySelectorAll('.qh-cart-color-opt').forEach(function(o) {
        o.classList.remove('selected');
    });
    btn.classList.add('selected');

    fetch('/cart/change-color/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: 'item_id=' + itemId + '&color_name=' + encodeURIComponent(colorName)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            // Cập nhật nhãn màu
            var dropdown = document.querySelector('.qh-cart-color-dropdown[data-item-id="' + itemId + '"]');
            if (dropdown) {
                var label = dropdown.querySelector('.qh-cart-color-selected span');
                var displayColor = data.new_color;
                    if (displayColor && displayColor.indexOf(' - ') !== -1) displayColor = displayColor.split(' - ').slice(1).join(' - ');
                    if (label) label.textContent = 'Màu: ' + displayColor;
            }

            // Cập nhật hình ảnh sản phẩm với thumbnail màu
            if (data.new_thumbnail) {
                var imgEl = document.getElementById('itemImg_' + itemId);
                if (imgEl) imgEl.src = data.new_thumbnail;
            }

            // Cập nhật giá
            var priceEl = document.getElementById('itemPrice_' + itemId);
            if (priceEl) priceEl.textContent = formatPrice(data.item_price) + 'đ';

            var origPriceEl = document.getElementById('itemOrigPrice_' + itemId);
            if (origPriceEl) {
                if (data.original_price > 0) {
                    origPriceEl.textContent = formatPrice(data.original_price) + 'đ';
                    origPriceEl.style.display = 'block';
                } else {
                    origPriceEl.style.display = 'none';
                }
            }

            // Cập nhật tổng tiền
            updateSummaryPrices(data.total_price);
            updateCartBadge(data.total_items);

            if (window.QHToast) QHToast.show(data.message, 'success');

            // Tải lại sau một khoảng ngắn để lấy dữ liệu mới
            setTimeout(function() { location.reload(); }, 800);
        } else {
            if (window.QHToast) QHToast.show(data.message, 'error');
        }
    })
    .catch(function(err) {
        console.error('Lỗi:', err);
        if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
    });
}

/* ==================== Dropdown dung lượng ==================== */
function toggleStorageDropdown(el) {
    var dropdown = el.closest('.qh-cart-storage-dropdown');
    var itemId = dropdown.getAttribute('data-item-id');

    // Đóng tất cả các dropdown dung lượng khác
    document.querySelectorAll('.qh-cart-storage-dropdown.open').forEach(function(d) {
        if (d !== dropdown) d.classList.remove('open');
    });

    // Đóng tất cả các dropdown màu
    document.querySelectorAll('.qh-cart-color-dropdown.open').forEach(function(d) {
        d.classList.remove('open');
    });

    dropdown.classList.toggle('open');
}

/* ==================== Thay đổi dung lượng ==================== */
function changeStorage(btn, itemId, storage) {
    // Phản hồi trực quan
    var options = document.getElementById('storageOptions_' + itemId);
    options.querySelectorAll('.qh-cart-storage-opt').forEach(function(o) {
        o.classList.remove('selected');
    });
    btn.classList.add('selected');

    fetch('/cart/change-storage/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: 'item_id=' + itemId + '&storage=' + encodeURIComponent(storage)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            // Cập nhật nhãn dung lượng
            var dropdown = document.querySelector('.qh-cart-storage-dropdown[data-item-id="' + itemId + '"]');
            if (dropdown) {
                var label = dropdown.querySelector('.qh-cart-storage-selected span');
                if (label) label.textContent = 'Dung lượng: ' + data.new_storage;
            }

            // Cập nhật giá
            var priceEl = document.getElementById('itemPrice_' + itemId);
            if (priceEl) priceEl.textContent = formatPrice(data.item_price) + 'đ';

            var origPriceEl = document.getElementById('itemOrigPrice_' + itemId);
            if (origPriceEl) {
                if (data.original_price > 0) {
                    origPriceEl.textContent = formatPrice(data.original_price) + 'đ';
                    origPriceEl.style.display = 'block';
                } else {
                    origPriceEl.style.display = 'none';
                }
            }

            // Cập nhật tổng tiền
            updateSummaryPrices(data.total_price);
            updateCartBadge(data.total_items);

            if (window.QHToast) QHToast.show(data.message, 'success');

            // Tải lại sau một khoảng ngắn để lấy dữ liệu mới
            setTimeout(function() { location.reload(); }, 800);
        } else {
            if (window.QHToast) QHToast.show(data.message, 'error');
        }
    })
    .catch(function(err) {
        console.error('Lỗi:', err);
        if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
    });
}

/* ==================== Cập nhật số lượng ==================== */
function updateCartQuantity(itemId, quantity) {
    quantity = parseInt(quantity);
    if (isNaN(quantity) || quantity < 1) {
        if (window.QHToast) QHToast.show('Số lượng tối thiểu là 1', 'error');
        return;
    }
    fetch('/cart/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: 'item_id=' + itemId + '&quantity=' + quantity
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            updateCartBadge(data.total_items);

            // Cập nhật ô nhập số lượng
            var qtyInput = document.getElementById('qtyInput_' + itemId);
            if (qtyInput) qtyInput.value = data.item_quantity;

            // Bật/tắt nút trừ
            var minusBtn = document.querySelector('.qh-cart-qty-minus[data-item-id="' + itemId + '"]');
            if (minusBtn) minusBtn.disabled = (data.item_quantity <= 1);

            // Cập nhật tổng tiền cho các sản phẩm đã chọn
            updateSelectedCount();

            if (window.QHToast) QHToast.show(data.message, 'success');
        } else if (data.require_login) {
            QHConfirm.show(data.message + '. Bạn có muốn đăng nhập không?', function() {
                window.location.href = '/login/';
            });
        } else {
            if (window.QHToast) QHToast.show(data.message, 'error');
        }
    })
    .catch(function(err) {
        console.error('Lỗi:', err);
        if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
    });
}

/* ==================== Xóa sản phẩm ==================== */
function removeFromCart(itemId) {
    QHConfirm.show('Bạn có chắc muốn xóa sản phẩm này khỏi giỏ hàng?', function() {
        fetch('/cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: 'item_id=' + itemId
        })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            updateCartBadge(data.total_items);
            if (window.QHToast) QHToast.show(data.message, 'success');
            setTimeout(function() { location.reload(); }, 500);
        } else if (data.require_login) {
            QHConfirm.show(data.message + '. Bạn có muốn đăng nhập không?', function() {
                window.location.href = '/login/';
            });
        } else {
            if (window.QHToast) QHToast.show(data.message, 'error');
        }
    })
    .catch(function(err) {
        console.error('Lỗi:', err);
        if (window.QHToast) QHToast.show('Có lỗi xảy ra', 'error');
    });
    }); // end QHConfirm callback
}

/* ==================== Cập nhật tóm tắt ==================== */
function updateSummaryPrices(totalPrice) {
    var totalEl = document.getElementById('summaryTotal');
    var formatted = formatPrice(totalPrice) + ' đ';
    if (totalEl) totalEl.textContent = formatted;
}

/* ==================== JS Sticky Summary - Tóm tắt di chuyển theo scroll ==================== */
(function () {
    function initSticky() {
        var summary = document.querySelector('.qh-cart-summary');
        var container = document.querySelector('.qh-cart-container');
        if (!summary || !container) return;

        var TOP = 90; // chiều cao navbar
        var isFixed = false;
        var naturalLeft = 0;
        var naturalWidth = 0;

        function captureNaturalPosition() {
            // Chỉ đo khi đang ở trạng thái tự nhiên (không fixed)
            if (!isFixed) {
                var r = summary.getBoundingClientRect();
                naturalLeft = r.left;
                naturalWidth = r.width;
            }
        }

        function stick() {
            if (isFixed) return;
            captureNaturalPosition();
            summary.style.position = 'fixed';
            summary.style.top = TOP + 'px';
            summary.style.left = naturalLeft + 'px';
            summary.style.width = naturalWidth + 'px';
            summary.style.zIndex = '100';
            isFixed = true;
        }

        function unstick() {
            if (!isFixed) return;
            summary.style.position = '';
            summary.style.top = '';
            summary.style.left = '';
            summary.style.width = '';
            summary.style.zIndex = '';
            isFixed = false;
        }

        function onScroll() {
            if (window.innerWidth <= 992) {
                unstick();
                return;
            }
            var containerRect = container.getBoundingClientRect();
            var summaryH = summary.offsetHeight;

            if (containerRect.top <= TOP) {
                stick();
                // Clamp ở đáy container
                var remaining = containerRect.bottom - summaryH;
                var newTop = remaining < TOP ? Math.max(remaining, containerRect.top) : TOP;
                summary.style.top = newTop + 'px';
            } else {
                unstick();
            }
        }

        function onResize() {
            unstick();
            // Đo lại vị trí tự nhiên sau khi unstick
            setTimeout(function () {
                captureNaturalPosition();
                onScroll();
            }, 50);
        }

        // Đo vị trí ban đầu
        captureNaturalPosition();
        onScroll();

        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onResize);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSticky);
    } else {
        initSticky();
    }
})();

/* ==================== Thanh toán ==================== */
function checkout() {
    var checked = document.querySelectorAll('.cart-item-check:checked');
    if (checked.length === 0) {
        if (window.QHToast) {
            QHToast.show('Vui lòng chọn sản phẩm để thanh toán', 'error');
        }
        return;
    }
    // Thu thập các ID sản phẩm đã chọn
    var ids = [];
    checked.forEach(function(cb) {
        ids.push(cb.getAttribute('data-item-id'));
    });
    window.location.href = '/checkout/?items=' + ids.join(',');
}
