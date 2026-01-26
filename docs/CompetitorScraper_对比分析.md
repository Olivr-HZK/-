# CompetitorScraperRapidAPI.py vs CompetitorDailyScraperFromDB.py 对比分析

## 📋 概述

这两个脚本都用于爬取竞品社交媒体数据，但采用了不同的架构和数据处理方式。

---

## 🔧 实现方式对比

### CompetitorScraperRapidAPI.py
- **架构类型**: 基于配置文件的独立爬虫脚本
- **配置来源**: 从 `config/config.yaml` 读取配置
- **数据存储**: 输出到 JSON 文件 (`output/competitor_social_raw.json`)
- **设计理念**: 一次性爬取，输出原始数据供后续处理
- **主要函数**: 
  - `scrape_competitor_social_with_rapidapi()` - 主入口函数
  - `load_config()` - 从 YAML 加载配置
  - `get_competitor_accounts()` - 解析配置中的账号信息

### CompetitorDailyScraperFromDB.py
- **架构类型**: 基于数据库的日常爬虫脚本
- **配置来源**: 从 SQLite 数据库 (`db/competitor_data.db`) 读取配置
- **数据存储**: 保存到 SQLite 数据库（每个公司一张表）
- **设计理念**: 日常定时任务，支持增量更新和历史数据管理
- **主要函数**:
  - `scrape_all_companies_to_database()` - 主入口函数
  - `scrape_company_platforms_from_db()` - 从数据库读取配置并爬取
  - `load_companies_from_json_to_database()` - 从 JSON 更新数据库配置

---

## 📥 输入对比

### CompetitorScraperRapidAPI.py

**配置来源**: `config/config.yaml`

```yaml
competitor_monitor:
  competitors:
    - name: voodoo
      priority: high
      platforms:
        - url: https://x.com/voodooplatform
          type: twitter
          enabled: true
      games:
        - name: papers.io
          platforms:
            - url: https://www.instagram.com/paper.io2game/
              type: instagram
              enabled: true
```

**特点**:
- ✅ 配置集中在一个 YAML 文件
- ✅ 适合一次性配置，无需数据库
- ❌ 配置修改需要编辑文件
- ❌ 不支持动态配置更新

### CompetitorDailyScraperFromDB.py

**配置来源**: SQLite 数据库 (`db/competitor_data.db`)

**数据库表结构**:
- `companies` - 公司基本信息
- `company_platforms` - 平台配置（支持公司级和游戏级）

**可选配置来源**: `input/twitter_input.json`（可自动同步到数据库）

**特点**:
- ✅ 配置存储在数据库，便于程序化管理
- ✅ 支持从 JSON 文件自动更新配置（`--json-path`）
- ✅ 支持动态启用/禁用平台（`enabled` 字段）
- ✅ 支持优先级管理（`priority` 字段）
- ✅ 可以存储平台特定信息（`user_id`, `page_id`, `channel_id`, `sec_uid` 等）
- ❌ 需要数据库初始化

---

## 📤 输出对比

### CompetitorScraperRapidAPI.py

**输出格式**: JSON 文件

**输出路径**: `output/competitor_social_raw.json`

**输出结构**:
```json
{
  "fetched_at": "2026-01-15T10:00:00Z",
  "items": [
    {
      "company": "voodoo",
      "game": null,
      "platform_type": "twitter",
      "url": "https://x.com/voodooplatform",
      "priority": "high",
      "posts": [...],
      "posts_count": 10
    }
  ]
}
```

**特点**:
- ✅ 单文件输出，便于传输和备份
- ✅ 适合一次性分析或测试
- ❌ 不保存历史数据
- ❌ 每次运行覆盖之前的结果
- ❌ 不支持按日期查询历史数据

### CompetitorDailyScraperFromDB.py

**输出格式**: SQLite 数据库

**数据库结构**:
- 每个公司一张表（例如: `voodoo_raw_data`）
- 表结构:
  ```sql
  CREATE TABLE {company}_raw_data (
    id INTEGER PRIMARY KEY,
    fetch_date TEXT NOT NULL,
    platform_type TEXT NOT NULL,
    game TEXT,
    url TEXT,
    posts_json TEXT,
    posts_count INTEGER,
    fetched_at TEXT
  )
  ```

**特点**:
- ✅ 按日期保存历史数据
- ✅ 支持按公司、日期、平台查询
- ✅ 支持增量更新（不会覆盖历史数据）
- ✅ 便于生成周报、月报等汇总报告
- ✅ 支持数据去重（如 YouTube Shorts）
- ❌ 需要数据库管理
- ❌ 数据文件较大

---

## 🌐 支持的平台对比

### 共同支持的平台

| 平台 | CompetitorScraperRapidAPI.py | CompetitorDailyScraperFromDB.py |
|------|------------------------------|----------------------------------|
| **Twitter/X** | ✅ | ✅ |
| **TikTok** | ✅ | ✅ |
| **Instagram** | ✅ | ✅ |
| **YouTube** | ✅ | ✅ |
| **YouTube Shorts** | ✅ | ✅ |
| **Facebook** | ✅ | ✅ |

### 平台实现细节

#### Twitter
- **CompetitorScraperRapidAPI.py**: 使用 `get_posts_from_twitter()`
- **CompetitorDailyScraperFromDB.py**: 使用 `scrape_twitter_platform()`，支持从数据库读取 `user_id`，如果没有则自动获取

#### TikTok
- **CompetitorScraperRapidAPI.py**: 使用 `get_posts_from_tiktok()`
- **CompetitorDailyScraperFromDB.py**: 使用 `scrape_tiktok_platform()`，支持从数据库读取 `sec_uid`，如果没有则自动获取，并添加了 2 秒延迟避免限流

#### Instagram
- **CompetitorScraperRapidAPI.py**: 使用 `get_posts_from_instagram()`
- **CompetitorDailyScraperFromDB.py**: 使用 `scrape_instagram_platform()`，添加了 1.5 秒延迟

#### YouTube
- **CompetitorScraperRapidAPI.py**: 使用 `get_posts_from_youtube()` 或 `get_youtube_shorts_from_channel()`
- **CompetitorDailyScraperFromDB.py**: 使用 `scrape_youtube_platform()`，支持自动识别 Shorts，支持历史数据去重

#### Facebook
- **CompetitorScraperRapidAPI.py**: 使用 `get_posts_from_facebook()`（直接调用 RapidAPI）
- **CompetitorDailyScraperFromDB.py**: 使用 `scrape_facebook_platform()`（通过 `FacebookScraper` 模块，使用 `_fetch_facebook_raw` 和 `parse_facebook_posts`）

---

## 🎯 使用场景对比

### CompetitorScraperRapidAPI.py

**适合场景**:
- ✅ 一次性爬取测试
- ✅ 快速验证 API 是否正常工作
- ✅ 不需要保存历史数据
- ✅ 配置简单，不需要数据库
- ✅ 适合 Docker 容器化部署（输出到 `/app/output`）

**典型用法**:
```python
# 直接调用主函数
scrape_competitor_social_with_rapidapi()
```

### CompetitorDailyScraperFromDB.py

**适合场景**:
- ✅ 日常定时任务（每天自动爬取）
- ✅ 需要保存历史数据
- ✅ 需要生成周报、月报等汇总报告
- ✅ 需要动态管理配置（启用/禁用平台）
- ✅ 需要按日期查询历史数据
- ✅ 需要数据去重（如 YouTube Shorts）

**典型用法**:
```bash
# 命令行运行
python CompetitorDailyScraperFromDB.py --days-ago 1

# 指定公司
python CompetitorDailyScraperFromDB.py --companies voodoo dream_games

# 指定日期
python CompetitorDailyScraperFromDB.py --date 2026-01-15

# 跳过从 JSON 加载配置
python CompetitorDailyScraperFromDB.py --skip-load-json
```

---

## 🔄 数据流程对比

### CompetitorScraperRapidAPI.py 数据流

```
config/config.yaml
    ↓
load_config() → get_competitor_accounts()
    ↓
scrape_posts_with_rapidapi() (调用 RapidAPI)
    ↓
output/competitor_social_raw.json
    ↓
(供后续 AI 分析使用)
```

### CompetitorDailyScraperFromDB.py 数据流

```
input/twitter_input.json (可选)
    ↓
load_companies_from_json_to_database()
    ↓
db/competitor_data.db (companies, company_platforms 表)
    ↓
scrape_company_platforms_from_db()
    ↓
调用 RapidAPI 爬取数据
    ↓
db/competitor_data.db ({company}_raw_data 表)
    ↓
(供后续分析、报告生成使用)
```

---

## 📊 功能特性对比

| 特性 | CompetitorScraperRapidAPI.py | CompetitorDailyScraperFromDB.py |
|------|------------------------------|----------------------------------|
| **配置管理** | YAML 文件 | SQLite 数据库 + JSON（可选） |
| **历史数据** | ❌ | ✅ |
| **按日期查询** | ❌ | ✅ |
| **数据去重** | ❌ | ✅ (YouTube Shorts) |
| **增量更新** | ❌ | ✅ |
| **平台启用/禁用** | ✅ (YAML 中 enabled) | ✅ (数据库 enabled 字段) |
| **优先级管理** | ✅ | ✅ |
| **自动获取 user_id/sec_uid** | ❌ | ✅ |
| **API 限流处理** | ✅ (自动切换 API Key) | ✅ (延迟 + API Key 切换) |
| **命令行参数** | ❌ | ✅ (丰富的参数选项) |
| **错误处理** | 基础 | 详细（包含调试信息） |
| **数据统计** | 基础 | 详细（公司、平台、帖子数统计） |

---

## 🚀 推荐使用场景

### 使用 CompetitorScraperRapidAPI.py 当:
1. 你只需要一次性爬取数据
2. 不需要保存历史数据
3. 配置简单，不想管理数据库
4. 在 Docker 环境中运行，输出到 `/app/output`
5. 作为工作流的第一步，后续有专门的脚本处理 JSON 输出

### 使用 CompetitorDailyScraperFromDB.py 当:
1. 需要每天定时爬取数据
2. 需要保存历史数据用于分析
3. 需要生成周报、月报等汇总报告
4. 需要动态管理配置（启用/禁用平台）
5. 需要按日期、公司、平台查询历史数据
6. 需要数据去重功能（如 YouTube Shorts）
7. 需要更细粒度的控制（命令行参数）

---

## 💡 总结

- **CompetitorScraperRapidAPI.py**: 轻量级、一次性爬取工具，适合快速测试和简单场景
- **CompetitorDailyScraperFromDB.py**: 企业级、日常爬取工具，适合生产环境和长期数据管理

两者都使用相同的底层 API 函数（`CompetitorScraperRapidAPI.py` 中的函数），但数据管理和存储方式不同。根据你的需求选择合适的工具。

