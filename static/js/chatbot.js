/**
 * Widget Chatbot AI của QHUN22
 */
const QHChat = (() => {
    const API_URL = '/api/chatbot/';
    const HISTORY_KEY = 'qh_chat_history_v1';
    const HISTORY_LIMIT = 60;
    const WELCOME_TEXT = 'Chào anh/chị, em là một trợ lý nhỏ của hệ thống, em có thể giúp gì được cho quý anh/chị ngày hôm nay ạ?';
    const WELCOME_SUGGESTIONS = ['Tư vấn chọn máy', 'So sánh sản phẩm', 'Kiểm tra đơn hàng', 'Gặp nhân viên'];
    let isOpen = false;
    let isSending = false;
    let history = [];

    const $ = (sel) => document.querySelector(sel);

    function init() {
        const fab = $('#qh-chat-fab');
        const closeBtn = $('#qh-chat-close');
        const resetBtn = $('#qh-chat-reset');
        const sendBtn = $('#qh-chat-send');
        const input = $('#qh-chat-input');

        if (!fab) return;

        fab.addEventListener('click', toggle);
        closeBtn.addEventListener('click', toggle);
        resetBtn?.addEventListener('click', resetChat);
        sendBtn.addEventListener('click', send);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        });

        loadHistory();
        restoreHistory();
        if (!history.length) {
            addBotMessage(WELCOME_TEXT, WELCOME_SUGGESTIONS, []);
        }
    }

    async function resetChat() {
        const container = $('#qh-chat-messages');
        const input = $('#qh-chat-input');
        if (!container) return;

        await callResetAPI();
        showTyping(false);
        container.innerHTML = '';
        history = [];
        saveHistory();
        isSending = false;
        setSendDisabled(false);
        if (input) input.value = '';
        addBotMessage(WELCOME_TEXT, WELCOME_SUGGESTIONS, []);
    }

    function toggle() {
        const win = $('#qh-chat-window');
        const fab = $('#qh-chat-fab');
        isOpen = !isOpen;
        win.classList.toggle('open', isOpen);
        fab.classList.toggle('active', isOpen);
        if (isOpen) {
            setTimeout(() => $('#qh-chat-input')?.focus(), 200);
        }
    }

    function send() {
        if (isSending) return;
        const input = $('#qh-chat-input');
        const msg = input.value.trim();
        if (!msg) return;

        input.value = '';
        addUserMessage(msg);
        callAPI(msg);
    }

    function sendSuggestion(text) {
        if (isSending) return;
        addUserMessage(text);
        callAPI(text);
    }

    function callAPI(message) {
        isSending = true;
        setSendDisabled(true);
        showTyping(true);

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
            || '';

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ message }),
        })
            .then((res) => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then((data) => {
                showTyping(false);
                addBotMessage(
                    data.message || 'Em chưa hiểu ý anh/chị. Anh/chị thử lại nhé!',
                    data.suggestions || [],
                    data.product_cards || data.cards || []
                );
            })
            .catch(() => {
                showTyping(false);
                addBotMessage('Xin lỗi, hệ thống đang bận. Anh/chị thử lại sau nhé! 🙏', [], []);
            })
            .finally(() => {
                isSending = false;
                setSendDisabled(false);
                $('#qh-chat-input')?.focus();
            });
    }

    function callResetAPI() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
            || '';

        return fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ action: 'reset' }),
        }).catch(() => null);
    }

    function addUserMessage(text, persist = true) {
        const container = $('#qh-chat-messages');
        const el = document.createElement('div');
        el.className = 'qh-chat-msg user';
        el.innerHTML = `
            <div class="qh-chat-msg-avatar"><i class="ri-user-line"></i></div>
            <div class="qh-chat-msg-bubble">${escapeHtml(text)}</div>
        `;
        container.appendChild(el);
        if (persist) pushHistory({ role: 'user', text });
        scrollToBottom();
    }

    function addBotMessage(text, suggestions, cards = [], persist = true) {
        const container = $('#qh-chat-messages');
        const el = document.createElement('div');
        el.className = 'qh-chat-msg bot';

        let html = `
            <div class="qh-chat-msg-avatar"><img src="/static/icons/gatchan.png" class="qh-chat-bot-image" alt="Bot avatar"></div>
            <div>
                <div class="qh-chat-msg-bubble">${formatMarkdown(text)}</div>
        `;

        if (cards && cards.length) {
            html += '<div class="qh-chat-cards">';
            cards.forEach((card) => {
                const safeTitle = escapeHtml(card?.title || 'Sản phẩm');
                const safeSubtitle = escapeHtml(card?.subtitle || '');
                const rawImage = (card?.image_url || '').trim();
                const safeImage = /^(https?:\/\/|\/)/i.test(rawImage) ? rawImage : `/${rawImage}`;
                const safeImageAttr = escapeAttr(safeImage);

                html += `
                    <div class="qh-chat-card">
                        <img class="qh-chat-card-thumb" src="${safeImageAttr}" alt="${safeTitle}" loading="lazy">
                        <div class="qh-chat-card-meta">
                            <div class="qh-chat-card-title">${safeTitle}</div>
                            ${safeSubtitle ? `<div class="qh-chat-card-subtitle">${safeSubtitle}</div>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        if (suggestions && suggestions.length) {
            html += '<div class="qh-chat-suggestions">';
            suggestions.forEach((s) => {
                html += `<button class="qh-chat-suggestion-btn" onclick="QHChat.sendSuggestion('${escapeAttr(s)}')">${escapeHtml(s)}</button>`;
            });
            html += '</div>';
        }

        html += '</div>';
        el.innerHTML = html;
        container.appendChild(el);
        if (persist) pushHistory({ role: 'bot', text, suggestions: suggestions || [], cards: cards || [] });
        scrollToMessageStart(el);
    }

    function loadHistory() {
        try {
            const raw = localStorage.getItem(HISTORY_KEY);
            const parsed = raw ? JSON.parse(raw) : [];
            history = Array.isArray(parsed) ? parsed : [];
        } catch {
            history = [];
        }
    }

    function saveHistory() {
        try {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
        } catch {
            // ignore localStorage quota/browser issues
        }
    }

    function pushHistory(item) {
        history.push(item);
        if (history.length > HISTORY_LIMIT) {
            history = history.slice(history.length - HISTORY_LIMIT);
        }
        saveHistory();
    }

    function restoreHistory() {
        if (!history.length) return;
        history.forEach((item) => {
            if (item?.role === 'user' && item.text) {
                addUserMessage(item.text, false);
                return;
            }
            if (item?.role === 'bot' && item.text) {
                addBotMessage(item.text, item.suggestions || [], item.cards || [], false);
            }
        });
    }

    function showTyping(show) {
        const el = $('#qh-chat-typing');
        if (el) el.classList.toggle('show', show);
        if (show) scrollToBottom();
    }

    function setSendDisabled(disabled) {
        const btn = $('#qh-chat-send');
        if (btn) btn.disabled = disabled;
    }

    function scrollToBottom() {
        const container = $('#qh-chat-messages');
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    function scrollToMessageStart(messageEl) {
        const container = $('#qh-chat-messages');
        if (!container || !messageEl) return;

        requestAnimationFrame(() => {
            const containerRect = container.getBoundingClientRect();
            const messageRect = messageEl.getBoundingClientRect();
            const nextTop = messageRect.top - containerRect.top + container.scrollTop - 8;
            container.scrollTop = Math.max(0, nextTop);
        });
    }

    function formatMarkdown(text) {
        return escapeHtml(text)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function escapeAttr(str) {
        return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    document.addEventListener('DOMContentLoaded', init);

    return { toggle, sendSuggestion };
})();
