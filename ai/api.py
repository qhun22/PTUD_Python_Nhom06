"""Module API FastAPI cho chatbot QHUN22."""
import os
import sys
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Thiết lập đường dẫn
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import FastAPI
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("Chưa cài FastAPI")


# Các model request/response
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    intent: str
    confidence: float
    source: str
    products: Optional[list] = None
    session_id: str


def create_app():
    """Tạo ứng dụng FastAPI."""
    if not FASTAPI_AVAILABLE:
        return None

    app = FastAPI(title="QHUN22 Chatbot API")
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Biến chatbot lazy-load
    chatbot = None
    
    def get_chatbot():
        """Tải chatbot khi cần."""
        nonlocal chatbot
        if chatbot is None:
            from .rag_pipeline import ChatPipeline
            chatbot = ChatPipeline()
        return chatbot
    
    @app.get("/")
    def root():
        """API gốc."""
        return {"message": "QHUN22 Chatbot API", "status": "running"}
    
    @app.get("/health")
    def health():
        """Kiểm tra trạng thái."""
        return {"status": "ok"}
    
    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest):
        """API chat chính."""
        if not FASTAPI_AVAILABLE:
            raise HTTPException(status_code=500, detail="FastAPI chưa sẵn sàng")
        
        try:
            bot = get_chatbot()
            result = bot.process(
                message=request.message,
                session_id=request.session_id,
                user_id=request.user_id,
            )
            
            return ChatResponse(
                message=result.get("message", ""),
                intent=result.get("detected_intent", "unknown"),
                confidence=result.get("intent_confidence", 0),
                source=result.get("source", "unknown"),
                products=result.get("products"),
                session_id=result.get("session_id", request.session_id),
            )
        
        except Exception as e:
            logger.error(f"Lỗi chat: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/session/{session_id}")
    def get_session(session_id: str):
        """Lấy thông tin phiên chat."""
        try:
            bot = get_chatbot()
            context = bot.conversation_memory.get_context(session_id)
            
            if not context:
                return {"error": "Không tìm thấy phiên"}
            
            history = bot.conversation_memory.get_history(session_id)
            
            return {
                "session_id": session_id,
                "focused_product": context.focused_product,
                "mentioned_products": context.mentioned_products,
                "history": history,
            }
        
        except Exception as e:
            logger.error(f"Lỗi lấy phiên: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/session/{session_id}")
    def delete_session(session_id: str):
        """Xóa phiên chat."""
        try:
            bot = get_chatbot()
            bot.conversation_memory.delete_session(session_id)
            
            return {"message": "Đã xóa phiên", "session_id": session_id}
        
        except Exception as e:
            logger.error(f"Lỗi xóa phiên: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/train")
    def train_models(vectors: bool = True, intent: bool = True):
        """Huấn luyện lại model."""
        try:
            from .trainer import Trainer
            
            trainer = Trainer()
            result = trainer.run_full_training(
                recreate_vectors=vectors,
                recreate_intent=intent,
            )
            
            return {"message": "Huấn luyện xong", "result": result}
        
        except Exception as e:
            logger.error(f"Lỗi huấn luyện: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/products/search")
    def search_products(q: str, limit: int = 10):
        """Tìm kiếm sản phẩm."""
        try:
            bot = get_chatbot()
            results = bot.search_products(q, k=limit)
            
            return {"results": results, "count": len(results)}
        
        except Exception as e:
            logger.error(f"Lỗi tìm kiếm: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


# Tạo app
app = create_app()


# Chạy server
if __name__ == "__main__":
    import uvicorn
    
    logging.info("Đang khởi động API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
