# 竞品社媒监控系统

一个完整的竞品社媒数据爬取、分析和报告生成系统，支持多平台（Twitter、TikTok、Instagram、YouTube、Facebook）的自动化监控。

## 📁 项目结构

```
.
├── database/          # 数据库模块
│   ├── competitor_db.py    # 竞品数据数据库（SQLite，每个公司一张表）
│   └── history_db.py       # 历史数据数据库（存储AI分析结果）
│
├── scrapers/          # 爬虫模块
│   ├── rapidapi.py         # RapidAPI 爬虫（Twitter, TikTok, Instagram, YouTube）
│   ├── facebook.py          # Facebook 爬虫
│   ├── daily_scraper.py    # 每日数据爬取脚本
│   └── king_facebook.py    # King 公司 Facebook 专用爬虫
│
├── analyzers/         # AI 分析模块
│   ├── daily_ai.py          # 日报 AI 分析
│   ├── period_ai.py         # 时间段 AI 分析
│   └── summary_ai.py        # 摘要 AI 分析
│
├── reports/           # 报告生成模块
│   ├── daily_report.py      # 日报生成
│   ├── period_generator.py  # 时间段报告生成
│   ├── period_extractor.py  # 时间段数据提取
│   └── weekly_report.py      # 周报生成
│
├── workflows/         # 工作流模块
│   ├── daily_workflow.py    # 日报工作流（爬取+分析+发送）
│   └── period_workflow.py   # 时间段工作流（提取+分析+报告）
│
├── senders/           # 消息发送模块
│   ├── feishu.py            # 飞书消息发送
│   ├── wework.py             # 企业微信消息发送
│   └── trends_sender.py      # Google Trends AI 结果发送器
│
├── tools/             # 工具脚本
│   ├── import_company.py    # 导入公司配置
│   ├── load_companies.py    # 加载公司配置
│   ├── reload_companies.py  # 重新加载公司配置
│   ├── export_sheets.py     # 导出到 Google Sheets
│   └── delete_*.py          # 数据库清理工具
│
├── tests/             # 测试脚本
│   ├── test_rapidapi_scraper.py
│   ├── test_twitter_latest5.py
│   └── test_youtube_shorts.py
│
├── config/            # 配置文件
│   ├── config.yaml          # 主配置文件
│   └── frequency_words.txt   # 高频词列表
│
├── docs/              # 文档目录
│   ├── 竞品数据爬取使用说明.md
│   ├── CompetitorPeriodWorkflow使用说明.md
│   └── ...
│
├── db/                # 数据库文件目录
│   └── competitor_data.db
│
├── env_loader.py      # 环境变量加载器
├── requirements.txt   # Python 依赖
└── README.md          # 本文件
```

## 🚀 快速开始

### 1. 环境配置

```bash
# （推荐）在项目根目录创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制 .env.example 并填写）
cp .env.example .env
```

### 2. 数据库初始化

**重要：** 在使用爬虫脚本之前，需要先将公司配置导入到数据库中。

#### 方法一：从 JSON 文件加载（推荐）

```bash
# 创建 input 目录（如果不存在）
mkdir -p input

# 准备 input/twitter_input.json 配置文件（参考下面的格式）

# 加载所有公司配置到数据库
python tools/load_companies.py
```

#### 方法二：使用导入工具

```bash
# 导入示例公司（需要先有 input/twitter_input.json）
python tools/import_company.py

# 或重新加载配置
python tools/reload_companies.py
```

**详细说明请参考：** [数据库初始化说明](docs/数据库初始化说明.md)

**JSON 配置文件格式示例：**

```json
{
  "competitors": [
    {
      "name": "公司名称",
      "priority": "high",
      "platforms": [
        {
          "type": "twitter",
          "enabled": true,
          "username": "company_twitter",
          "url": "https://twitter.com/company_twitter"
        }
      ]
    }
  ]
}
```

### 3. 运行工作流

#### 日报工作流（爬取+分析+发送）

```bash
# 爬取今天的数据并生成日报
python workflows/daily_workflow.py

# 爬取昨天的数据
python workflows/daily_workflow.py --days-ago 1

# 爬取指定公司的数据
python workflows/daily_workflow.py --companies "dream games" "vita studio"
```

#### 时间段工作流（提取+分析+报告）

```bash
# 完整工作流（提取+分析+报告）
python workflows/period_workflow.py --start-date 2026-01-07 --end-date 2026-01-13

# 只提取数据
python workflows/period_workflow.py --start-date 2026-01-07 --end-date 2026-01-13 --skip-analysis --skip-report

# 只进行分析（使用已提取的数据）
python workflows/period_workflow.py --start-date 2026-01-07 --end-date 2026-01-13 --skip-extract --skip-report
```

#### 仅爬取数据（不分析）

```bash
# 爬取今天的数据
python scrapers/daily_scraper.py

# 爬取昨天的数据
python scrapers/daily_scraper.py --days-ago 1
```

#### 仅生成报告（使用已有数据）

```bash
# 从数据库生成日报
python reports/daily_report.py --date 2026-01-25

# 生成周报
python reports/weekly_report.py --start-date 2026-01-20 --end-date 2026-01-26
```

## 📖 核心模块说明

### 数据库模块 (`database/`)

- **`competitor_db.py`**: 存储每个公司每个平台每天的原始数据，每个公司一张表
- **`history_db.py`**: 存储AI分析结果和历史报告

### 爬虫模块 (`scrapers/`)

- **`rapidapi.py`**: 通过 RapidAPI 爬取 Twitter、TikTok、Instagram、YouTube 数据
- **`facebook.py`**: Facebook 数据爬取
- **`daily_scraper.py`**: 从数据库读取配置，自动爬取所有公司的数据

### 分析模块 (`analyzers/`)

- **`daily_ai.py`**: 对每日数据进行AI分析，识别重要内容
- **`period_ai.py`**: 对时间段数据进行深度分析，重点关注玩法更新和线下活动
- **`summary_ai.py`**: 生成数据摘要

### 报告模块 (`reports/`)

- **`daily_report.py`**: 从历史数据库读取AI分析结果，生成日报
- **`period_generator.py`**: 生成时间段报告（飞书卡片格式）
- **`period_extractor.py`**: 从数据库提取指定时间段的数据

### 工作流模块 (`workflows/`)

- **`daily_workflow.py`**: 完整的日报工作流（爬取 → 分析 → 生成报告 → 发送）
- **`period_workflow.py`**: 时间段工作流（提取 → 分析 → 生成报告 → 发送）

### 发送器模块 (`senders/`)

- **`feishu.py`**: 发送飞书消息卡片
- **`wework.py`**: 发送企业微信消息
- **`trends_sender.py`**: 轻量级发送器，用于发送 Google Trends AI 分析结果

## 🔧 工具脚本

### 数据管理

```bash
# 导入公司配置
python tools/import_company.py

# 加载公司配置到数据库
python tools/load_companies.py input/twitter_input.json

# 重新加载公司配置
python tools/reload_companies.py

# 导出数据到 Google Sheets
python tools/export_sheets.py
```

### 数据清理

```bash
# 删除所有 YouTube 数据
python tools/delete_all_youtube_posts_from_db.py

# 删除指定公司的数据
python tools/delete_king_data_from_db.py
```

## 📚 详细文档

更多详细使用说明请查看 `docs/` 目录：

- [竞品数据爬取使用说明](docs/竞品数据爬取使用说明.md)
- [时间段监控工作流使用说明](docs/CompetitorPeriodWorkflow使用说明.md)
- [数据库使用说明](docs/数据库使用说明.md)
- [定时任务配置说明](docs/定时任务配置说明.md)

## ⚙️ 配置说明

### 环境变量 (`.env`)

```bash
# RapidAPI 配置
RAPIDAPI_KEY=your_rapidapi_key

# OpenAI/OpenRouter 配置
OPENAI_API_KEY=your_openai_key
# 或
OPENROUTER_API_KEY=your_openrouter_key

# 飞书配置
FEISHU_WEBHOOK_URL=your_feishu_webhook_url

# 企业微信配置
WEWORK_WEBHOOK_URL=your_wework_webhook_url

# 数据库路径（可选）
COMPETITOR_DB_DIR=/app/db
```

### 配置文件 (`config/config.yaml`)

包含各平台的API配置、爬取参数等。详细说明请参考配置文件中的注释。

## ⏰ 定时任务配置

项目提供了定时任务脚本，支持 Windows 和 macOS/Linux：

### Windows 脚本（PowerShell）

- **`run-daily-scraper.ps1`** - 每日爬取任务（爬取前一天的社媒数据）
- **`run-weekly-period-workflow.ps1`** - 每周周报生成任务（生成上周的竞品周报）

### macOS/Linux 脚本（Bash）

- **`run-daily-scraper.sh`** - 每日爬取任务（爬取前一天的社媒数据）
- **`run-weekly-period-workflow.sh`** - 每周周报生成任务（生成上周的竞品周报）

### 快速使用

**Windows (PowerShell):**
```powershell
# 手动测试每日爬取任务
.\run-daily-scraper.ps1

# 手动测试每周周报生成任务
.\run-weekly-period-workflow.ps1
```

**macOS/Linux (Bash):**
```bash
# 手动测试每日爬取任务
./run-daily-scraper.sh

# 手动测试每周周报生成任务
./run-weekly-period-workflow.sh
```

### 配置定时任务

**Windows 任务计划程序：**

详细配置说明请参考：[定时任务脚本使用说明](docs/定时任务脚本使用说明.md)

**简要步骤：**
1. **每日爬取任务**
   - 触发器：每天 08:00
   - 程序：`powershell.exe`
   - 参数：`-ExecutionPolicy Bypass -File "C:\path\to\run-daily-scraper.ps1"`

2. **每周周报生成任务**
   - 触发器：每周一 09:00
   - 程序：`powershell.exe`
   - 参数：`-ExecutionPolicy Bypass -File "C:\path\to\run-weekly-period-workflow.ps1"`

**macOS/Linux Cron：**

```bash
# 编辑 crontab
crontab -e

# 每天上午 8:00 运行爬虫（爬取前一天数据）
0 8 * * * cd /path/to/project && ./run-daily-scraper.sh >> logs/cron.log 2>&1

# 每周一上午 9:00 运行周报生成
0 9 * * 1 cd /path/to/project && ./run-weekly-period-workflow.sh >> logs/cron.log 2>&1
```

**日志文件：**
- 每日爬取日志：`logs/daily_scraper_YYYY-MM-DD.log`
- 每周周报日志：`logs/weekly_period_workflow_YYYY-MM-DD.log`

## 🐳 Docker 部署

```bash
# 构建镜像
docker-compose -f docker/docker-compose-build.yml build

# 运行容器
docker-compose -f docker/docker-compose.yml up -d
```

## 📝 开发说明

### 添加新的爬虫平台

1. 在 `scrapers/` 目录下创建新的爬虫文件
2. 实现统一的接口函数
3. 在 `scrapers/daily_scraper.py` 中集成

### 添加新的分析器

1. 在 `analyzers/` 目录下创建新的分析文件
2. 实现分析函数
3. 在相应的工作流中调用

### 添加新的发送器

1. 在 `senders/` 目录下创建新的发送器文件
2. 实现发送函数
3. 在工作流中集成

## 📄 许可证

详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
