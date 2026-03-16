"""Module huấn luyện và tạo index dữ liệu cho AI."""
import os
import sys
import json
import logging
import django
from typing import List, Dict, Any, Optional

# Thiết lập Django
def setup_django():
    """Thiết lập môi trường Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    try:
        django.setup()
    except Exception as e:
        logger.warning(f"Thiết lập Django lỗi: {e}")


logger = logging.getLogger(__name__)


class DataLoader:
    """
    Tải dữ liệu từ database.
    """
    
    def __init__(self):
        """Khoi tao"""
        self._setup_django()
    
    def _setup_django(self):
        """Thiết lập Django."""
        try:
            from django.conf import settings
            if not settings.configured:
                setup_django()
        except:
            setup_django()
    
    def _parse_spec_json(self, spec_str):
        """Parse JSON thông số."""
        if not spec_str:
            return {}
        
        try:
            if isinstance(spec_str, dict):
                return spec_str
            return json.loads(spec_str)
        except:
            return {}
    
    def get_products(self) -> List[Dict]:
        """Lay danh sach san pham"""
        try:
            from store.models import Product
            
            products = Product.objects.filter(is_active=True).select_related('brand', 'detail').prefetch_related('detail__variants')
            
            result = []
            for p in products:
                try:
                    detail = p.detail
                    specs = self._parse_spec_json(detail.specification.spec_json) if hasattr(detail, 'specification') and detail.specification else {}
                    
                    variants = []
                    prices = []
                    
                    if hasattr(detail, 'variants'):
                        for v in detail.variants.all():
                            variants.append({
                                'color': v.color_name,
                                'storage': v.storage,
                                'price': float(v.price) if v.price else 0,
                            })
                            if v.price:
                                prices.append(float(v.price))
                    
                    result.append({
                        'id': p.id,
                        'name': p.name,
                        'brand': p.brand.name if p.brand else '',
                        'description': p.description or '',
                        'price': float(p.price) if p.price else 0,
                        'specifications': specs,
                        'variants': variants,
                        'min_price': min(prices) if prices else float(p.price) if p.price else 0,
                        'max_price': max(prices) if prices else float(p.price) if p.price else 0,
                    })
                except Exception as e:
                    logger.warning(f"Loi load san pham {p.id}: {e}")
            
            return result
        
        except Exception as e:
            logger.error(f"Loi load products: {e}")
            return []
    
    def get_brands(self) -> List[Dict]:
        """Lay danh sach hang"""
        try:
            from store.models import Brand
            
            brands = Brand.objects.filter(is_active=True)
            
            return [
                {'id': b.id, 'name': b.name, 'description': b.description or ''}
                for b in brands
            ]
        
        except Exception as e:
            logger.error(f"Loi load brands: {e}")
            return []
    
    def get_categories(self) -> List[Dict]:
        """Lay danh sach danh muc"""
        try:
            from store.models import Category
            
            cats = Category.objects.filter(is_active=True)
            
            return [
                {'id': c.id, 'name': c.name, 'description': c.description or ''}
                for c in cats
            ]
        
        except Exception as e:
            logger.error(f"Loi load categories: {e}")
            return []
    
    def get_reviews(self) -> List[Dict]:
        """Lay danh sach danh gia"""
        try:
            from store.models import ProductReview
            
            reviews = ProductReview.objects.filter(is_approved=True).select_related('product')
            
            return [
                {
                    'id': r.id,
                    'product_id': r.product_id,
                    'product_name': r.product.name if r.product else '',
                    'rating': r.rating,
                    'content': r.content or '',
                }
                for r in reviews
            ]
        
        except Exception as e:
            logger.error(f"Loi load reviews: {e}")
            return []
    
    def get_product_content(self) -> List[Dict]:
        """Lay noi dung san pham"""
        try:
            from store.models import ProductContent
            
            contents = ProductContent.objects.filter(is_active=True).select_related('product')
            
            return [
                {
                    'id': c.id,
                    'product_id': c.product_id,
                    'product_name': c.product.name if c.product else '',
                    'title': c.title or '',
                    'content': c.content or '',
                    'content_type': c.content_type,
                }
                for c in contents
            ]
        
        except Exception as e:
            logger.error(f"Loi load content: {e}")
            return []
    
    def get_faqs(self) -> List[Dict]:
        """Lay FAQ"""
        return []
    
    def get_all_data(self) -> Dict[str, Any]:
        """Lay tat ca du lieu"""
        return {
            'products': self.get_products(),
            'brands': self.get_brands(),
            'categories': self.get_categories(),
            'reviews': self.get_reviews(),
            'content': self.get_product_content(),
            'faqs': self.get_faqs(),
        }
    
    def get_total_count(self) -> int:
        """Dem tong so luong"""
        total = 0
        data = self.get_all_data()
        for key, value in data.items():
            if isinstance(value, list):
                total += len(value)
        return total


class Trainer:
    """
    Class huan luyen model
    """
    
    def __init__(self, data_loader=None):
        """Khoi tao"""
        self.data_loader = data_loader or DataLoader()
        
        self.vector_store_path = "data/vector_store"
        self.intent_model_path = "data/intent_model.pkl"
        self.embedding_dim = 384
    
    def train_intent_model(self, save_path: Optional[str] = None) -> Dict:
        """Huan luyen intent classifier"""
        from .intent_model import IntentClassifier
        
        save_path = save_path or self.intent_model_path
        
        logger.info("Đang huấn luyện intent model...")
        
        clf = IntentClassifier(model_type="logistic")
        result = clf.train(save_path=save_path)
        
        logger.info(f"Huấn luyện xong: {result}")
        
        return result
    
    def index_all_data(self, recreate: bool = True) -> Dict:
        """Index tat ca du lieu"""
        from .embeddings import create_embedding_generator
        from .vector_store import MultiIndexVectorStore
        
        logger.info("Đang tải dữ liệu...")
        
        data = self.data_loader.get_all_data()
        
        # Tạo embedding generator
        embed_gen = create_embedding_generator(
            model_name="mini",
            cache_dir="data/embeddings_cache",
        )
        
        # Tạo vector store
        vstore = MultiIndexVectorStore(base_path=self.vector_store_path)
        
        results = {}
        
        # Index sản phẩm
        if data.get('products'):
            logger.info(f"Đang index {len(data['products'])} sản phẩm...")
            
            index = vstore.create_index("products", dimension=self.embedding_dim)
            
            texts = []
            ids = []
            metadata = []
            
            for p in data['products']:
                text = f"{p['name']} {p.get('brand', '')} {p.get('description', '')}"
                texts.append(text)
                ids.append(f"product_{p['id']}")
                metadata.append({
                    "type": "product",
                    "name": p['name'],
                    "brand": p.get('brand', ''),
                    "price": p.get('min_price', 0),
                })
            
            embeddings = embed_gen.embed_texts(texts)
            index.add_vectors(embeddings, ids=ids, metadata=metadata)
            index.save()
            
            results['products'] = len(texts)
        
        # Index thương hiệu
        if data.get('brands'):
            logger.info(f"Đang index {len(data['brands'])} thương hiệu...")
            
            index = vstore.create_index("brands", dimension=self.embedding_dim)
            
            texts = []
            ids = []
            metadata = []
            
            for b in data['brands']:
                text = f"{b['name']} {b.get('description', '')}"
                texts.append(text)
                ids.append(f"brand_{b['id']}")
                metadata.append({
                    "type": "brand",
                    "name": b['name'],
                })
            
            embeddings = embed_gen.embed_texts(texts)
            index.add_vectors(embeddings, ids=ids, metadata=metadata)
            index.save()
            
            results['brands'] = len(texts)
        
        # Index nội dung
        if data.get('content'):
            logger.info(f"Đang index {len(data['content'])} nội dung...")
            
            index = vstore.create_index("content", dimension=self.embedding_dim)
            
            texts = []
            ids = []
            metadata = []
            
            for c in data['content']:
                text = f"{c.get('title', '')} {c.get('content', '')}"
                texts.append(text)
                ids.append(f"content_{c['id']}")
                metadata.append({
                    "type": "content",
                    "title": c.get('title', ''),
                    "product_name": c.get('product_name', ''),
                })
            
            embeddings = embed_gen.embed_texts(texts)
            index.add_vectors(embeddings, ids=ids, metadata=metadata)
            index.save()
            
            results['content'] = len(texts)
        
        logger.info(f"Index xong: {results}")
        
        return results
    
    def run_full_training(self, recreate_vectors: bool = True, 
                         recreate_intent: bool = True) -> Dict:
        """Chay toan bo qua trinh training"""
        logger.info("Bắt đầu huấn luyện toàn bộ...")
        
        results = {}
        
        if recreate_intent:
            logger.info("Huấn luyện intent model...")
            results['intent'] = self.train_intent_model()
        
        if recreate_vectors:
            logger.info("Index dữ liệu...")
            results['indexing'] = self.index_all_data()
        
        logger.info(f"Huấn luyện toàn bộ xong: {results}")
        
        return results
    
    def update_product(self, product_id: int) -> bool:
        """Cap nhat 1 san pham"""
        logger.info(f"Đang cập nhật sản phẩm {product_id}...")
        
        try:
            from .embeddings import create_embedding_generator
            from .vector_store import MultiIndexVectorStore
            
            data = self.data_loader.get_all_data()
            products = [p for p in data.get('products', []) if p['id'] == product_id]
            
            if not products:
                logger.warning(f"Không tìm thấy sản phẩm {product_id}")
                return False
            
            product = products[0]
            
            embed_gen = create_embedding_generator(model_name="mini")
            vstore = MultiIndexVectorStore(base_path=self.vector_store_path)
            
            index = vstore.load_index("products")
            
            if index is None:
                logger.error("Không tìm thấy index sản phẩm")
                return False
            
            text = f"{product['name']} {product.get('brand', '')} {product.get('description', '')}"
            embedding = embed_gen.embed_text(text)
            
            index.add_vectors(
                embedding.reshape(1, -1),
                ids=[f"product_{product_id}"],
                metadata=[{
                    "type": "product",
                    "name": product['name'],
                    "brand": product.get('brand', ''),
                    "price": product.get('min_price', 0),
                }]
            )
            
            index.save()
            
            logger.info(f"Đã cập nhật sản phẩm {product_id}")
            return True
        
        except Exception as e:
            logger.error(f"Loi update product: {e}")
            return False


def run_training(recreate_vectors=True, recreate_intent=True):
    """Ham chay training"""
    trainer = Trainer()
    return trainer.run_full_training(recreate_vectors, recreate_intent)


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Train AI models")
    parser.add_argument("--vectors", action="store_true", help="Reindex vectors")
    parser.add_argument("--intent", action="store_true", help="Retrain intent model")
    parser.add_argument("--all", action="store_true", help="Train everything")
    
    args = parser.parse_args()
    
    recreate_vectors = args.all or args.vectors
    recreate_intent = args.all or args.intent
    
    if not recreate_vectors and not recreate_intent:
        recreate_vectors = True
        recreate_intent = True
    
    run_training(recreate_vectors, recreate_intent)
