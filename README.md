# fin_robot — AI 市场状态分析系统

智能化的金融信息采集与分析系统。自动抓取 RSS 新闻，通过 AI 提取结构化市场信号，为投资决策提供数据支撑。

## 系统架构

```
RSS 源 ──→  collectors/rss/  ──→  规范化 RawItem
                                         │
                                    ┌────┘
                                    ▼
                         services/ingestion_service.py
                         ├── Phase 1: 批量原始入库 + 皮尔逊去重
                         │   (Bigram + Pearson, 阈值 0.85)
                         ├── Phase 2: 并发 AI 提取（Semaphore=5, 45s timeout）
                         │   ├── financial_filter   金融过滤（缩写 JSON）
                         │   └── market_state_analyzer  信号提取（缩写 JSON）
                         │       └── Few-Shot 资产标准化 → 沪深300/纳斯达克100
                         └── Phase 3: 批量信号入库
                                    │
                                    ▼
                         core/database/   SQLite 持久化
                                    │
                                    ▼
                         market_signals  结构化信号
```

## 核心能力

| 能力 | 说明 |
|------|------|
| RSS 采集 | 7 个金融/科技源，关键词过滤，自动重试 |
| AI 金融过滤 | 判断内容是否金融相关，非金融自动降级 |
| 信号提取 | 情绪/重要性/置信度/影响标的/板块/风险等级 |
| 文本去重 | Bigram + 皮尔逊相关系数去重，纯 Python 实现，无第三方依赖 |
| 资产标准化 | Few-Shot Prompt 引导模型输出沪深300/纳斯达克100等标准标的名称 |
| 并发管线 | asyncio.Semaphore(5) 并发控制，45s 超时熔断 |
| 三级 Fallback | xiaomi → deepseek → openrouter 自动降级 |
| 源分类 | macro / market / industry / sentiment / policy |
| 字段缩写 | JSON 键名缩写化，减少 token 消耗约 20% |
| 语言解绑 | 英文文本的摘要/逻辑字段保留英文原语，不翻译 |
| 数据库 | SQLite，自动建表 + 迁移，兼容旧库 |
| 多模型支持 | xiaomi / deepseek / openrouter（已移除 zhipu / volcengine） |

## 快速开始

### 1. 安装依赖

```bash
cd fin_robot
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置

复制环境变量模板并编辑：

```bash
cp .env.example .env
```

在 `.env` 中至少需要配置：

- **AI 模型**：`ACTIVE_MODEL` + 对应 API Key
  - 默认首选 `xiaomi`：配置 `XIAOMI_API_KEY`
  - 或切换 `deepseek`（推荐，英文能力更强）：配置 `DEEPSEEK_API_KEY`
  - 兜底 `openrouter`：配置 `OPENROUTER_API_KEY`
- **代理**：`HTTP_PROXY` / `HTTPS_PROXY`（国内访问外网必需）

### 3. 运行

```bash
# RSS 全流程：抓取 → AI 分析 → 入库
python scripts/run_rss.py

# 查看最近信号
python -c "import sys, json, sqlite3; sys.path.insert(0,'.'); from core.database.db import DB_PATH; conn=sqlite3.connect(DB_PATH); rows=conn.execute('SELECT category, sentiment, summary FROM market_signals ORDER BY id DESC LIMIT 10').fetchall(); [print(json.dumps(dict(r),ensure_ascii=False)) for r in rows]"
```

## 配置说明

### AI 模型（`.env`）

```ini
# 当前激活：xiaomi / deepseek / openrouter
ACTIVE_MODEL=deepseek

# 小米模型（首选默认）
XIAOMI_API_KEY=your_key

# DeepSeek（推荐，英文能力强，速度快）
DEEPSEEK_API_KEY=your_key

# OpenRouter（兜底）
OPENROUTER_API_KEY=your_key
```

### 并发与超时

系统默认以 `Semaphore(5)` 并发调用 AI 模型，单次调用超时 45 秒。可在 `services/ingestion_service.py` 中调整。

### RSS 源

默认 7 个源，可在 `.env` 中覆盖：

```ini
RSS_FEEDS_JSON=[{"name":"36kr","url":"https://36kr.com/feed"}, ...]
```

### X 推文（选配）

```ini
X_AUTH_TOKEN=从浏览器开发者工具 Cookie 中获取
X_TRACKED_USERS=[{"user":"elonmusk","weight":0.3,"tags":["科技","宏观"],"note":"马斯克"}, ...]
```

### 信息源分类

系统自动将每个信息源归入 5 类之一，可在 `.env` 中覆盖：

| 分类 | 说明 | 示例 |
|------|------|------|
| macro | 宏观 | Reuters, WSJ, bbc_business |
| market | 市场行情 | cnbc_finance, marketwatch_top |
| industry | 行业 | elonmusk, 36kr, techcrunch |
| sentiment | 情绪/观点 | CathieDWood |
| policy | 政策 | 预留 |

## 项目结构

```
fin_robot/
├── core/                    # 核心层
│   ├── ai/                  # AI 模型、Prompts、Analyzers、Pipeline
│   │   ├── ai_client.py     # 模型路由、请求重试、三级 Fallback
│   │   ├── pipeline.py      # 编排分析流程
│   │   ├── analyzers/       # financial_filter + market_state_analyzer
│   │   └── prompts/         # Prompt 文本 + Schema + 字段映射
│   ├── models/              # 数据模型（RawItem / MarketSignal / MarketState）
│   ├── database/            # 建表、迁移、Repository
│   ├── market/              # 预留：状态引擎 / 主题追踪 / 量化因子
│   └── utils/               # 工具函数
│       └── similarity.py    # 皮尔逊相关系数 + Bigram 文本相似度
├── collectors/              # 采集器
│   ├── rss/                 # RSS 抓取、规范化、源配置
│   └── x/                   # X 推文采集（预留迁移）
├── configs/                 # 配置管理
├── services/                # 业务流程编排
│   └── ingestion_service.py # 三阶段并发管线（Phase 1/2/3）
├── scripts/                 # 可运行入口
│   ├── run_rss.py           # RSS 全流程入口
│   ├── test_english_slim.py # 英文文本对照测试脚本
│   └── test_few_shot.py     # Few-Shot 资产标准化验证脚本
└── data/                    # 数据存储
```

### 各层职责

| 层 | 职责 | 不负责 |
|------|------|--------|
| core/ai/ai_client.py | 模型路由、请求重试、三级 Fallback | Prompt、业务逻辑 |
| core/ai/prompts/ | Prompt 文本、Schema、字段缩写映射 | 业务逻辑 |
| core/ai/analyzers/ | 独立信号分析器 | Prompt、数据库 |
| core/ai/pipeline.py | 编排分析流程 | 模型调用细节 |
| core/database/ | SQLite CRUD + 迁移 | AI、采集 |
| collectors/ | 数据采集 + 规范化 | AI、数据库 |
| services/ | 编排完整三阶段并发流程 | 抓取、模型细节 |

## 数据流

```
1. RSS 抓取 →  2. 规范化（RawItem）→  3. 皮尔逊去重 + 批量原始入库（Phase 1）
                                               │
                                               ▼
                                    4. 并发 AI 提取（Phase 2）
                                    Semaphore(5), 45s timeout
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                              金融过滤    信号提取     异常/Fallback
                              (缩写JSON)  (缩写JSON)   (自动降级)
                                    │          │
                                    └──────────┘
                                               │
                                    expand_signal_fields()
                                    (缩写→全拼 还原映射)
                                               │
                                               ▼
                                    5. 批量信号入库（Phase 3）
                                               │
                                               ▼
                                    6. SQLite 持久化
```

## 数据模型

### RawItem（原始条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| source_type | str | rss |
| source_name | str | 源名称 |
| title | str | 标题 |
| content | str | 正文 |
| metadata.source_category | str | macro / market / industry / sentiment / policy |

### MarketSignal（结构化信号）

AI 提取使用**缩写字段名**以减少 token 消耗，入库前自动还原为全拼：

| 缩写 | 全拼 | 说明 |
|------|------|------|
| cat | category | macro / industry / company / sentiment / policy / event / non_financial |
| emo | sentiment | 看涨 / 看跌 / 中性 |
| imp | importance | 1-5 |
| conf | confidence | 0.0-1.0 |
| hor | horizon | 短期 / 中期 / 长期 |
| mkts | affected_markets | 影响的市场/指数 |
| assets | affected_assets | 影响的具体标的 |
| sects | affected_sectors | 影响的行业板块 |
| themes | theme_tags | 市场叙事标签 |
| sum | summary | 摘要（英文文本保持英文原语） |
| log | logic | 逻辑分析（英文文本保持英文原语） |
| risks | risk_points | 风险点（英文文本保持英文原语） |
| r_lvl | risk_level | 低 / 中 / 高 |
| bias | action_bias | 偏利多 / 偏利空 / 观望 |

## 模型对照测试

系统已内置英文金融文本的多模型对照测试脚本：

```bash
python scripts/test_english_slim.py
```

该脚本使用美联储利率决议相关英文文本，独立调用当前配置的模型，验证 JSON 完整性和语言解绑效果。

## Few-Shot 资产标准化测试

验证模型是否能通过 Few-Shot 示例将模糊的"核心资产"表述自动映射为标准标的名称：

```bash
python scripts/test_few_shot.py
```

该脚本输入"A股核心资产全线爆发"的文本，检测 `assets` 字段是否输出 `沪深300`。经实测，DeepSeek 模型可完美命中标准化名称。

## 文本去重机制

Phase 1 入库前对所有新抓取条目进行两两皮尔逊去重：

- **算法**：Bigram 词频向量 + 皮尔逊相关系数，纯 Python 实现，无第三方依赖
- **阈值**：0.85 — 仅拦截高度雷同的重复推送，不会误杀同一事件的不同报道
- **位置**：`core/utils/similarity.py`

## 模型 Fallback 链路

```
首选:  xiaomi (mimo-v2.5-pro)    — 中文场景表现良好
  ↓ 失败自动降级
次选:  deepseek (deepseek-chat)  — 中英文均衡，速度快
  ↓ 失败自动降级
兜底:  openrouter (ring-2.6-1t)  — 能力最强，但有免费限频
```

## 性能参考

以下为 7 个 RSS 源（约 90 条新闻）的完整流程实测数据：

| 模型 | 总耗时 | 信号入库 | 英文支持 |
|------|--------|---------|---------|
| xiaomi (mimo-v2.5-pro) | 180s+ | 约 2 条（仅中文） | 差（频繁超时/中断） |
| deepseek (deepseek-chat) | 77s | 约 84 条（中英文） | 优（4.6s/条） |
| openrouter (ring-2.6-1t) | — | — | 优（但有免费限频） |

推荐生产环境使用 `ACTIVE_MODEL=deepseek` 以获得最佳的中英文覆盖和响应速度。
