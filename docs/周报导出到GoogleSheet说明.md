# 周报导出到 Google Sheet 使用说明

## 📋 概述

本工具将数据库中的周报数据导出为 CSV 文件，每个公司一个 CSV，每个平台一行，所有分析字段都已展开。然后可以导入到 Google Sheet 进行进一步分析。

## 🚀 使用方法

### 1. 导出 CSV 文件

```bash
# 激活虚拟环境并设置 PYTHONPATH
cd /Users/oliver/guru/-
source .venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"

# 运行导出脚本
python3 tools/export_weekly_reports_to_csv.py
```

**输出结果：**
- 所有 CSV 文件保存在 `output/weekly_reports/` 目录
- 每个公司一个 CSV 文件，命名格式：`weekly_{公司名}.csv`
- 例如：`weekly_king.csv`, `weekly_voodoo.csv` 等

### 2. 自定义参数

```bash
# 指定数据库路径
python3 tools/export_weekly_reports_to_csv.py --db-path /path/to/competitor_data.db

# 指定输出目录
python3 tools/export_weekly_reports_to_csv.py --output-dir /path/to/output
```

## 📊 CSV 文件格式

每个 CSV 文件包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| `company` | 公司名称 | King |
| `start_date` | 周期开始日期 | 2026-01-19 |
| `end_date` | 周期结束日期 | 2026-01-25 |
| `period_days` | 监控天数 | 7 |
| `created_at` | 报告创建时间 | 2026-01-26T11:53:32.665311 |
| `platform_title` | 平台标题 | King - Candy Crush Saga - instagram |
| `platform` | 平台类型 | instagram, twitter, facebook |
| `game` | 游戏名称（如果有） | Candy Crush Saga |
| `url` | 平台 URL | https://www.instagram.com/candycrushsaga |
| `usability_score` | 可用性评分 | 8.0 |
| `posts_count` | 帖子数量 | 5 |
| `summary` | 摘要 | King 在过去 7 天内主要通过 Instagram... |
| `key_updates` | 重点内容 | 下周将有重磅更新... |
| `gameplay_changes` | 玩法变化 | 虽然没有直接公布新代码... |
| `offline_events` | 线下活动 | 本时段内未观察到明确的线下展会... |
| `ad_creative_insights` | 广告创意观察 | 1. 幕后背书感：引入真实员工... |
| `platform_summary` | 平台概况 | 该平台保持高频且稳定的更新节奏... |
| `risk_or_warning` | 风险或警告 | 1. 悬念营销风险... |
| `direct_action_suggestions` | 建议动作 | 尝试制作以'策划面对面'...（多条用换行分隔） |

**数据特点：**
- **一行 = 一个平台在某个周期的分析**
- 如果一个公司有多个周报，每个周报的每个平台都会有一行
- 所有分析字段都已展开为独立的列

## 📤 导入到 Google Sheet

### 方法一：手动导入（推荐，简单稳定）

1. **打开 Google Drive**，创建或打开一个 Google Sheet

2. **导入 CSV 文件**：
   - 点击 `文件` → `导入`
   - 选择 `上传` 标签
   - 选择要导入的 CSV 文件（如 `weekly_king.csv`）
   - 选择导入选项：
     - **"插入到当前工作表"** - 在当前工作表追加数据
     - **"新建工作表"** - 为每个 CSV 创建一个新的工作表（推荐）
   - 点击 `导入数据`

3. **为每个公司创建独立的工作表**：
   - 如果选择"新建工作表"，每个 CSV 会自动创建一个工作表
   - 工作表名称可以手动重命名为公司名（如 "King"）

4. **重复步骤 2-3**，导入所有公司的 CSV 文件

### 方法二：使用 Google Sheets API 自动导入（高级）

如果需要完全自动化，可以使用 `tools/export_sheets.py` 作为参考，编写自动上传脚本。

**前提条件：**
1. 在 Google Cloud Console 创建项目并启用 Google Sheets API
2. 创建 Service Account 并下载 JSON 凭证
3. 在 Google Sheet 中共享给 Service Account 的邮箱
4. 安装依赖：`pip install gspread google-auth`

## 📈 在 Google Sheet 中分析数据

导入后，你可以：

1. **筛选和排序**：
   - 按公司、平台、日期范围筛选
   - 按可用性评分排序，找出最重要的更新

2. **数据透视表**：
   - 按公司统计平台数量
   - 按平台类型统计平均评分
   - 按日期范围统计更新频率

3. **图表可视化**：
   - 创建柱状图显示各公司的平台更新数量
   - 创建折线图显示评分趋势
   - 创建饼图显示平台类型分布

4. **条件格式**：
   - 高评分（>8.0）用绿色标记
   - 低评分（<3.0）用红色标记
   - 突出显示包含"玩法变化"的行

## 🔄 定期更新

每次生成新的周报后，重新运行导出脚本：

```bash
# 重新导出（会覆盖现有 CSV 文件）
python3 tools/export_weekly_reports_to_csv.py
```

然后在 Google Sheet 中：
- 删除旧数据
- 重新导入新的 CSV 文件
- 或者使用 Google Sheets API 自动更新

## 📝 示例：查看 King 公司的数据

```bash
# 查看 King 公司的 CSV 文件
cat output/weekly_reports/weekly_king.csv | head -5

# 或者用 Excel/Numbers 打开
open output/weekly_reports/weekly_king.csv
```

## ❓ 常见问题

### Q1: CSV 文件中的中文显示乱码？

**解决方案：** CSV 文件使用 UTF-8 编码。在 Google Sheet 导入时：
- 选择 `文件` → `导入`
- 在导入设置中，确保 `字符编码` 选择 `UTF-8`

### Q2: 如何只导出特定公司的数据？

**解决方案：** 可以修改脚本，添加 `--companies` 参数过滤，或者：
- 导出所有数据后，在 Google Sheet 中筛选
- 只导入需要的 CSV 文件

### Q3: 如何合并多个周报的数据？

**解决方案：** 
- 在 Google Sheet 中，每个公司的 CSV 导入到一个工作表
- 如果同一公司有多个周报，它们会在同一个 CSV 中，按日期排序
- 可以使用数据透视表按日期分组分析

## 📚 相关文档

- [数据库使用说明](数据库使用说明.md)
- [数据库初始化说明](数据库初始化说明.md)
- [Google Sheets 配置说明](Google_Sheets_配置说明.md)
