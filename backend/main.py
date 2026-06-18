"""
反噶韭菜商品风险分析工具 - 后端 API 服务
使用 FastAPI 实现

启动方式：
    cd backend
    uvicorn main:app --reload
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal
from models import AnalysisRecord
from config import set_runtime_config, get_ai_config, has_api_key
from services.ai_analyzer import analyze_product
from services.screenshot import capture_url_screenshot


# ---------------------------------------------------------------------------
# 应用初始化
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库"""
    init_db()
    yield


app = FastAPI(
    title="反噶韭菜商品风险分析工具",
    description="上传商品截图或输入商品链接，系统自动识别可疑营销话术并生成风险分析报告",
    version="1.2.0",
    lifespan=lifespan,
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件存储目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# API 接口
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """健康检查接口，返回项目状态"""
    return {
        "name": "反噶韭菜商品风险分析工具",
        "version": "1.2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/config")
async def save_config(
    base_url: str = Form(None, description="OpenAI Compatible Base URL"),
    api_key: str = Form(None, description="API Key"),
    model: str = Form(None, description="模型名称"),
    extra_prompt: str = Form(None, description="用户自定义额外提示词"),
):
    """
    保存运行时 API 配置（不写入数据库，仅存内存）
    """
    set_runtime_config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        extra_prompt=extra_prompt,
    )

    return {
        "success": True,
        "message": "配置已保存",
    }


@app.get("/api/config/status")
async def get_config_status():
    """返回当前配置状态，不返回 API Key 本身"""
    config = get_ai_config()
    configured = has_api_key()

    return {
        "api_configured": configured,
        "base_url": config["base_url"],
        "model": config["model"],
        "extra_prompt_configured": config["extra_prompt"] is not None,
        "mode": "real_api" if configured else "mock",
    }


@app.post("/api/config/test")
async def test_api_config():
    """
    一键测试 API 配置是否可用

    使用当前运行时配置中的 base_url、api_key、model，
    发起一次最小测试请求验证连通性。

    不会调用商品分析 prompt，不会把 API Key 返回给前端。
    """
    config = get_ai_config()
    api_key = config["api_key"]
    base_url = config["base_url"]
    model = config["model"]

    # 如果 API Key 为空，直接返回
    if not api_key.strip():
        return {
            "success": False,
            "message": "未配置 API Key",
            "mode": "mock",
        }

    # 发起最小测试请求
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "请只回复 OK"}],
            temperature=0,
            max_tokens=10,
        )

        # 检查是否正常返回
        reply = response.choices[0].message.content.strip()
        if reply:
            return {
                "success": True,
                "message": "API 配置可用",
                "mode": "real_api",
                "model": model,
            }
        else:
            return {
                "success": False,
                "message": "API 返回内容为空",
                "mode": "error",
                "model": model,
            }

    except Exception as e:
        # 提取简短的错误摘要，不暴露 API Key
        error_msg = str(e)
        # 截取关键错误信息，避免过长
        if len(error_msg) > 80:
            error_msg = error_msg[:80] + "..."

        # 常见的错误类型映射为友好信息
        error_lower = str(e).lower()
        if "401" in error_lower or "unauthorized" in error_lower or "auth" in error_lower:
            friendly_msg = "认证失败，请检查 API Key 是否正确"
        elif "404" in error_lower or "not found" in error_lower:
            friendly_msg = "模型不存在或 Base URL 错误，请检查模型名和接口地址"
        elif "timeout" in error_lower or "timed out" in error_lower:
            friendly_msg = "连接超时，请检查 Base URL 是否可访问"
        elif "connection" in error_lower or "connect" in error_lower or "resolve" in error_lower:
            friendly_msg = "无法连接，请检查 Base URL 和网络设置"
        elif "429" in error_lower or "rate limit" in error_lower:
            friendly_msg = "请求频率过高，请稍后再试"
        else:
            friendly_msg = f"API 调用失败：{error_msg}"

        return {
            "success": False,
            "message": friendly_msg,
            "mode": "error",
            "model": model,
        }


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(None, description="商品截图（可选）"),
    url: str = Form(None, description="商品链接（可选）"),
):
    """
    商品风险分析接口

    返回格式：
    {
        "success": true,
        "mode": "real_api" | "mock",
        "report": { ... }
    }
    """
    # 校验：至少需要提供一种输入
    if not image and not url:
        raise HTTPException(
            status_code=400,
            detail="请至少提供商品截图或商品链接中的一种",
        )

    # 保存上传的图片
    image_path = None
    if image:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        filepath = UPLOAD_DIR / filename

        with open(filepath, "wb") as f:
            shutil.copyfileobj(image.file, f)

        image_path = str(filepath)

    # 如果提供了 URL，先尝试截图（MVP 阶段截图返回 None）
    if url:
        screenshot_path = capture_url_screenshot(url)
        if screenshot_path and not image_path:
            image_path = screenshot_path

    # 调用 AI 分析模块，获取报告和模式标识
    report, mode = analyze_product(image_path=image_path, url=url)

    # 将分析结果保存到数据库
    try:
        db = SessionLocal()
        record = AnalysisRecord(
            input_type="image" if image else "url",
            input_value=url or image.filename,
            risk_level=report.get("risk_level", "未知"),
            summary=report.get("summary", ""),
            report_json=json.dumps(report, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception as e:
        print(f"[Warning] 数据库写入失败: {e}")

    return {
        "success": True,
        "mode": mode,
        "report": report,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)