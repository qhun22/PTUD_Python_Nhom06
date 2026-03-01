// JavaScript Banner Slider - Vòng lặp vô hạn (Production)
(function() {
    const requiredBannerIds = [23412, 74346, 87412, 76234];
    let bannerTimer = null;
    let isTransitioning = false;
    let currentSlide = 0;
    let totalRealSlides = 0; // Số slide thực (không tính clone)
    let banners = [];
    let track = null;
    let slidesPerView = 2;
    let transitionDuration = 500;

    // Xác định số slide hiển thị dựa trên độ rộng màn hình
    function getSlidesPerView() {
        return window.innerWidth <= 768 ? 1 : 2;
    }

    function initBannerSlider() {
        track = document.getElementById('qhBannerTrack');
        if (!track) return;

        slidesPerView = getSlidesPerView();

        const items = track.querySelectorAll('.qh-banner-item');
        // Số slide thực = tổng - (clone đầu + clone cuối)
        const cloneCount = slidesPerView * 2;
        totalRealSlides = items.length - cloneCount;

        if (totalRealSlides < slidesPerView) {
            hideBannerSection();
            return;
        }

        // Hiển thị phần banner
        const section = document.querySelector('.qh-banner-slider');
        if (section) section.style.display = 'block';

        // Tự động chuyển slide mỗi 3 giây
        startAutoSlide();

        // Nút điều hướng
        const prevBtn = document.getElementById('qhBannerPrev');
        const nextBtn = document.getElementById('qhBannerNext');

        if (prevBtn) {
            prevBtn.addEventListener('click', prevSlide);
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', nextSlide);
        }

        // Tạm dừng khi di chuột vào
        const wrap = track.closest('.qh-banner-slider-wrap');
        if (wrap) {
            wrap.addEventListener('mouseenter', stopAutoSlide);
            wrap.addEventListener('mouseleave', startAutoSlide);
        }

        // Xử lý khi thay đổi kích thước cửa sổ
        window.addEventListener('resize', handleResize);
    }

    function handleResize() {
        const newSlidesPerView = getSlidesPerView();
        if (newSlidesPerView !== slidesPerView) {
            slidesPerView = newSlidesPerView;
            loadBanners();
        }
    }

    /**
     * Di chuyển đến slide với transition
     */
    function moveToSlide(slideIndex, withTransition = true) {
        if (!track) return;

        const slideWidth = 100 / slidesPerView;
        const translateX = slideIndex * slideWidth;

        if (withTransition) {
            track.style.transition = `transform ${transitionDuration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
        } else {
            track.style.transition = 'none';
        }

        track.style.transform = `translateX(-${translateX}%)`;
    }

    /**
     * Xử lý infinite loop - Chỉ reset khi thực sự vượt quá clones
     * 
     * Cấu trúc: [Clone 3,4][  1  ][  2  ][  3  ][  4  ][Clone 1,2]
     * Index:       0,1       2     3     4     5      6,7
     * 
     * totalRealSlides = 4, cloneCount = 2
     * Real slides: 2,3,4,5 (index 2-5)
     * Clone tail: 6,7 (cho phép transition đến các vị trí này)
     * Reset khi: currentSlide > 6 (tức >= 7)
     */
    function handleInfiniteBoundary() {
        const cloneCount = slidesPerView;
        const maxValidIndex = totalRealSlides + cloneCount; // = 6
        
        // TIẾP: vượt quá index max (ví dụ: 7, 8, ...)
        if (currentSlide > maxValidIndex) {
            // Reset về vị trí real đầu tiên (sau clones head)
            currentSlide = cloneCount;
            moveToSlide(currentSlide, false);
            return true;
        }

        // LÙI: đi qua clone đầu tiên (index < 0)
        if (currentSlide < 0) {
            // Reset về vị trí real cuối cùng
            currentSlide = totalRealSlides - 1 + cloneCount;
            moveToSlide(currentSlide, false);
            return true;
        }

        return false;
    }

    function nextSlide() {
        // Không cho click trong khi đang transition
        if (isTransitioning) return;

        stopAutoSlide();
        isTransitioning = true;

        currentSlide++;

        // Check nếu đi qua boundary
        if (!handleInfiniteBoundary()) {
            moveToSlide(currentSlide);
        }

        // Cho phép transition xong mới cho click tiếp
        setTimeout(() => {
            isTransitioning = false;
        }, transitionDuration);

        startAutoSlide();
    }

    function prevSlide() {
        if (isTransitioning) return;

        stopAutoSlide();
        isTransitioning = true;

        currentSlide--;

        // Check nếu đi qua boundary  
        if (!handleInfiniteBoundary()) {
            moveToSlide(currentSlide);
        }

        setTimeout(() => {
            isTransitioning = false;
        }, transitionDuration);

        startAutoSlide();
    }

    function startAutoSlide() {
        stopAutoSlide();
        // Dùng setTimeout để đảm bảo interval không bị ảnh hưởng bởi các thao tác click
        setTimeout(() => {
            bannerTimer = setInterval(nextSlide, 3000);
        }, transitionDuration);
    }

    function stopAutoSlide() {
        if (bannerTimer) {
            clearInterval(bannerTimer);
            bannerTimer = null;
        }
    }

    function hideBannerSection() {
        const section = document.querySelector('.qh-banner-slider');
        if (section) section.style.display = 'none';
    }

    function loadBanners() {
        track = document.getElementById('qhBannerTrack');

        fetch('/banner-images/list/')
            .then(res => res.json())
            .then(data => {
                if (!track) return;

                if (data.success && data.banners && data.banners.length > 0) {
                    banners = requiredBannerIds
                        .map(id => data.banners.find(b => b.banner_id == id))
                        .filter(b => b && b.image_url);

                    if (banners.length >= 2) {
                        createBannerHTML();
                    } else {
                        hideBannerSection();
                    }
                } else {
                    hideBannerSection();
                }
            })
            .catch(err => {
                console.error('Error loading banners:', err);
                hideBannerSection();
            });
    }

    /**
     * Tạo HTML với cấu trúc infinite loop đúng chuẩn:
     * [CLONES_HEAD...][REAL_SLIDES...][CLONES_TAIL...]
     * 
     * VD: 4 banners, 2 per view
     * [Clone 3,4][1,2,3,4][Clone 1,2]
     * Index:   0,1     2,3,4,5    6,7
     * 
     * - Khi ở index 5 (slide 4 thực) và next -> đến index 6 (Clone 1) với transition mượt
     * - Khi ở index 6 và next tiếp -> reset về index 2 (slide 1 thực) KHÔNG transition
     */
    function createBannerHTML() {
        slidesPerView = getSlidesPerView();
        const cloneCount = slidesPerView;
        let html = '';

        // 1. Clone last N banners Ở ĐẦU (cho prev smooth)
        for (let i = 0; i < cloneCount; i++) {
            const cloneIndex = (banners.length - cloneCount + i) % banners.length;
            html += createBannerItem(banners[cloneIndex], `clone-head-${i}`, true);
        }

        // 2. Original slides (các banner thực)
        banners.forEach((banner, idx) => {
            html += createBannerItem(banner, `real-${idx}`, false);
        });

        // 3. Clone first N banners Ở CUỐI (cho next smooth)
        for (let i = 0; i < cloneCount; i++) {
            const cloneIndex = i % banners.length;
            html += createBannerItem(banners[cloneIndex], `clone-tail-${i}`, true);
        }

        track.innerHTML = html;

        // Khởi tạo tại vị trí bắt đầu (sau clones đầu)
        // Index = cloneCount = 2 (tức là slide thực đầu tiên)
        currentSlide = cloneCount;
        
        // Khởi tạo slider
        initBannerSlider();
        
        // Di chuyển đến vị trí ban đầu (không animation)
        moveToSlide(currentSlide, false);
    }

    function createBannerItem(banner, id, isClone) {
        return `<div class="qh-banner-item" data-id="${id}" ${isClone ? 'data-clone="true"' : ''}>
            <a href="#">
                <img src="${banner.image_url}" alt="Banner ${banner.banner_id}">
            </a>
        </div>`;
    }

    // Khởi tạo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadBanners);
    } else {
        loadBanners();
    }

    // Công khai để gọi từ bên ngoài
    window.initBannerSlider = initBannerSlider;
})();
