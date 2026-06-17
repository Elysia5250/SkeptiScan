"""
网页截图服务模块

第一版（MVP）：
  - capture_url_screenshot() 返回 None，主流程不受影响
  - 后续可使用 Playwright 实现整页截图功能

后续扩展：
  1. pip install playwright
  2. playwright install chromium
  3. 在下方 capture_url_screenshot 中实现截图逻辑
"""

import os
from typing import Optional

# 截图存储目录
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")


def capture_url_screenshot(url: str) -> Optional[str]:
    """
    截取指定 URL 的网页截图

    TODO: 使用 Playwright 实现整页截图
    示例代码（取消注释即可使用）：
    ```
    from playwright.sync_api import sync_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filename = f"screenshot_{hash(url)}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=filepath, full_page=True)
        browser.close()

    return filepath
    ```

    Args:
        url: 要截图的网页 URL

    Returns:
        截图文件路径，如未实现则返回 None
    """
    # MVP 阶段暂不实现截图，返回 None
    return None