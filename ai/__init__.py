"""Module AI cho hệ thống QHUN22."""
__version__ = "1.0.0"
__author__ = "QHUN22"

# Export lớp chính
from .rag_pipeline import ChatPipeline, create_chatbot

# Giữ tên cũ để tương thích
ChatBot = ChatPipeline
AIRAGPipeline = ChatPipeline
create_rag_pipeline = create_chatbot

__all__ = [
    "ChatPipeline",
    "ChatBot",
    "AIRAGPipeline",
    "create_chatbot",
    "create_rag_pipeline",
]
