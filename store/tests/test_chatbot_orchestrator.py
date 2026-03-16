from types import SimpleNamespace
from django.test import SimpleTestCase

from store.chatbot_orchestrator import HybridChatbotOrchestrator


class _FakeLocalService:
    def __init__(self, intent='unknown', response=None):
        self.intent = intent
        self.response = response or {'message': 'local', 'suggestions': []}
        self.process_calls = 0
        self.reset_calls = 0

    def detect_intent(self, message):
        return self.intent

    def process_message(self, message, user=None, session=None):
        self.process_calls += 1
        return dict(self.response)

    def reset_conversation(self, session):
        self.reset_calls += 1


class _FakeMemory:
    def __init__(self):
        self.deleted = []

    def delete_session(self, session_id):
        self.deleted.append(session_id)


class _FakeAIPipeline:
    def __init__(self, response=None, should_raise=False):
        self.response = response or {
            'message': 'ai-answer',
            'detected_intent': 'phone_recommendation',
            'source': 'claude',
            'products': [{'name': 'iPhone 17'}],
        }
        self.should_raise = should_raise
        self.calls = 0
        self.conversation_memory = _FakeMemory()

    def process(self, message, session_id='default', user_id=None):
        self.calls += 1
        if self.should_raise:
            raise RuntimeError('AI failed')
        return dict(self.response)


class HybridChatbotOrchestratorTests(SimpleTestCase):
    def test_budget_message_routes_local(self):
        local = _FakeLocalService(intent='consult', response={'message': 'budget-safe', 'suggestions': ['A']})
        ai = _FakeAIPipeline()
        orchestrator = HybridChatbotOrchestrator(local_service=local, ai_pipeline=ai)

        out = orchestrator.process_message('mình có khoảng 15 triệu, cần máy pin trâu')

        self.assertEqual(out.get('message'), 'budget-safe')
        self.assertEqual(out.get('engine'), 'django_local')
        self.assertEqual(local.process_calls, 1)
        self.assertEqual(ai.calls, 0)

    def test_order_capability_routes_local(self):
        local = _FakeLocalService(intent='order_capability', response={'message': 'local-capability', 'suggestions': ['Kiểm tra đơn hàng']})
        ai = _FakeAIPipeline()
        orchestrator = HybridChatbotOrchestrator(local_service=local, ai_pipeline=ai)

        out = orchestrator.process_message('shop có hỗ trợ tra đơn hàng không')

        self.assertEqual(out.get('message'), 'local-capability')
        self.assertEqual(out.get('engine'), 'django_local')
        self.assertEqual(local.process_calls, 1)
        self.assertEqual(ai.calls, 0)

    def test_reset_clears_local_and_ai_memory(self):
        local = _FakeLocalService(intent='unknown')
        ai = _FakeAIPipeline()
        orchestrator = HybridChatbotOrchestrator(local_service=local, ai_pipeline=ai)

        session = SimpleNamespace(session_key='abc123')
        ok = orchestrator.reset_conversation(session)

        self.assertTrue(ok)
        self.assertEqual(local.reset_calls, 1)
        self.assertEqual(ai.conversation_memory.deleted, ['web-abc123'])

    def test_ai_failure_fallback_to_local(self):
        local = _FakeLocalService(intent='consult', response={'message': 'fallback-local', 'suggestions': ['B']})
        ai = _FakeAIPipeline(should_raise=True)
        orchestrator = HybridChatbotOrchestrator(local_service=local, ai_pipeline=ai)

        out = orchestrator.process_message('mình là sinh viên cần máy học online')

        self.assertEqual(out.get('message'), 'fallback-local')
        self.assertEqual(out.get('engine'), 'django_local_fallback')
        self.assertEqual(ai.calls, 1)
        self.assertEqual(local.process_calls, 1)
