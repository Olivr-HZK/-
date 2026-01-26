# CompetitorDailyScraperFromDB.py 爬虫逻辑说明

## 📋 整体流程

Daily Scraper 的爬虫逻辑采用 **"JSON → 数据库 → 爬取 → 数据库"** 的双向数据流模式。

---

## 🔄 完整数据流程

```
┌─────────────────────────────────────────────────────────────┐
│  步骤 0: 配置同步（可选，默认启用）                            │
└─────────────────────────────────────────────────────────────┘
                    ↓
    input/twitter_input.json
                    ↓
    load_companies_from_json_to_database()
                    ↓
    ┌──────────────────────────────────────┐
    │  db/competitor_data.db                │
    │  - companies 表（公司基本信息）        │
    │  - company_platforms 表（平台配置）   │
    └──────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 1: 从数据库读取配置                                      │
└─────────────────────────────────────────────────────────────┘
                    ↓
    db.get_all_companies() 或 指定的 companies
                    ↓
    db.get_company_platforms() (公司级 + 游戏级)
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 2: 爬取数据                                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
    对每个公司的每个平台：
    - scrape_twitter_platform()
    - scrape_tiktok_platform()
    - scrape_instagram_platform()
    - scrape_youtube_platform()
    - scrape_facebook_platform()
                    ↓
    调用 RapidAPI 获取数据
                    ↓
┌─────────────────────────────────────────────────────────────┐
│  步骤 3: 保存到数据库                                         │
└─────────────────────────────────────────────────────────────┘
                    ↓
    db.save_raw_data(company, platforms_data, fetch_date)
                    ↓
    ┌──────────────────────────────────────┐
    │  db/competitor_data.db                │
    │  - {company}_raw_data 表              │
    │    (按日期存储爬取的数据)              │
    └──────────────────────────────────────┘
```

---

## 🔍 详细步骤说明

### 步骤 0: 从 JSON 加载配置到数据库（默认启用）

**函数**: `load_companies_from_json_to_database()`

**执行时机**: 
- 默认情况下，每次运行爬虫前都会执行
- 可以通过 `--skip-load-json` 参数跳过

**功能**:
1. 读取 `input/twitter_input.json` 文件
2. 解析 JSON 结构：
   ```json
   {
     "competitors": [
       {
         "name": "voodoo",
         "priority": "high",
         "platforms": [...],
         "games": [...]
       }
     ]
   }
   ```
3. 调用 `db.save_company_social_media_config()` 将配置写入数据库：
   - 更新 `companies` 表（公司基本信息）
   - 更新 `company_platforms` 表（平台配置，包括公司级和游戏级）

**数据库表结构**:
- `companies`: 存储公司名称、优先级
- `company_platforms`: 存储每个平台的详细信息（URL、username、user_id、page_id、channel_id、handle、sec_uid、enabled、priority）

**特点**:
- ✅ 支持增量更新（不会删除已有配置）
- ✅ 如果 JSON 中某个平台被禁用（`enabled: false`），数据库中的 `enabled` 字段会被更新
- ✅ 如果 JSON 中某个平台被删除，数据库中的记录仍然保留（只是不会在爬取时使用）

---

### 步骤 1: 从数据库读取配置

**函数**: `scrape_all_companies_to_database()` → `scrape_company_platforms_from_db()`

**执行逻辑**:
1. 获取公司列表：
   - 如果命令行指定了 `--companies`，使用指定的公司列表
   - 否则调用 `db.get_all_companies()` 获取所有公司

2. 对每个公司，获取平台配置：
   - **公司级平台**: `db.get_company_platforms(company, game_name=None, enabled_only=True)`
   - **游戏级平台**: 直接查询 `company_platforms` 表，筛选 `game_name IS NOT NULL AND enabled = 1`

3. 合并所有平台配置，准备爬取

**关键点**:
- ✅ 只爬取 `enabled = 1` 的平台
- ✅ 支持公司级和游戏级平台
- ✅ 从数据库读取已保存的标识符（如 `user_id`、`sec_uid`、`channel_id` 等）

---

### 步骤 2: 爬取数据

**函数**: 各个平台的 `scrape_*_platform()` 函数

**执行逻辑**:
对每个平台，根据平台类型调用相应的爬取函数：

1. **Twitter**: `scrape_twitter_platform()`
   - 优先使用数据库中的 `user_id`
   - 如果没有，调用 `get_twitter_user_id_from_username()` 获取
   - 调用 `get_posts_from_twitter()` 爬取数据

2. **TikTok**: `scrape_tiktok_platform()`
   - 优先使用数据库中的 `sec_uid`
   - 如果没有，调用 `get_tiktok_secuid_from_username()` 获取
   - 调用 `get_posts_from_tiktok()` 爬取数据
   - 添加 2 秒延迟避免限流

3. **Instagram**: `scrape_instagram_platform()`
   - 从 URL 或配置中提取 `username`
   - 调用 `get_posts_from_instagram()` 爬取数据
   - 添加 1.5 秒延迟

4. **YouTube**: `scrape_youtube_platform()`
   - 支持普通视频和 Shorts
   - 优先使用数据库中的 `channel_id`
   - 如果没有，尝试从 `handle` 获取
   - 对于 Shorts，支持历史数据去重

5. **Facebook**: `scrape_facebook_platform()`
   - 使用数据库中的 `page_id`
   - 调用 `FacebookScraper._fetch_facebook_raw()` 和 `parse_facebook_posts()` 爬取数据

**数据过滤**:
- 根据 `days_ago` 参数过滤指定日期的数据
- 只返回有数据的平台（`posts_count > 0`）

---

### 步骤 3: 保存到数据库

**函数**: `db.save_raw_data()`

**执行逻辑**:
1. 为每个公司创建或使用对应的表：`{company}_raw_data`
2. 将爬取的数据按日期保存：
   ```sql
   INSERT INTO {company}_raw_data (
     fetch_date,
     platform_type,
     game,
     url,
     posts_json,
     posts_count,
     fetched_at
   ) VALUES (...)
   ```

**数据存储格式**:
- `fetch_date`: 爬取的目标日期（YYYY-MM-DD）
- `platform_type`: 平台类型（twitter, tiktok, instagram, youtube, facebook）
- `game`: 游戏名称（如果是游戏级平台，否则为 NULL）
- `url`: 平台 URL
- `posts_json`: 帖子数据的 JSON 字符串
- `posts_count`: 帖子数量
- `fetched_at`: 爬取时间戳

**特点**:
- ✅ 按日期存储，不会覆盖历史数据
- ✅ 支持同一天多次爬取（会插入新记录）
- ✅ 即使没有数据，也会插入一条空记录（用于记录查询时间）

---

## 🎛️ 命令行参数控制

### 默认行为（推荐）

```bash
python CompetitorDailyScraperFromDB.py --days-ago 1
```

**执行流程**:
1. ✅ 从 `input/twitter_input.json` 加载配置到数据库
2. ✅ 从数据库读取所有公司的配置
3. ✅ 爬取昨天的数据
4. ✅ 保存到数据库

### 跳过 JSON 加载

```bash
python CompetitorDailyScraperFromDB.py --days-ago 1 --skip-load-json
```

**执行流程**:
1. ❌ 跳过 JSON 加载（直接使用数据库中的配置）
2. ✅ 从数据库读取所有公司的配置
3. ✅ 爬取昨天的数据
4. ✅ 保存到数据库

**适用场景**: 
- 数据库配置已经是最新的，不需要从 JSON 更新
- 提高运行速度（跳过配置同步步骤）

### 指定公司

```bash
python CompetitorDailyScraperFromDB.py --companies voodoo dream_games --days-ago 1
```

**执行流程**:
1. ✅ 从 JSON 加载配置到数据库
2. ✅ 只爬取指定的公司（voodoo, dream_games）
3. ✅ 爬取昨天的数据
4. ✅ 保存到数据库

### 指定日期

```bash
python CompetitorDailyScraperFromDB.py --date 2026-01-15
```

**执行流程**:
1. ✅ 从 JSON 加载配置到数据库
2. ✅ 从数据库读取所有公司的配置
3. ✅ 爬取指定日期（2026-01-15）的数据
4. ✅ 保存到数据库

### 自定义 JSON 路径

```bash
python CompetitorDailyScraperFromDB.py --json-path input/my_custom_config.json
```

---

## 📊 数据流总结

### 配置数据流

```
JSON 文件 (input/twitter_input.json)
    ↓ [load_companies_from_json_to_database]
数据库配置表 (companies, company_platforms)
    ↓ [get_company_platforms]
爬虫函数 (scrape_*_platform)
```

### 爬取数据流

```
RapidAPI
    ↓ [get_posts_from_*]
平台数据 (List[Dict])
    ↓ [save_raw_data]
数据库原始数据表 ({company}_raw_data)
```

---

## 🔑 关键特性

### 1. 配置同步机制

- **默认行为**: 每次运行前都会从 JSON 同步配置到数据库
- **好处**: 确保数据库配置与 JSON 文件一致
- **可控制**: 可以通过 `--skip-load-json` 跳过

### 2. 标识符自动获取

- **Twitter**: 自动获取 `user_id`（如果数据库中没有）
- **TikTok**: 自动获取 `sec_uid`（如果数据库中没有）
- **YouTube**: 自动获取 `channel_id`（如果数据库中没有）
- **好处**: 首次爬取时自动获取标识符，后续直接使用，提高效率

### 3. 历史数据管理

- 按日期存储，不会覆盖历史数据
- 支持按日期查询历史数据
- 支持数据去重（如 YouTube Shorts）

### 4. 灵活的配置管理

- 支持从 JSON 文件批量更新配置
- 支持在数据库中直接管理配置（启用/禁用平台）
- 支持优先级管理

---

## 💡 最佳实践

### 日常使用

```bash
# 每天定时任务：爬取昨天的数据
python CompetitorDailyScraperFromDB.py --days-ago 1
```

### 配置更新后

```bash
# 更新配置后，重新爬取（会自动从 JSON 同步配置）
python CompetitorDailyScraperFromDB.py --days-ago 0
```

### 快速测试

```bash
# 只爬取特定公司，跳过 JSON 加载（如果配置已更新）
python CompetitorDailyScraperFromDB.py --companies voodoo --skip-load-json --days-ago 0
```

### 补爬历史数据

```bash
# 爬取指定日期的数据
python CompetitorDailyScraperFromDB.py --date 2026-01-10
```

---

## ❓ 常见问题

### Q: 如果 JSON 文件不存在会怎样？

A: 如果 `input/twitter_input.json` 不存在，会显示警告并跳过配置更新，直接使用数据库中的配置。

### Q: 如果数据库中没有配置会怎样？

A: 如果数据库中没有公司配置，会显示 "⚠️ 数据库中未找到任何公司" 并退出。

### Q: JSON 配置和数据库配置哪个优先？

A: 
- **配置读取**: 从数据库读取（JSON 只是用于更新数据库）
- **配置更新**: JSON 文件是配置的"源"，每次运行（默认）会同步到数据库

### Q: 如何禁用某个平台？

A: 
- **方法 1**: 在 JSON 文件中设置 `"enabled": false`，然后运行爬虫（会自动同步到数据库）
- **方法 2**: 直接在数据库中更新 `company_platforms` 表的 `enabled` 字段为 0

### Q: 爬取的数据会覆盖历史数据吗？

A: 不会。数据按日期存储，同一天可以多次爬取（会插入新记录），不会覆盖之前的数据。

