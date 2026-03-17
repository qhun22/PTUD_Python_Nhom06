import re
import json
import logging
import time
import random
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from django.db.models import Q, Sum
from django.utils import timezone

from .models import Product, ProductDetail, ProductSpecification, ProductVariant, ProductContent, Order, OrderItem
from .claude_service import ClaudeService

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# PROMPTS
# ════════════════════════════════════════════════════════════════

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

NORMAL_USER_TEMPLATE = """DỮ LIỆU HỆ THỐNG:
{context}

CÂU HỎI KHÁCH:
"{message}"

YÊU CẦU:
- Trả lời rõ ràng, đủ ý theo đúng câu hỏi.
- Ưu tiên 6-10 dòng khi nội dung cần chi tiết.
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

NORMAL_MAX_TOKENS = 700
COMPARE_MAX_TOKENS = 1000

# ════════════════════════════════════════════════════════════════
# FIXED MESSAGES
# ════════════════════════════════════════════════════════════════

NOT_FOUND_MSG = "Hiện tại QHUN22 chưa kinh doanh sản phẩm này. Anh/chị có muốn em tư vấn mẫu khác không?"
CLARIFY_MSG = "Em chưa hiểu vấn đề anh/chị đang trao đổi, anh/chị có thể nói rõ hơn được không ạ?"

MENU_MSG = "Em có thể hỗ trợ anh/chị những gì nè?"
MENU_SUGGESTIONS = [
    "Tư vấn chọn máy",
    "So sánh sản phẩm",
    "Kiểm tra đơn hàng",
    "Gặp nhân viên",
]

STAFF_MSG = "Anh/chị vui lòng liên hệ Hotline 0327221005 hoặc Telegram @qhun22 để được nhân viên hỗ trợ trực tiếp nhé!"

INSTALLMENT_MSG = (
    "QHUN22 hỗ trợ trả góp 0% lãi suất qua thẻ tín dụng và các công ty tài chính.\n"
    "Anh/chị liên hệ hotline 0327221005 hoặc đến trực tiếp cửa hàng để được hướng dẫn chi tiết nhé!"
)

WARRANTY_MSG = (
    "Tất cả sản phẩm tại QHUN22 đều là hàng chính hãng, bảo hành 12 tháng tại trung tâm bảo hành ủy quyền.\n"
    "Ngoài ra, QHUN22 hỗ trợ đổi trả trong 7 ngày nếu sản phẩm lỗi từ nhà sản xuất.\n"
    "Anh/chị cần hỗ trợ thêm về bảo hành sản phẩm nào không?"
)

# ════════════════════════════════════════════════════════════════
# INTENT PATTERNS
# ════════════════════════════════════════════════════════════════

GREETING_PATTERNS = re.compile(
    r"(xin chào|chào bạn|chào shop|chào\b|hello\b|^hi\b|^hey\b|alo\b|"
    r"ê shop|shop ơi|ad ơi|admin ơi|"
    r"có ai không|có ai trực không|tư vấn giúp|giúp mình với|"
    r"^help\b|^support\b|mình cần hỗ trợ|cho mình hỏi|hỏi chút)",
    re.IGNORECASE,
)

GREETING_PATTERNS_NORM = re.compile(
    r"(xin chao|chao|hello|hi|hey|alo|shop oi|ad oi|admin oi|"
    r"co ai khong|co ai truc khong|tu van giup|giup toi voi|"
    r"help|support|toi can ho tro|cho toi hoi|hoi chut|"
    r"tu van voi|tv giup)",
    re.IGNORECASE,
)

LIST_PRODUCT_PATTERNS = re.compile(
    r"(mẫu nào|những mẫu|có những gì|bán gì|sản phẩm nào|có gì|"
    r"xem sản phẩm mới|mẫu mới|hàng mới về|"
    r"danh sách máy|các máy đang bán|các mẫu iphone|các dòng iphone|"
    r"shop có bán|hiện có những|hiện đang bán|còn những máy nào|"
    r"có những dòng nào|đang kinh doanh gì|bán những gì|"
    r"có bán|đang bán gì|shop có gì|có máy nào|liệt kê)",
    re.IGNORECASE,
)

LIST_PRODUCT_PATTERNS_NORM = re.compile(
    r"(mau nao|nhung mau|co nhung gi|ban gi|san pham nao|co gi|"
    r"xem san pham moi|mau moi|hang moi ve|"
    r"danh sach may|cac may dang ban|shop co ban|hien co nhung|"
    r"hien dang ban|con nhung may nao|co nhung dong nao|"
    r"dang kinh doanh gi|ban nhung gi|co may nao|liet ke)",
    re.IGNORECASE,
)

PRICE_PATTERNS = re.compile(
    r"(\bgiá\b|bao nhiêu tiền|bao nhiêu\b|giá bn|bn tiền|bao tiền|"
    r"giá sao|giá nhiêu|giá hiện tại|giá bây giờ|"
    r"bao nhiu|giá cả|mức giá|giá khoảng|"
    r"giá rẻ nhất|giá thấp nhất|giá cao nhất|"
    r"nhiêu tiền|bao nhiêu v|bao nhiêu ạ)",
    re.IGNORECASE,
)

PRICE_PATTERNS_NORM = re.compile(
    r"(gia|bao nhieu tien|bao nhieu|gia bn|bn tien|bao tien|"
    r"gia sao|gia nhieu|gia hien tai|gia bay gio|"
    r"bao nhiu|muc gia|gia khoang|nhiu tien|xin gia|"
    r"bao nhieu a|bao nhieu vay)",
    re.IGNORECASE,
)

STOCK_PATTERNS = re.compile(
    r"(còn hàng không|còn không|còn máy không|hết hàng chưa|"
    r"có hàng không|có sẵn không|còn sẵn không|"
    r"tình trạng|stock|hàng còn không|còn k|"
    r"còn bán không|hết chưa|còn hay hết|"
    r"mua được không|đặt được không|order được không)",
    re.IGNORECASE,
)

STOCK_PATTERNS_NORM = re.compile(
    r"(con hang khong|con khong|con may khong|het hang chua|"
    r"co hang khong|co san khong|con san khong|"
    r"tinh trang|stock|hang con khong|con k|"
    r"con ko|het chua|con hay het|"
    r"mua duoc khong|dat duoc khong|order duoc khong|"
    r"available|in stock)",
    re.IGNORECASE,
)

VARIANT_PATTERNS = re.compile(
    r"(màu gì|có màu gì|mấy màu|màu nào đẹp|màu nào|có mấy màu|"
    r"phiên bản nào|bản nào|dung lượng nào|có bản nào|"
    r"bao nhiêu gb|bao nhiêu tb|ram bao nhiêu|rom bao nhiêu|"
    r"có bao nhiêu phiên bản|mấy bản|mấy gb|bản gì|"
    r"màu đẹp nhất|nên chọn màu|màu nào bền)",
    re.IGNORECASE,
)

VARIANT_PATTERNS_NORM = re.compile(
    r"(mau gi|co mau gi|may mau|mau nao dep|mau nao|co may mau|"
    r"phien ban nao|ban nao|dung luong nao|co ban nao|"
    r"bao nhieu gb|bao nhieu tb|ram bao nhieu|rom bao nhieu|"
    r"co bao nhieu phien ban|may ban|may gb|ban gi)",
    re.IGNORECASE,
)

SPEC_PATTERNS = re.compile(
    r"(\bpin\b|mấy mah|camera|bao nhiêu mp|"
    r"chip gì|chip nào|màn hình|"
    r"cấu hình|thông số|spec\b|"
    r"\bram\b|\brom\b|bộ nhớ|dung lượng trong|"
    r"sạc nhanh|có sạc không dây|"
    r"kháng nước|chống nước|ip68|ip67|"
    r"nặng bao nhiêu|kích thước|trọng lượng|"
    r"tần số quét|\bhz\b|độ sáng|\bnit\b|"
    r"hiệu năng|mạnh không|chơi game|"
    r"chụp ảnh|quay phim|selfie)",
    re.IGNORECASE,
)

SPEC_PATTERNS_NORM = re.compile(
    r"(pin|mah|camera|mp|chip|man hinh|"
    r"cau hinh|thong so|spec|ram|rom|bo nho|dung luong trong|"
    r"sac nhanh|sac khong day|khang nuoc|chong nuoc|ip68|ip67|"
    r"nang bao nhieu|kich thuoc|trong luong|tan so quet|hz|do sang|nit|"
    r"hieu nang|manh khong|choi game|chup anh|quay phim|selfie)",
    re.IGNORECASE,
)

COMPARE_PATTERNS = re.compile(
    r"(so sánh|vs|versus|hay hơn|khác gì|"
    r"khác nhau|nên mua cái nào|chọn cái nào|"
    r"so với|đặt cạnh|so giùm|so giúp|"
    r"hơn gì|thua gì|ưu điểm hơn|nhược điểm)",
    re.IGNORECASE,
)

COMPARE_PATTERNS_NORM = re.compile(
    r"(so sanh|vs|versus|hay hon|khac gi|"
    r"khac nhau|nen mua cai nao|chon cai nao|"
    r"so voi|dat canh|so giup|hơn gi|thua gi|uu diem hon|nhuoc diem)",
    re.IGNORECASE,
)

CONSULT_PATTERNS = re.compile(
    r"(tư vấn|gợi ý|recommend|suggest|"
    r"nên mua máy nào|chọn máy nào|"
    r"máy nào tốt|máy nào đáng mua|"
    r"trong tầm giá|budget|dưới \d+|trên \d+|"
    r"\d+\s*(triệu|tr|m)|"
    r"máy nào phù hợp|phù hợp với|"
    r"máy nào chơi game|máy chụp ảnh đẹp|máy pin trâu|"
    r"dùng lâu|bền|đáng tiền)",
    re.IGNORECASE,
)

CONSULT_PATTERNS_NORM = re.compile(
    r"(tu van|goi y|recommend|suggest|"
    r"nen mua may nao|chon may nao|"
    r"may nao tot|may nao dang mua|"
    r"trong tam gia|budget|duoi \d+|tren \d+|"
    r"\d+\s*(trieu|tr|m)|"
    r"may nao phu hop|phu hop voi|"
    r"may nao choi game|may chup anh dep|may pin trau|"
    r"dung lau|ben|dang tien|tv dum|tv giup)",
    re.IGNORECASE,
)

ORDER_PATTERNS = re.compile(
    r"(đơn hàng|mã đơn|order|kiểm tra đơn|"
    r"tra cứu đơn|tracking|đơn của tôi|"
    r"đơn của mình|giao tới đâu rồi|"
    r"đơn tới đâu|bao giờ giao|khi nào nhận)",
    re.IGNORECASE,
)

ORDER_PATTERNS_NORM = re.compile(
    r"(don hang|ma don|order|kiem tra don|"
    r"tra cuu don|check don|tracking|don cua toi|"
    r"don cua minh|don cua t|giao toi dau roi|"
    r"don toi dau|ship toi dau|bao gio giao|khi nao nhan|"
    r"ma van don)",
    re.IGNORECASE,
)

ORDER_CAPABILITY_PATTERNS = re.compile(
    r"((bạn|em|bot).*(có thể|giúp).*(tra cứu|kiểm tra).*(đơn hàng|mã đơn).*(không|hay không|được không))|"
    r"((hỗ trợ|giúp).*(tra cứu|kiểm tra|tra đơn|tra đơn hàng).*(không|hay không|được không))|"
    r"((tra cứu|kiểm tra|tra đơn).*(đơn hàng|mã đơn).*(được không|hay không|không))",
    re.IGNORECASE,
)

ORDER_CAPABILITY_PATTERNS_NORM = re.compile(
    r"((ban|em|bot).*(co the|giup|ho tro).*(tra cuu|kiem tra|check).*(don|ma don|don hang).*(duoc khong|hay khong|khong)?)|"
    r"((ho tro|giup).*(tra cuu|kiem tra|check|tra don|tra don hang).*(duoc khong|hay khong|khong))|"
    r"((tra cuu|kiem tra|check|tra don).*(don|ma don|don hang).*(duoc khong|hay khong|khong))|"
    r"(giup.*(tra cuu|kiem tra).*(don|ma don).*(duoc khong|khong|hay khong))",
    re.IGNORECASE,
)

ORDER_CODE_PATTERN = re.compile(r"\b(QH\d{6,}|QHUN\d+)\b", re.IGNORECASE)

# Session keys (multi-turn)
PENDING_COMPARE_KEY = "qh_chatbot_pending_compare"
PENDING_COMPARE_TTL_SEC = 10 * 60
FOCUSED_PRODUCT_KEY = "qh_chatbot_focused_product"
FOCUSED_PRODUCT_TTL_SEC = 60 * 60

INSTALLMENT_PATTERNS = re.compile(
    r"(trả góp|trả góp 0%|trả góp không lãi|"
    r"mua trả góp|trả trước bao nhiêu|"
    r"góp mỗi tháng bao nhiêu|"
    r"hỗ trợ trả góp|có trả góp|góp được không|"
    r"mua góp|chia kỳ|thanh toán góp)",
    re.IGNORECASE,
)

INSTALLMENT_PATTERNS_NORM = re.compile(
    r"(tra gop|tra gop 0|tra gop khong lai|"
    r"mua tra gop|tra truoc bao nhieu|"
    r"gop moi thang bao nhieu|"
    r"ho tro tra gop|co tra gop|gop duoc khong|"
    r"mua gop|chia ky|thanh toan gop)",
    re.IGNORECASE,
)

WARRANTY_PATTERNS = re.compile(
    r"(bảo hành bao lâu|bảo hành mấy tháng|"
    r"bảo hành chính hãng không|bảo hành ở đâu|"
    r"đổi trả|chính sách bảo hành|"
    r"bảo hành|warranty|đổi máy|trả máy|"
    r"lỗi thì sao|hư thì sao|bể màn)",
    re.IGNORECASE,
)

WARRANTY_PATTERNS_NORM = re.compile(
    r"(bao hanh bao lau|bao hanh may thang|"
    r"bao hanh chinh hang khong|bao hanh o dau|"
    r"doi tra|chinh sach bao hanh|"
    r"bao hanh|warranty|doi may|tra may|"
    r"loi thi sao|hu thi sao|be man)",
    re.IGNORECASE,
)

STAFF_PATTERNS = re.compile(
    r"(gặp nhân viên|người thật|"
    r"nói chuyện với người|gặp tư vấn viên|"
    r"kết nối nhân viên|chuyển nhân viên|"
    r"gọi nhân viên|cần người hỗ trợ)",
    re.IGNORECASE,
)

STAFF_PATTERNS_NORM = re.compile(
    r"(gap nhan vien|nguoi that|"
    r"noi chuyen voi nguoi|gap tu van vien|"
    r"ket noi nhan vien|chuyen nhan vien|"
    r"goi nhan vien|can nguoi ho tro|"
    r"noi chuyen admin|gap ad)",
    re.IGNORECASE,
)

IDENTITY_PATTERNS = re.compile(
    r"(bạn là ai|em là ai|bot là ai|ai vậy|"
    r"giới thiệu về bạn|giới thiệu về em|"
    r"tên bạn là gì|tên em là gì|"
    r"bạn là bot gì|em là bot gì|"
    r"bạn làm được gì|em làm được gì)",
    re.IGNORECASE,
)

IDENTITY_PATTERNS_NORM = re.compile(
    r"(ban la ai|em la ai|bot la ai|ai vay|"
    r"gioi thieu ve ban|gioi thieu ve em|"
    r"ten ban la gi|ten em la gi|"
    r"ban la bot gi|em la bot gi|"
    r"ban lam duoc gi|em lam duoc gi)",
    re.IGNORECASE,
)

PRODUCT_NAME_PATTERNS = re.compile(
    r"(iphone|\bip\b|\bip\s*\d{1,2}\b|\bip\d{1,2}\b|samsung|xiaomi|oppo|vivo|realme|huawei|nokia|pixel|"
    r"galaxy|redmi|note|pro|ultra|plus|max|lite|se|mini|air|fold|flip)",
    re.IGNORECASE,
)

PRODUCT_NAME_PATTERNS_NORM = re.compile(
    r"(iphone|\bip\b|\bip\s*\d{1,2}\b|\bip\d{1,2}\b|samsung|xiaomi|oppo|vivo|realme|huawei|nokia|pixel|"
    r"galaxy|redmi|note|pro|max|plus|ultra|lite|se|mini|air|fold|flip)",
    re.IGNORECASE,
)

# ════════════════════════════════════════════════════════════════
# UTILS
# ════════════════════════════════════════════════════════════════

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SKU_PREFIX_RE = re.compile(r"^[A-Z0-9]{4,8}\s*-\s*", re.IGNORECASE)


def _normalize_text(value: str) -> str:
    """Normalize Vietnamese + common shorthand/typos for product matching."""
    text = (value or "").lower().strip()

    replacements = {
        "preomax": "pro max",
        "promax": "pro max",
        "promaxx": "pro max",
        "prm": "pro max",
        "ip16": "iphone 16",
        "ip15": "iphone 15",
        "ip14": "iphone 14",
        "ip13": "iphone 13",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    # Common shorthand/teencode normalization to improve intent understanding.
    text = re.sub(r"\b(k|ko|kh|hk|hok|hong)\b", "khong", text)
    text = re.sub(r"\b(dc|đc|dk|đk)\b", "duoc", text)
    text = re.sub(r"\b(ko?z)\b", "khong", text)
    text = re.sub(r"\b(sp)\b", "san pham", text)
    text = re.sub(r"\b(dt|đt)\b", "dien thoai", text)
    text = re.sub(r"\b(bn)\b", "bao nhieu", text)
    text = re.sub(r"\b(tui|toi|t)\b", "toi", text)

    # Handle shorthand like: ip6, ip 6, ip6pm, ip 17 promax
    text = re.sub(r"\bip\s*(\d{1,2})\b", r"iphone \1", text)
    text = re.sub(r"\bip(\d{1,2})\b", r"iphone \1", text)
    text = re.sub(r"\biphone\s*(\d{1,2})\s*pm\b", r"iphone \1 pro max", text)
    text = re.sub(r"\biphone\s*(\d{1,2})\s*promax\b", r"iphone \1 pro max", text)

    text = re.sub(r"\bip\b", "iphone", text)

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _format_price(value) -> str:
    try:
        v = int(value)
        if v <= 0:
            return None
        return f"{v:,}₫".replace(",", ".")
    except (TypeError, ValueError):
        return None


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def _clean_color_name(raw: str) -> str:
    return _SKU_PREFIX_RE.sub("", raw).strip()


def _get_product_price_range(product: Product) -> tuple:
    """Return (min_price_str, max_price_str) from variants, or product.price."""
    try:
        variants = product.detail.variants.all()
        prices = [v.price for v in variants if v.price and v.price > 0]
        if prices:
            return _format_price(min(prices)), _format_price(max(prices))
    except Exception:
        pass
    p = _format_price(product.price)
    return p, p


def _get_product_colors(product: Product) -> list[str]:
    try:
        variants = product.detail.variants.all()
        return list(dict.fromkeys(_clean_color_name(v.color_name) for v in variants))
    except Exception:
        return []


def _get_product_storages(product: Product) -> list[str]:
    try:
        variants = product.detail.variants.all()
        return list(dict.fromkeys(v.storage for v in variants if v.storage))
    except Exception:
        return []


def _get_storage_prices(product: Product) -> dict:
    try:
        variants = product.detail.variants.all()
        sp = {}
        for v in variants:
            if v.storage and v.price and v.price > 0 and v.storage not in sp:
                sp[v.storage] = v.price
        return sp
    except Exception:
        return {}


def _get_min_numeric_price(product: Product) -> int:
    """Lấy giá nhỏ nhất dạng số để lọc/tối ưu tư vấn theo ngân sách."""
    try:
        variants = product.detail.variants.all()
        prices = [int(v.price) for v in variants if v.price and int(v.price) > 0]
        if prices:
            return min(prices)
    except Exception:
        pass

    try:
        p = int(product.price or 0)
        return p if p > 0 else 0
    except Exception:
        return 0


def _parse_spec_json(spec_json) -> list[str]:
    if not spec_json:
        return []
    data = spec_json if isinstance(spec_json, (dict, list)) else json.loads(spec_json)

    lines = []
    groups = data.get("groups", data) if isinstance(data, dict) else data

    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict) and "items" in group:
                for item in group["items"]:
                    label = item.get("label", "")
                    value = item.get("value", "")
                    if label and value:
                        lines.append(f"  - {label}: {value.replace(chr(10), ', ')}")
            elif isinstance(group, dict):
                for k, v in group.items():
                    lines.append(f"  - {k}: {v}")
    elif isinstance(groups, dict):
        for k, v in groups.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    lines.append(f"  - {sk}: {sv}")
            else:
                lines.append(f"  - {k}: {v}")

    return lines[:35]


def _extract_prices_from_text(text: str) -> list[int]:
    """Tách các mốc giá xuất hiện trong câu trả lời để kiểm tra ràng buộc ngân sách."""
    if not text:
        return []

    prices: list[int] = []

    dong_matches = re.findall(r"(\d{1,3}(?:[\.,]\d{3})+)\s*₫", text)
    for value in dong_matches:
        num = re.sub(r"[^\d]", "", value)
        if num.isdigit():
            prices.append(int(num))

    million_matches = re.findall(r"(\d+(?:[\.,]\d+)?)\s*(triệu|tr|m)\b", text.lower())
    for raw_value, _ in million_matches:
        try:
            prices.append(int(float(raw_value.replace(",", ".")) * 1_000_000))
        except ValueError:
            continue

    return prices


def _normalize_image_path(path: str) -> str | None:
    raw = (path or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return raw if raw.startswith("/") else f"/{raw}"


# ════════════════════════════════════════════════════════════════
# CHATBOT SERVICE
# ════════════════════════════════════════════════════════════════

class ChatbotService:

    def __init__(self):
        self.claude = ClaudeService()

    # ── Intent detection (thứ tự quan trọng!) ───────────────────
    def detect_intent(self, message: str) -> str:
        msg = message.strip()
        msg_norm = _normalize_text(msg)

        def matched(raw_pat, norm_pat) -> bool:
            return bool(raw_pat.search(msg) or norm_pat.search(msg_norm))

        if matched(ORDER_CAPABILITY_PATTERNS, ORDER_CAPABILITY_PATTERNS_NORM):
            return "order_capability"

        if matched(ORDER_PATTERNS, ORDER_PATTERNS_NORM) or ORDER_CODE_PATTERN.search(msg):
            return "order"

        if matched(LIST_PRODUCT_PATTERNS, LIST_PRODUCT_PATTERNS_NORM):
            return "list_products"

        if matched(COMPARE_PATTERNS, COMPARE_PATTERNS_NORM):
            return "compare"

        if matched(CONSULT_PATTERNS, CONSULT_PATTERNS_NORM):
            return "consult"

        if matched(SPEC_PATTERNS, SPEC_PATTERNS_NORM):
            return "spec"

        if matched(PRICE_PATTERNS, PRICE_PATTERNS_NORM):
            return "price"

        if matched(STOCK_PATTERNS, STOCK_PATTERNS_NORM):
            return "stock"

        if matched(VARIANT_PATTERNS, VARIANT_PATTERNS_NORM):
            return "variant"

        if matched(INSTALLMENT_PATTERNS, INSTALLMENT_PATTERNS_NORM):
            return "installment"

        if matched(WARRANTY_PATTERNS, WARRANTY_PATTERNS_NORM):
            return "warranty"

        if matched(STAFF_PATTERNS, STAFF_PATTERNS_NORM):
            return "staff"

        if matched(IDENTITY_PATTERNS, IDENTITY_PATTERNS_NORM):
            return "identity"

        if matched(GREETING_PATTERNS, GREETING_PATTERNS_NORM):
            return "greeting"

        if PRODUCT_NAME_PATTERNS.search(msg) or PRODUCT_NAME_PATTERNS_NORM.search(msg_norm):
            return "product_mention"

        return "unknown"

    # ── Product name detection ──────────────────────────────────
    def detect_product_names(self, message: str) -> list[str]:
        products = list(Product.objects.filter(is_active=True).values_list("name", flat=True))
        if not products:
            return []

        msg_norm = _normalize_text(message)
        msg_tokens = set(re.findall(r"[a-z0-9]+", msg_norm))
        scored: list[tuple[str, float]] = []

        for name in products:
            name_norm = _normalize_text(name)
            if not name_norm:
                continue

            name_tokens = set(re.findall(r"[a-z0-9]+", name_norm))
            overlap = len(msg_tokens & name_tokens)
            token_ratio = overlap / max(1, len(name_tokens))
            text_ratio = SequenceMatcher(None, msg_norm, name_norm).ratio()

            score = (token_ratio * 0.8) + (text_ratio * 0.2)
            if name_norm in msg_norm:
                score += 1.2

            if overlap > 0 or text_ratio >= 0.55 or name_norm in msg_norm:
                scored.append((name, score))

        if not scored:
            return []

        scored.sort(key=lambda item: item[1], reverse=True)
        top_score = scored[0][1]
        # Lower threshold a bit to better catch shorthand mentions such as "ip6", "ip 17pm".
        threshold = max(0.52, top_score - 0.25)
        top_matches = [name for name, score in scored if score >= threshold][:3]
        return top_matches

    def _fuzzy_match(self, msg_lower: str, product_names) -> list[str]:
        # Tokenize into single-word tokens (previous pattern produced multi-word tokens → poor matching)
        tokens = re.findall(r"[a-zA-Z0-9]+", msg_lower)
        candidates: list[tuple[str, int]] = []
        for name in product_names:
            name_lower = name.lower()
            name_tokens = set(re.findall(r"[a-zA-Z0-9]+", name_lower))
            match_count = sum(1 for t in tokens if t in name_tokens or any(t in nt for nt in name_tokens))
            if match_count >= 2 or (len(name_tokens) == 1 and match_count >= 1 and len(tokens) <= 3):
                candidates.append((name, match_count))
        candidates.sort(key=lambda x: -x[1])
        return [c[0] for c in candidates[:3]]

    def _get_pending_compare_base(self, session) -> str | None:
        if not session:
            return None
        try:
            data = session.get(PENDING_COMPARE_KEY)
            if not isinstance(data, dict):
                return None
            base = (data.get("base") or "").strip()
            ts = float(data.get("ts") or 0)
            if not base:
                return None
            if not ts or (time.time() - ts) > PENDING_COMPARE_TTL_SEC:
                session.pop(PENDING_COMPARE_KEY, None)
                return None
            return base
        except Exception:
            return None

    def _set_pending_compare_base(self, session, base_name: str) -> None:
        if not session:
            return
        try:
            session[PENDING_COMPARE_KEY] = {"base": base_name, "ts": time.time()}
            session.modified = True
        except Exception:
            pass

    def _clear_pending_compare(self, session) -> None:
        if not session:
            return
        try:
            session.pop(PENDING_COMPARE_KEY, None)
            session.modified = True
        except Exception:
            pass

    def _get_focused_product(self, session) -> str | None:
        if not session:
            return None
        try:
            data = session.get(FOCUSED_PRODUCT_KEY)
            if not isinstance(data, dict):
                return None
            product_name = (data.get("name") or "").strip()
            ts = float(data.get("ts") or 0)
            if not product_name:
                return None
            if not ts or (time.time() - ts) > FOCUSED_PRODUCT_TTL_SEC:
                session.pop(FOCUSED_PRODUCT_KEY, None)
                return None
            return product_name
        except Exception:
            return None

    def _set_focused_product(self, session, product_name: str) -> None:
        if not session:
            return
        try:
            session[FOCUSED_PRODUCT_KEY] = {"name": product_name, "ts": time.time()}
            session.modified = True
        except Exception:
            pass

    def _clear_focused_product(self, session) -> None:
        if not session:
            return
        try:
            session.pop(FOCUSED_PRODUCT_KEY, None)
            session.modified = True
        except Exception:
            pass

    def reset_conversation(self, session) -> None:
        self._clear_pending_compare(session)
        self._clear_focused_product(session)

    # ── Build product context for Claude ────────────────────────
    def _build_product_context(self, product: Product) -> str:
        parts = [f"San pham: {product.name}"]

        if product.stock > 0:
            parts.append("Tinh trang: CON HANG")
        else:
            parts.append("Tinh trang: HET HANG")

        try:
            detail = product.detail

            if detail.description:
                desc = _strip_html(detail.description[:400])
                if desc:
                    parts.append(f"Mo ta: {desc}")

            variants = detail.variants.all()
            if variants.exists():
                prices = [v.price for v in variants if v.price and v.price > 0]
                if prices:
                    min_p = _format_price(min(prices))
                    max_p = _format_price(max(prices))
                    if min_p and max_p and min_p != max_p:
                        parts.append(f"Gia: tu {min_p} den {max_p}")
                    elif min_p:
                        parts.append(f"Gia: {min_p}")

                colors = list(dict.fromkeys(_clean_color_name(v.color_name) for v in variants))
                if colors:
                    parts.append(f"Mau sac: {', '.join(colors)}")

                storages = list(dict.fromkeys(v.storage for v in variants if v.storage))
                if storages:
                    parts.append(f"Dung luong: {', '.join(storages)}")

                storage_prices = {}
                for v in variants:
                    if v.storage and v.price and v.price > 0 and v.storage not in storage_prices:
                        storage_prices[v.storage] = v.price
                if storage_prices:
                    price_lines = [f"  - {s}: {_format_price(p)}" for s, p in storage_prices.items() if _format_price(p)]
                    if price_lines:
                        parts.append("Gia theo dung luong:\n" + "\n".join(price_lines))
            else:
                p_price = _format_price(product.price)
                if p_price:
                    parts.append(f"Gia: {p_price}")
                if product.original_price and product.original_price > product.price:
                    op = _format_price(product.original_price)
                    if op:
                        parts.append(f"Gia goc: {op} (giam {product.get_discount_percent()}%)")

            try:
                spec = detail.specification
                if spec.spec_json:
                    spec_lines = _parse_spec_json(spec.spec_json)
                    if spec_lines:
                        parts.append("Thong so ky thuat:\n" + "\n".join(spec_lines))
            except ProductSpecification.DoesNotExist:
                pass

        except ProductDetail.DoesNotExist:
            p_price = _format_price(product.price)
            if p_price:
                parts.append(f"Gia: {p_price}")

        contents = ProductContent.objects.filter(product=product).values_list("content_text", flat=True)[:2]
        for ct in contents:
            if ct:
                clean = _strip_html(ct[:300])
                if clean:
                    parts.append(f"Noi dung: {clean}")

        return "\n".join(parts)

    def _build_product_cards(self, products: list[Product], limit: int = 4) -> list[dict[str, str]]:
        cards: list[dict[str, str]] = []
        seen: set[str] = set()

        for product in products[:limit]:
            if not product:
                continue

            image_url = None
            try:
                if getattr(product, "image", None):
                    image_url = _normalize_image_path(product.image.url)
            except Exception:
                image_url = None

            if not image_url:
                continue

            key = f"{product.id}|{image_url}"
            if key in seen:
                continue
            seen.add(key)

            min_p, _ = _get_product_price_range(product)
            tag_parts = []
            if product.is_featured:
                tag_parts.append("Nổi bật")

            subtitle = min_p or "Liên hệ"
            if tag_parts:
                subtitle = f"{subtitle} | {' • '.join(tag_parts)}"
            cards.append({
                "title": product.name,
                "image_url": image_url,
                "subtitle": subtitle,
            })

        return cards

    def _products_mentioned_in_reply(self, reply_text: str, candidates: list[Product]) -> list[Product]:
        """Lấy các sản phẩm trong candidates được nhắc trực tiếp trong reply_text."""
        if not reply_text or not candidates:
            return []

        reply_norm = _normalize_text(reply_text)
        matches: list[tuple[int, Product]] = []

        for product in candidates:
            name_norm = _normalize_text(product.name)
            if not name_norm:
                continue
            idx = reply_norm.find(name_norm)
            if idx >= 0:
                matches.append((idx, product))

        matches.sort(key=lambda x: x[0])
        return [product for _, product in matches]

    # ════════════════════════════════════════════════════════════
    # HANDLERS (không gọi Claude)
    # ════════════════════════════════════════════════════════════

    def _handle_greeting(self) -> dict[str, Any]:
        return {
            "message": "Chào anh/chị! Em là trợ lý mua sắm của QHUN22. Em có thể giúp gì cho anh/chị?",
            "suggestions": MENU_SUGGESTIONS,
        }

    def _handle_identity(self) -> dict[str, Any]:
        return {
            "message": "Em là trợ lý nhỏ của hệ thống QHUN22. Em có thể hỗ trợ anh/chị tư vấn chọn máy, so sánh sản phẩm, kiểm tra đơn hàng hoặc kết nối nhân viên khi cần ạ.",
            "suggestions": MENU_SUGGESTIONS,
        }

    def _handle_staff(self) -> dict[str, Any]:
        return {"message": STAFF_MSG, "suggestions": ["Tư vấn chọn máy", "So sánh sản phẩm"]}

    def _handle_installment(self) -> dict[str, Any]:
        return {"message": INSTALLMENT_MSG, "suggestions": ["Tư vấn chọn máy", "Gặp nhân viên"]}

    def _handle_warranty(self) -> dict[str, Any]:
        return {"message": WARRANTY_MSG, "suggestions": MENU_SUGGESTIONS}

    def _handle_list_products(self) -> dict[str, Any]:
        products = Product.objects.filter(is_active=True).order_by("name")
        if not products.exists():
            return {"message": "Hiện tại shop chưa có sản phẩm nào. Anh/chị quay lại sau nhé!", "suggestions": []}

        lines = ["QHUN22 hiện đang kinh doanh các sản phẩm sau:"]
        for p in products:
            min_p, max_p = _get_product_price_range(p)
            price_txt = f"từ {min_p}" if min_p else "Liên hệ"
            lines.append(f"  - {p.name} / {price_txt}")
        lines.append("\nAnh/chị muốn tìm hiểu sản phẩm nào, cứ hỏi em nhé!")
        product_list = list(products)
        return {
            "message": "\n".join(lines),
            "suggestions": [p.name for p in product_list[:4]],
            "product_cards": self._build_product_cards(product_list, limit=4),
        }

    def _handle_new_products(self) -> dict[str, Any]:
        featured = list(Product.objects.filter(is_active=True, stock__gt=0, is_featured=True).order_by("-updated_at")[:8])
        latest = list(Product.objects.filter(is_active=True, stock__gt=0).order_by("-created_at")[:24])

        pool = featured + [p for p in latest if p.id not in {f.id for f in featured}]
        if not pool:
            return {"message": "Hiện tại shop chưa có sản phẩm mới để gợi ý. Anh/chị quay lại sau nhé!", "suggestions": []}

        random.shuffle(pool)
        picked = pool[:4]

        lines = ["Em gợi ý nhanh một số sản phẩm mới/nổi bật cho anh/chị:"]
        for p in picked:
            min_p, _ = _get_product_price_range(p)
            badges = []
            if p.is_featured:
                badges.append("Nổi bật")
            badge_suffix = f" ({', '.join(badges)})" if badges else ""
            lines.append(f"  - {p.name} / từ {min_p or 'Liên hệ'}{badge_suffix}")
        lines.append("\nAnh/chị muốn em tư vấn theo nhu cầu học tập, game hay camera luôn không?")

        return {
            "message": "\n".join(lines),
            "suggestions": [p.name for p in picked[:3]],
            "product_cards": self._build_product_cards(picked, limit=4),
            "source": "rule",
        }

    def _handle_price(self, product: Product) -> dict[str, Any]:
        min_p, max_p = _get_product_price_range(product)
        storage_prices = _get_storage_prices(product)

        if storage_prices:
            lines = [f"{product.name} hiện có giá như sau:"]
            for storage, price in storage_prices.items():
                lines.append(f"  - Bản {storage}: {_format_price(price)}")
            msg = "\n".join(lines)
        elif min_p and max_p and min_p != max_p:
            msg = f"{product.name} có giá từ {min_p} đến {max_p}, tùy theo dung lượng anh/chị chọn."
        elif min_p:
            msg = f"{product.name} hiện có giá {min_p}."
        else:
            msg = f"Em chưa có thông tin giá của {product.name}, anh/chị liên hệ hotline để được hỗ trợ nhé!"

        return {
            "message": msg,
            "suggestions": [f"Thông số {product.name}", f"Còn hàng {product.name}", "So sánh sản phẩm"],
            "product_cards": self._build_product_cards([product], limit=1),
        }

    def _handle_stock(self, product: Product) -> dict[str, Any]:
        if product.stock > 0:
            colors = _get_product_colors(product)
            storages = _get_product_storages(product)
            lines = [f"{product.name} hiện đang còn hàng."]
            if colors:
                lines.append(f"Màu có sẵn: {', '.join(colors)}.")
            if storages:
                lines.append(f"Dung lượng: {', '.join(storages)}.")
            lines.append("Anh/chị muốn đặt mua luôn không?")
            msg = "\n".join(lines)
        else:
            msg = f"{product.name} hiện tạm hết hàng. Anh/chị để lại thông tin, em sẽ thông báo khi có hàng trở lại nhé!"

        return {
            "message": msg,
            "suggestions": [f"Giá {product.name}", "Tư vấn mẫu khác", "Gặp nhân viên"],
            "product_cards": self._build_product_cards([product], limit=1),
        }

    def _handle_variant(self, product: Product) -> dict[str, Any]:
        colors = _get_product_colors(product)
        storages = _get_product_storages(product)
        storage_prices = _get_storage_prices(product)

        lines = [f"{product.name} hiện có:"]
        if colors:
            lines.append(f"Màu sắc: {', '.join(colors)}.")
        if storages and storage_prices:
            sp_lines = []
            for s in storages:
                p = storage_prices.get(s)
                sp_lines.append(f"  - {s}: {_format_price(p)}" if p and _format_price(p) else f"  - {s}")
            lines.append("Dung lượng và giá:\n" + "\n".join(sp_lines))
        elif storages:
            lines.append(f"Dung lượng: {', '.join(storages)}.")

        if not colors and not storages:
            lines = [f"Em chưa có thông tin chi tiết phiên bản của {product.name}, anh/chị liên hệ hotline nhé!"]

        return {
            "message": "\n".join(lines),
            "suggestions": [f"Thông số {product.name}", f"Giá {product.name}", "So sánh sản phẩm"],
            "product_cards": self._build_product_cards([product], limit=1),
        }

    def _handle_order(self, message: str, user) -> dict[str, Any]:
        def build_order_cards(order: Order) -> list[dict[str, str]]:
            items = OrderItem.objects.filter(order=order).select_related("product")[:4]
            cards: list[dict[str, str]] = []
            seen_keys: set[str] = set()

            for item in items:
                image_url = _normalize_image_path(item.thumbnail)
                if not image_url and item.product and getattr(item.product, "image", None):
                    try:
                        image_url = _normalize_image_path(item.product.image.url)
                    except Exception:
                        image_url = None

                if not image_url:
                    continue

                key = f"{item.product_name}|{image_url}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                meta_parts = []
                if item.color_name:
                    meta_parts.append(item.color_name)
                if item.storage:
                    meta_parts.append(item.storage)
                meta_parts.append(f"SL: {item.quantity}")

                cards.append({
                    "title": item.product_name,
                    "image_url": image_url,
                    "subtitle": " | ".join(meta_parts),
                })

            return cards

        code_match = ORDER_CODE_PATTERN.search(message)
        if code_match:
            order_code = code_match.group(1).upper()
            try:
                order = Order.objects.get(order_code=order_code)
                status_map = dict(Order.STATUS_CHOICES)
                status_vn = status_map.get(order.status, order.status)
                msg = (
                    f"Đơn hàng {order.order_code}\n"
                    f"Trạng thái: {status_vn}\n"
                    f"Tổng tiền: {_format_price(order.total_amount) or '0₫'}\n"
                    f"Phương thức TT: {order.get_payment_method_display()}\n"
                    f"Ngày đặt: {timezone.localtime(order.created_at).strftime('%d/%m/%Y %H:%M')}"
                )
                return {
                    "message": msg,
                    "suggestions": ["Xem sản phẩm mới", "Tư vấn chọn máy"],
                    "product_cards": build_order_cards(order),
                }
            except Order.DoesNotExist:
                return {
                    "message": f"Em không tìm thấy đơn hàng {order_code}. Anh/chị kiểm tra lại mã nhé!",
                    "suggestions": ["Kiểm tra đơn hàng khác", "Gặp nhân viên"],
                }

        if user and user.is_authenticated:
            recent = Order.objects.filter(user=user).order_by("-created_at")[:3]
            if recent.exists():
                status_map = dict(Order.STATUS_CHOICES)
                lines = ["Đơn hàng gần đây của anh/chị:"]
                for o in recent:
                    lines.append(f"  - {o.order_code} / {status_map.get(o.status, o.status)} / {_format_price(o.total_amount) or '0₫'}")
                return {"message": "\n".join(lines), "suggestions": ["Xem chi tiết đơn hàng"]}

        return {
            "message": "Anh/chị cho em mã đơn hàng (VD: QH250101 hoặc QHUN38453) để em tra cứu nhé!",
            "suggestions": ["Tư vấn chọn máy", "Gặp nhân viên"],
        }

    def _handle_order_capability(self) -> dict[str, Any]:
        return {
            "message": "Dạ có ạ. Em có thể hỗ trợ anh/chị tra cứu đơn hàng. Anh/chị gửi giúp em mã đơn (VD: QH250101 hoặc QHUN38453) để em kiểm tra ngay nhé!",
            "suggestions": ["Kiểm tra đơn hàng", "Gặp nhân viên"],
        }

    def _extract_budget(self, message: str) -> tuple[int | None, str | None]:
        """Tách ngân sách từ câu chat: trả về (số tiền VND, kiểu ràng buộc)."""
        msg = (message or "").lower()
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(triệu|tr|m)\b", msg)
        if not match:
            return None, None

        raw_value = match.group(1).replace(",", ".")
        try:
            budget = int(float(raw_value) * 1_000_000)
        except ValueError:
            return None, None

        if re.search(r"\b(tren|hơn|tu\s*\d+)\b", _normalize_text(msg)):
            return budget, "min"
        if re.search(r"\b(duoi|toi da|khong qua|tam|khoang|trong tam)\b", _normalize_text(msg)):
            return budget, "max"
        return budget, "max"

    def _pick_products_by_budget(self, budget: int, budget_mode: str, limit: int = 5) -> list[Product]:
        """Lọc sản phẩm bằng giá thấp nhất thực tế (ưu tiên không vượt ngân sách)."""
        all_products = list(Product.objects.filter(is_active=True, stock__gt=0))
        priced_items: list[tuple[Product, int]] = []
        for product in all_products:
            min_price = _get_min_numeric_price(product)
            if min_price > 0:
                priced_items.append((product, min_price))

        if not priced_items:
            return []

        if budget_mode == "min":
            filtered = [(p, mp) for p, mp in priced_items if mp >= budget]
            filtered.sort(key=lambda item: item[1])
        else:
            filtered = [(p, mp) for p, mp in priced_items if mp <= budget]
            filtered.sort(key=lambda item: item[1], reverse=True)

        return [p for p, _ in filtered[:limit]]

    def _build_consult_list_message(self, products: list[Product], title: str) -> str:
        lines = [title]
        for p in products:
            min_p, _ = _get_product_price_range(p)
            lines.append(f"  - {p.name} / từ {min_p or 'Liên hệ'}")
        lines.append("\nAnh/chị quan tâm mẫu nào, hỏi em thêm nhé!")
        return "\n".join(lines)

    def _handle_consult(self, message: str) -> dict[str, Any]:
        budget, budget_mode = self._extract_budget(message)
        if budget and budget_mode:
            featured = self._pick_products_by_budget(budget, budget_mode, limit=5)

            if featured:
                contexts = [self._build_product_context(p) for p in featured]
                combined_context = "\n\n---\n\n".join(contexts)
                budget_note = (
                    "Chỉ đề xuất sản phẩm có giá KHÔNG VƯỢT ngân sách khách nêu."
                    if budget_mode == "max"
                    else "Chỉ đề xuất sản phẩm có giá TỪ mức ngân sách khách nêu trở lên."
                )
                user_prompt = (
                    f"DỮ LIỆU SẢN PHẨM:\n{combined_context}\n\n"
                    f"YÊU CẦU KHÁCH: \"{message}\"\n"
                    f"RÀNG BUỘC: {budget_note}\n"
                    "CHỈ ĐƯỢC nhắc tên sản phẩm có trong DỮ LIỆU SẢN PHẨM, không tự thêm mẫu ngoài danh sách.\n"
                    "Viết ngắn gọn 4-7 dòng, nêu 2-3 lựa chọn phù hợp nhất và lý do theo nhu cầu."
                )

                ai_reply = self.claude.call(SYSTEM_PROMPT, user_prompt, max_tokens=NORMAL_MAX_TOKENS)
                if ai_reply:
                    mentioned_products = self._products_mentioned_in_reply(ai_reply, featured)
                    if budget_mode == "max":
                        mentioned_prices = _extract_prices_from_text(ai_reply)
                        if any(p > budget for p in mentioned_prices):
                            logger.warning("Claude reply vượt ngân sách, chuyển sang fallback an toàn")
                        elif not mentioned_products:
                            logger.warning("Claude reply không khớp danh sách sản phẩm đã cấp, chuyển fallback an toàn")
                        else:
                            return {
                                "message": ai_reply,
                                "suggestions": [p.name for p in featured[:3]],
                                "source": "claude",
                                "product_cards": self._build_product_cards(mentioned_products, limit=4),
                            }
                    else:
                        if not mentioned_products:
                            logger.warning("Claude reply không khớp danh sách sản phẩm đã cấp, chuyển fallback an toàn")
                        else:
                            return {
                                "message": ai_reply,
                                "suggestions": [p.name for p in featured[:3]],
                                "source": "claude",
                                "product_cards": self._build_product_cards(mentioned_products, limit=4),
                            }

                if budget_mode == "max":
                    title = f"Trong khoảng {budget // 1_000_000} triệu (không vượt ngân sách), em gợi ý:"
                else:
                    title = f"Từ mức {budget // 1_000_000} triệu trở lên, em gợi ý:"
                return {
                    "message": self._build_consult_list_message(featured, title),
                    "suggestions": [p.name for p in featured[:3]],
                    "source": "rule_fallback",
                    "product_cards": self._build_product_cards(featured, limit=4),
                }

            if budget_mode == "max":
                return {
                    "message": "Hiện chưa có mẫu nào nằm trong mức ngân sách này. Anh/chị muốn em gợi ý mức gần nhất phía trên không ạ?",
                    "suggestions": ["Tư vấn mẫu gần giá", "Gặp nhân viên"],
                    "source": "rule",
                }

        featured = Product.objects.filter(is_active=True, is_featured=True).order_by("-updated_at")[:5]
        if not featured.exists():
            featured = Product.objects.filter(is_active=True, stock__gt=0).order_by("-updated_at")[:5]

        if featured.exists():
            featured_list = list(featured)
            contexts = [self._build_product_context(p) for p in featured_list]
            combined_context = "\n\n---\n\n".join(contexts)
            user_prompt = (
                f"DỮ LIỆU SẢN PHẨM:\n{combined_context}\n\n"
                f"YÊU CẦU KHÁCH: \"{message}\"\n"
                "CHỈ ĐƯỢC nhắc tên sản phẩm có trong DỮ LIỆU SẢN PHẨM, không tự thêm mẫu ngoài danh sách.\n"
                "Hãy gợi ý 2-3 mẫu phù hợp nhất theo nhu cầu khách, giải thích ngắn gọn từng mẫu."
            )
            ai_reply = self.claude.call(SYSTEM_PROMPT, user_prompt, max_tokens=NORMAL_MAX_TOKENS)
            if ai_reply:
                mentioned_products = self._products_mentioned_in_reply(ai_reply, featured_list)
                if mentioned_products:
                    return {
                        "message": ai_reply,
                        "suggestions": [p.name for p in featured_list[:3]],
                        "source": "claude",
                        "product_cards": self._build_product_cards(mentioned_products, limit=4),
                    }

                logger.warning("Claude reply không khớp danh sách sản phẩm đã cấp, chuyển fallback an toàn")

            lines = ["Em gợi ý một số mẫu cho anh/chị:"]
            for p in featured_list:
                min_p, _ = _get_product_price_range(p)
                lines.append(f"  - {p.name} / từ {min_p or 'Liên hệ'}")
            lines.append("\nAnh/chị quan tâm mẫu nào, hỏi em thêm nhé!")
            return {
                "message": "\n".join(lines),
                "suggestions": [p.name for p in featured_list[:3]],
                "source": "rule_fallback",
                "product_cards": self._build_product_cards(featured_list, limit=4),
            }

        return {"message": NOT_FOUND_MSG, "suggestions": MENU_SUGGESTIONS, "source": "rule"}

    def _handle_compare_with_ai(self, message: str, products: list[Product]) -> dict[str, Any]:
        contexts = [self._build_product_context(p) for p in products]
        combined = "\n\n---\n\n".join(contexts)

        compare_system = SYSTEM_PROMPT + COMPARE_SYSTEM_EXTRA
        user_prompt = COMPARE_USER_TEMPLATE.format(combined_context=combined, message=message)

        ai_reply = self.claude.call(compare_system, user_prompt, max_tokens=COMPARE_MAX_TOKENS)
        if ai_reply:
            mentioned_products = self._products_mentioned_in_reply(ai_reply, products)
            if mentioned_products:
                return {
                    "message": ai_reply,
                    "suggestions": [p.name for p in products],
                    "product_cards": self._build_product_cards(mentioned_products, limit=4),
                }

            logger.warning("Claude compare reply không khớp cặp sản phẩm, chuyển fallback so sánh nhanh")

        lines = ["So sánh nhanh:"]
        for p in products:
            min_p, _ = _get_product_price_range(p)
            lines.append(f"  - {p.name} / {min_p or 'Liên hệ'}")
        return {
            "message": "\n".join(lines),
            "suggestions": MENU_SUGGESTIONS,
            "product_cards": self._build_product_cards(products, limit=4),
        }

    def _handle_spec_with_ai(self, message: str, product: Product) -> dict[str, Any]:
        context = self._build_product_context(product)
        user_prompt = NORMAL_USER_TEMPLATE.format(context=context, message=message)

        ai_reply = self.claude.call(SYSTEM_PROMPT, user_prompt, max_tokens=NORMAL_MAX_TOKENS)
        if ai_reply:
            return {
                "message": ai_reply,
                "suggestions": [f"Giá {product.name}", f"Còn hàng {product.name}", "So sánh sản phẩm"],
                "product_cards": self._build_product_cards([product], limit=1),
            }

        return self._fallback_product_response(product)

    def _handle_product_with_ai(self, message: str, product: Product) -> dict[str, Any]:
        context = self._build_product_context(product)
        user_prompt = NORMAL_USER_TEMPLATE.format(context=context, message=message)

        ai_reply = self.claude.call(SYSTEM_PROMPT, user_prompt, max_tokens=NORMAL_MAX_TOKENS)
        if ai_reply:
            suggestions = ["Xem thêm sản phẩm", "So sánh sản phẩm"]
            if product.stock <= 0:
                suggestions.insert(0, "Tư vấn mẫu khác")
            return {
                "message": ai_reply,
                "suggestions": suggestions,
                "product_cards": self._build_product_cards([product], limit=1),
            }

        return self._fallback_product_response(product)

    def _fallback_product_response(self, product: Product) -> dict[str, Any]:
        min_p, _ = _get_product_price_range(product)
        msg = (
            f"{product.name}\n"
            f"Giá: {min_p or 'Liên hệ'}"
        )
        return {
            "message": msg,
            "suggestions": MENU_SUGGESTIONS,
            "product_cards": self._build_product_cards([product], limit=1),
        }

    # ════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ════════════════════════════════════════════════════════════

    def process_message(self, message: str, user=None, session=None) -> dict[str, Any]:
        message = message.strip()
        if not message:
            return {"message": MENU_MSG, "suggestions": MENU_SUGGESTIONS}

        # Ưu tiên bắt nhanh nút suggest để không rơi vào nhánh list chung.
        if message == "Xem sản phẩm mới":
            return self._handle_new_products()

        focused_product_name = self._get_focused_product(session)

        # ── Multi-turn compare: if user previously picked base product, and now sends a product name ──
        pending_base = self._get_pending_compare_base(session)
        if pending_base:
            # Try resolve the second product from this message
            target_names = self.detect_product_names(message)
            if target_names:
                base_product = Product.objects.filter(is_active=True, name=pending_base).first()
                target_qs = (
                    Product.objects.filter(is_active=True, name__in=target_names)
                    .exclude(name=pending_base)
                )
                if base_product and target_qs.exists():
                    target_product = max(list(target_qs), key=lambda p: len(p.name))
                    self._clear_pending_compare(session)
                    return self._handle_compare_with_ai(
                        f"So sánh {base_product.name} và {target_product.name}",
                        [base_product, target_product],
                    )
            # If user changes topic (non-compare intent), clear pending compare to avoid sticky state
            intent_now = self.detect_intent(message)
            if intent_now not in ("compare", "unknown"):
                self._clear_pending_compare(session)

        intent = self.detect_intent(message)

        # ── Fixed responses (không gọi Claude) ──────────────────
        if intent == "order_capability":
            return self._handle_order_capability()

        if intent == "order":
            return self._handle_order(message, user)

        if intent == "greeting":
            return self._handle_greeting()

        if intent == "identity":
            return self._handle_identity()

        if intent == "staff":
            return self._handle_staff()

        if intent == "installment":
            return self._handle_installment()

        if intent == "warranty":
            return self._handle_warranty()

        if intent == "list_products":
            return self._handle_list_products()

        # Xử lý nhanh suggestion buttons
        if message.strip() == "Gặp nhân viên":
            return self._handle_staff()
        if message.strip() == "Tư vấn chọn máy":
            return self._handle_consult(message)
        if message.strip() == "Xem sản phẩm mới":
            return self._handle_new_products()
        if message.strip() == "So sánh sản phẩm":
            return {"message": "Anh/chị muốn so sánh 2 sản phẩm nào? VD: so sánh iPhone 17 vs iPhone Air", "suggestions": []}
        if message.strip() == "Kiểm tra đơn hàng":
            return self._handle_order(message, user)

        # ── Detect product names ────────────────────────────────
        product_names = self.detect_product_names(message)

        # Nếu đang có ngữ cảnh sản phẩm trước đó, câu follow-up không nêu tên vẫn giữ mạch hội thoại.
        if not product_names and focused_product_name and intent in ("consult", "spec", "price", "stock", "variant", "product_mention", "unknown"):
            product_names = [focused_product_name]

        # ── Intents cần sản phẩm ────────────────────────────────
        if intent == "consult":
            if product_names:
                products = Product.objects.filter(name__in=product_names, is_active=True)
                if products.exists():
                    product = max(products, key=lambda p: len(p.name))
                    self._set_focused_product(session, product.name)
                    return self._handle_product_with_ai(message, product)
            return self._handle_consult(message)

        if intent == "compare":
            if product_names:
                products = Product.objects.filter(name__in=product_names, is_active=True)
                if products.count() >= 2:
                    return self._handle_compare_with_ai(message, list(products[:2]))
                elif products.count() == 1:
                    # Remember base product for the next user click/answer
                    base_name = products.first().name
                    self._set_pending_compare_base(session, base_name)
                    self._set_focused_product(session, base_name)
                    return {
                        "message": f"Anh/chị muốn so sánh {base_name} với sản phẩm nào?",
                        "suggestions": [p.name for p in Product.objects.filter(is_active=True).exclude(name=base_name)[:3]],
                    }
            return {"message": "Anh/chị muốn so sánh 2 sản phẩm nào? VD: so sánh iPhone 17 vs iPhone Air", "suggestions": []}

        if not product_names:
            if intent == "unknown":
                logger.info("Chatbot unknown intent message: %s", message)
                return {"message": CLARIFY_MSG, "suggestions": MENU_SUGGESTIONS}
            return {"message": NOT_FOUND_MSG, "suggestions": MENU_SUGGESTIONS}

        products = Product.objects.filter(name__in=product_names, is_active=True)
        if not products.exists():
            return {"message": NOT_FOUND_MSG, "suggestions": MENU_SUGGESTIONS}

        ranked_products = {p.name: p for p in products}
        product = ranked_products.get(product_names[0]) or next(iter(ranked_products.values()))
        self._set_focused_product(session, product.name)

        # ── Direct responses (không gọi Claude) ────────────────
        if intent == "price":
            return self._handle_price(product)

        if intent == "stock":
            return self._handle_stock(product)

        if intent == "variant":
            return self._handle_variant(product)

        # ── AI responses (gọi Claude) ──────────────────────────
        if intent == "spec":
            return self._handle_spec_with_ai(message, product)

        return self._handle_product_with_ai(message, product)
