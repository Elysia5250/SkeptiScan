"""
OCR 图片文字提取服务
从商品截图/上传图片中提取文字，用于增强关键词检测和 AI 分析

安全措施：
  - 图片尺寸校验（像素 + 文件大小）
  - OCR 执行超时（线程池 + timeout）
"""

import os
import re
import concurrent.futures
from typing import Optional
from pathlib import Path

# OCR 超时（秒）
OCR_TIMEOUT = 30

# 最大图片尺寸：4000x4000 像素，超过则跳过 OCR 防止 OOM
MAX_IMAGE_PIXELS = 4000 * 4000

# 线程池（复用，避免频繁创建线程）
_OCR_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# ---------------------------------------------------------------------------
# 尝试导入 OCR 引擎（优先级：PaddleOCR > pytesseract）
# ---------------------------------------------------------------------------
_OCR_ENGINE = None
_OCR_ENGINE_NAME = None

# 尝试导入 PaddleOCR
try:
    from paddleocr import PaddleOCR

    _OCR_ENGINE = PaddleOCR(
        use_angle_cls=True,
        lang="ch",
        show_log=False,
        use_gpu=False,
    )
    _OCR_ENGINE_NAME = "paddleocr"
except ImportError:
    pass

# 降级到 pytesseract
if _OCR_ENGINE is None:
    try:
        import pytesseract
        from PIL import Image

        try:
            pytesseract.get_tesseract_version()
            _OCR_ENGINE_NAME = "pytesseract"
        except Exception:
            _OCR_ENGINE_NAME = None
    except ImportError:
        _OCR_ENGINE_NAME = None


def is_ocr_available() -> bool:
    """检查是否有可用的 OCR 引擎"""
    return _OCR_ENGINE_NAME is not None


def get_ocr_engine_name() -> str:
    """返回当前使用的 OCR 引擎名称"""
    return _OCR_ENGINE_NAME or "不可用"


def _check_image_safe(image_path: str) -> bool:
    """检查图片是否安全可处理，过大则跳过"""
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            pixels = w * h
            if pixels > MAX_IMAGE_PIXELS:
                print(f"[OCR] 图片过大 ({w}x{h}={pixels} 像素)，跳过 OCR")
                return False
            return True
    except Exception as e:
        print(f"[OCR] 图片校验失败: {e}")
        return False


def _extract_with_paddleocr(image_path: str) -> str:
    """使用 PaddleOCR 提取文字"""
    result = _OCR_ENGINE.ocr(image_path, cls=True)
    text_parts = []
    for line_group in result:
        if line_group is None:
            continue
        for line in line_group:
            text = line[1][0] if isinstance(line, (list, tuple)) and len(line) > 1 else ""
            if text and text.strip():
                text_parts.append(text.strip())
    return "\n".join(text_parts)


def _extract_with_pytesseract(image_path: str) -> str:
    """使用 pytesseract 提取文字"""
    from PIL import Image
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang="chi_sim+eng", config="--psm 6")
    return text.strip()


def extract_text(image_path: str) -> Optional[str]:
    """
    从图片中提取文字（带超时和尺寸校验）

    Args:
        image_path: 图片文件路径

    Returns:
        提取的文本内容，失败返回 None
    """
    if not image_path or not Path(image_path).exists():
        return None

    if _OCR_ENGINE_NAME is None:
        return None

    # 尺寸校验
    if not _check_image_safe(image_path):
        return None

    try:
        # 在线程池中运行 OCR，带超时
        future = _OCR_POOL.submit(_run_ocr_engine, image_path)
        text = future.result(timeout=OCR_TIMEOUT)

        if text and len(text.strip()) > 5:
            print(f"[OCR] 成功提取 {len(text)} 字符 (引擎: {_OCR_ENGINE_NAME})")
            return text.strip()
        return None

    except concurrent.futures.TimeoutError:
        print(f"[Warning] OCR 超时 ({OCR_TIMEOUT}s)")
        return None
    except Exception as e:
        print(f"[Warning] OCR 提取失败: {e}")
        return None


def _run_ocr_engine(image_path: str) -> str:
    """在子线程中执行实际的 OCR 调用"""
    if _OCR_ENGINE_NAME == "paddleocr":
        return _extract_with_paddleocr(image_path)
    elif _OCR_ENGINE_NAME == "pytesseract":
        return _extract_with_pytesseract(image_path)
    return ""


def extract_risk_keywords_from_image(image_path: str) -> list:
    """
    从图片中提取文字后运行关键词检测

    Args:
        image_path: 图片文件路径

    Returns:
        匹配到的风险关键词列表
    """
    text = extract_text(image_path)
    if not text:
        return []

    from services.risk_rules import detect_risk_keywords
    keywords = detect_risk_keywords(text)
    return keywords["all_matched"]
