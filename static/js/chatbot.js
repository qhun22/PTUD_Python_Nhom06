/**
 * Widget Chatbot AI của QHUN22
 */
const QHChat = (() => {
    const API_URL = '/api/chatbot/';
    let isOpen = false;
    let isSending = false;

    const $ = (sel) => document.querySelector(sel);

    function init() {
        const fab = $('#qh-chat-fab');
        const closeBtn = $('#qh-chat-close');
        const sendBtn = $('#qh-chat-send');
        const input = $('#qh-chat-input');

        if (!fab) return;

        fab.addEventListener('click', toggle);
        closeBtn.addEventListener('click', toggle);
        sendBtn.addEventListener('click', send);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        });

        addBotMessage(
            'Chào anh/chị, em là trợ lý AI của anh Huy đẹp trai. Em có thể giúp gì cho anh/chị?',
            ['Tư vấn chọn máy', 'So sánh sản phẩm', 'Kiểm tra đơn hàng', 'Gặp nhân viên']
        );
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
                addBotMessage(data.message || 'Mình chưa hiểu ý anh/chị. Thử lại nhé!', data.suggestions || []);
            })
            .catch(() => {
                showTyping(false);
                addBotMessage('Xin lỗi, hệ thống đang bận. Anh/chị thử lại sau nhé! 🙏', []);
            })
            .finally(() => {
                isSending = false;
                setSendDisabled(false);
                $('#qh-chat-input')?.focus();
            });
    }

    function addUserMessage(text) {
        const container = $('#qh-chat-messages');
        const el = document.createElement('div');
        el.className = 'qh-chat-msg user';
        el.innerHTML = `
            <div class="qh-chat-msg-avatar"><i class="ri-user-line"></i></div>
            <div class="qh-chat-msg-bubble">${escapeHtml(text)}</div>
        `;
        container.appendChild(el);
        scrollToBottom();
    }

    function addBotMessage(text, suggestions) {
        const container = $('#qh-chat-messages');
        const el = document.createElement('div');
        el.className = 'qh-chat-msg bot';

        let html = `
            <div class="qh-chat-msg-avatar"><i class="ri-robot-2-line"></i></div>
            <div>
                <div class="qh-chat-msg-bubble">${formatMarkdown(text)}</div>
        `;

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
        scrollToBottom();
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
