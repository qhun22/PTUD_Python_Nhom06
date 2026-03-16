"""Module tạo embedding văn bản cho hệ thống QHUN22."""

import os
import logging
import hashlib
import pickle
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Thử import sentence-transformers, thiếu thì fallback TF-IDF
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Không có sentence-transformers, chuyển sang TF-IDF fallback")


class TextEmbedder:
    """
    Generate text embeddings using sentence-transformers.
    Supports caching and batch processing.
    """
    
    # Các model hỗ trợ - bản multilingual hợp tiếng Việt
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    MODELS = {
        "mini": "paraphrase-multilingual-MiniLM-L12-v2",
        "base": "paraphrase-multilingual-mpnet-base-v2",
        "vietnamese": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    }
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of sentence-transformers model
            cache_dir: Directory to cache embeddings
            device: Device to use ('cpu', 'cuda', or None for auto)
            use_cache: Whether to cache embeddings
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), "cache")
        self.device = device
        self.use_cache = use_cache
        self._model = None
        self._embedding_cache = {}
        
        # Tạo thư mục cache
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    @property
    def model(self):
        """Tải model theo kiểu lazy-load."""
        if self._model is None:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self._model = SentenceTransformer(
                        self.model_name,
                        cache_folder=self.cache_dir,
                        device=self.device,
                    )
                    logger.info(f"Loaded embedding model: {self.model_name}")
                except Exception as e:
                    logger.error(f"Failed to load model {self.model_name}: {e}")
                    raise
            else:
                raise RuntimeError("sentence-transformers not available")
        return self._model
    
    def _get_cache_key(self, text: str) -> str:
        """Tạo cache key cho văn bản."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()
    
    def _get_cache_path(self, text: str) -> str:
        """Lấy đường dẫn file cache cho văn bản."""
        cache_key = self._get_cache_key(text)
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    def _load_from_cache(self, text: str) -> Optional[np.ndarray]:
        """Đọc embedding từ cache."""
        if not self.use_cache:
            return None
        
        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for text: {e}")
        return None
    
    def _save_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """Lưu embedding vào cache."""
        if not self.use_cache:
            return
        
        cache_path = self._get_cache_path(text)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Failed to save cache for text: {e}")
    
    def embed_text(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text (supports Vietnamese)
            normalize: Whether to normalize embedding
            
        Returns:
            Embedding vector as numpy array
        """
        # Kiểm tra cache trước
        cached_vec = self._load_from_cache(text)
        if cached_vec is not None:
            return cached_vec
        
        # Tạo embedding
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            vec = self.model.encode(
                text,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        else:
            raise RuntimeError("sentence-transformers not available")
        
        # Lưu cache
        self._save_to_cache(text, vec)
        
        return vec
    
    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            normalize: Whether to normalize embeddings
            show_progress: Whether to show progress bar
            
        Returns:
            Embeddings array (num_texts x embedding_dim)
        """
        # Kiểm tra văn bản nào đã có cache
        result_vectors = []
        pending_texts = []
        pending_idx = []
        
        for i, text in enumerate(texts):
            cached_vec = self._load_from_cache(text)
            if cached_vec is not None:
                result_vectors.append(cached_vec)
            else:
                pending_texts.append(text)
                pending_idx.append(i)
        
        # Encode các văn bản còn lại
        if pending_texts:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                new_vectors = self.model.encode(
                    pending_texts,
                    batch_size=batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                )
            else:
                raise RuntimeError("sentence-transformers not available")
            
            # Lưu embedding mới vào cache rồi ghép kết quả
            for i, text in enumerate(pending_texts):
                vec = new_vectors[i]
                self._save_to_cache(text, vec)
                result_vectors.append(vec)
        
        return np.array(result_vectors)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embedding vectors."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            # Lấy số chiều bằng cách encode câu test
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            return len(test_embedding)
        return 384  # Mặc định của MiniLM
    
    def clear_cache(self) -> int:
        """Clear all cached embeddings."""
        if not os.path.exists(self.cache_dir):
            return 0
        
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".pkl"):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {filename}: {e}")
        
        logger.info(f"Đã xóa {count} embedding cache")
        return count


class TfidfFallback:
    """
    Fallback embedding bằng TF-IDF khi không có sentence-transformers.
    Cung cấp độ tương đồng cơ bản, không dùng neural embedding.
    """
    
    def __init__(self, max_features: int = 5000, ngram_range: tuple = (1, 2)):
        """
        Initialize TF-IDF fallback.
        
        Args:
            max_features: Maximum number of features
            ngram_range: N-gram range to use
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            lowercase=True,
            analyzer="word",
        )
        self._fitted = False
        self._embedding_dim = max_features
    
    def fit(self, texts: List[str]) -> "TfidfFallback":
        """Fit vectorizer on texts."""
        self.vectorizer.fit(texts)
        self._fitted = True
        return self
    
    def transform(self, text: str) -> np.ndarray:
        """Transform text to TF-IDF vector."""
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")
        return self.vectorizer.transform([text]).toarray()[0]
    
    def embed_text(self, text: str) -> np.ndarray:
        """Alias for transform."""
        return self.transform(text)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Transform multiple texts."""
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")
        return self.vectorizer.transform(texts).toarray()
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_dim


def create_embedding_generator(
    model_name: str = "mini",
    cache_dir: Optional[str] = None,
    device: Optional[str] = None,
    use_cache: bool = True,
) -> Union[TextEmbedder, TfidfFallback]:
    """
    Factory function to create an embedding generator.
    
    Args:
        model_name: Model name ('mini', 'base', or 'vietnamese')
        cache_dir: Cache directory path
        device: Device to use
        use_cache: Whether to use caching
        
    Returns:
        TextEmbedder or TfidfFallback instance
    """
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        model = TextEmbedder.MODELS.get(model_name, model_name)
        return TextEmbedder(
            model_name=model,
            cache_dir=cache_dir,
            device=device,
            use_cache=use_cache,
        )
    else:
        logger.info("Dùng TF-IDF fallback cho embedding")
        return TfidfFallback()
