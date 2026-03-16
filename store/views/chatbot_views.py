"""
Chatbot Views (AI chatbot API) - QHUN22 Store
Auto-generated from views.py
"""
import os
import json
import uuid
import random
import time
import traceback
import requests
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db import models
from django.db.models import Q, Count, Sum, Max
from django.utils import timezone
from django.urls import reverse
import datetime
from store.chatbot_orchestrator import HybridChatbotOrchestrator


_CHATBOT_ORCHESTRATOR = None


def _get_orchestrator() -> HybridChatbotOrchestrator:
    global _CHATBOT_ORCHESTRATOR
    if _CHATBOT_ORCHESTRATOR is None:
        _CHATBOT_ORCHESTRATOR = HybridChatbotOrchestrator()
    return _CHATBOT_ORCHESTRATOR



def chatbot_api(request):
    import json as _json
    import traceback as _tb

    try:
        body = _json.loads(request.body)
        action = (body.get("action") or "").strip().lower()
        message = body.get("message", "").strip()
    except Exception:
        return JsonResponse({"message": "Tin nhắn không hợp lệ.", "suggestions": []}, status=400)

    if action == "reset":
        try:
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            ok = _get_orchestrator().reset_conversation(getattr(request, "session", None), user=user)
            return JsonResponse({"ok": bool(ok)})
        except Exception:
            return JsonResponse({"ok": False}, status=200)

    if not message:
        return JsonResponse({"message": "Vui lòng nhập nội dung.", "suggestions": []}, status=400)

    if len(message) > 500:
        return JsonResponse({"message": "Tin nhắn quá dài, vui lòng rút gọn lại nhé!", "suggestions": []}, status=400)

    try:
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        result = _get_orchestrator().process_message(message, user=user, session=getattr(request, "session", None))
        return JsonResponse(result)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Chatbot API error")
        if settings.DEBUG:
            return JsonResponse({
                "message": f"[DEBUG] Lỗi: {type(e).__name__}: {e}",
                "suggestions": [],
            }, status=200)
        return JsonResponse({
            "message": "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau!",
            "suggestions": ["Tư vấn chọn máy", "Gặp nhân viên"],
        }, status=200)
