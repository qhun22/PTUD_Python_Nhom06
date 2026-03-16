"""Module gọi Claude API cho hệ thống QHUN22."""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Thử import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests chưa có trong môi trường")


# Cấu hình API
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-haiku-20240307"
DEFAULT_MAX_TOKENS = 400
REQUEST_TIMEOUT = 15


class ClaudeClient:
    """
    Client gọi Claude API.
    Có xử lý giới hạn tần suất, thử lại và bắt lỗi.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = CLAUDE_MODEL,
        timeout: int = REQUEST_TIMEOUT,
        max_retries: int = 3,
    ):
        """Khởi tạo Claude client."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY chưa được cấu hình")
    
    def is_available(self) -> bool:
        """Kiểm tra Claude API có sẵn hay không."""
        return bool(self.api_key) and REQUESTS_AVAILABLE
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Optional[str]:
        """
        Call Claude API.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Max tokens in response
            
        Returns:
            Response text or None if failed
        """
        if not self.is_available():
            logger.error("Claude API chưa sẵn sàng")
            return None
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    CLAUDE_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content_blocks = data.get("content", [])
                    
                    if content_blocks:
                        return content_blocks[0].get("text", "")
                    
                    logger.warning("Claude trả về rỗng")
                    return None
                
                elif response.status_code == 429:
                    # Bị giới hạn tần suất
                    wait_time = 2 ** attempt
                    logger.warning(f"Bị giới hạn tần suất, chờ {wait_time}s...")
                    import time
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.error(f"Lỗi Claude API {response.status_code}: {response.text[:300]}")
                    return None
            
            except requests.exceptions.Timeout:
                logger.error(f"Claude API timeout (lần {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return None
            
            except Exception as e:
                logger.error(f"Ngoại lệ Claude API: {e}")
                if attempt == self.max_retries - 1:
                    return None
        
        return None
    
    def call_with_prompt_dict(
        self,
        prompt_dict: Dict[str, Any],
    ) -> Optional[str]:
        """
        Call Claude API with prompt dictionary.
        
        Args:
            prompt_dict: Dictionary with 'system_prompt', 'user_prompt', 'max_tokens'
            
        Returns:
            Response text or None if failed
        """
        return self.call(
            system_prompt=prompt_dict.get("system_prompt", ""),
            user_message=prompt_dict.get("user_prompt", ""),
            max_tokens=prompt_dict.get("max_tokens", DEFAULT_MAX_TOKENS),
        )
    
    def compare_products(
        self,
        products: list,
        user_message: str,
    ) -> Optional[str]:
        """
        Compare products using Claude.
        
        Args:
            products: List of product dictionaries
            user_message: User's question
            
        Returns:
            Comparison response or None
        """
        from .prompt_builder import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build_compare_prompt(products, user_message)
        
        return self.call_with_prompt_dict(prompt)
    
    def recommend_products(
        self,
        products: list,
        user_message: str,
        budget: Optional[str] = None,
        needs: Optional[str] = None,
    ) -> Optional[str]:
        """
        Recommend products using Claude.
        
        Args:
            products: List of product dictionaries
            user_message: User's question
            budget: User's budget
            needs: User's needs
            
        Returns:
            Recommendation response or None
        """
        from .prompt_builder import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build_recommend_prompt(products, user_message, budget, needs)
        
        return self.call_with_prompt_dict(prompt)
    
    def get_advice(
        self,
        products: list,
        user_message: str,
    ) -> Optional[str]:
        """
        Get purchase advice using Claude.
        
        Args:
            products: List of product dictionaries
            user_message: User's question
            
        Returns:
            Advice response or None
        """
        from .prompt_builder import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build_advice_prompt(products, user_message)
        
        return self.call_with_prompt_dict(prompt)
    
    def summarize_products(
        self,
        products: list,
        user_message: str,
    ) -> Optional[str]:
        """
        Summarize products using Claude.
        
        Args:
            products: List of product dictionaries
            user_message: User's question
            
        Returns:
            Summary response or None
        """
        from .prompt_builder import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build_summarize_prompt(products, user_message)
        
        return self.call_with_prompt_dict(prompt)


def create_claude_client() -> ClaudeClient:
    """
    Factory function to create a Claude client.
    
    Returns:
        ClaudeClient instance
    """
    return ClaudeClient()


# Giữ tương thích ngược
class ClaudeService(ClaudeClient):
    """Alias cho ClaudeClient để giữ tương thích ngược."""
    
    def __init__(self):
        super().__init__()
