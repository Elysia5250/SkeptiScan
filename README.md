# 🛡️ 反噶韭菜商品风险分析工具

上传商品截图或输入商品链接，系统自动识别可疑营销话术，并调用大模型 API 生成一份商品风险分析报告。帮你和家中的长辈识别消费陷阱，远离智商税。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Axios |
| 后端 | Python FastAPI |
| 数据库 | SQLite (via SQLAlchemy) |
| AI 模型 | OpenAI Compatible API（GPT-4o-mini / DeepSeek / Qwen 等） |
| 截图 (预留) | Playwright |

## 项目结构

```
anti-leek-checker/
├── backend/
│   ├── main.py                  # FastAPI 应用入口 & API 路由
│   ├── config.py                # 环境变量 + 运行时动态配置（UI > 环境变量 > 默认值）
│   ├── database.py              # 数据库连接 & 会话管理
│   ├── models.py                # SQLAlchemy 数据模型
│   ├── services/
│   │   ├── ai_analyzer.py       # AI 分析模块（三层提示词结构 + OpenAI SDK）
│   │   ├── risk_rules.py        # 关键词规则检测
│   │   └── screenshot.py        # 网页截图（预留）
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── main.js              # Vue 应用入口
│       ├── App.vue              # 主页面组件（含配置面板 + 报告展示）
│       ├── api.js               # 后端 API 封装
│       └── style.css            # 全局样式
└── README.md
```

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd anti-leek-checker
```

### 2. 启动后端

```bash
# 进入后端目录
cd backend

# 推荐创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量文件
cp .env.example .env

# 启动服务（默认 http://localhost:8000）
uvicorn main:app --reload
```

> **提示**：如果不配置 `OPENAI_API_KEY`，系统会自动使用 Mock 模式返回模拟报告，无需真实 API Key 即可演示完整功能。

### 3. 启动前端

**新开一个终端窗口**，进入前端目录：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev
```

### 4. 访问页面

浏览器打开 http://localhost:5173

## 环境变量说明

在 `backend/.env` 文件中配置。**优先级：UI 运行时配置 > 环境变量 > 默认值**。

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI Compatible API Key | 空（Mock 模式） |
| `OPENAI_API_BASE` | API 地址 | https://api.openai.com/v1 |
| `OPENAI_MODEL` | 使用的模型 | gpt-4o-mini |
| `EXTRA_PROMPT` | 自定义额外提示词 | 空 |

## API 配置方式

### 方式一：前端 UI 配置

1. 展开首页顶部的 **⚙️ 模型配置** 面板
2. 填写 API Base URL、API Key（密码框隐藏）、Model、Extra Prompt
3. 点击 **💾 保存配置**
4. 配置状态会显示为"已配置 API"或"Mock 演示模式"

### 方式二：环境变量

在 `backend/.env` 中填写：
```
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
EXTRA_PROMPT=请重点关注保健品骗局
```

## 提示词注入位置

提示词分为三层，全部在后端 `backend/services/ai_analyzer.py` 中拼接，**前端不参与提示词构建**：

```
messages = [
  {
    "role": "system",
    "content": BASE_SYSTEM_PROMPT       # 后端写死的基础系统提示词
  },
  {
    "role": "system",
    "content": "以下是用户补充的分析要求...\n" + extra_prompt  # 用户 Extra Prompt（有值时才添加）
  },
  {
    "role": "user",
    "content": USER_PROMPT               # 根据图片/URL动态生成的任务提示词
  }
]
```

- **BASE_SYSTEM_PROMPT**：内置风险分析规则（夸大疗效、伪科学包装、虚假背书、健康焦虑、投资返利、诱导销售六大类）
- **EXTRA_PROMPT**：用户在 UI 中配置的额外提示词，以独立 system message 注入
- **USER_PROMPT**：根据是否有图片、URL 动态生成

## API 接口

### `GET /`
返回项目状态信息。

### `POST /api/config`
保存运行时 API 配置（不写入数据库，仅存内存）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `base_url` | string | 否 | OpenAI Compatible Base URL |
| `api_key` | string | 否 | API Key |
| `model` | string | 否 | 模型名称 |
| `extra_prompt` | string | 否 | 自定义额外提示词 |

### `GET /api/config/status`
返回当前配置状态（不返回 API Key）。

```json
{
  "api_configured": false,
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "extra_prompt_configured": false,
  "mode": "mock"
}
```

### `POST /api/analyze`
支持 `multipart/form-data`：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image` | File | 否 | 商品截图 |
| `url` | string | 否 | 商品链接 |

返回格式：

```json
{
  "success": true,
  "mode": "real_api",
  "report": {
    "summary": "...",
    "risk_level": "高",
    "suspicious_claims": ["..."],
    "marketing_tricks": ["..."],
    "fact_check_suggestions": ["..."],
    "purchase_advice": "...",
    "elderly_friendly_warning": "..."
  }
}
```

`mode` 字段表示分析来源：
- `"real_api"`：来自真实 API 调用
- `"mock"`：来自 Mock 演示模式

## 当前功能（v2.0）

- [x] 首页包含文件上传和 URL 输入两种方式
- [x] 上传商品截图或输入链接进行分析
- [x] Mock 模式：无需 API Key 即可演示完整流程
- [x] 真实模式：支持 OpenAI Compatible API（GPT / DeepSeek / Qwen 等）
- [x] **前端 UI 配置 API Key、Base URL、Model、Extra Prompt**
- [x] **三层提示词结构：BASE_SYSTEM_PROMPT + EXTRA_PROMPT + USER_PROMPT**
- [x] **OpenAI SDK 调用，支持 OpenAI Compatible 协议**
- [x] 关键词规则检测（量子、磁疗、负离子等 16 个风险词）
- [x] 完整的风险报告展示（7 个报告区域）
- [x] 分析结果标识模式（真实 API / Mock 演示）
- [x] 分析记录持久化到 SQLite 数据库
- [x] 支持文件拖拽上传
- [x] 密码框隐藏 API Key，不返回到前端
- [x] API 调用失败自动降级到 Mock 模式
- [x] 响应式设计，移动端友好

## 后续可扩展方向

- [ ] **Playwright 自动截图**：输入 URL 后自动截取商品页面，提高分析准确性
- [ ] **OCR 识别**：从图片中提取文字，增强关键词检测能力
- [ ] **联网事实核查**：自动搜索权威来源进行交叉验证
- [ ] **价格比对**：对比同类商品市场价格，识别虚高定价
- [ ] **黑名单商家库**：积累不良商家信息，查询历史记录
- [ ] **面向中老年人的简洁模式**：大字体、语音播报、一键分享给子女
- [ ] **微信小程序端**：降低使用门槛，方便中老年人使用

## License

MIT