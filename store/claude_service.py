import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-haiku-20240307"
DEFAULT_MAX_TOKENS = 700
REQUEST_TIMEOUT = 15


class ClaudeService:
    """Gọi Claude API (claude-3-haiku) với kiểm soát chi phí."""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY chưa được cấu hình trong .env")

    def _call_once(self, payload: dict, headers: dict) -> dict | None:
        try:
            resp = requests.post(
                CLAUDE_API_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code != 200:
                logger.error("Claude API lỗi %s: %s", resp.status_code, resp.text[:300])
                return None
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error("Claude API timeout sau %ss", REQUEST_TIMEOUT)
            return None
        except Exception as exc:
            logger.error("Claude API exception: %s", exc)
            return None

    @staticmethod
    def _extract_text_blocks(data: dict) -> str:
        content_blocks = data.get("content", []) or []
        texts = [blk.get("text", "") for blk in content_blocks if isinstance(blk, dict) and blk.get("type") == "text"]
        return "\n".join(t.strip() for t in texts if t and t.strip()).strip()

    def call(self, system_prompt: str, user_message: str, max_tokens: int = DEFAULT_MAX_TOKENS):
        if not self.api_key:
            logger.error("Thiếu ANTHROPIC_API_KEY")
            return None

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        messages = [{"role": "user", "content": user_message}]
        answer_parts: list[str] = []

        # Cho phép nối nhiều nhịp để tránh câu trả lời bị cắt giữa chừng vì max_tokens.
        for _ in range(4):
            payload = {
                "model": CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": messages,
            }

            data = self._call_once(payload, headers)
            if not data:
                break

            chunk = self._extract_text_blocks(data)
            if chunk:
                answer_parts.append(chunk)

            stop_reason = data.get("stop_reason")
            if stop_reason != "max_tokens":
                break

            messages.append({"role": "assistant", "content": chunk or ""})
            messages.append({
                "role": "user",
                "content": "Tiếp tục đúng phần còn dang dở của câu trả lời trước đó, không lặp lại ý đã nói.",
            })

        final_answer = "\n".join(part for part in answer_parts if part).strip()
        return final_answer or None
