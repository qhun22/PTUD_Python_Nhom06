"""Điều phối chatbot web: ưu tiên pipeline AI đã train, fallback an toàn về local."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from ai.rag_pipeline import create_rag_pipeline

from .chatbot_service import ChatbotService
from .models import Product

logger = logging.getLogger(__name__)


class HybridChatbotOrchestrator:
    """Orchestrator cho widget web với chiến lược AI-first + fallback an toàn."""

    LOCAL_ONLY_INTENTS = {
        "order",
        "order_capability",
        "staff",
        "installment",
        "warranty",
        "list_products",
    }

    PRODUCT_RELIANT_AI_INTENTS = {
        "phone_recommendation",
        "compare_phones",
        "product_search",
        "price_query",
        "stock_query",
        "variant_query",
        "specification",
        "price_comparison",
        "troubleshooting",
    }

    BUDGET_PATTERN = re.compile(r"\d+(?:[\.,]\d+)?\s*(triệu|tr|m)\b", re.IGNORECASE)

    def __init__(self, local_service: Optional[ChatbotService] = None, ai_pipeline: Optional[Any] = None):
        self.local_service = local_service or ChatbotService()
        self.ai_pipeline = ai_pipeline

    def _get_ai_pipeline(self):
        if self.ai_pipeline is None:
            self.ai_pipeline = create_rag_pipeline()
        return self.ai_pipeline

    @staticmethod
    def _ensure_session_id(session, user=None) -> str:
        if session is not None:
            session_key = getattr(session, "session_key", None)
            if not session_key and hasattr(session, "save"):
                try:
                    session.save()
                    session_key = getattr(session, "session_key", None)
                except Exception:
                    session_key = None
            if session_key:
                return f"web-{session_key}"

        if user is not None and getattr(user, "is_authenticated", False):
            user_id = getattr(user, "id", "anonymous")
            return f"web-user-{user_id}"

        return "web-anonymous"

    def _should_route_local(self, message: str, intent: str) -> bool:
        if intent in self.LOCAL_ONLY_INTENTS:
            return True

        # Câu tư vấn có ngân sách cần logic cứng để không vượt trần.
        if intent == "consult" and self.BUDGET_PATTERN.search(message or ""):
            return True

        return False

    @staticmethod
    def _build_suggestions(intent: str, ai_result: Dict[str, Any]) -> list[str]:
        products = ai_result.get("products") or []
        names = [p.get("name", "") for p in products if isinstance(p, dict) and p.get("name")]

        if intent in {"phone_recommendation", "product_search", "price_query", "stock_query", "variant_query"}:
            return names[:3] or ["Tư vấn chọn máy", "So sánh sản phẩm", "Gặp nhân viên"]
        if intent == "compare_phones":
            return names[:2] or ["So sánh sản phẩm", "Tư vấn chọn máy"]
        if intent == "order_capability":
            return ["Kiểm tra đơn hàng", "Gặp nhân viên"]
        return ["Tư vấn chọn máy", "So sánh sản phẩm", "Kiểm tra đơn hàng"]

    def _normalize_ai_response(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        detected_intent = ai_result.get("detected_intent") or ai_result.get("intent") or "unknown"
        message = (ai_result.get("message") or "").strip()

        if not message:
            return {}

        product_cards = self._build_ai_product_cards(ai_result.get("products") or [])

        return {
            "message": message,
            "suggestions": self._build_suggestions(detected_intent, ai_result),
            "source": ai_result.get("source", "ai_pipeline"),
            "intent": detected_intent,
            "engine": "ai_pipeline",
            "products": ai_result.get("products") or [],
            "product_cards": product_cards,
        }

    @staticmethod
    def _build_ai_product_cards(products: list[dict[str, Any]], limit: int = 4) -> list[dict[str, str]]:
        cards: list[dict[str, str]] = []
        seen: set[str] = set()

        for item in products:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or "").strip()
            if not name or name in seen:
                continue

            product = Product.objects.filter(is_active=True, name__icontains=name).first()
            if not product:
                continue

            image_url = None
            try:
                if getattr(product, "image", None):
                    image_url = product.image.url
            except Exception:
                image_url = None

            if not image_url:
                continue

            seen.add(name)
            min_price = item.get("min_price") or item.get("price") or 0
            subtitle = ""
            try:
                price_num = int(min_price)
                subtitle = f"Giá từ {price_num:,}₫".replace(",", ".") if price_num > 0 else ""
            except Exception:
                subtitle = ""

            cards.append({
                "title": product.name,
                "image_url": image_url if str(image_url).startswith("/") else f"/{image_url}",
                "subtitle": subtitle,
            })

            if len(cards) >= limit:
                break

        return cards

    def process_message(self, message: str, user=None, session=None) -> Dict[str, Any]:
        text = (message or "").strip()
        if not text:
            return {"message": "Vui lòng nhập nội dung.", "suggestions": []}

        detected_local_intent = self.local_service.detect_intent(text)
        if self._should_route_local(text, detected_local_intent):
            local_result = self.local_service.process_message(text, user=user, session=session)
            local_result.setdefault("engine", "django_local")
            local_result.setdefault("source", "local")
            return local_result

        session_id = self._ensure_session_id(session, user=user)

        try:
            ai_result = self._get_ai_pipeline().process(
                message=text,
                session_id=session_id,
                user_id=str(getattr(user, "id", "")) if user is not None and getattr(user, "is_authenticated", False) else None,
            )
            normalized = self._normalize_ai_response(ai_result)
            if normalized:
                ai_intent = normalized.get("intent", "unknown")
                ai_products = normalized.get("products") or []

                # Nếu intent cần dữ liệu sản phẩm mà AI không có context,
                # ưu tiên fallback local để tránh trả lời lệch DB.
                if ai_intent in self.PRODUCT_RELIANT_AI_INTENTS and not ai_products:
                    logger.warning("AI thiếu context sản phẩm (%s), fallback local", ai_intent)
                else:
                    return normalized

        except Exception as exc:
            logger.exception("AI pipeline lỗi, chuyển fallback local: %s", exc)

        local_result = self.local_service.process_message(text, user=user, session=session)
        local_result.setdefault("engine", "django_local_fallback")
        local_result.setdefault("source", "local_fallback")
        return local_result

    def reset_conversation(self, session, user=None) -> bool:
        ok = True
        try:
            self.local_service.reset_conversation(session)
        except Exception:
            ok = False

        try:
            session_id = self._ensure_session_id(session, user=user)
            pipeline = self._get_ai_pipeline()
            pipeline.conversation_memory.delete_session(session_id)
        except Exception:
            ok = False

        return ok
