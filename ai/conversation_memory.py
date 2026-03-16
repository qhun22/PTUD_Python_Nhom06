"""Module bộ nhớ hội thoại cho chatbot QHUN22."""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    intent: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Represents the context of a conversation."""
    session_id: str
    user_id: Optional[str] = None
    focused_product: Optional[str] = None
    pending_compare: Optional[Dict[str, Any]] = None
    last_intent: Optional[str] = None
    mentioned_products: List[str] = field(default_factory=list)
    mentioned_brands: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)  # 1 hour


class ConversationMemory:
    """
    Quản lý lịch sử hội thoại và ngữ cảnh.
    Hỗ trợ hội thoại nhiều lượt với theo dõi ngữ cảnh.
    """
    
    # Session timeout in seconds (1 hour)
    SESSION_TIMEOUT = 3600
    
    # Max conversation history
    MAX_HISTORY = 20
    
    # Intents that should reset some context
    RESET_INTENTS = ["greeting", "identity", "staff_request"]
    
    # Intents that reference previous context
    CONTEXT_INTENTS = [
        "specification", "price_query", "stock_query", "variant_query",
        "compare_phones", "phone_recommendation", "troubleshooting",
    ]
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_history: int = MAX_HISTORY,
        session_timeout: int = SESSION_TIMEOUT,
    ):
        """
        Initialize conversation memory.
        
        Args:
            storage_path: Path to store conversation history
            max_history: Max number of messages to keep
            session_timeout: Session timeout in seconds
        """
        self.storage_path = storage_path or "data/conversations"
        self.max_history = max_history
        self.session_timeout = session_timeout
        
        # In-memory storage
        self._sessions: Dict[str, deque] = {}
        self._contexts: Dict[str, ConversationContext] = {}
        
        # Create storage directory
        if self.storage_path:
            os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
    
    def _get_session_key(self, session_id: str) -> str:
        """Get storage key for a session."""
        return f"session_{session_id}"
    
    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    session_id = filename.replace(".json", "").replace("session_", "")
                    session_path = os.path.join(self.storage_path, filename)
                    
                    with open(session_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Load messages
                    messages = deque()
                    for msg_data in data.get("messages", []):
                        messages.append(Message(**msg_data))
                    
                    # Load context
                    context_data = data.get("context", {})
                    if context_data:
                        context = ConversationContext(**context_data)
                        
                        # Check expiration
                        if time.time() < context.expires_at:
                            self._sessions[session_id] = messages
                            self._contexts[session_id] = context
                        else:
                            # Delete expired session
                            os.remove(session_path)
        except Exception as e:
            logger.warning(f"Failed to load sessions: {e}")
    
    def _save_session(self, session_id: str) -> None:
        """Save a session to disk."""
        if not self.storage_path:
            return
        
        session_path = os.path.join(
            self.storage_path,
            f"session_{session_id}.json"
        )
        
        try:
            data = {
                "messages": [
                    asdict(msg) for msg in self._sessions.get(session_id, [])
                ],
                "context": asdict(self._contexts[session_id]) 
                    if session_id in self._contexts else None,
            }
            
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")
    
    def get_or_create_session(self, session_id: str) -> Tuple[deque, ConversationContext]:
        """
        Get or create a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (messages deque, context)
        """
        # Check if session exists and is valid
        if session_id in self._contexts:
            context = self._contexts[session_id]
            
            # Check expiration
            if time.time() > context.expires_at:
                # Delete expired session
                self.delete_session(session_id)
                return self._create_session(session_id)
            
            # Update timestamp
            context.updated_at = time.time()
            context.expires_at = time.time() + self.session_timeout
            
            if session_id in self._sessions:
                return self._sessions[session_id], context
        
        return self._create_session(session_id)
    
    def _create_session(self, session_id: str) -> Tuple[deque, ConversationContext]:
        """Create a new session."""
        messages = deque(maxlen=self.max_history)
        context = ConversationContext(
            session_id=session_id,
            expires_at=time.time() + self.session_timeout,
        )
        
        self._sessions[session_id] = messages
        self._contexts[session_id] = context
        
        return messages, context
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to the conversation.
        
        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content
            intent: Detected intent
            metadata: Additional metadata
        """
        messages, context = self.get_or_create_session(session_id)
        
        # Create message
        message = Message(
            role=role,
            content=content,
            intent=intent,
            metadata=metadata or {},
        )
        
        # Add to history
        messages.append(message)
        
        # Update context
        context.updated_at = time.time()
        
        if intent:
            context.last_intent = intent
            
            # Handle specific intents
            if intent == "product_mention" or intent in self.CONTEXT_INTENTS:
                # Extract product info from metadata if available
                if metadata:
                    if "product_name" in metadata:
                        if metadata["product_name"] not in context.mentioned_products:
                            context.mentioned_products.append(metadata["product_name"])
                        context.focused_product = metadata["product_name"]
                    
                    if "brand" in metadata:
                        if metadata["brand"] not in context.mentioned_brands:
                            context.mentioned_brands.append(metadata["brand"])
            
            # Handle compare intent
            if intent == "compare_phones":
                if metadata and "products" in metadata:
                    context.pending_compare = {
                        "products": metadata["products"],
                        "timestamp": time.time(),
                    }
            
            # Reset on certain intents
            if intent in self.RESET_INTENTS:
                # Keep some context but reset product focus
                context.focused_product = None
                context.pending_compare = None
        
        # Save session
        self._save_session(session_id)
    
    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            session_id: Session identifier
            limit: Max number of messages to return
            
        Returns:
            List of message dictionaries
        """
        messages, _ = self.get_or_create_session(session_id)
        
        history = [asdict(msg) for msg in messages]
        
        if limit:
            return history[-limit:]
        
        return history
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context."""
        if session_id in self._contexts:
            context = self._contexts[session_id]
            if time.time() < context.expires_at:
                return context
        return None
    
    def get_focused_product(self, session_id: str) -> Optional[str]:
        """Get the currently focused product."""
        context = self.get_context(session_id)
        return context.focused_product if context else None
    
    def set_focused_product(self, session_id: str, product_name: str) -> None:
        """Set the focused product."""
        _, context = self.get_or_create_session(session_id)
        context.focused_product = product_name
        
        if product_name not in context.mentioned_products:
            context.mentioned_products.append(product_name)
        
        self._save_session(session_id)
    
    def get_pending_compare(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get pending compare info."""
        context = self.get_context(session_id)
        
        if context and context.pending_compare:
            compare = context.pending_compare
            
            # Check if still valid (10 minutes)
            if time.time() - compare.get("timestamp", 0) < 600:
                return compare
            else:
                # Delete expired
                context.pending_compare = None
        
        return None
    
    def clear_pending_compare(self, session_id: str) -> None:
        """Clear pending compare."""
        context = self.get_context(session_id)
        if context:
            context.pending_compare = None
            self._save_session(session_id)
    
    def get_last_user_message(self, session_id: str) -> Optional[str]:
        """Get the last user message."""
        messages, _ = self.get_or_create_session(session_id)
        
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        
        return None
    
    def get_last_assistant_message(self, session_id: str) -> Optional[str]:
        """Get the last assistant message."""
        messages, _ = self.get_or_create_session(session_id)
        
        for msg in reversed(messages):
            if msg.role == "assistant":
                return msg.content
        
        return None
    
    def get_mentioned_products(self, session_id: str) -> List[str]:
        """Get all products mentioned in the conversation."""
        context = self.get_context(session_id)
        return context.mentioned_products if context else []
    
    def is_context_continuation(self, session_id: str) -> bool:
        """
        Check if this is a continuation of previous context.
        Example: "còn hàng không" after "iPhone 15 giá bao nhiêu"
        """
        context = self.get_context(session_id)
        
        if not context:
            return False
        
        # Check if there's a focused product
        if context.focused_product:
            return True
        
        # Check for recent messages
        messages = self._sessions.get(session_id, [])
        if len(messages) >= 2:
            last_msg = messages[-1]
            # If last message from assistant and mentions a product
            if last_msg.role == "assistant" and last_msg.metadata.get("product_name"):
                return True
        
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted
        """
        # Remove from memory
        self._sessions.pop(session_id, None)
        self._contexts.pop(session_id, None)
        
        # Remove from disk
        if self.storage_path:
            session_path = os.path.join(
                self.storage_path,
                f"session_{session_id}.json"
            )
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    return True
                except Exception as e:
                    logger.warning(f"Failed to delete session file: {e}")
        
        return True
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        count = 0
        current_time = time.time()
        
        expired_sessions = [
            sid for sid, ctx in self._contexts.items()
            if current_time > ctx.expires_at
        ]
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
            count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        
        return count
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._contexts)
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary."""
        context = self.get_context(session_id)
        
        if not context:
            return {"status": "no_session"}
        
        return {
            "session_id": session_id,
            "focused_product": context.focused_product,
            "mentioned_products": context.mentioned_products,
            "mentioned_brands": context.mentioned_brands,
            "last_intent": context.last_intent,
            "message_count": len(self._sessions.get(session_id, [])),
            "pending_compare": context.pending_compare is not None,
            "created_at": context.created_at,
            "updated_at": context.updated_at,
        }

    def get_response_context(
        self,
        session_id: str,
        current_intent: str,
        current_products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Lấy ngữ cảnh để tạo phản hồi cho lượt hiện tại."""
        context = self.get_context(session_id)

        if not context:
            return {"is_new_session": True}

        is_continuation = self.is_context_continuation(session_id)
        focused_product = context.focused_product

        if current_products and len(current_products) > 0:
            if current_intent in self.CONTEXT_INTENTS:
                focused_product = current_products[0]
                self.set_focused_product(session_id, focused_product)

        pending_compare = self.get_pending_compare(session_id)

        return {
            "is_new_session": False,
            "is_continuation": is_continuation,
            "focused_product": focused_product,
            "mentioned_products": context.mentioned_products,
            "mentioned_brands": context.mentioned_brands,
            "last_intent": context.last_intent,
            "pending_compare": pending_compare,
            "history": self.get_history(session_id, limit=5),
        }


class SessionManager:
    """
    Manage multiple conversation sessions.
    Provides high-level API for session management.
    """
    
    def __init__(self, memory: Optional[ConversationMemory] = None):
        """
        Initialize session manager.
        
        Args:
            memory: ConversationMemory instance
        """
        self.memory = memory or ConversationMemory()
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        intent: str,
        assistant_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Process a message turn.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            intent: Detected intent
            assistant_message: Assistant's response
            metadata: Additional metadata
        """
        # Add user message
        self.memory.add_message(
            session_id=session_id,
            role="user",
            content=user_message,
            intent=intent,
            metadata=metadata,
        )
        
        # Add assistant message if available
        if assistant_message:
            self.memory.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_message,
                intent=intent,
                metadata=metadata,
            )
    
    def get_response_context(
        self,
        session_id: str,
        current_intent: str,
        current_products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get context for generating response.
        
        Args:
            session_id: Session identifier
            current_intent: Current detected intent
            current_products: Products detected in current message
            
        Returns:
            Context dictionary for generating response
        """
        context = self.memory.get_context(session_id)
        
        if not context:
            return {"is_new_session": True}
        
        # Check if this is a follow-up question
        is_continuation = self.memory.is_context_continuation(session_id)
        
        # Get focused product from previous context
        focused_product = context.focused_product
        
        # If current message has products, update focus
        if current_products and len(current_products) > 0:
            # If intent is specification, price, etc., focus on product
            if current_intent in self.memory.CONTEXT_INTENTS:
                focused_product = current_products[0]
                self.memory.set_focused_product(session_id, focused_product)
        
        # Get pending compare info
        pending_compare = self.memory.get_pending_compare(session_id)
        
        return {
            "is_new_session": False,
            "is_continuation": is_continuation,
            "focused_product": focused_product,
            "mentioned_products": context.mentioned_products,
            "mentioned_brands": context.mentioned_brands,
            "last_intent": context.last_intent,
            "pending_compare": pending_compare,
            "history": self.memory.get_history(session_id, limit=5),
        }
    
    def clear_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.memory.delete_session(session_id)
