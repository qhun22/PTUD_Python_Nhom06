"""Module lưu trữ và tìm kiếm vector cho QHUN22."""
import os
import json
import logging
import pickle
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS chưa có, dùng fallback bằng numpy")


class VectorStore:
    """
    Vector store dùng FAISS
    """
    
    def __init__(self, dimension=384, index_type="IVF", metric="cosine",
                 nlist=100, nprobe=10, storage_path=None):
        """Khoi tao"""
        self.dimension = dimension
        self.index_type = index_type.upper()
        self.metric = metric.lower()
        self.nlist = nlist
        self.nprobe = nprobe
        self.storage_path = storage_path
        
        self._index = None
        self._metadata = []
        self._id_to_idx = {}
        
        if self.storage_path:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        self._create_index()
    
    def _create_index(self) -> None:
        """Tao index"""
        if not FAISS_AVAILABLE:
            logger.warning("FAISS chưa sẵn sàng")
            self._index = None
            return
        
        try:
            if self.index_type == "FLAT":
                if self.metric == "cosine":
                    self._index = faiss.IndexFlatIP(self.dimension)
                else:
                    self._index = faiss.IndexFlatL2(self.dimension)
            
            elif self.index_type == "IVF":
                quantizer = faiss.IndexFlatL2(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
            
            elif self.index_type == "HNSW":
                self._index = faiss.IndexHNSWFlat(self.dimension, 32)
                self._index.hnsw.efConstruction = 200
                self._index.hnsw.efSearch = 200
            
            else:
                self._index = faiss.IndexFlatL2(self.dimension)
            
            logger.info(f"Đã tạo index: {self.index_type}, metric: {self.metric}")
        
        except Exception as e:
            logger.error(f"Loi tao index: {e}")
            self._index = None
    
    def is_trained(self) -> bool:
        """Kiem tra da train chua"""
        if self._index is None:
            return False
        if hasattr(self._index, "is_trained"):
            return self._index.is_trained
        return True
    
    def train(self, vectors: np.ndarray) -> None:
        """Train index"""
        if self._index is None or not FAISS_AVAILABLE:
            return
        
        if not self._index.is_trained:
            logger.info(f"Đang train trên {len(vectors)} vectors...")
            self._index.train(vectors.astype(np.float32))
            logger.info("Train xong")
    
    def add_vectors(self, vectors: np.ndarray, ids: Optional[List[str]] = None,
                   metadata: Optional[List[Dict]] = None) -> List[int]:
        """Them vectors"""
        if self._index is None:
            return self._add_fallback(vectors, ids, metadata)
        
        vectors = vectors.astype(np.float32)
        
        # Chuẩn hóa
        if self.metric == "cosine":
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            vectors = vectors / norms
        
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(vectors))]
        
        if metadata is None:
            metadata = [{} for _ in range(len(vectors))]
        
        start_idx = len(self._metadata)
        self._index.add(vectors)
        
        for i, (doc_id, meta) in enumerate(zip(ids, metadata)):
            idx = start_idx + i
            self._metadata.append({"id": doc_id, "index": idx, **meta})
            self._id_to_idx[doc_id] = idx
        
        logger.info(f"Đã thêm {len(vectors)} vectors")
        return list(range(start_idx, start_idx + len(vectors)))
    
    def _add_fallback(self, vectors, ids=None, metadata=None):
        """Fallback numpy"""
        if not hasattr(self, "_fallback_vectors"):
            self._fallback_vectors = []
        
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(vectors))]
        
        if metadata is None:
            metadata = [{} for _ in range(len(vectors))]
        
        start_idx = len(self._fallback_vectors)
        self._fallback_vectors.extend(vectors)
        
        for i, (doc_id, meta) in enumerate(zip(ids, metadata)):
            idx = start_idx + i
            self._metadata.append({"id": doc_id, "index": idx, **meta})
            self._id_to_idx[doc_id] = idx
        
        return list(range(start_idx, start_idx + len(vectors)))
    
    def search(self, query_vector: np.ndarray, k: int = 10,
              filters: Optional[Dict] = None) -> List[Dict]:
        """Tim kiem vectors tuong tu"""
        if self._index is None or not FAISS_AVAILABLE:
            return self._search_fallback(query_vector, k, filters)
        
        query_vector = query_vector.astype(np.float32)
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        
        if self.metric == "cosine":
            norm = np.linalg.norm(query_vector)
            if norm > 0:
                query_vector = query_vector / norm
        
        if hasattr(self._index, "nprobe"):
            self._index.nprobe = self.nprobe
        
        scores, indices = self._index.search(query_vector, min(k * 2, self._index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            
            meta = self._metadata[idx].copy()
            
            if filters:
                match = all(meta.get(k) == v for k, v in filters.items())
                if not match:
                    continue
            
            if self.metric == "l2":
                similarity = 1 / (1 + score)
            else:
                similarity = float(score)
            
            meta["score"] = similarity
            meta["index"] = int(idx)
            results.append(meta)
            
            if len(results) >= k:
                break
        
        return results
    
    def _search_fallback(self, query_vector, k=10, filters=None):
        """Fallback tim kiem"""
        if not hasattr(self, "_fallback_vectors") or not self._fallback_vectors:
            return []
        
        vectors = np.array(self._fallback_vectors)
        
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = vectors / norms
        
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector = query_vector / query_norm
        
        similarities = np.dot(normalized, query_vector.T).flatten()
        
        top_k = min(k, len(similarities))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if idx >= len(self._metadata):
                continue
            
            meta = self._metadata[idx].copy()
            
            if filters:
                match = all(meta.get(k) == v for k, v in filters.items())
                if not match:
                    continue
            
            meta["score"] = float(similarities[idx])
            meta["index"] = int(idx)
            results.append(meta)
        
        return results
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """Lay metadata theo ID"""
        return self._metadata[self._id_to_idx.get(doc_id)] if doc_id in self._id_to_idx else None
    
    def save(self, path: Optional[str] = None) -> str:
        """Luu index vao disk"""
        path = path or self.storage_path
        if not path:
            raise ValueError("No storage path")
        
        index_path = f"{path}.index"
        if self._index is not None and FAISS_AVAILABLE:
            faiss.write_index(self._index, index_path)
        
        metadata_path = f"{path}.meta"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        
        config = {
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
        }
        config_path = f"{path}.config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved to {path}")
        return path
    
    def load(self, path: Optional[str] = None) -> bool:
        """Load tu disk"""
        path = path or self.storage_path
        if not path:
            raise ValueError("No storage path")
        
        config_path = f"{path}.config.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.dimension = config.get("dimension", self.dimension)
            self.index_type = config.get("index_type", self.index_type)
            self.metric = config.get("metric", self.metric)
            self.nlist = config.get("nlist", self.nlist)
            self.nprobe = config.get("nprobe", self.nprobe)
        
        index_path = f"{path}.index"
        if os.path.exists(index_path) and FAISS_AVAILABLE:
            self._index = faiss.read_index(index_path)
            logger.info(f"Đã load index với {self._index.ntotal} vectors")
        
        metadata_path = f"{path}.meta"
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
            
            self._id_to_idx = {
                meta["id"]: meta["index"] 
                for meta in self._metadata 
                if "id" in meta and "index" in meta
            }
            logger.info(f"Đã load {len(self._metadata)} metadata")
        
        return True
    
    @property
    def num_vectors(self) -> int:
        """Dem so vectors"""
        if self._index is not None and FAISS_AVAILABLE:
            return self._index.ntotal
        elif hasattr(self, "_fallback_vectors"):
            return len(self._fallback_vectors)
        return 0
    
    def __len__(self) -> int:
        return self.num_vectors


class MultiIndexVectorStore:
    """Vector store nhieu indices"""
    
    def __init__(self, base_path="data/vector_store"):
        """Khoi tao"""
        self.base_path = base_path
        self.indices: Dict[str, VectorStore] = {}
        
        os.makedirs(base_path, exist_ok=True)
    
    def create_index(self, name: str, dimension: int = 384,
                    index_type: str = "IVF", **kwargs) -> VectorStore:
        """Tao index moi"""
        storage_path = os.path.join(self.base_path, name)
        
        index = VectorStore(
            dimension=dimension,
            index_type=index_type,
            storage_path=storage_path,
            **kwargs,
        )
        
        self.indices[name] = index
        return index
    
    def get_index(self, name: str) -> Optional[VectorStore]:
        """Lay index theo ten"""
        return self.indices.get(name)
    
    def load_index(self, name: str) -> Optional[VectorStore]:
        """Load index tu disk"""
        storage_path = os.path.join(self.base_path, name)
        
        if not os.path.exists(storage_path + ".index"):
            return None
        
        index = VectorStore(storage_path=storage_path)
        index.load()
        
        self.indices[name] = index
        return index
    
    def load_all_indices(self) -> Dict[str, VectorStore]:
        """Load tat ca indices"""
        if not os.path.exists(self.base_path):
            return {}
        
        for name in os.listdir(self.base_path):
            if os.path.isdir(os.path.join(self.base_path, name)):
                self.load_index(name)
        
        return self.indices
    
    def save_index(self, name: str) -> None:
        """Luu index"""
        if name in self.indices:
            self.indices[name].save()
    
    def save_all_indices(self) -> None:
        """Luu tat ca"""
        for name, index in self.indices.items():
            index.save()


def create_vector_store(dimension=384, index_type="IVF", storage_path=None):
    """Ham tao VectorStore"""
    return VectorStore(dimension=dimension, index_type=index_type, storage_path=storage_path)
