/* ==================== JavaScript điều khiển Hero Slider ==================== */
(function() {
    const slider = document.getElementById('qhHeroSlider');
    if (!slider) return;

    const slides = Array.from(slider.querySelectorAll('.qh-hero-slide'));
    const dotsWrap = document.getElementById('qhHeroDots');
    const dots = dotsWrap ? Array.from(dotsWrap.querySelectorAll('.qh-hero-dot')) : [];
    const prevBtn = document.getElementById('qhHeroPrev');
    const nextBtn = document.getElementById('qhHeroNext');
    const total = slides.length;

    let idx = 0;
    let timer = null;

    // Hàm phát video
    function playVideo(video) {
        if (!video) return;
        
        // Đảm bảo video được tắt tiếng để autoplay hoạt động
        video.muted = true;
        video.playsInline = true;
        
        const playPromise = video.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.log('Video autoplay was prevented:', error);
            });
        }
    }

    // Hàm tạm dừng video
    function pauseVideo(video) {
        if (!video) return;
        try {
            video.pause();
        } catch(e) {}
    }

    function setActive(nextIdx) {
        idx = (nextIdx + total) % total;
        slides.forEach((s, i) => {
            const active = i === idx;
            s.classList.toggle('active', active);
            const v = s.querySelector('video');
            if (v) {
                if (active) {
                    // Phát video đang hoạt động
                    playVideo(v);
                } else {
                    // Tạm dừng các video không hoạt động
                    pauseVideo(v);
                }
            }
        });
        dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    }

    function next() { setActive(idx + 1); }
    function prev() { setActive(idx - 1); }

    function start() {
        stop();
        // Tự động chuyển slide mỗi 7 giây
        timer = setInterval(next, 7000);
    }

    function stop() {
        if (timer) clearInterval(timer);
        timer = null;
    }

    prevBtn && prevBtn.addEventListener('click', () => { prev(); start(); });
    nextBtn && nextBtn.addEventListener('click', () => { next(); start(); });

    dots.forEach((d) => {
        d.addEventListener('click', () => {
            const n = parseInt(d.getAttribute('data-slide') || '0', 10);
            setActive(isNaN(n) ? 0 : n);
            start();
        });
    });

    // Tạm dừng khi tab bị ẩn
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stop();
            // Tạm dừng tất cả video khi tab bị ẩn
            slides.forEach(s => {
                const v = s.querySelector('video');
                if (v) pauseVideo(v);
            });
        } else {
            // Tiếp tục phát khi tab hiển thị
            const activeSlide = slides[idx];
            if (activeSlide) {
                const v = activeSlide.querySelector('video');
                if (v) playVideo(v);
            }
            start();
        }
    });

    // Khởi tạo - phát video đầu tiên ngay lập tức
    setActive(0);
    
    // Trì hoãn việc tự động chuyển để video đầu tiên bắt đầu phát
    setTimeout(() => {
        const firstVideo = slides[0]?.querySelector('video');
        if (firstVideo) playVideo(firstVideo);
        start();
    }, 500);
})();
