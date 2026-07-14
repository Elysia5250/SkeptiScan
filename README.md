# 🛡️ 反噶韭菜商品风险分析工具 v2.0VI

上传商品截图、输入商品链接或直接粘贴商品文案，系统自动提取文字、识别可疑营销话术，并通过联网事实核查交叉验证，生成一份结构化风险分析报告。帮你和家中的长辈识别消费陷阱，远离智商税。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Axios |
| 后端 | Python FastAPI |
| 数据库 | SQLite (via SQLAlchemy) |
| AI 模型 | OpenAI Compatible API（DeepSeek / GPT / Qwen 等） |
| 截图引擎 | Playwright（降级备用） |
| 文字提取 | OCR (Tesseract) + HTML 正文抽取 (lxml) |
| 事实核查 | DuckDuckGo / Bing / Wikipedia 多后端搜索 |

## 项目结构

```
anti-leek-checker/
├── backend/
│   ├── main.py                  # FastAPI 应用入口 & API 路由
│   ├── config.py                # 环境变量 + 运行时动态配置
│   ├── database.py              # 数据库连接 & 会话管理
│   ├── models.py                # SQLAlchemy 数据模型
│   ├── services/
│   │   ├── ai_analyzer.py       # AI 分析模块（10 级风险评分 + Markdown 解释）
│   │   ├── prompt_builder.py    # 分层 prompt 构建器（SillyTavern 风格）
│   │   ├── experience_db.py     # 自学习纠正记录（SQLite + 相似检索）
│   │   ├── html_extractor.py    # 网页正文快速提取（httpx + lxml）
│   │   ├── screenshot.py        # Playwright 截图（降级备用）
│   │   ├── ocr.py               # OCR 图片文字提取（Tesseract）
│   │   ├── fact_checker.py      # 联网事实核查（多搜索引擎）
│   │   ├── risk_rules.py        # 关键词规则检测
│   │   └── scam_knowledge_base.py # 伪科学/骗局知识库
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── main.js              # Vue 应用入口
│       ├── App.vue              # 主页面组件（配置面板 + 报告 + 模型列表获取）
│       ├── api.js               # 后端 API 封装
│       └── style.css            # 全局样式
├── tests/
│   ├── run_benchmark.py         # 基准测试入口（多 worker 并发）
│   ├── generate_dataset.py      # 测试数据集生成
│   ├── scrape_sources.py        # 搜索真实商品链接
│   ├── reporter.py              # ECharts HTML 报告生成
│   ├── archive/                 # 三轮基准测试归档
│   │   ├── v1/                  # 20 条简单用例 (100%)
│   │   ├── v2/                  # 100 条中等难度 (95%)
│   │   └── v3/                  # 100 条最难 (70%→78%)
│   └── dataset_100.csv          # 当前工作数据集
└── README.md
```

## 快速开始

### 1. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium      # 截图引擎
brew install tesseract tesseract-lang  # macOS OCR 引擎
cp .env.example .env
uvicorn main:app --reload        # http://localhost:8000
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

## 环境变量说明

优先级：**UI 运行时配置 > 环境变量 > 默认值**。

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI Compatible API Key | 空（Mock 模式） |
| `OPENAI_API_BASE` | API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 使用的模型 | `deepseek-v4-flash` |
| `EXTRA_PROMPT` | 自定义额外提示词 | 空 |

## 配置方式

### 前端 UI

展开 **⚙️ 模型配置** 面板，填写 Base URL、API Key、Model，点"保存配置"。还可以点"获取模型列表"自动拉取可用模型。

### 环境变量

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
```

## API 接口

### `POST /api/analyze`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image` | File | 否 | 商品截图（OCR 提取文字，不传图给 LLM） |
| `url` | string | 否 | 商品链接（HTML 提取 → 截图降级 → OCR） |
| `text` | string | 否 | 直接输入商品文案（跳过提取步骤） |
| `mode` | string | 否 | `external`（前端完整报告）/ `benchmark`（测试精简模式） |

返回 `risk_level` 为整数 1-10，附带 `detailed_analysis` 字段（Markdown 格式推理过程）。详细 JSON schema 见后端代码。

### `POST /api/models/list`

从已配置的 API 拉取可用模型列表（调用 OpenAI Compatible `/v1/models`）。

其他接口（`GET /`、`/api/config`、`/api/config/status`、`/api/config/test`）与 v1.1 保持一致。

## 核心流程

```
input (url/image/text)
    ↓
文字提取
  ├── url → HTML 直接提取（httpx, ~1s）
  │         失败 → Playwright 截图 + OCR（~8s, 降级）
  ├── image → OCR（Tesseract, 带超时 30s）
  └── text → 直接使用
    ↓
关键词规则检测（risk_rules.py）
    ↓
AI 分析（纯文本，不传图片，节省 token）
    ↓
联网事实核查（Bing → DuckDuckGo → Wikipedia，多后端）
    ↓
external 模式：事实核查结果注入第二轮增强分析
    ↓
返回 1-10 级风险评分 + Markdown 解释
```

## 基准测试结果

三轮递增难度测试，使用 DeepSeek V4 Flash 模型，以 6 为阈值（≥6 = scam）：

| 版本 | 用例 | 说明 | 准确率 |
|------|------|------|--------|
| v1 | 20 条简单 | 纯骗局 vs 纯正品 | **100%** |
| v2 | 100 条中等 | 混入合规信息/注册号 | **95%** |
| v3 | 100 条最难 | 偷换概念/让步/钓鱼/混淆样本 | **87%** |

v3 测试涵盖：经典骗局案例加工、偷换概念型广告（引用不相关研究）、让步免责型（"不替代药品但…"）、钓鱼后续收费型、听起来像骗局的真实产品。通过多轮迭代（KB 知识库 + Few-shot 对抗样本 + 让步免责检测 + 自学习），准确率从 70% 逐步提升至 87%。

> v2.0VI 新增自学习系统：用户可通过前端"纠正"按钮提交反馈，系统自动从历史纠正中提取相似案例注入 prompt，持续自我改进。

详细报告和解释文件见 `tests/archive/`。

## 版本日志

<details open>
<summary><b>v2.0VI</b> (2026-07-13) — self-learning + layered prompt</summary>
<br>

- [x] **自学习系统**：用户通过前端"纠正"按钮提交意见 → `experience_db.py` SQLite 存储 → 下次分析自动检索相似历史注入 prompt
- [x] **分层 prompt 构建器**：`prompt_builder.py` — SillyTavern 风格 JSON 分层组装（system/extra/learning/KB/fact-check/user）
- [x] **每一层有唯一标识** `_layer` + `_label`，便于 debug 和排序
- [x] **`POST /api/analyze/feedback`**：前端提交纠正的接口
- [x] **纠正弹窗**：分析结果底部"纠正"按钮 → 选择正确 verdict + 备注
- [x] **纯文本输入**：前端支持直接粘贴商品文案，互斥图片/URL/文本三种输入
- [x] **状态指示器**：分析中实时显示当前步骤（文字提取→KB 预检→AI 调用→深入分析）
- [x] **查看测试报告**：前端底部按钮，打开最新 benchmark 报告
</details>

<details>
<summary><b>v2.0V</b> (2026-07-13) — 87% accuracy</summary>
<br>

- [x] **KB 知识库扩展**：新增偷换概念、让步免责信号 + CONCESSION_PATTERNS 正则检测
- [x] **Few-shot 对抗样本**：Base Prompt 加入引用偷换、让步、NASA 真品等示例
- [x] **让步免责自动检测**：让步修辞 + 效果暗示组合模式扫描，提示模型注意
- [x] **v3 hardest 测试集 87%**（KB + Few-shot + 让步检测迭代，从 81% → 87%）
- [x] **品牌更新**：SkeptiScan，页面渐入动画

</details>

<details>
<summary><b>v2.0IV</b> (2026-07-13) — stability fix</summary>
<br>

- [x] **简化系统提示词**：去掉过长清单，改为简洁指令 + KB 注入
- [x] **修复 502 死锁**：`run_in_executor` → FastAPI 同步端点
- [x] **Key 持久化**：`/api/config` 保存 Key 时自动写入 `.env`，重启不丢
- [x] **benchmark 跳过事实核查**：跑分速度从数小时降至 ~10 分钟
- [x] `async` 端点全部改为 sync，避免线程池死锁

</details>

<details>
<summary><b>v2.0III</b> (2026-07-13) — checklist scoring + KB + deep fact-check</summary>
<br>

- [x] **量化评分系统**：7 维度检查清单（伪科学 25+虚假医疗 25+虚假背书 15+传销违法 20+诱导营销 10+数据欺诈 10+可信信号 -10）
- [x] **后端计分**：`_compute_risk_level()` 从 score_breakdown 计算最终等级
- [x] **伪科学知识库**：`scam_knowledge_base.py` — 70+ 伪科学术语 + 正规信号 + 复合风险模式
- [x] **KB 注入 prompt**：扫描文本后将匹配结果注入 LLM 上下文
- [x] **事实核查升级**：`build_fact_check_prompt` 含标题+摘要+链接，第二轮深度分析

</details>

<details>
<summary><b>v2.0II</b> (2026-07-13) — security patch</summary>
<br>

- [x] **安全加固：API Key 防泄漏**
- [x] 异常信息打印前过滤 API Key（`_safe_error` / `_safe_api_error`）
- [x] `/api/models/list` 错误返回过滤 Key，不再暴露给前端
- [x] `/api/config/test` fallback 错误信息加固
- [x] 全局异常处理器：debug 模式下不泄露函数参数
- [x] `generate_dataset.py` 取消 `--key` CLI 参数，改为 `OPENAI_API_KEY` 环境变量

</details>

<details>
<summary><b>v2.0I</b> (2026-07-13) — major rewrite</summary>
<br>

- [x] **10 级风险评分制**：1-10 分制替代原来的"低/中/高"三级
- [x] **Markdown 详细解释**：每条分析附带 `detailed_analysis` 字段，展示完整推理过程
- [x] **HTML 直接提取正文**：URL 输入优先通过 httpx + lxml 提取页面文字（~1s），替代截图
- [x] **多模式输出**：`external`（前端完整报告）/ `benchmark`（测试精简模式）
- [x] **多 worker 并发基准测试**：`run_benchmark.py --workers N`，支持并发跑分
- [x] **联网事实核查增强**：Bing + DuckDuckGo + Wikipedia 多后端搜索，自动生成核查摘要
- [x] **自动拉取模型列表**：前端"获取模型列表"按钮，通过 `/v1/models` 接口自动获取
- [x] **图片不传 LLM**：OCR 提取文字后仅传文本，节省图片 token 费用
- [x] **纯文本输入**：`/api/analyze` 新增 `text` 参数，可直接传文案分析
- [x] **数据集生成器**：`generate_dataset.py` 基于种子模板 + LLM 生成变体，支持难样本
- [x] **测试结果归档**：`tests/archive/v1-v3`，每轮含 CSV + HTML 报告 + 解释文件
- [x] **DeepSeek V4 Flash 默认模型**：默认对接 DeepSeek，降低推理成本
- [x] **系统提示词增强**：新增偷换概念、让步免责、钓鱼收费、数据引用欺诈 4 类风险信号
- [x] 思考模式自动禁用（DeepSeek 兼容性）
- [x] 安全加固：文件上传大小限制（10MB）、OCR 超时（30s）、图片尺寸校验、SSL 验证

</details>

<details>
<summary><b>v1.1</b> (previous version)</summary>
<br>

- [x] 首页包含文件上传和 URL 输入两种方式
- [x] 上传商品截图或输入链接进行分析
- [x] Mock 模式：无需 API Key 即可演示完整流程
- [x] 真实模式：支持 OpenAI Compatible API（GPT / DeepSeek / Qwen 等）
- [x] **一键检测 API 配置**：点击"测试 API 配置"验证连通性
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
- [x] 保存配置与测试 API 分离设计

</details>

## License

MIT
