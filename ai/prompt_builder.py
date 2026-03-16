"""Module tạo prompt cho Claude API của hệ thống QHUN22."""

import re
import html
from typing import List, Dict, Any, Optional


# Prompt hệ thống
SYSTEM_PROMPT = """Bạn là trợ lý bán hàng của QHUN22 – cửa hàng điện thoại chính hãng.

NGUYÊN TẮC BẮT BUỘC:
1. Chỉ được sử dụng dữ liệu được cung cấp trong phần "DỮ LIỆU HỆ THỐNG".
2. Tuyệt đối không bịa thông tin. Không sử dụng kiến thức bên ngoài.
3. Nếu dữ liệu không có thông tin để trả lời, hãy nói: "Em chưa có thông tin này, anh/chị liên hệ hotline để được hỗ trợ nhé!"
4. Không nhắc đến việc bạn là AI. Không giải thích cách bạn hoạt động.
5. Không lặp lại câu hỏi của khách.
6. Xưng "em", gọi khách là "anh/chị".
7. Trả lời bằng tiếng Việt.
8. Không sử dụng emoji hay icon.
9. Không bịa ra sản phẩm không có trong dữ liệu. Chỉ nhắc đến sản phẩm đã được cung cấp."""

# Mẫu prompt
NORMAL_USER_TEMPLATE = """DỮ LIỆU HỆ THỐNG:
{context}

CÂU HỎI KHÁCH:
"{message}"

YÊU CẦU:
- Trả lời ngắn gọn tối đa.
- Không quá 6 dòng.
- Không quá 120 từ.
- Chỉ nêu thông tin quan trọng nhất.
- Tập trung giúp khách ra quyết định mua.
- Không trình bày dạng bảng.
- Không dùng emoji hay icon."""

COMPARE_SYSTEM_EXTRA = """
KHI SO SÁNH SẢN PHẨM:
1. Chỉ so sánh dựa trên dữ liệu được cung cấp.
2. Không sử dụng bảng Markdown.
3. Trình bày dạng bullet point rõ ràng.
4. So sánh các tiêu chí quan trọng: Màn hình, Chip/Hiệu năng, Pin, Camera, Giá, RAM, ROM.
5. Chỉ nêu điểm khác biệt chính, không lặp lại điểm giống nhau.
6. Có thể viết 20-25 dòng để trả lời đầy đủ và chi tiết.
7. Kết thúc bằng 1 câu gợi ý nên chọn máy nào theo nhu cầu.
8. Trả lời đầy đủ, không bỏ sót thông tin quan trọng.
9. Không dùng emoji hay icon."""

COMPARE_USER_TEMPLATE = """DỮ LIỆU SẢN PHẨM ĐỂ SO SÁNH:
{combined_context}

YÊU CẦU:
"{message}"

Hãy so sánh theo đúng quy tắc."""

RECOMMEND_SYSTEM_EXTRA = """
KHI TƯ VẤN MUA SẮM:
1. Dựa vào ngân sách và nhu cầu của khách để gợi ý.
2. Đưa ra 2-3 sản phẩm phù hợp nhất.
3. Giải thích ngắn gọn tại sao nên chọn sản phẩm đó.
4. So sánh ưu nhược điểm của từng sản phẩm.
5. Khuyến khích khách đưa ra quyết định.
6. Không dùng emoji hay icon."""

RECOMMEND_USER_TEMPLATE = """THÔNG TIN KHÁCH HÀNG:
{budget_info}
{nhu_cau}

DỮ LIỆU SẢN PHẨM:
{products_context}

YÊU CẦU:
"{message}"

Hãy tư vấn cho khách hàng."""

ADVICE_SYSTEM_EXTRA = """
KHI ĐƯA RA LỜI KHUYÊN MUA HÀNG:
1. Xem xét nhu cầu thực sự của khách (chơi game, chụp ảnh, công việc,...)
2. Cân nhắc ngân sách và giá trị sản phẩm.
3. Đưa ra lời khuyên trung thực, không chỉ bán sản phẩm đắt nhất.
4. Có thể đề xuất sản phẩm thay thế nếu phù hợp hơn.
5. Không dùng emoji hay icon."""

SUMMARIZE_SYSTEM_EXTRA = """
KHI TÓM TẮT THÔNG TIN:
1. Tóm tắt ngắn gọn, dễ hiểu.
2. Sử dụng bullet points.
3. Nêu điểm chính, bỏ qua chi tiết không cần thiết.
4. Giúp khách nắm bắt nhanh thông tin.
5. Không dùng emoji hay icon."""

# Giới hạn token
NORMAL_MAX_TOKENS = 250
COMPARE_MAX_TOKENS = 600
RECOMMEND_MAX_TOKENS = 400
SUMMARIZE_MAX_TOKENS = 300


class PromptBuilder:
    """
    Tạo prompt cho Claude API từ ngữ cảnh và dữ liệu sản phẩm.
    """
    
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT
    
    def build_product_context(
        self,
        product: Dict[str, Any],
        include_specs: bool = True,
    ) -> str:
        """
        Build text context for a product.
        
        Args:
            product: Product dictionary
            include_specs: Whether to include specifications
            
        Returns:
            Formatted context string
        """
        parts = [f"Sản phẩm: {product.get('name', 'Unknown')}"]
        
        # Tình trạng kho
        stock = product.get('stock', 0)
        if stock > 0:
            parts.append("Tình trạng: CÒN HÀNG")
        else:
            parts.append("Tình trạng: HẾT HÀNG")
        
        # Hãng
        if product.get('brand'):
            parts.append(f"Hãng: {product['brand']}")
        
        # Giá
        min_price = product.get('min_price')
        max_price = product.get('max_price')
        if min_price and max_price:
            if min_price == max_price:
                parts.append(f"Giá: {self._format_price(min_price)}")
            else:
                parts.append(f"Giá: từ {self._format_price(min_price)} đến {self._format_price(max_price)}")
        elif min_price:
            parts.append(f"Giá: {self._format_price(min_price)}")
        
        # Mô tả
        if product.get('description'):
            desc = self._strip_html(product['description'][:400])
            if desc:
                parts.append(f"Mô tả: {desc}")
        
        # Màu sắc
        colors = product.get('colors', [])
        if colors:
            parts.append(f"Màu sắc: {', '.join(colors)}")
        
        # Dung lượng
        storages = product.get('storages', [])
        if storages:
            parts.append(f"Dung lượng: {', '.join(storages)}")
        
        # Thông số kỹ thuật
        if include_specs and product.get('specifications'):
            parts.append(f"Thông số kỹ thuật: {product['specifications']}")
        
        return "\n".join(parts)
    
    def build_multiple_product_context(
        self,
        products: List[Dict[str, Any]],
    ) -> str:
        """
        Build context for multiple products.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            Combined context string
        """
        contexts = []
        
        for i, product in enumerate(products, 1):
            context = self.build_product_context(product)
            contexts.append(f"--- SẢN PHẨM {i} ---\n{context}")
        
        return "\n\n".join(contexts)
    
    def build_compare_prompt(
        self,
        products: List[Dict[str, Any]],
        user_message: str,
    ) -> Dict[str, str]:
        """
        Build prompt for comparing products.
        
        Args:
            products: List of products to compare
            user_message: User's question
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        # Tạo ngữ cảnh sản phẩm
        combined_context = self.build_multiple_product_context(products)
        
        # Ghép prompt hệ thống
        system_prompt = self.system_prompt + "\n" + COMPARE_SYSTEM_EXTRA
        
        # Tạo prompt người dùng
        user_prompt = COMPARE_USER_TEMPLATE.format(
            combined_context=combined_context,
            message=user_message,
        )
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": COMPARE_MAX_TOKENS,
        }
    
    def build_recommend_prompt(
        self,
        products: List[Dict[str, Any]],
        user_message: str,
        budget: Optional[str] = None,
        needs: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Build prompt for product recommendations.
        
        Args:
            products: List of candidate products
            user's question
            budget: User's budget
            needs: User's needs
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        # Tạo ngữ cảnh sản phẩm
        products_context = self.build_multiple_product_context(products)
        
        # Tạo thông tin ngân sách và nhu cầu
        budget_info = f"Ngân sách: {budget}" if budget else "Ngân sách: Chưa xác định"
        needs_info = f"Nhu cầu: {needs}" if needs else "Nhu cầu: Chưa xác định"
        
        # Ghép prompt hệ thống
        system_prompt = self.system_prompt + "\n" + RECOMMEND_SYSTEM_EXTRA
        
        # Tạo prompt người dùng
        user_prompt = RECOMMEND_USER_TEMPLATE.format(
            budget_info=budget_info,
            nhu_cau=needs_info,
            products_context=products_context,
            message=user_message,
        )
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": RECOMMEND_MAX_TOKENS,
        }
    
    def build_advice_prompt(
        self,
        products: List[Dict[str, Any]],
        user_message: str,
    ) -> Dict[str, str]:
        """
        Build prompt for giving purchase advice.
        
        Args:
            products: List of products
            user_message: User's question
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        products_context = self.build_multiple_product_context(products)
        
        system_prompt = self.system_prompt + "\n" + ADVICE_SYSTEM_EXTRA
        
        user_prompt = f"""DỮ LIỆU SẢN PHẨM:
{products_context}

CÂU HỎI KHÁCH:
"{user_message}"

Hãy đưa ra lời khuyên mua hàng phù hợp."""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": RECOMMEND_MAX_TOKENS,
        }
    
    def build_summarize_prompt(
        self,
        products: List[Dict[str, Any]],
        user_message: str,
    ) -> Dict[str, str]:
        """
        Build prompt for summarizing products.
        
        Args:
            products: List of products
            user_message: User's question
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        products_context = self.build_multiple_product_context(products)
        
        system_prompt = self.system_prompt + "\n" + SUMMARIZE_SYSTEM_EXTRA
        
        user_prompt = f"""DỮ LIỆU SẢN PHẨM:
{products_context}

YÊU CẦU:
"{user_message}"

Hãy tóm tắt thông tin."""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": SUMMARIZE_MAX_TOKENS,
        }
    
    def build_simple_prompt(
        self,
        context: str,
        user_message: str,
        max_tokens: int = NORMAL_MAX_TOKENS,
    ) -> Dict[str, str]:
        """
        Build simple prompt with context.
        
        Args:
            context: Context string
            user_message: User's question
            max_tokens: Max tokens in response
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        user_prompt = NORMAL_USER_TEMPLATE.format(
            context=context,
            message=user_message,
        )
        
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": max_tokens,
        }
    
    def build_spec_prompt(
        self,
        product: Dict[str, Any],
        user_message: str,
    ) -> Dict[str, str]:
        """
        Build prompt for product specification questions.
        
        Args:
            product: Product dictionary
            user_message: User's question
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        context = self.build_product_context(product, include_specs=True)
        
        return self.build_simple_prompt(
            context=context,
            user_message=user_message,
            max_tokens=NORMAL_MAX_TOKENS,
        )
    
    def build_review_summary_prompt(
        self,
        reviews: List[Dict[str, Any]],
        user_message: str,
    ) -> Dict[str, str]:
        """
        Build prompt for summarizing reviews.
        
        Args:
            reviews: List of review dictionaries
            user_message: User's question
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        # Tạo ngữ cảnh đánh giá
        review_parts = ["ĐÁNH GIÁ SẢN PHẨM:"]
        
        for i, review in enumerate(reviews[:10], 1):  # Giới hạn 10 đánh giá
            rating = review.get('rating', 0)
            comment = review.get('comment', '')[:200]
            review_parts.append(f"{i}. Rating: {rating}/5 - {comment}")
        
        reviews_context = "\n".join(review_parts)
        
        system_prompt = self.system_prompt + "\n" + SUMMARIZE_SYSTEM_EXTRA
        
        user_prompt = f"""{reviews_context}

CÂU HỎI KHÁCH:
"{user_message}"

Hãy tổng hợp đánh giá từ khách hàng."""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": SUMMARIZE_MAX_TOKENS,
        }
    
    def _format_price(self, price: int) -> str:
        """Format price in Vietnamese Dong."""
        if price <= 0:
            return "Liên hệ"
        
        # Định dạng dấu chấm cho hàng nghìn
        return f"{price:,}đ".replace(",", ".")
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        # Xóa thẻ HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Giải mã HTML entities
        text = html.unescape(text)
        # Dọn khoảng trắng
        text = re.sub(r'\s+', ' ', text).strip()
        return text


def create_prompt_builder() -> PromptBuilder:
    """Factory function to create PromptBuilder."""
    return PromptBuilder()
