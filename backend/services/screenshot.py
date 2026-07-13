"""
网页截图服务模块
使用 Playwright 同步 API 截取商品页面整页截图
"""

import os
import re
import hashlib
from typing import Optional

# 截图存储目录
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")

# 最大截图尺寸（字节），超过则跳过
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024


def _sanitize_filename(url: str) -> str:
    """从 URL 生成安全的短文件名"""
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    domain_match = re.search(r"https?://([^/]+)", url)
    domain = domain_match.group(1).replace("www.", "")[:20] if domain_match else "unknown"
    domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
    return f"{domain}_{h}.png"


def capture_url_screenshot(url: str) -> Optional[str]:
    """
    截取指定 URL 的网页整页截图（Playwright 同步 API）

    Args:
        url: 要截图的网页 URL

    Returns:
        截图文件路径，截图失败或不可用时返回 None
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Warning] playwright 未安装，截图功能不可用")
        return None

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filename = _sanitize_filename(url)
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            page.screenshot(path=filepath, full_page=True)
            browser.close()

        size = os.path.getsize(filepath)
        if size > MAX_SCREENSHOT_BYTES:
            print(f"[Warning] 截图过大 ({size / 1024 / 1024:.1f}MB)，跳过")
            os.remove(filepath)
            return None

        print(f"[Screenshot] 截图成功: {filepath} ({size / 1024:.0f}KB)")
        return filepath

    except Exception as e:
        print(f"[Warning] 截图失败 ({url[:50]}...): {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None