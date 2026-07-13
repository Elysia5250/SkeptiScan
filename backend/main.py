"""
反噶韭菜商品风险分析工具 - 后端 API 服务
使用 FastAPI 实现

启动方式：
    cd backend
    uvicorn main:app --reload

安全说明：
    - 所有异常信息在返回到前端前会过滤 API Key
    - /api/config/status 不返回 API Key
    - 日志中出现的异常也会过滤 API Key
"""

import asyncio
import json
import re
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

# ---------------------------------------------------------------------------
# 安全过滤：异常信息中可能包含 API Key
# ---------------------------------------------------------------------------

_API_KEY_PATTERN = re.compile(r'(sk-[a-zA-Z0-9]{10,})\S*')


def _safe_api_error(e: Exception) -> str:
    """过滤异常信息中的 API Key，限制长度后返回"""
    msg = str(e)
    msg = _API_KEY_PATTERN.sub("sk-...", msg)
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return msg


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
    version="2.0.1",
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
# 全局异常处理器：防止 debug 模式下泄露函数参数（含 API Key）
# ---------------------------------------------------------------------------

from starlette.requests import Request
from starlette.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，返回通用错误信息（不暴露细节）"""
    print(f"[Error] {request.method} {request.url.path}: {_safe_api_error(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


# ---------------------------------------------------------------------------
# API 接口
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """健康检查接口，返回项目状态"""
    return {
        "name": "反噶韭菜商品风险分析工具",
        "version": "2.0.1",
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
    保存运行时 API 配置（持久化到 .env，重启不丢失）
    """
    set_runtime_config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        extra_prompt=extra_prompt,
    )

    # 持久化到 .env（确保重启后 Key 不丢失）
    try:
        env_path = Path(__file__).parent / ".env"
        lines = []
        keys_set = {"OPENAI_API_KEY": False, "OPENAI_API_BASE": False,
                    "OPENAI_MODEL": False, "EXTRA_PROMPT": False}

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("OPENAI_API_KEY="):
                        if api_key:
                            lines.append(f"OPENAI_API_KEY={api_key}\n")
                            keys_set["OPENAI_API_KEY"] = True
                        continue
                    elif stripped.startswith("OPENAI_API_BASE="):
                        if base_url:
                            lines.append(f"OPENAI_API_BASE={base_url}\n")
                            keys_set["OPENAI_API_BASE"] = True
                        continue
                    elif stripped.startswith("OPENAI_MODEL="):
                        if model:
                            lines.append(f"OPENAI_MODEL={model}\n")
                            keys_set["OPENAI_MODEL"] = True
                        continue
                    elif stripped.startswith("EXTRA_PROMPT="):
                        if extra_prompt is not None:
                            lines.append(f"EXTRA_PROMPT={extra_prompt}\n")
                            keys_set["EXTRA_PROMPT"] = True
                        continue
                    lines.append(line)

        # 追加未设置的配置项
        if api_key and not keys_set["OPENAI_API_KEY"]:
            lines.append(f"OPENAI_API_KEY={api_key}\n")
        if base_url and not keys_set["OPENAI_API_BASE"]:
            lines.append(f"OPENAI_API_BASE={base_url}\n")
        if model and not keys_set["OPENAI_MODEL"]:
            lines.append(f"OPENAI_MODEL={model}\n")
        if extra_prompt is not None and not keys_set["EXTRA_PROMPT"]:
            lines.append(f"EXTRA_PROMPT={extra_prompt}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[Warning] .env 写入失败: {e}")

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

        request_kwargs = dict(
            model=model,
            messages=[{"role": "user", "content": "请只回复 OK"}],
            temperature=0,
            max_tokens=50,
        )
        # 禁用思考模式（DeepSeek 等模型默认开启）
        try:
            request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        except Exception:
            pass

        response = client.chat.completions.create(**request_kwargs)

        msg = response.choices[0].message
        reply = (msg.content or "").strip()
        if not reply and hasattr(msg, "reasoning_content"):
            reply = (msg.reasoning_content or "").strip()

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
        # 常见的错误类型映射为友好信息（不暴露原始错误详情）
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
            friendly_msg = f"API 调用失败：{_safe_api_error(e)}"

        return {
            "success": False,
            "message": friendly_msg,
            "mode": "error",
            "model": model,
        }


@app.post("/api/models/list")
def fetch_models():
    """
    从已配置的 API 拉取可用模型列表
    调用 OpenAI Compatible 的 GET /v1/models 接口
    """
    config = get_ai_config()
    api_key = config["api_key"]
    base_url = config["base_url"]

    if not api_key.strip():
        return {"success": False, "models": [], "message": "请先配置 API Key"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
        response = client.models.list()
        models = sorted([m.id for m in response.data])
        return {"success": True, "models": models}
    except Exception as e:
        return {"success": False, "models": [], "message": _safe_api_error(e)}


@app.post("/api/analyze")
def analyze(
    image: UploadFile = File(None, description="商品截图（可选）"),
    url: str = Form(None, description="商品链接（可选）"),
    text: str = Form(None, description="商品文案（直接输入文本，跳过URL/截图）"),
    mode: str = Form("external", description="external=完整报告（前端）, benchmark=精简模式（测试脚本）"),
):
    """
    商品风险分析接口

    三种输入方式（任选其一）：
    - url: 提供商品链接，系统自动提取正文
    - image: 上传商品截图，OCR提取文字
    - text: 直接输入商品文案，跳过提取步骤

    两种模式：
    - external（默认）：完整分析 + 事实核查增强，返回前端友好报告
    - benchmark：精简分析，跳过事实核查增强，返回结构化结果供测试比对

    返回格式：
    {
        "success": true,
        "mode": "real_api" | "mock",
        "report": { ... }
    }
    """
    # 校验：至少需要提供一种输入
    if not image and not url and not text:
        raise HTTPException(
            status_code=400,
            detail="请至少提供商品截图、商品链接或商品文案中的一种",
        )

    # 保存上传的图片（限制大小 10MB）
    image_path = None
    if image:
        MAX_FILE_BYTES = 10 * 1024 * 1024
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        filepath = UPLOAD_DIR / filename

        total = 0
        with open(filepath, "wb") as f:
            while True:
                chunk = image.file.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    filepath.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")
                f.write(chunk)

        image_path = str(filepath)

    # 调用 AI 分析模块（同步调用，FastAPI 自动在默认线程池中执行）
    report, api_mode = analyze_product(image_path, url, mode, text)

    # 将分析结果保存到数据库
    try:
        db = SessionLocal()
        input_label = "image" if image else ("url" if url else "text")
        input_val = (url or text or (image.filename if image else ""))[:100]
        record = AnalysisRecord(
            input_type=input_label,
            input_value=input_val,
            risk_level=str(report.get("risk_level", "")),
            summary=report.get("summary", "")[:200],
            report_json=json.dumps(report, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception as e:
        print(f"[Warning] 数据库写入失败: {e}")

    return {
        "success": True,
        "mode": api_mode,
        "report": report,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)