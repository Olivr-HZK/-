# CompetitorPeriodWorkflow.py 完整依赖分析

## 📊 依赖树结构

```
CompetitorPeriodWorkflow.py (主工作流)
│
├── CompetitorPeriodDataExtractor.py (第一部分)
│   └── CompetitorDatabaseDB.py
│       └── 标准库: json, os, re, sqlite3, datetime, typing, pathlib
│
├── CompetitorPeriodAnalysisAI.py (第二部分)
│   ├── CompetitorDailyAnalysisAI.py
│   │   ├── openai (第三方库)
│   │   └── env_loader.py
│   │       └── dotenv (第三方库, pathlib)
│   └── env_loader.py
│
└── CompetitorPeriodReportGenerator.py (第三部分)
    ├── CompetitorDatabaseDB.py (同上)
    ├── requests (第三方库)
    ├── yaml (第三方库)
    └── env_loader.py
    └── config/config.yaml (配置文件 - 可选，仅用于飞书webhook配置)
```

## ✅ 必需的Python文件（7个）

1. **CompetitorPeriodWorkflow.py** - 主工作流文件
2. **CompetitorPeriodDataExtractor.py** - 数据提取模块
3. **CompetitorPeriodAnalysisAI.py** - AI分析模块
4. **CompetitorPeriodReportGenerator.py** - 报告生成模块
5. **CompetitorDatabaseDB.py** - 数据库操作模块
6. **CompetitorDailyAnalysisAI.py** - AI分析工具函数（被Part2使用）
7. **env_loader.py** - 环境变量加载器

## 📁 必需的配置文件（可选）

- **config/config.yaml** - 配置文件（仅当使用飞书webhook配置时需要，也可以通过环境变量替代）

## 📦 必需的第三方库

- **openai** - OpenAI API客户端
- **requests** - HTTP请求库
- **yaml** - YAML解析库
- **dotenv** - 环境变量加载（通过env_loader.py使用）

## 📂 数据库文件（必需）

- **db/competitor_data.db** - SQLite数据库文件

## ❌ 冗余文件（对CompetitorPeriodWorkflow工作流不需要）

**注意**：虽然爬虫用于填充数据库，但 `CompetitorPeriodWorkflow` 工作流**只从数据库读取数据**，不执行爬虫操作。因此所有爬虫相关文件都是冗余的。

### RapidAPI爬虫相关文件（用于填充数据库，但不被工作流使用）
- `CompetitorScraperRapidAPI.py` - RapidAPI爬虫核心模块 ⚠️ **用于填充数据库，但工作流不依赖**
- `scrape_youtube_only.py` - YouTube爬虫脚本
- `scrape_youtube_shorts_only.py` - YouTube Shorts爬虫脚本
- `test_youtube_shorts.py` - YouTube Shorts测试
- `test_rapidapi_scraper.py` - RapidAPI爬虫测试

### 其他爬虫相关文件
- `CompetitorScraper.py` - 竞品爬虫（使用Playwright，本工作流不需要）
- `CompetitorSummaryAI.py` - 竞品总结AI（不同工作流）

### 其他工作流文件
- `CompetitorDailyWorkflow.py` - 每日工作流（不同用途，使用RapidAPI爬虫）
- `CompetitorDailyWorkflow/` 目录 - 每日工作流的模块
- `CompetitorReportFromDB.py` - 从DB生成报告（不同工作流）
- `CompetitorFeishuSender.py` - 飞书发送器（被其他工作流使用，本工作流有自己的实现）

### 单个平台的工作流（Twitter/Facebook/TikTok/YouTube等）
这些文件使用 `CompetitorScraperRapidAPI.py` 进行爬虫，但本工作流不需要：
- `TwitterScraper.py` - 使用RapidAPI爬虫
- `TwitterAnalysisAI.py`
- `TwitterFeishuSender.py`
- `FacebookScraper.py` - 使用RapidAPI配置
- `FacebookAnalysisAI.py`
- `FacebookFeishuSender.py`
- `TikTokScraper.py` - 使用RapidAPI爬虫
- `TikTokAnalysisAI.py`
- `TikTokFeishuSender.py`
- `tiktok_video_extractor.py` - 使用RapidAPI爬虫

### 其他工具和测试文件
- `GTscraper.py` - Google Trends爬虫
- `GTSummaryAI.py` - Google Trends总结AI
- `Imagesearch.py` - 图片搜索
- `twitter_workflow.py` - Twitter工作流
- `migrate_json_to_database.py` - 数据迁移工具（用于导入数据到数据库）
- `import_twitter_input_to_db.py` - 导入工具（用于导入数据到数据库）
- `delete_youtube_posts_from_db.py` - 删除工具（用于清理数据库）
- `test_*.py` - 所有测试文件（包括 `test_youtube_shorts.py`, `test_rapidapi_scraper.py`, `test_twitter_latest5.py`）
- `CompetitorHistoryDB.py` - 历史数据库（旧版，已被CompetitorDatabaseDB替代）

### 示例和文档文件
- `*.txt` 示例文件（twitter示例.txt, facebook示例.txt等）
- `*.json` 示例/测试文件
- `README.md` - 项目文档（非代码依赖）
- `*.md` 文档文件

### 其他配置文件
- `requirements.txt` - 依赖管理（开发时需要，运行时不需要）
- `pyproject.toml` - 项目配置（开发时需要）
- `setup-*.sh/bat` - 安装脚本
- `start-http.*` - HTTP服务器启动脚本
- `docker/` - Docker相关（除非在Docker中运行）
- `sender/` - 发送器模块（被其他工作流使用）

### 数据库相关（已合并到CompetitorDatabaseDB）
- `CompetitorHistoryDB.py` - 旧版历史数据库（已被CompetitorDatabaseDB替代）

## 📋 总结

### 最小化文件列表（仅运行CompetitorPeriodWorkflow所需）

**Python文件 (7个):**
1. CompetitorPeriodWorkflow.py
2. CompetitorPeriodDataExtractor.py
3. CompetitorPeriodAnalysisAI.py
4. CompetitorPeriodReportGenerator.py
5. CompetitorDatabaseDB.py
6. CompetitorDailyAnalysisAI.py
7. env_loader.py

**配置文件 (1个，可选):**
- config/config.yaml (如果使用文件配置飞书webhook)

**数据库文件 (1个，必需):**
- db/competitor_data.db

**第三方库:**
- 需要在requirements.txt中安装：openai, requests, pyyaml, python-dotenv

**环境变量文件 (可选):**
- .env (用于存储API密钥和webhook URL)

### 冗余文件统计

- **RapidAPI爬虫相关**: 5+个文件（用于填充数据库，但工作流不依赖）
- **其他爬虫相关**: 3+个文件
- **其他工作流文件**: 15+个
- **单个平台工作流**: 12+个文件（使用RapidAPI爬虫）
- **工具和测试文件**: 10+个
- **测试和示例文件**: 10+个
- **文档和配置**: 多个（非代码依赖）

**总计**: 约55+个Python文件对 `CompetitorPeriodWorkflow.py` 工作流都是**非必需的**。

### ⚠️ 重要说明

虽然以下文件用于**填充数据库**（爬虫阶段），但 `CompetitorPeriodWorkflow` 工作流**只从数据库读取数据**，不执行爬虫操作：

- `CompetitorScraperRapidAPI.py` - RapidAPI爬虫（用于数据采集阶段）
- `scrape_youtube_*.py` - YouTube爬虫脚本
- `migrate_json_to_database.py` - 数据迁移工具
- `import_twitter_input_to_db.py` - 导入工具

**工作流架构**：
```
数据采集阶段（独立） → 数据库 → 数据分析阶段（CompetitorPeriodWorkflow）
   [爬虫脚本]          [db/]        [本工作流]
```

因此，爬虫相关文件虽然对**数据库填充**很重要，但对**运行工作流**是冗余的。
