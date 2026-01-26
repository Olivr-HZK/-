# CompetitorPeriodWorkflow 使用说明

## 📋 概述

`CompetitorPeriodWorkflow.py` 是一个完整的竞品社媒时间段监控工作流程序，用于从数据库提取指定时间范围内的社媒数据，进行 AI 分析，并生成飞书日报。

### 工作流组成

该工作流分为三个独立部分，可以单独执行或组合执行：

1. **数据提取** (`CompetitorPeriodDataExtractor`)
   - 从数据库 `competitor_data.db` 中提取指定时间范围内的社媒数据
   - 支持按公司、日期范围筛选

2. **AI分析** (`CompetitorPeriodAnalysisAI`)
   - 对提取的数据进行 AI 分析
   - 重点关注玩法更新和线下活动
   - 对每个帖子/视频进行评分（玩法更新和线下活动 8-10 分，日常维护 1-3 分）

3. **报告生成** (`CompetitorPeriodReportGenerator`)
   - 生成格式化的飞书卡片报告
   - 按公司分开生成报告
   - 包含监控时间段、监控平台、AI 分析结果等信息
   - 支持发送到飞书、企业微信或仅生成文件

## 🚀 快速开始

### 基本用法

#### 完整工作流（推荐）

运行完整流程，包括数据提取、AI分析和报告生成：

```powershell
# Windows PowerShell
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13

# 不发送到飞书，只生成报告文件
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 --skip-send
```

#### Linux/Mac

```bash
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13
```

## 📝 命令行参数详解

### 必需参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `--start-date` | YYYY-MM-DD | 开始日期（必需） | `2026-01-07` |
| `--end-date` | YYYY-MM-DD | 结束日期（必需） | `2026-01-13` |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--companies` | 字符串列表 | 所有公司 | 指定要处理的公司列表（空格分隔） |
| `--db-path` | 文件路径 | `db/competitor_data.db` | 数据库文件路径 |
| `--output-dir` | 目录路径 | `output/` | 输出目录 |
| `--skip-extract` | 标志 | False | 跳过数据提取步骤（需提供 `--extracted-data`） |
| `--skip-analysis` | 标志 | False | 跳过 AI 分析步骤（需提供 `--analysis-result`） |
| `--skip-report` | 标志 | False | 跳过报告生成步骤 |
| `--skip-send` | 标志 | False | 跳过发送到飞书，只生成报告文件 |
| `--send-to-wework` | 标志 | False | 同时发送到企业微信（需要配置 WEWORK_WEBHOOK_URL） |
| `--extracted-data` | 文件路径 | 无 | 提取数据的 JSON 文件路径（跳过提取时使用） |
| `--analysis-result` | 文件路径 | 无 | 分析结果的 JSON 文件路径（跳过分析时使用） |

## 💡 使用场景和示例

### 场景1：完整工作流（提取+分析+报告）

适用于日常监控，需要完整的分析报告：

```powershell
# 分析最近7天的数据并发送到飞书
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13
```

### 场景2：只提取数据

适用于数据提取时间较长，需要分步执行：

```powershell
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --skip-analysis --skip-report
```

输出文件：`output/competitor_extracted_data_2026-01-07_to_2026-01-13.json`

### 场景3：只进行 AI 分析

使用已有的提取数据进行 AI 分析：

```powershell
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --skip-extract --skip-report `
    --extracted-data output/competitor_extracted_data_2026-01-07_to_2026-01-13.json
```

输出文件：`output/competitor_analysis_result_2026-01-07_to_2026-01-13.json`

### 场景4：只生成报告

使用已有的分析结果生成报告：

```powershell
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --skip-extract --skip-analysis `
    --analysis-result output/competitor_analysis_result_2026-01-07_to_2026-01-13.json
```

或者直接调用报告生成模块：

```powershell
python CompetitorPeriodReportGenerator.py `
    --input output/competitor_analysis_result_2026-01-07_to_2026-01-13.json
```

### 场景5：分析特定公司

只分析指定的公司：

```powershell
# 单个公司
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --companies "dream games"

# 多个公司
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --companies "dream games" "vita studio" "voodoo"
```

### 场景6：测试模式（不发送到飞书）

先测试生成的文件，确认无误后再发送：

```powershell
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --skip-send
```

### 场景7：使用自定义路径

```powershell
# 自定义数据库路径
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --db-path "D:\data\competitor_data.db"

# 自定义输出目录
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --output-dir "D:\reports\output"
```

### 场景8：使用 PowerShell 动态计算日期

```powershell
# 分析最近7天的数据
$endDate = (Get-Date).ToString("yyyy-MM-dd")
$startDate = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
python CompetitorPeriodWorkflow.py --start-date $startDate --end-date $endDate
```

### 场景9：分析最近30天的数据

```powershell
$endDate = (Get-Date).ToString("yyyy-MM-dd")
$startDate = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")
python CompetitorPeriodWorkflow.py --start-date $startDate --end-date $endDate `
    --skip-send
```

## 📊 输出文件说明

### 文件命名规则

所有输出文件保存在 `output/` 目录（或 `--output-dir` 指定的目录），文件命名格式：

- **提取数据**：`competitor_extracted_data_YYYY-MM-DD_to_YYYY-MM-DD.json`
- **分析结果**：`competitor_analysis_result_YYYY-MM-DD_to_YYYY-MM-DD.json`
- **报告文件**：`competitor_period_reports_YYYY-MM-DD_to_YYYY-MM-DD.json`
- **Markdown报告**：`competitor_period_report_COMPANY_YYYY-MM-DD_to_YYYY-MM-DD.md`

### 文件结构

#### 1. 提取数据文件 (`competitor_extracted_data_*.json`)

```json
{
  "start_date": "2026-01-07",
  "end_date": "2026-01-13",
  "extracted_at": "2026-01-14T10:30:00Z",
  "companies": {
    "dream games": {
      "platforms": {
        "twitter": [
          {
            "text": "帖子内容",
            "published_at": "2026-01-07T12:00:00",
            "post_url": "https://x.com/...",
            "engagement": {...}
          }
        ]
      }
    }
  }
}
```

#### 2. 分析结果文件 (`competitor_analysis_result_*.json`)

```json
{
  "start_date": "2026-01-07",
  "end_date": "2026-01-13",
  "analyzed_at": "2026-01-14T10:35:00Z",
  "companies": {
    "dream games": {
      "platforms": {
        "twitter": {
          "summary": "平台总结",
          "posts": [
            {
              "title": "帖子标题",
              "text": "帖子内容",
              "score": 8,
              "reason": "包含玩法更新",
              "post_url": "...",
              "published_at": "..."
            }
          ]
        }
      }
    }
  }
}
```

## ⚙️ 环境配置

### 必需的环境变量

1. **AI 分析 API Key**（二选一）
   - `OPENROUTER_API_KEY` - OpenRouter API Key（推荐）
   - `OPENAI_API_KEY` - OpenAI API Key

2. **飞书 Webhook URL**（可选，仅在发送到飞书时需要）
   - `FEISHU_WEBHOOK_URL` - 飞书机器人 Webhook URL
   - 或在 `config/config.yaml` 中配置：`notification.webhooks.feishu_url`

### 配置文件

程序会自动加载 `.env` 文件中的环境变量，或从 `config/config.yaml` 读取配置。

### 数据库要求

- 数据库文件：`db/competitor_data.db`（默认路径）
- 确保数据库中包含指定时间段内的数据
- 公司名称必须与数据库中的名称完全匹配（区分大小写）

## 🔍 工作流程详解

### 完整流程

```
开始
  ↓
【第一部分】数据提取
  ├─ 从数据库读取配置
  ├─ 按日期范围提取数据
  └─ 保存提取数据到 JSON
  ↓
【第二部分】AI分析
  ├─ 读取提取的数据
  ├─ 调用 AI API 进行分析
  ├─ 评分和筛选（玩法更新、线下活动优先）
  └─ 保存分析结果到 JSON
  ↓
【第三部分】报告生成
  ├─ 读取分析结果
  ├─ 查询平台配置
  ├─ 生成飞书卡片
  ├─ 保存报告文件
  └─ 发送到飞书（可选）
  ↓
完成
```

### 分步执行流程

如果使用 `--skip-*` 参数跳过某些步骤，需要确保提供相应的中间文件：

```
跳过提取 → 需提供 --extracted-data
跳过分析 → 需提供 --analysis-result
跳过报告 → 不生成报告文件，不发送飞书
跳过发送 → 生成报告文件但不发送
```

## 💡 最佳实践

### 1. 首次使用建议

```powershell
# 先测试，不发送到飞书
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13 `
    --skip-send

# 查看生成的文件，确认无误后再发送
python CompetitorPeriodWorkflow.py --start-date 2026-01-07 --end-date 2026-01-13
```

### 2. 数据量较大时的策略

```powershell
# 第一步：提取数据（可能耗时较长）
python CompetitorPeriodWorkflow.py --start-date 2026-01-01 --end-date 2026-01-31 `
    --skip-analysis --skip-report

# 第二步：AI分析（可能需要多次重试）
python CompetitorPeriodWorkflow.py --start-date 2026-01-01 --end-date 2026-01-31 `
    --skip-extract --skip-report `
    --extracted-data output/competitor_extracted_data_2026-01-01_to_2026-01-31.json

# 第三步：生成报告（可以多次执行，修改报告格式）
python CompetitorPeriodWorkflow.py --start-date 2026-01-01 --end-date 2026-01-31 `
    --skip-extract --skip-analysis `
    --analysis-result output/competitor_analysis_result_2026-01-01_to_2026-01-31.json
```

### 3. 定期监控脚本

创建一个 PowerShell 脚本 `weekly_report.ps1`：

```powershell
# weekly_report.ps1
$endDate = (Get-Date).ToString("yyyy-MM-dd")
$startDate = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")

Write-Host "分析时间段: $startDate 至 $endDate"

python CompetitorPeriodWorkflow.py --start-date $startDate --end-date $endDate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 工作流执行成功"
} else {
    Write-Host "❌ 工作流执行失败"
}
```

然后使用 Windows 任务计划程序或 cron 定期执行。

### 4. 错误处理

- 如果 AI 分析失败，可以重新执行第二部分（不需要重新提取数据）
- 如果报告生成失败，可以重新执行第三部分（不需要重新分析）
- 所有中间文件都保存在 `output/` 目录，可以手动查看和调试

## ⚠️ 常见问题

### Q1: 日期格式错误

**错误信息**：
```
❌ 日期格式错误: ...
   请使用 YYYY-MM-DD 格式，例如: 2026-01-07
```

**解决方案**：
- 确保日期格式为 `YYYY-MM-DD`
- 使用 `--` 连接符，不是 `/` 或 `.`

### Q2: 开始日期晚于结束日期

**错误信息**：
```
❌ 开始日期不能晚于结束日期
```

**解决方案**：
- 检查日期参数顺序
- 确保 `--start-date` 早于或等于 `--end-date`

### Q3: 跳过数据提取但未提供文件

**错误信息**：
```
❌ 跳过数据提取步骤但未提供提取数据文件路径
```

**解决方案**：
- 使用 `--skip-extract` 时必须提供 `--extracted-data` 参数
- 确保文件路径正确且文件存在

### Q4: 跳过分析但未提供文件

**错误信息**：
```
❌ 跳过AI分析步骤但未提供分析结果文件路径
```

**解决方案**：
- 使用 `--skip-analysis` 时必须提供 `--analysis-result` 参数
- 确保文件路径正确且文件存在

### Q5: 未找到任何数据

**提示信息**：
```
⚠️ 未找到任何数据，工作流终止
```

**可能原因**：
- 数据库中不存在指定时间段的数据
- 公司名称不匹配（区分大小写）
- 数据库路径错误

**解决方案**：
- 检查数据库文件路径
- 确认公司名称与数据库中的完全一致
- 检查数据库中是否有对应时间段的数据

### Q6: AI 分析失败

**可能原因**：
- API Key 未配置或无效
- 网络连接问题
- API 配额用尽

**解决方案**：
- 检查 `.env` 文件中的 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`
- 检查网络连接
- 查看终端输出的详细错误信息

### Q7: 没有发送到飞书

**可能原因**：
- 使用了 `--skip-send` 参数
- 飞书 Webhook URL 未配置
- Webhook URL 无效

**解决方案**：
- 确认未使用 `--skip-send` 参数
- 检查环境变量 `FEISHU_WEBHOOK_URL` 或配置文件
- 测试 Webhook URL 是否有效

### Q8: 监控平台数显示为0

**已修复**：代码已更新，现在会正确查询包括游戏级平台在内的所有平台。

如果仍然出现此问题：
- 检查数据库中是否存在平台配置
- 确认平台配置已启用（`enabled=1`）

## 📤 企业微信发送

### 方式1：在工作流中直接发送

在工作流执行时同时发送到企业微信：

```powershell
# 同时发送到飞书和企业微信
python CompetitorPeriodWorkflow.py --start-date 2026-01-12 --end-date 2026-01-18 --send-to-wework

# 只发送到企业微信（跳过飞书）
python CompetitorPeriodWorkflow.py --start-date 2026-01-12 --end-date 2026-01-18 --skip-send --send-to-wework
```

### 方式2：从已生成的报告文件发送（推荐）

如果已经生成了报告文件，可以使用独立脚本 `SendReportToWeWork.py` 发送到企业微信：

```powershell
# 发送所有公司的报告（默认使用Markdown格式）
python SendReportToWeWork.py --input output/competitor_period_reports_2026-01-12_to_2026-01-18.json

# 只发送指定公司的报告
python SendReportToWeWork.py --input output/competitor_period_reports_2026-01-12_to_2026-01-18.json --company "Dream Games"

# 发送并同时保存Markdown文件
python SendReportToWeWork.py --input output/competitor_period_reports_2026-01-12_to_2026-01-18.json --save-md

# 指定Markdown文件输出目录
python SendReportToWeWork.py --input output/competitor_period_reports_2026-01-12_to_2026-01-18.json --save-md --output-dir output/markdown

# 使用text格式发送（而不是markdown）
python SendReportToWeWork.py --input output/competitor_period_reports_2026-01-12_to_2026-01-18.json --msg-type text
```

### 配置企业微信 Webhook

#### 方式1：环境变量

```powershell
# Windows PowerShell
$env:WEWORK_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
$env:WEWORK_MSG_TYPE = "markdown"  # 或 "text"
```

#### 方式2：配置文件

在 `config/config.yaml` 中配置：

```yaml
notification:
  webhooks:
    wework_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    wework_msg_type: "markdown"  # 或 "text"
```

### 获取企业微信 Webhook

1. 在企业微信群中添加机器人
2. 获取机器人的 Webhook URL
3. URL 格式：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY`

### 消息格式说明

- **Markdown 格式**（推荐）：适合群机器人，支持富文本格式
- **Text 格式**：纯文本格式，自动去除 Markdown 标记

## 📚 相关文档

- [竞品数据爬取使用说明.md](./竞品数据爬取使用说明.md) - 数据爬取程序使用说明
- [竞品时间段监控工作流使用说明.md](./竞品时间段监控工作流使用说明.md) - 简化版使用说明
- [数据库使用说明.md](./数据库使用说明.md) - 数据库结构和操作说明

## 🔗 相关模块

- `CompetitorPeriodDataExtractor.py` - 数据提取模块
- `CompetitorPeriodAnalysisAI.py` - AI 分析模块
- `CompetitorPeriodReportGenerator.py` - 报告生成模块
- `CompetitorDatabaseDB.py` - 数据库操作模块
- `SendReportToWeWork.py` - 企业微信发送脚本（独立使用）

## 📞 获取帮助

运行以下命令查看帮助信息：

```powershell
python CompetitorPeriodWorkflow.py --help
```

或查看源代码中的 `main()` 函数，包含详细的参数说明和示例。
