"""
项目配置模块
从 .env 文件或环境变量加载配置
支持运行时动态配置（用户通过 UI 设置的 API 信息）
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# ---------------------------------------------------------------------------
# 运行时配置（用户通过 UI 设置，优先级高于环境变量）
# ---------------------------------------------------------------------------
_runtime_config = {
    "base_url": None,    # OpenAI Compatible Base URL
    "api_key": None,     # API Key
    "model": None,       # 模型名称
    "extra_prompt": None, # 用户自定义额外提示词
}


def set_runtime_config(base_url=None, api_key=None, model=None, extra_prompt=None):
    """
    设置运行时配置（由 POST /api/config 调用）
    只更新非 None 的值，保留之前的配置
    """
    if base_url is not None:
        _runtime_config["base_url"] = base_url.strip() or None
    if api_key is not None:
        _runtime_config["api_key"] = api_key.strip() or None
    if model is not None:
        _runtime_config["model"] = model.strip() or None
    if extra_prompt is not None:
        _runtime_config["extra_prompt"] = extra_prompt.strip() or None


def get_ai_config() -> dict:
    """
    获取最终 AI 配置，优先级：
    1. UI 运行时配置
    2. 环境变量
    3. 默认值

    返回：
    {
        "api_key": str,
        "base_url": str,
        "model": str,
        "extra_prompt": str or None
    }
    """
    # 默认值
    defaults = {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    }

    # 环境变量
    env = {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_API_BASE", ""),
        "model": os.getenv("OPENAI_MODEL", ""),
        "extra_prompt": os.getenv("EXTRA_PROMPT", ""),
    }

    # 运行时配置
    runtime = dict(_runtime_config)

    # 合并：运行时 > 环境变量 > 默认值
    config = {
        "api_key": runtime["api_key"] or env["api_key"] or "",
        "base_url": runtime["base_url"] or env["base_url"] or defaults["base_url"],
        "model": runtime["model"] or env["model"] or defaults["model"],
        "extra_prompt": runtime["extra_prompt"] or env["extra_prompt"] or None,
    }

    return config


def has_api_key() -> bool:
    """检查是否有可用的 API Key"""
    config = get_ai_config()
    key = config["api_key"].strip()
    return bool(key) and key != "your-api-key-here"


# ---------------------------------------------------------------------------
# 静态配置（从 .env 加载，改为使用动态配置函数）
# ---------------------------------------------------------------------------
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/analyses.db")


settings = Settings()