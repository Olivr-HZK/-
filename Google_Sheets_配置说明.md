# Google Sheets 导出配置说明

## 📋 概述

本说明介绍如何配置和使用 `export_to_google_sheets.py` 脚本，将数据库中的**社交媒体更新（帖子/视频数据）**导出到 Google Sheets。

## 🔧 前置准备

### 1. 安装必要的 Python 库

```powershell
pip install gspread google-auth
```

### 2. 创建 Google Service Account

1. **访问 Google Cloud Console**
   - 打开 https://console.cloud.google.com/
   - 创建新项目或选择现有项目

2. **启用 Google Sheets API 和 Google Drive API**
   - 在左侧菜单选择 "API 和服务" > "库"
   - 搜索 "Google Sheets API"，点击启用
   - 搜索 "Google Drive API"，点击启用

3. **创建 Service Account**
   - 在左侧菜单选择 "API 和服务" > "凭据"
   - 点击 "创建凭据" > "服务账号"
   - 填写服务账号名称（例如：sheets-exporter）
   - 点击 "创建并继续"
   - 角色选择：可以跳过或选择 "Editor"
   - 点击 "完成"

4. **创建密钥**
   - 在服务账号列表中，点击刚创建的服务账号
   - 切换到 "密钥" 标签页
   - 点击 "添加密钥" > "创建新密钥"
   - 选择 "JSON" 格式
   - 点击 "创建"
   - 下载的 JSON 文件就是你的凭证文件，**请妥善保管**

### 3. 共享 Google Sheets 表格（如果使用现有表格）

如果使用现有表格，需要将表格共享给服务账号的邮箱：

1. 打开你的 Google Sheets 表格
2. 点击右上角的 "共享" 按钮
3. 在 "添加用户和组" 中输入服务账号的邮箱（格式：`服务账号名称@项目ID.iam.gserviceaccount.com`）
4. 权限设置为 "编辑者"
5. 点击 "发送"

## 📝 使用方法

### 方法 1：创建新表格

```powershell
# 使用环境变量指定凭证路径
$env:GOOGLE_CREDENTIALS_PATH = "path/to/credentials.json"
python export_to_google_sheets.py --create-new

# 或使用命令行参数
python export_to_google_sheets.py --create-new --credentials path/to/credentials.json
```

脚本会：
- 创建新的 Google Sheets 表格
- 自动设置表格为公开只读（可选）
- 显示表格 ID 和 URL

### 方法 2：使用现有表格

```powershell
# 使用环境变量
$env:GOOGLE_CREDENTIALS_PATH = "path/to/credentials.json"
$env:GOOGLE_SPREADSHEET_ID = "your_spreadsheet_id"
python export_to_google_sheets.py

# 或使用命令行参数
python export_to_google_sheets.py \
    --credentials path/to/credentials.json \
    --spreadsheet-id your_spreadsheet_id
```

### 方法 3：导出指定日期范围的数据

```powershell
# 导出最近7天的数据
python export_to_google_sheets.py \
    --credentials path/to/credentials.json \
    --spreadsheet-id your_spreadsheet_id \
    --start-date 2026-01-10 \
    --end-date 2026-01-17
```

### 方法 4：导出指定公司的数据

```powershell
# 只导出 King 和 voodoo 的数据
python export_to_google_sheets.py \
    --credentials path/to/credentials.json \
    --spreadsheet-id your_spreadsheet_id \
    --companies King voodoo
```

### 方法 3：指定工作表名称

```powershell
python export_to_google_sheets.py \
    --credentials path/to/credentials.json \
    --spreadsheet-id your_spreadsheet_id \
    --worksheet-name "竞品社媒信息"
```

## 🔑 环境变量配置

可以在 `.env` 文件中配置：

```env
# Google Service Account 凭证文件路径
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json

# Google Sheets 表格 ID（如果使用现有表格）
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
```

## 📊 导出的数据字段

脚本会导出以下字段（每条帖子/视频一行）：

| 字段名 | 说明 |
|--------|------|
| 公司名称 | 公司名称 |
| 抓取日期 | 数据抓取日期 |
| 平台类型 | 平台类型（twitter/instagram/tiktok/youtube/facebook等） |
| 游戏名称 | 游戏名称（如果为游戏级平台） |
| 账号URL | 社媒账号的 URL |
| 用户名 | 平台用户名 |
| 帖子内容 | 帖子/视频的文本内容（前500字符） |
| 帖子链接 | 帖子/视频的链接 |
| 发布时间 | 帖子/视频的发布时间 |
| 点赞数 | 点赞数量 |
| 评论数 | 评论数量 |
| 分享数 | 分享数量 |
| 观看数 | 观看数量（如果有） |
| 媒体数量 | 图片/视频数量 |
| 媒体类型 | 媒体类型（图片/视频） |
| 抓取时间 | 数据抓取时间 |

## ⚙️ 命令行参数说明

| 参数 | 说明 | 必需 |
|------|------|------|
| `--db-path` | 数据库文件路径 | 否 |
| `--spreadsheet-id` | Google Sheets 表格 ID | 否* |
| `--worksheet-name` | 工作表名称 | 否（默认：社媒更新） |
| `--credentials` | Google 凭证文件路径 | 否* |
| `--create-new` | 创建新表格 | 否 |
| `--start-date` | 开始日期（YYYY-MM-DD） | 否 |
| `--end-date` | 结束日期（YYYY-MM-DD） | 否 |
| `--companies` | 指定公司列表 | 否 |

*如果使用现有表格，需要提供 `--spreadsheet-id`；如果创建新表格，需要 `--create-new`。凭证路径可以通过环境变量或 `--credentials` 参数提供。

## 🔍 获取表格 ID

Google Sheets 表格 ID 可以从表格 URL 中获取：

```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
                                    ^^^^^^^^^^^^^^^^
                                    这就是表格 ID
```

## ⚠️ 注意事项

1. **凭证文件安全**：请妥善保管 Service Account 的 JSON 凭证文件，不要提交到代码仓库
2. **API 配额**：Google Sheets API 有配额限制，大量数据可能需要分批处理
3. **权限设置**：确保服务账号有足够的权限访问表格
4. **数据覆盖**：脚本会清空现有工作表的数据，然后写入新数据
5. **存储配额**：如果遇到 "Drive storage quota has been exceeded" 错误，说明 Google Drive 存储空间已满，需要：
   - 清理 Google Drive 空间
   - 使用现有表格而不是创建新表格
   - 或升级 Google Drive 存储计划

## 🔧 解决存储配额问题

如果遇到 **"The user's Drive storage quota has been exceeded"** 错误：

### 方案 1：使用现有表格（推荐）

1. **手动创建 Google Sheets 表格**
   - 访问 https://sheets.google.com
   - 点击 "空白" 创建新表格
   - 或使用现有表格

2. **获取表格 ID**
   - 从表格 URL 中提取 ID
   - URL 格式：`https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - 例如：`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

3. **共享表格给服务账号**
   - 点击表格右上角的 "共享" 按钮
   - 输入服务账号邮箱（格式：`服务账号名称@项目ID.iam.gserviceaccount.com`）
   - 权限设置为 "编辑者"
   - 点击 "发送"

4. **运行脚本使用现有表格**
   ```powershell
   python export_to_google_sheets.py \
       --spreadsheet-id YOUR_SPREADSHEET_ID \
       --credentials path/to/credentials.json
   ```

### 方案 2：清理 Google Drive 空间

1. 访问 https://drive.google.com
2. 删除不需要的文件
3. 清空回收站
4. 然后重新运行脚本

### 方案 3：升级存储计划

- 访问 https://one.google.com/storage
- 升级到 Google One 付费计划

## 🐛 常见问题

### 问题 1：`ModuleNotFoundError: No module named 'gspread'`

**解决方法**：
```powershell
pip install gspread google-auth
```

### 问题 2：`Permission denied` 或 `403 Forbidden`

**可能原因**：
- 服务账号没有访问表格的权限
- API 未启用

**解决方法**：
1. 确保已启用 Google Sheets API 和 Google Drive API
2. 将表格共享给服务账号邮箱（编辑者权限）

### 问题 3：找不到凭证文件

**解决方法**：
- 检查凭证文件路径是否正确
- 使用绝对路径
- 确保文件存在且有读取权限

## 📚 相关文档

- [gspread 文档](https://docs.gspread.org/)
- [Google Sheets API 文档](https://developers.google.com/sheets/api)
- [Google Service Account 文档](https://cloud.google.com/iam/docs/service-accounts)
