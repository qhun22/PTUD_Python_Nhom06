"""Module phát hiện intent người dùng cho hệ thống QHUN22."""

import os
import json
import logging
import pickle
import re
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

# Thử import sklearn
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn chưa có trong môi trường")


# Định nghĩa intent cho cửa hàng
INTENTS = {
    # Intent chính
    "greeting": {
        "description": "Chào hỏi, xin chào",
        "keywords": ["xin chào", "chào bạn", "chào shop", "hello", "hi", "hey", "alo"],
        "requires_claude": False,
    },
    "product_search": {
        "description": "Tìm kiếm sản phẩm",
        "keywords": ["tìm", "kiếm", "xem", "tìm kiếm", "tìm máy", "tìm điện thoại"],
        "requires_claude": False,
    },
    "phone_recommendation": {
        "description": "Tư vấn, gợi ý điện thoại",
        "keywords": ["tư vấn", "gợi ý", "recommend", "suggest", "nên mua", "chọn máy", "máy nào tốt"],
        "requires_claude": True,
    },
    "compare_phones": {
        "description": "So sánh điện thoại",
        "keywords": ["so sánh", "vs", "versus", "hay hơn", "khác gì", "nên mua cái nào"],
        "requires_claude": True,
    },
    "specification": {
        "description": "Hỏi về thông số kỹ thuật",
        "keywords": ["thông số", "spec", "pin", "camera", "màn hình", "chip", "ram", "rom"],
        "requires_claude": False,
    },
    "price_query": {
        "description": "Hỏi về giá",
        "keywords": ["giá", "bao nhiêu", "bao tiền", "giá bao nhiêu", "giá cả"],
        "requires_claude": False,
    },
    "stock_query": {
        "description": "Hỏi về tình trạng hàng",
        "keywords": ["còn hàng", "hết hàng", "có hàng", "còn không", "mua được không"],
        "requires_claude": False,
    },
    "variant_query": {
        "description": "Hỏi về màu/dung lượng",
        "keywords": ["màu gì", "dung lượng", "phiên bản", "bản nào", "ram", "rom"],
        "requires_claude": False,
    },
    "order_query": {
        "description": "Tra cứu đơn hàng",
        "keywords": ["đơn hàng", "mã đơn", "order", "tra cứu", "tracking", "kiểm tra đơn"],
        "requires_claude": False,
    },
    "installment": {
        "description": "Hỏi về trả góp",
        "keywords": ["trả góp", "trả góp 0%", "mua góp", "góp"],
        "requires_claude": False,
    },
    "warranty": {
        "description": "Hỏi về bảo hành",
        "keywords": ["bảo hành", "đổi trả", "warranty", "bao hanh"],
        "requires_claude": False,
    },
    "staff_request": {
        "description": "Yêu cầu gặp nhân viên",
        "keywords": ["gặp nhân viên", "người thật", "chuyển nhân viên"],
        "requires_claude": False,
    },
    "identity": {
        "description": "Hỏi về danh tính bot",
        "keywords": ["bạn là ai", "em là ai", "bot là gì"],
        "requires_claude": False,
    },
    "troubleshooting": {
        "description": "Hỏi về xử lý sự cố",
        "keywords": ["lỗi", "hư", "không được", "bị", "vấn đề", "sự cố", "hỏng"],
        "requires_claude": True,
    },
    "price_comparison": {
        "description": "So sánh giá",
        "keywords": ["giá nào rẻ hơn", "so sánh giá", "máy nào rẻ hơn"],
        "requires_claude": True,
    },
    "faq": {
        "description": "Hỏi câu hỏi thường gặp",
        "keywords": ["faq", "câu hỏi", "hỏi đáp"],
        "requires_claude": False,
    },
    "unknown": {
        "description": "Không xác định được",
        "keywords": [],
        "requires_claude": False,
    },
}

# Dữ liệu train cho từng intent
INTENT_TRAINING_DATA = {
    "greeting": [
        "xin chào", "chào bạn", "chào shop", "chào em", "hello", "hi", "hey", "alo",
        "ê shop", "shop ơi", "ad ơi", "admin ơi", "có ai không", "tư vấn giúp",
        "chào buổi sáng", "chào buổi trưa", "chào buổi tối", "xin chào shop",
        "hi there", "greetings", "chào đấy", "alo alo",
    ],
    "product_search": [
        "tìm điện thoại", "tìm máy", "xem sản phẩm", "có những máy nào",
        "danh sách sản phẩm", "máy đang bán", "sản phẩm có gì", "iphone có không",
        "samsung có không", "xiaomi có không", "tìm kiếm sản phẩm",
        "show me phones", "list products", "what phones do you have",
        "các mẫu iphone", "các dòng samsung", "điện thoại apple",
        "máy nào đang kinh doanh", "có bán máy gì", "liệt kê sản phẩm",
    ],
    "phone_recommendation": [
        "tư vấn máy", "tư vấn điện thoại", "gợi ý máy", "máy nào tốt",
        "máy nào đáng mua", "nên mua máy nào", "chọn máy nào", "recommend phone",
        "máy phù hợp", "máy cho sinh viên", "máy cho game", "máy chụp ảnh đẹp",
        "máy pin trâu", "máy dưới 10 triệu", "máy trong tầm giá",
        "máy nào性价比", "máy tốt nhất", "đáng tiền nhất",
        "tư vấn giúp", "giúp tôi chọn máy", "máy cho người dùng thường",
    ],
    "compare_phones": [
        "so sánh", "so sánh iphone 14 và iphone 15", "iphone hay samsung",
        "vs", "versus", "máy nào tốt hơn", "khác gì", "khác nhau",
        "so sánh samsung và iphone", "nên mua iphone hay samsung",
        "so sánh galaxy và iphone", "so sánh 2 máy", "so sánh chi tiết",
        "ưu nhược điểm", "so sánh pin", "so sánh camera", "so sánh màn hình",
        "con nào tốt hơn", "máy nào ngon hơn", "chọn cái nào",
    ],
    "specification": [
        "thông số", "spec", "cấu hình", "pin bao nhiêu", "mấy mah",
        "camera bao nhiêu mp", "chip gì", "màn hình", "ram", "rom",
        "dung lượng pin", "sạc nhanh", "sạc không dây", "kháng nước",
        "ip68", "trọng lượng", "kích thước", "tần số quét", "hz",
        "hiệu năng", "chơi game", "chụp ảnh", "quay phim", "selfie",
    ],
    "price_query": [
        "giá bao nhiêu", "giá bao nhiêu tiền", "bao nhiêu tiền",
        "giá iphone 15", "giá samsung s24", "giá xiaomi", "price",
        "giá cả", "mức giá", "giá khoảng", "giá rẻ nhất", "giá cao nhất",
        "bao nhiêu v", "bao nhiêu ạ", "giá hiện tại", "giá bây giờ",
    ],
    "stock_query": [
        "còn hàng không", "còn máy không", "hết hàng chưa", "có hàng không",
        "còn sẵn không", "tình trạng", "stock", "còn k", "còn bán không",
        "mua được không", "đặt được không", "order được không",
        "available", "in stock", "con hang khong", "het hang chua",
    ],
    "variant_query": [
        "màu gì", "có màu gì", "mấy màu", "màu nào đẹp", "màu nào",
        "phiên bản nào", "bản nào", "dung lượng nào", "có bản nào",
        "bao nhiêu gb", "ram bao nhiêu", "rom bao nhiêu", "màu đẹp nhất",
        "nên chọn màu", "màu nào bền", "bản 128gb", "bản 256gb",
        "bản 512gb", "bản 1tb", "phiên bản", "biến thể",
    ],
    "order_query": [
        "đơn hàng", "mã đơn", "order", "kiểm tra đơn", "tra cứu đơn",
        "tracking", "đơn của tôi", "đơn của mình", "giao tới đâu rồi",
        "đơn tới đâu", "bao giờ giao", "khi nào nhận", "vận đơn",
        "mã vận chuyển", "order của tôi", "check order", "xem đơn",
    ],
    "installment": [
        "trả góp", "trả góp 0%", "trả góp không lãi", "mua trả góp",
        "trả trước bao nhiêu", "góp mỗi tháng", "hỗ trợ trả góp",
        "có trả góp", "góp được không", "mua góp", "chia kỳ",
        "thanh toán góp", "installment", "tra gop", "0% interest",
    ],
    "warranty": [
        "bảo hành", "bảo hành bao lâu", "bảo hành mấy tháng",
        "bảo hành chính hãng không", "bảo hành ở đâu", "đổi trả",
        "chính sách bảo hành", "warranty", "đổi máy", "trả máy",
        "lỗi thì sao", "hư thì sao", "bể màn", "hỏng",
    ],
    "staff_request": [
        "gặp nhân viên", "người thật", "nói chuyện với người",
        "gặp tư vấn viên", "kết nối nhân viên", "chuyển nhân viên",
        "gọi nhân viên", "cần người hỗ trợ", "talk to human",
        "speak to staff", "gặp admin", "nói chuyện với shop",
    ],
    "identity": [
        "bạn là ai", "em là ai", "bot là ai", "ai vậy",
        "giới thiệu về bạn", "giới thiệu về em", "tên bạn là gì",
        "tên em là gì", "bạn là bot gì", "em là bot gì",
        "bạn làm được gì", "em làm được gì", "who are you",
    ],
    "troubleshooting": [
        "lỗi", "hư", "không được", "bị", "vấn đề", "sự cố",
        "hỏng", "máy không lên", "điện thoại không bật", "bị treo",
        "lag", "giật", "nóng máy", "hết pin nhanh", "sạc không vào",
        "màn hình không hiển thị", "loa không có tiếng", "camera không chụp được",
    ],
    "price_comparison": [
        "giá nào rẻ hơn", "so sánh giá", "máy nào rẻ hơn",
        "giá iphone so với samsung", "nơi nào bán rẻ hơn",
        "so sánh giá cả", "đâu giá tốt hơn", "mua ở đâu rẻ",
    ],
    "faq": [
        "faq", "câu hỏi thường gặp", "hỏi đáp", "cần hỏi",
        "thắc mắc", "giải đáp", "hướng dẫn", "cách mua",
    ],
}


class IntentClassifier:
    """
    Classify user intent using TF-IDF + Logistic Regression/SVM.
    Supports training, prediction, and model save/load.
    """
    
    def __init__(
        self,
        model_type: str = "logistic",
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 3),
        min_df: int = 2,
        use_fallback: bool = True,
    ):
        """
        Initialize intent classifier.
        
        Args:
            model_type: Model type ('logistic' or 'svm')
            max_features: Maximum TF-IDF features
            ngram_range: N-gram range for TF-IDF
            min_df: Minimum document frequency
            use_fallback: Use keyword fallback if ML fails
        """
        self.model_type = model_type
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.use_fallback = use_fallback
        
        self._pipeline = None
        self._vectorizer = None
        self._classifier = None
        self._is_trained = False
        self._intent_list = list(INTENTS.keys())
    
    def _create_pipeline(self) -> Pipeline:
        """Tạo pipeline sklearn."""
        if self.model_type == "svm":
            classifier = LinearSVC(
                C=1.0,
                class_weight="balanced",
                max_iter=10000,
                random_state=42,
            )
        else:
            classifier = LogisticRegression(
                C=1.0,
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
                solver="lbfgs",
                multi_class="multinomial",
            )
        
        vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            lowercase=True,
            analyzer="char_wb",  # N-gram theo ký tự cho tiếng Việt
        )
        
        pipeline = Pipeline([
            ("tfidf", vectorizer),
            ("classifier", classifier),
        ])
        
        return pipeline
    
    def _prepare_training_data(self) -> Tuple[List[str], List[str]]:
        """Chuẩn bị dữ liệu train từ bộ intent có sẵn."""
        text_list = []
        label_list = []
        
        for intent, samples in INTENT_TRAINING_DATA.items():
            text_list.extend(samples)
            label_list.extend([intent] * len(samples))
        
        return text_list, label_list
    
    def _keyword_fallback(self, text: str) -> str:
        """Fallback theo từ khóa để phát hiện intent."""
        msg = text.lower()
        
        # Chuẩn hóa tiếng Việt
        replacements = {
            "ko": "không", "k": "không", "hok": "không",
            "dc": "được", "đc": "được",
            "vs": "so sánh",
            "ip": "iphone",
            "sg": "samsung",
        }
        for old, new in replacements.items():
            msg = msg.replace(old, new)
        
        # So khớp theo từ khóa
        scores = {}
        for intent, config in INTENTS.items():
            if intent == "unknown":
                continue
            
            score = 0
            for keyword in config.get("keywords", []):
                if keyword in msg:
                    score += 1
            if score > 0:
                scores[intent] = score
        
        if scores:
            # Trả intent có điểm cao nhất
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "unknown"
    
    def train(
        self,
        texts: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        test_size: float = 0.2,
        save_path: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Train intent classifier.
        
        Args:
            texts: Training texts (if None, use predefined data)
            labels: Training labels (if None, use predefined data)
            test_size: Test set ratio
            save_path: Path to save trained model
            
        Returns:
            Dictionary with training metrics
        """
        if not SKLEARN_AVAILABLE:
            logger.error("sklearn chưa sẵn sàng để train")
            return {"error": "sklearn not available"}
        
        # Dùng dữ liệu có sẵn nếu chưa truyền vào
        if texts is None or labels is None:
            texts, labels = self._prepare_training_data()
        
        logger.info(f"Training intent classifier on {len(texts)} samples...")
        
        # Chia dữ liệu
        x_train, x_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        # Tạo và train pipeline
        self._pipeline = self._create_pipeline()
        self._pipeline.fit(x_train, y_train)
        
        # Đánh giá
        y_pred = self._pipeline.predict(x_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Training complete. Test accuracy: {accuracy:.4f}")
        
        # Lấy classification report
        report = classification_report(y_test, y_pred, output_dict=True)
        
        self._is_trained = True
        
        # Lưu nếu có đường dẫn
        if save_path:
            self.save(save_path)
        
        return {
            "accuracy": accuracy,
            "train_size": len(x_train),
            "test_size": len(x_test),
            "report": report,
        }
    
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict intent for a text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with intent, confidence, and metadata
        """
        if self._pipeline is None or not self._is_trained:
            if self.use_fallback:
                intent = self._keyword_fallback(text)
                return {
                    "intent": intent,
                    "confidence": 0.5,
                    "method": "keyword_fallback",
                    "requires_claude": INTENTS.get(intent, {}).get("requires_claude", False),
                }
            else:
                return {
                    "intent": "unknown",
                    "confidence": 0.0,
                    "method": "not_trained",
                    "requires_claude": False,
                }
        
        try:
            # Dự đoán intent
            intent = self._pipeline.predict([text])[0]
            
            # Lấy xác suất nếu model hỗ trợ
            if hasattr(self._pipeline, "predict_proba"):
                proba = self._pipeline.predict_proba([text])[0]
                classes = self._pipeline.classes_
                confidence = float(proba[classes.tolist().index(intent)])
            else:
                confidence = 0.8
            
            return {
                "intent": intent,
                "confidence": confidence,
                "method": "ml_model",
                "requires_claude": INTENTS.get(intent, {}).get("requires_claude", False),
            }
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            
            if self.use_fallback:
                intent = self._keyword_fallback(text)
                return {
                    "intent": intent,
                    "confidence": 0.3,
                    "method": "keyword_fallback",
                    "requires_claude": INTENTS.get(intent, {}).get("requires_claude", False),
                }
            
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "method": "error",
                "requires_claude": False,
            }
    
    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Predict intent for multiple texts."""
        result_list = [self.predict(text) for text in texts]
        return result_list
    
    def get_intent_info(self, intent: str) -> Optional[Dict[str, Any]]:
        """Get information about an intent."""
        return INTENTS.get(intent)
    
    def save(self, path: str) -> None:
        """Save trained model to disk."""
        if self._pipeline is None:
            logger.warning("No model to save")
            return
        
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "pipeline": self._pipeline,
                "model_type": self.model_type,
                "max_features": self.max_features,
                "ngram_range": self.ngram_range,
                "is_trained": self._is_trained,
            }, f)
        
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str) -> bool:
        """Load trained model from disk."""
        if not os.path.exists(path):
            logger.error(f"Model file not found: {path}")
            return False
        
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            
            self._pipeline = data["pipeline"]
            self.model_type = data.get("model_type", "logistic")
            self.max_features = data.get("max_features", 5000)
            self.ngram_range = data.get("ngram_range", (1, 3))
            self._is_trained = data.get("is_trained", True)
            
            logger.info(f"Model loaded from {path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


def create_intent_classifier(
    model_type: str = "logistic",
    train: bool = True,
    save_path: Optional[str] = None,
) -> IntentClassifier:
    """
    Hàm factory để tạo intent classifier.
    
    Args:
        model_type: Model type ('logistic' or 'svm')
        train: Whether to train on creation
        save_path: Path to save/load model
        
    Returns:
        Trained IntentClassifier
    """
    classifier = IntentClassifier(model_type=model_type)
    
    if train:
        classifier.train(save_path=save_path)
    elif save_path and os.path.exists(save_path):
        classifier.load(save_path)
    
    return classifier
