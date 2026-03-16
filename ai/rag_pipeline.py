"""
Module RAG cho chatbot QHUN22.
Pipeline gồm: phát hiện intent, tìm kiếm vector,
lấy ngữ cảnh, trả lời cục bộ và gọi Claude khi cần.
"""

import os
import sys
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Các câu trả lời đơn giản không cần Claude
SIMPLE_RESPONSE_TEMPLATES = {
    "greeting": "Chào anh/chị! Em là trợ lý mua sắm của QHUN22. Em có thể giúp gì cho anh/chị?",
    "identity": "Em là trợ lý nhỏ của hệ thống QHUN22. Em có thể hỗ trợ anh/chị tư vấn chọn máy, so sánh sản phẩm, kiểm tra đơn hàng hoặc kết nối nhân viên khi cần ạ.",
    "staff": "Anh/chị vui lòng liên hệ Hotline 0327221005 hoặc Telegram @qhun22 để được nhân viên hỗ trợ trực tiếp nhé!",
    "installment": "QHUN22 hỗ trợ trả góp 0% lãi suất qua thẻ tín dụng và các công ty tài chính. Anh/chị liên hệ hotline 0327221005 hoặc đến trực tiếp cửa hàng để được hướng dẫn chi tiết nhé!",
    "warranty": "Tất cả sản phẩm tại QHUN22 đều là hàng chính hãng, bảo hành 12 tháng tại trung tâm bảo hành ủy quyền. Ngoài ra, QHUN22 hỗ trợ đổi trả trong 7 ngày nếu sản phẩm lỗi từ nhà sản xuất.",
    "order_capability": "Dạ có ạ. Em có thể hỗ trợ anh/chị tra cứu đơn hàng. Anh/chị gửi giúp em mã đơn (VD: QH250101 hoặc QHUN38453) để em kiểm tra ngay nhé!",
}


class ChatPipeline:
    """
    Main RAG pipeline for QHUN22 phone store.
    
    Workflow:
    1. User question
    2. Detect intent (local ML model)
    3. Retrieve relevant products from vector DB
    4. Build context
    5. Answer locally if simple
    6. Call Claude only when necessary
    """
    
    # Intent đơn giản không cần Claude
    SIMPLE_INTENTS = [
        "greeting", "identity", "staff_request", "installment",
        "warranty", "order_capability", "faq",
    ]
    
    # Intent cần tra sản phẩm
    PRODUCT_INTENTS = [
        "product_search", "price_query", "stock_query", "variant_query",
    ]
    
    # Intent phức tạp cần Claude
    COMPLEX_INTENTS = [
        "phone_recommendation", "compare_phones", "troubleshooting",
        "price_comparison", "specification",
    ]
    
    def __init__(
        self,
        vector_store_path: str = "data/vector_store",
        intent_model_path: str = "data/intent_model.pkl",
        embedding_dimension: int = 384,
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            vector_store_path: Path to vector store
            intent_model_path: Path to intent model
            embedding_dimension: Dimension of embeddings
        """
        self.vector_store_path = vector_store_path
        self.intent_model_path = intent_model_path
        self.embedding_dimension = embedding_dimension
        
        # Lazy-load components
        self._embedding_generator = None
        self._vector_store = None
        self._intent_classifier = None
        self._conversation_memory = None
        self._claude_client = None
        self._prompt_builder = None
        
        # Thiết lập Django
        self._setup_django()
    
    def _setup_django(self):
        """Setup Django if needed."""
        try:
            from django.conf import settings
            if not settings.configured:
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, project_root)
                import django
                django.setup()
        except Exception as e:
            logger.warning(f"Django setup: {e}")
    
    @property
    def embedding_generator(self):
        """Lazy load embedding generator."""
        if self._embedding_generator is None:
            from .embeddings import create_embedding_generator
            self._embedding_generator = create_embedding_generator(
                model_name="mini",
                cache_dir="data/embeddings_cache",
            )
        return self._embedding_generator
    
    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            from .vector_store import MultiIndexVectorStore
            self._vector_store = MultiIndexVectorStore(base_path=self.vector_store_path)
            self._vector_store.load_all_indices()
        return self._vector_store
    
    @property
    def intent_classifier(self):
        """Lazy load intent classifier."""
        if self._intent_classifier is None:
            from .intent_model import IntentClassifier
            self._intent_classifier = IntentClassifier()
            if os.path.exists(self.intent_model_path):
                self._intent_classifier.load(self.intent_model_path)
            else:
                self._intent_classifier.train()
        return self._intent_classifier
    
    @property
    def conversation_memory(self):
        """Lazy load conversation memory."""
        if self._conversation_memory is None:
            from .conversation_memory import ConversationMemory
            self._conversation_memory = ConversationMemory(storage_path="data/conversations")
        return self._conversation_memory
    
    @property
    def claude_client(self):
        """Lazy load Claude client."""
        if self._claude_client is None:
            from .claude_client import ClaudeClient
            self._claude_client = ClaudeClient()
        return self._claude_client
    
    @property
    def prompt_builder(self):
        """Lazy load prompt builder."""
        if self._prompt_builder is None:
            from .prompt_builder import PromptBuilder
            self._prompt_builder = PromptBuilder()
        return self._prompt_builder
    
    def detect_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect user intent.
        
        Args:
            message: User message
            
        Returns:
            Intent detection result
        """
        return self.intent_classifier.predict(message)
    
    def search_products(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant products.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            
        Returns:
            List of product results
        """
        # Tạo embedding câu hỏi
        query_embedding = self.embedding_generator.embed_text(query)
        
        # Lấy index sản phẩm
        products_index = self.vector_store.get_index("products")
        
        if products_index is None:
            logger.warning("Products index not found")
            return []
        
        # Tìm kiếm
        result_list = products_index.search(query_embedding, k=k, filters=filters)
        
        return result_list
    
    def extract_products_from_message(self, message: str) -> List[str]:
        """
        Extract product names from message.
        
        Args:
            message: User message
            
        Returns:
            List of product names
        """
        try:
            from store.models import Product
            
            products = list(Product.objects.filter(is_active=True).values_list("name", flat=True))
            
            if not products:
                return []
            
            # Simple matching
            message_lower = message.lower()
            product_list = []
            
            for name in products:
                name_lower = name.lower()
                if name_lower in message_lower:
                    product_list.append(name)
            
            return product_list[:3]
        
        except Exception as e:
            logger.warning(f"Failed to extract products: {e}")
            return []
    
    def get_product_details(self, product_names: List[str]) -> List[Dict[str, Any]]:
        """Get product details from database."""
        try:
            from store.models import Product, ProductDetail, ProductSpecification
            
            products = []
            
            for name in product_names:
                product = Product.objects.filter(name__icontains=name, is_active=True).first()
                if not product:
                    continue
                
                # Get details
                detail = None
                try:
                    detail = product.detail
                except:
                    pass
                
                # Get specs
                specs = ""
                try:
                    spec_data = detail.specification
                    specs = str(spec_data.spec_json) if spec_data.spec_json else ""
                except:
                    pass
                
                # Get variants
                colors = []
                storages = []
                prices = []
                
                if detail:
                    for variant in detail.variants.all():
                        if variant.color_name:
                            colors.append(variant.color_name)
                        if variant.storage:
                            storages.append(variant.storage)
                        if variant.price:
                            prices.append(int(variant.price))
                
                products.append({
                    "id": f"product_{product.id}",
                    "name": product.name,
                    "brand": product.brand.name if product.brand else "",
                    "description": product.description or "",
                    "min_price": min(prices) if prices else int(product.price),
                    "max_price": max(prices) if prices else int(product.price),
                    "specifications": specs,
                    "colors": list(set(colors)),
                    "storages": list(set(storages)),
                    "stock": product.stock,
                    "is_featured": product.is_featured,
                })
            
            return products
        
        except Exception as e:
            logger.error(f"Failed to get product details: {e}")
            return []
    
    def _handle_simple_intent(self, intent: str) -> Dict[str, Any]:
        """Handle simple intents with predefined responses."""
        message = SIMPLE_RESPONSE_TEMPLATES.get(intent, "Em chưa hiểu, anh/chị có thể nói rõ hơn không?")
        
        return {
            "message": message,
            "intent": intent,
            "requires_claude": False,
            "source": "template",
        }
    
    def _handle_product_intent(
        self,
        intent: str,
        message: str,
        products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Handle intents that need product lookup."""
        # Nếu có tên sản phẩm thì lấy chi tiết trước
        if products:
            product_details = self.get_product_details(products)
            if product_details:
                product = product_details[0]
                
                if intent == "price_query":
                    return self._handle_price(product)
                elif intent == "stock_query":
                    return self._handle_stock(product)
                elif intent == "variant_query":
                    return self._handle_variant(product)
        
        # Nếu không thì tìm theo câu hỏi
        search_results = self.search_products(message, k=5)
        
        if search_results:
            product_names = [r.get("name", "") for r in search_results[:3]]
            product_details = self.get_product_details(product_names)
            
            if product_details:
                return {
                    "message": f"Tìm thấy {len(product_details)} sản phẩm: " + ", ".join([p["name"] for p in product_details]),
                    "products": product_details,
                    "intent": intent,
                    "requires_claude": False,
                    "source": "search",
                }
        
        return {
            "message": "Em chưa tìm thấy sản phẩm phù hợp. Anh/chị có thể nói rõ hơn không?",
            "intent": intent,
            "requires_claude": False,
            "source": "fallback",
        }
    
    def _handle_price(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Handle price query."""
        min_price = product.get("min_price", 0)
        max_price = product.get("max_price", 0)
        
        if min_price and max_price:
            if min_price == max_price:
                msg = f"{product['name']} có giá {self._format_price(min_price)}."
            else:
                msg = f"{product['name']} có giá từ {self._format_price(min_price)} đến {self._format_price(max_price)}."
        else:
            msg = f"Em chưa có thông tin giá của {product['name']}."
        
        return {
            "message": msg,
            "product": product,
            "intent": "price_query",
            "requires_claude": False,
            "source": "local",
        }
    
    def _handle_stock(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stock query."""
        stock = product.get("stock", 0)
        
        if stock > 0:
            msg = f"{product['name']} hiện đang còn hàng."
            if product.get("colors"):
                msg += f" Màu có sẵn: {', '.join(product['colors'][:3])}."
        else:
            msg = f"{product['name']} hiện tạm hết hàng."
        
        return {
            "message": msg,
            "product": product,
            "intent": "stock_query",
            "requires_claude": False,
            "source": "local",
        }
    
    def _handle_variant(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Handle variant query."""
        msg = f"{product['name']} hiện có:\n"
        
        if product.get("colors"):
            msg += f"Màu sắc: {', '.join(product['colors'])}.\n"
        
        if product.get("storages"):
            msg += f"Dung lượng: {', '.join(product['storages'])}.\n"
        
        return {
            "message": msg,
            "product": product,
            "intent": "variant_query",
            "requires_claude": False,
            "source": "local",
        }
    
    def _handle_complex_intent(
        self,
        intent: str,
        message: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle complex intents with Claude."""
        # Lấy ngữ cảnh từ bộ nhớ hội thoại
        context = self.conversation_memory.get_response_context(
            session_id=session_id,
            current_intent=intent,
        )
        
        # Tách tên sản phẩm từ tin nhắn
        product_list = self.extract_products_from_message(message)
        
        # Lấy chi tiết sản phẩm
        product_details = []
        if product_list:
            product_details = self.get_product_details(product_list)
        
        # Không thấy thì tìm kiếm thêm
        if not product_details:
            search_results = self.search_products(message, k=5)
            product_names = [r.get("name", "") for r in search_results]
            product_details = self.get_product_details(product_names)
        
        # Vẫn không có thì lấy từ ngữ cảnh trước đó
        if not product_details and context.get("focused_product"):
            product_details = self.get_product_details([context["focused_product"]])
        
        # Vẫn không có thì tìm rộng hơn để gợi ý
        if not product_details:
            search_results = self.search_products(message, k=10)
            product_names = [r.get("name", "") for r in search_results]
            product_details = self.get_product_details(product_names)
        
        # Nếu Claude không sẵn sàng thì fallback
        if not self.claude_client.is_available():
            return {
                "message": f"Em tìm thấy {len(product_details)} sản phẩm liên quan. Anh/chị muốn xem chi tiết sản phẩm nào?",
                "products": product_details,
                "intent": intent,
                "requires_claude": False,
                "source": "fallback",
            }
        
        # Gọi Claude theo intent
        if intent == "compare_phones" and len(product_details) >= 2:
            ai_text = self.claude_client.compare_products(product_details, message)
            source = "claude"
        elif intent == "phone_recommendation":
            ai_text = self.claude_client.recommend_products(product_details, message)
            source = "claude"
        elif intent == "troubleshooting" and product_details:
            ai_text = self.claude_client.get_advice(product_details, message)
            source = "claude"
        else:
            ai_text = self.claude_client.summarize_products(product_details, message)
            source = "claude"
        
        if ai_text:
            return {
                "message": ai_text,
                "products": product_details,
                "intent": intent,
                "requires_claude": True,
                "source": source,
            }
        
        # Fallback
        return {
            "message": f"Em tìm thấy {len(product_details)} sản phẩm. " + 
                       ", ".join([p["name"] for p in product_details[:3]]),
            "products": product_details,
            "intent": intent,
            "requires_claude": False,
            "source": "fallback",
        }
    
    def process(
        self,
        message: str,
        session_id: str = "default",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process user message through RAG pipeline.
        
        Args:
            message: User message
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Response dictionary
        """
        # Bước 1: phát hiện intent
        intent_result = self.detect_intent(message)
        intent = intent_result.get("intent", "unknown")
        
        logger.info(f"Detected intent: {intent} (confidence: {intent_result.get('confidence', 0):.2f})")
        
        # Bước 2: lưu tin nhắn user
        self.conversation_memory.add_message(
            session_id=session_id,
            role="user",
            content=message,
            intent=intent,
        )
        
        # Bước 3: điều hướng xử lý
        result = {}
        
        # Intent đơn giản
        if intent in self.SIMPLE_INTENTS:
            result = self._handle_simple_intent(intent)
        
        # Intent sản phẩm
        elif intent in self.PRODUCT_INTENTS:
            products = self.extract_products_from_message(message)
            result = self._handle_product_intent(intent, message, products)
        
        # Intent phức tạp
        elif intent in self.COMPLEX_INTENTS:
            result = self._handle_complex_intent(intent, message, session_id)
        
        # Intent chưa rõ
        else:
            # Thử tìm sản phẩm trong câu hỏi
            products = self.extract_products_from_message(message)
            if products:
                product_details = self.get_product_details(products)
                result = {
                    "message": f"Anh/chị đang hỏi về {products[0]}. Em có thể giúp gì thêm?",
                    "products": product_details,
                    "intent": intent,
                    "requires_claude": False,
                    "source": "product_fallback",
                }
            else:
                result = {
                    "message": "Em chưa hiểu ý anh/chị. Anh/chị có thể nói rõ hơn không?",
                    "intent": intent,
                    "requires_claude": False,
                    "source": "unknown",
                }
        
        # Bước 4: lưu phản hồi assistant
        self.conversation_memory.add_message(
            session_id=session_id,
            role="assistant",
            content=result.get("message", ""),
            intent=intent,
            metadata={
                "product_name": result.get("products", [{}])[0].get("name") if result.get("products") else None,
            },
        )
        
        # Gắn metadata
        result["session_id"] = session_id
        result["detected_intent"] = intent
        result["intent_confidence"] = intent_result.get("confidence", 0)
        
        return result
    
    def _format_price(self, price: int) -> str:
        """Format price in Vietnamese Dong."""
        if price <= 0:
            return "Liên hệ"
        return f"{price:,}đ".replace(",", ".")


def create_chatbot() -> "ChatPipeline":
    """Tạo instance ChatPipeline."""
    return ChatPipeline()


# Giữ tên cũ để tương thích
ChatBot = ChatPipeline


def create_rag_pipeline() -> "ChatPipeline":
    """Tạo instance (giữ tương thích ngược)."""
    return ChatPipeline()


# Main entry point
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="RAG Pipeline for QHUN22")
    parser.add_argument("--message", "-m", required=True, help="User message")
    parser.add_argument("--session-id", "-s", default="test", help="Session ID")
    
    args = parser.parse_args()
    
    pipeline = create_rag_pipeline()
    response = pipeline.process(args.message, args.session_id)
    
    print("\n" + "=" * 50)
    print("RESPONSE")
    print("=" * 50)
    print(f"Intent: {response.get('detected_intent')}")
    print(f"Source: {response.get('source')}")
    print(f"Claude: {response.get('requires_claude')}")
    print(f"\nMessage:\n{response.get('message')}")
    
    if response.get("products"):
        print(f"\nProducts: {[p.get('name') for p in response.get('products', [])]}")
