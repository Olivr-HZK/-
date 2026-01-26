# CompetitorDailyWorkflow 使用文档

## 📋 概述

`CompetitorDailyWorkflow.py` 是一个完整的竞品监控日报工作流系统，整合了社交媒体爬虫、AI 分析和飞书推送功能。支持按公司分组处理，自动保存历史数据，并可以分段执行各个步骤。

## 🎯 核心功能

1. **多平台爬虫**：支持 Twitter/X、Instagram、TikTok、YouTube、Facebook
2. **AI 分析**：对爬取的内容进行智能分析和评分
3. **日报生成**：生成 Markdown 和 JSON 格式的日报
4. **飞书推送**：使用精美的卡片格式推送日报到飞书群
5. **历史数据管理**：自动保存和读取历史数据，支持数据比对

## 🔄 工作流逻辑

### 完整工作流（5 个步骤）

```
【步骤 1/5】读取输入配置
    ↓
【步骤 2/5】爬取各平台数据
    ↓ 保存到 db/raw_data/{date}/
【步骤 3/5】AI分析
    ↓ 保存到 db/ai_analysis/{date}/
【步骤 4/5】生成日报
    ↓ 保存到 output/{date}/ 和 db/reports/{date}/
【步骤 5/5】推送到飞书
```

### 数据流向

```
输入配置文件 (input/twitter_input.json)
    ↓
爬虫 → 原始数据 → db/raw_data/{date}/
    ↓
AI 分析 → AI 结果 → db/ai_analysis/{date}/
    ↓
生成日报 → Markdown → output/{date}/
         → JSON → db/reports/{date}/
    ↓
飞书推送 → 飞书群
```

## 📝 参数说明

### 基础参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | `-i` | 字符串 | `/input/twitter_input.json` | 输入 JSON 配置文件路径 |
| `--days-ago` | `-d` | 整数 | `1` | 爬取多少天前的数据（1=昨天，2=前天） |
| `--companies` | `-c` | 字符串列表 | `None` | 只处理指定的公司（可多个） |

### 分段执行参数（互斥，只能选一个）

| 参数 | 说明 |
|------|------|
| `--only-scrape` | 只执行爬虫步骤，将数据保存到数据库 |
| `--only-ai` | 只执行 AI 分析步骤（从数据库读取原始数据） |
| `--only-report` | 只生成日报步骤（从数据库读取 AI 结果和原始数据） |
| `--only-send` | 只发送日报步骤（从数据库读取报告数据） |

### 完整工作流的跳过选项

| 参数 | 说明 |
|------|------|
| `--skip-ai` | 跳过 AI 分析步骤（仅在完整工作流中有效） |
| `--skip-send` | 跳过飞书推送（仅在完整工作流中有效） |

## 💡 使用示例

### 1. 完整工作流（默认）

执行所有步骤：爬虫 → AI 分析 → 生成日报 → 推送飞书

```bash
python CompetitorDailyWorkflow.py
```

### 2. 指定日期

爬取 2 天前的数据（前天）

```bash
python CompetitorDailyWorkflow.py --days-ago 2
```

### 3. 指定公司

只处理指定的公司（可多个）

```bash
python CompetitorDailyWorkflow.py --companies voodoo homa
```

### 4. 完整工作流但跳过某些步骤

跳过 AI 分析和飞书推送（只爬虫和生成日报）

```bash
python CompetitorDailyWorkflow.py --skip-ai --skip-send
```

### 5. 分段执行：只执行爬虫

只爬取数据并保存到数据库，不进行 AI 分析和推送

```bash
python CompetitorDailyWorkflow.py --only-scrape
```

**使用场景**：
- 快速测试爬虫功能
- 批量爬取数据，稍后再分析
- 爬虫和 AI 分析分开执行（节省资源）

### 6. 分段执行：只执行 AI 分析

从数据库读取原始数据，进行 AI 分析并保存结果

```bash
python CompetitorDailyWorkflow.py --only-ai
```

**使用场景**：
- 爬虫已执行，现在只需要重新分析
- 调整 AI 分析逻辑后，重新分析已有数据
- 爬虫和 AI 分析在不同时间执行

### 7. 分段执行：只生成日报

从数据库读取 AI 结果和原始数据，生成日报文件

```bash
python CompetitorDailyWorkflow.py --only-report
```

**使用场景**：
- 重新生成日报（修改了日报格式）
- 只生成特定日期的日报
- 生成日报但不推送

### 8. 分段执行：只发送日报

从数据库读取报告数据，发送到飞书

```bash
python CompetitorDailyWorkflow.py --only-send
```

**使用场景**：
- 重新发送已生成的日报
- 发送特定日期的日报
- 测试飞书推送功能

### 9. 组合使用：指定公司 + 分段执行

只爬取指定公司的数据

```bash
python CompetitorDailyWorkflow.py --only-scrape --companies voodoo homa
```

只分析指定公司的数据

```bash
python CompetitorDailyWorkflow.py --only-ai --companies voodoo --days-ago 2
```

## 📂 输入配置文件格式

配置文件路径：`input/twitter_input.json`

```json
{
  "competitors": [
    {
      "name": "公司名称",
      "priority": "high|medium|low",
      "platforms": [
        {
          "type": "twitter|instagram|tiktok|youtube|facebook",
          "enabled": true,
          "url": "平台URL",
          "username": "用户名（可选）",
          "channel_id": "频道ID（YouTube，可选）",
          "handle": "Handle（YouTube，可选）"
        }
      ],
      "games": [
        {
          "name": "游戏名称",
          "priority": "high|medium|low",
          "platforms": [...]
        }
      ]
    }
  ]
}
```

## 📁 输出文件结构

### 原始数据
```
db/raw_data/
  └── 2026-01-11/
      └── 2026-01-11.json
```

### AI 分析结果
```
db/ai_analysis/
  └── 2026-01-11/
      └── 2026-01-11.json
```

### Markdown 日报
```
output/
  └── 2026-01-11/
      ├── daily_report_company1_2026-01-11.md
      └── daily_report_company2_2026-01-11.md
```

### JSON 日报
```
db/reports/
  └── 2026-01-11/
      ├── company1_2026-01-11.json
      └── company2_2026-01-11.json
```

## 🔍 各步骤详细说明

### 步骤 1：读取输入配置

- 从配置文件读取竞品账号信息
- 按公司分组所有平台的账号配置
- 支持公司级和游戏级的平台配置
- 支持优先级设置（high/medium/low）

### 步骤 2：爬取各平台数据

**支持的平台：**
- **Twitter/X**：获取推文
- **Instagram**：获取帖子
- **TikTok**：获取视频
- **YouTube**：获取视频（使用历史数据比对）
- **Facebook**：获取帖子

**特殊逻辑：**
- **YouTube**：由于 API 无法返回发布时间，使用历史数据比对来识别新视频
  - 获取最近 20 条视频
  - 与历史数据库中的视频 ID 比对
  - 返回不在历史数据中的新视频（即昨天发布的）

**数据保存：**
- 保存到 `db/raw_data/{date}/` 目录
- 每个日期一个文件，包含所有公司的数据

### 步骤 3：AI 分析

- 对每个平台的爬取内容进行 AI 分析
- 生成可用性评分、摘要、广告创意观察、玩法机制观察、建议动作等
- 支持优先级分析

**数据保存：**
- 保存到 `db/ai_analysis/{date}/` 目录
- 每个日期一个文件，包含所有公司的 AI 分析结果

### 步骤 4：生成日报

- 按公司生成 Markdown 格式的日报
- 同时生成 JSON 格式的日报（包含完整数据）
- 显示所有监控的社交媒体来源
- 显示无更新的平台信息
- 按评分排序展示有更新的平台

**输出文件：**
- Markdown：`output/{date}/daily_report_{company}_{date}.md`
- JSON：`db/reports/{date}/{company}_{date}.json`

### 步骤 5：推送到飞书

- 使用精美的卡片格式推送日报
- 每个公司一个卡片，不同公司使用不同颜色的边框
- 包含平台图标、优先级标识、评分、分析内容等
- 支持重试机制（最多 3 次）

## 🎨 飞书卡片格式

- **卡片头部**：公司名称 + 专属颜色边框
- **日期和来源**：显示监控日期和所有平台链接
- **无更新平台**：列出昨天无社媒更新的平台
- **有更新平台分析**：按评分排序展示
  - 平台图标和标题
  - 链接、评分、帖子数
  - 摘要、互动概览、广告创意观察、玩法机制观察、建议动作

## ⚙️ 环境变量

### 必需的环境变量

- `RAPIDAPI_KEY`：RapidAPI 主密钥
- `RAPIDAPI_KEY_2`：RapidAPI 备用密钥（可选，主密钥达到限制时自动切换）
- `FEISHU_WEBHOOK_URL`：飞书 Webhook URL（或通过 `config/config.yaml` 配置）

### 可选的环境变量

- `COMPETITOR_INPUT_PATH`：输入配置文件路径（覆盖默认路径）
- `COMPETITOR_DB_DIR`：数据库目录（默认：`/app/db` 或 `./db`）
- `OUTPUT_DIR`：输出目录（默认：`/app/output` 或 `./output`）
- `CONFIG_PATH`：配置文件路径（默认：`/app/config/config.yaml`）

## 🔧 常见使用场景

### 场景 1：每日定时任务

```bash
# 每天凌晨执行，爬取昨天的数据
python CompetitorDailyWorkflow.py
```

### 场景 2：分段执行（节省资源）

```bash
# 早上：只爬虫
python CompetitorDailyWorkflow.py --only-scrape

# 中午：只 AI 分析
python CompetitorDailyWorkflow.py --only-ai

# 下午：生成并推送日报
python CompetitorDailyWorkflow.py --only-report
python CompetitorDailyWorkflow.py --only-send
```

### 场景 3：重新分析历史数据

```bash
# 重新分析 3 天前的数据
python CompetitorDailyWorkflow.py --only-ai --days-ago 3
```

### 场景 4：只处理特定公司

```bash
# 只处理 voodoo 公司的数据
python CompetitorDailyWorkflow.py --companies voodoo
```

### 场景 5：测试爬虫功能

```bash
# 只测试爬虫，不分析和推送
python CompetitorDailyWorkflow.py --only-scrape --companies voodoo
```

## ⚠️ 注意事项

1. **首次运行**：
   - YouTube 爬虫首次运行可能返回一些旧视频（因为历史数据为空）
   - 从第二次运行开始，会准确识别新发布的视频

2. **数据依赖**：
   - 分段执行时，确保上一步的数据已保存到数据库
   - `--only-ai` 需要先执行 `--only-scrape`
   - `--only-report` 需要先执行 `--only-ai`
   - `--only-send` 需要先执行 `--only-report` 或完整工作流

3. **日期参数**：
   - `--days-ago` 参数在所有步骤中都需要一致
   - 例如：`--only-scrape --days-ago 2` 和 `--only-ai --days-ago 2` 必须使用相同的日期

4. **API 限制**：
   - 如果主 API key 达到限制，系统会自动切换到备用 key
   - 切换后不会换回主 key（只切换一次）

5. **文件路径**：
   - 支持绝对路径和相对路径
   - Docker 环境使用 `/app/` 前缀
   - 本地环境使用相对路径或项目根目录

## 🐛 故障排查

### 问题 1：找不到输入配置文件

**错误**：`❌ 无法读取输入配置`

**解决**：
- 检查 `--input` 参数是否正确
- 检查文件是否存在
- 检查环境变量 `COMPETITOR_INPUT_PATH` 是否设置

### 问题 2：API 调用失败

**错误**：`❌ RapidAPI 调用失败`

**解决**：
- 检查 `RAPIDAPI_KEY` 是否设置
- 检查 API key 是否有效
- 如果主 key 达到限制，系统会自动切换到备用 key

### 问题 3：找不到历史数据

**错误**：`⚠️ 未找到历史数据`

**解决**：
- 确保之前已执行过爬虫步骤
- 检查 `--days-ago` 参数是否正确
- 检查数据库目录是否存在

### 问题 4：飞书推送失败

**错误**：`❌ 飞书推送失败`

**解决**：
- 检查 `FEISHU_WEBHOOK_URL` 是否设置
- 检查 Webhook URL 是否有效
- 检查网络连接

## 📊 性能优化建议

1. **分段执行**：如果爬虫和 AI 分析耗时较长，可以分开执行
2. **指定公司**：只处理需要的公司，减少执行时间
3. **跳过步骤**：如果只需要爬虫，使用 `--skip-ai --skip-send`
4. **批量处理**：可以编写脚本批量处理多个日期

## 📚 相关文件

- `CompetitorScraperRapidAPI.py`：爬虫实现
- `CompetitorDailyAnalysisAI.py`：AI 分析实现
- `CompetitorHistoryDB.py`：历史数据管理
- `CompetitorFeishuSender.py`：飞书推送（独立脚本）

## 🔄 版本更新

- **v1.0**：支持完整工作流和分段执行
- **v1.1**：添加 YouTube 历史数据比对逻辑
- **v1.2**：添加备用 API key 支持
- **v1.3**：优化飞书卡片格式

---

**最后更新**：2026-01-11
