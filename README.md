# fin_robot — AI 市场状态分析系统

智能化的金融信息采集与分析系统。自动抓取 RSS 新闻和 X 推文，通过 AI 提取结构化市场信号，为投资决策提供数据支撑。

## 系统架构

```
RSS 源 ──→  collectors/rss/  ──→  规范化 RawItem
                                         │
X 推文  ──→  collectors/x/    ──→  规范化 RawItem
                                         │
                                    ┌────┘
                                    ▼
                         core/ai/pipeline.py
                         ├── financial_filter   金融过滤
                         └── market_state_analyzer  五因子分析
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
| X 推文采集 | GraphQL API，auth_token 认证 |
| AI 金融过滤 | 判断内容是否金融相关，非金融自动降级 |
| 信号提取 | 情绪/重要性/置信度/影响标的/板块/风险等级 |
| 源分类 | macro / market / industry / sentiment / policy |
| 数据库 | SQLite，自动建表 + 迁移，兼容旧库 |
| 多模型支持 | Zhipu / OpenRouter / DeepSeek / Volcengine |

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

- **AI 模型**：`ACTIVE_MODEL` + 对应 API Key（建议先配置 OpenRouter 或智谱）
- **代理**：`HTTP_PROXY` / `HTTPS_PROXY`（国内访问外网必需）

### 3. 运行

```bash
# RSS 全流程：抓取 → AI 分析 → 入库
python scripts/run_rss.py

# X 推文采集（需先配置 X_AUTH_TOKEN）
python -c "import asyncio, x_collector; asyncio.run(x_collector.ingest_x_items())"

# 查看最近信号
python -c "import rss, json; print(json.dumps(rss.get_recent_ingested_items(10), ensure_ascii=False, indent=2))"
```

## 配置说明

### AI 模型（`.env`）

```ini
# 当前激活：zhipu / openrouter / deepseek / volcengine
ACTIVE_MODEL=zhipu

# 智谱 GLM
ZHIPU_API_KEY=your_key
ZHIPU_MODEL=glm-4.5-air

# OpenRouter（推荐，模型更丰富）
# ACTIVE_MODEL=openrouter
# OPENROUTER_API_KEY=your_key
# OPENROUTER_MODEL=openai/gpt-4o
```

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

```ini
SOURCE_PROFILES_JSON={"Reuters":"macro","elonmusk":"industry","CathieDWood":"sentiment"}
```

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
│   ├── models/              # 数据模型（RawItem / MarketSignal / MarketState）
│   ├── database/            # 建表、迁移、Repository
│   ├── market/              # 预留：状态引擎 / 主题追踪 / 量化因子
│   └── utils/               # 工具函数
├── collectors/              # 采集器
│   ├── rss/                 # RSS 抓取、规范化、源配置
│   ├── x/                   # X 推文采集（预留迁移）
│   └── telegram/            # Telegram 采集（预留）
├── configs/                 # 配置管理
├── services/                # 业务流程编排
├── scripts/                 # 可运行入口
└── data/                    # 数据存储
```

### 各层职责

| 层 | 职责 | 不负责 |
|------|------|--------|
| core/ai/ai_client.py | 模型路由、请求、重试 | Prompt、业务逻辑 |
| core/ai/prompts/ | Prompt 文本、Schema | 业务逻辑 |
| core/ai/analyzers/ | 独立信号分析器 | Prompt、数据库 |
| core/ai/pipeline.py | 编排分析流程 | 模型调用细节 |
| core/database/ | SQLite CRUD + 迁移 | AI、采集 |
| collectors/ | 数据采集 + 规范化 | AI、数据库 |
| services/ | 编排完整流程 | 抓取、模型细节 |

## 数据流

```
1. RSS 抓取 →  2. 规范化（RawItem）→  3. 金融过滤（AI）
                                               │
                                               ├── non_financial → 降级标记 → 入库
                                               └── financial →  4. 五因子分析（AI）
                                                                       │
                                                                       ▼
                                                                 结构化 MarketSignal
                                                                       │
                                                                       ▼
                                                                5. SQLite 入库
```

## 数据模型

### RawItem（原始条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| source_type | str | rss / x |
| source_name | str | 源名称 |
| title | str | 标题 |
| content | str | 正文 |
| metadata.source_category | str | macro / market / industry / sentiment / policy |

### MarketSignal（结构化信号）

| 字段 | 说明 |
|------|------|
| category | macro / industry / company / sentiment / policy / event / non_financial |
| sentiment | 看涨 / 看跌 / 中性 |
| importance | 1-5 |
| confidence | 0.0-1.0 |
| horizon | 短期 / 中期 / 长期 |
| affected_markets | 影响的市场/指数 |
| affected_assets | 影响的具体标的 |
| affected_sectors | 影响的行业板块 |
| theme_tags | 市场叙事标签 |
| risk_level | 低 / 中 / 高 |
| action_bias | 偏利多 / 偏利空 / 观望 |

## 开发路线

- [x] RSS 采集闭环
- [x] AI 金融过滤 + 信号提取
- [x] 信息源分类系统
- [x] X 推文采集
- [x] 模块化架构重构
- [ ] Market State Engine（信号聚合 → 市场状态快照）
- [ ] Theme Tracker（跨时间追踪市场叙事）
- [ ] 日报生成
- [ ] 定时调度
- [ ] Telegram 频道采集
- [ ] 量化因子引擎

## 技术栈

- **Python 3.14+**（Async/Await 架构）
- **requests / feedparser** — 网络请求 + RSS 解析
- **OpenAI SDK** — AI 模型调用
- **SQLite** — 数据持久化
- **python-telegram-bot** — 消息推送（预留）
