---
name: competitor-monitoring
description: >
  当用户希望运行「竞品社媒每日监控」或「竞品某一时间段/周报工作流」时，
  使用本技能调用本目录内的 Python 脚本（每日爬虫 + 日报工作流 + 周期工作流），
  自动完成数据抓取、AI 分析、日报/周报生成和飞书/企业微信推送。
user-invocable: true
---

## 独立项目说明

**本技能目录即独立项目根目录**，已包含运行所需的全部脚本与配置模板，可直接打包交付（如交给 OpenClaw 或他人使用）。所有路径与命令均以**本目录为当前工作目录**执行。

- 目录结构：`env_loader.py`、`database/`、`scrapers/`、`analyzers/`、`reports/`、`workflows/`、`input/`、`config/`、`requirements.txt`、`.env.example`。
- 使用前：在本目录下执行 `pip install -r requirements.txt`，复制 `.env.example` 为 `.env` 并填写密钥，将竞品配置放入 `input/twitter_input.json`。

## When to Use / 何时触发

- 当用户说「跑一下竞品每日爬虫/日报」「生成昨天的竞品日报」「给我今天的竞品社媒监控」。
- 当用户说「生成某个时间段/一周的竞品社媒周报」「做 1 月 7 号到 1 月 13 号的竞品复盘」。
- 当工作目录为本技能目录（或已将该目录作为独立项目打开），可调用：
  - `scrapers/daily_scraper.py`
  - `workflows/daily_workflow.py`
  - `workflows/period_workflow.py`

> 如果用户需求与「竞品社媒监控/日报/周报」无关，不要使用本技能。

## Required Inputs / 必需输入

根据场景不同，所需输入如下：

- **通用必需条件**
  - 当前工作目录为**本技能目录**（即独立项目根，包含 `scrapers/`、`workflows/`、`database/` 等）。
  - 已安装并激活 Python 虚拟环境（推荐 Python 3.10+），并在本目录下执行 `pip install -r requirements.txt`。
  - 已将 `.env.example` 复制为 `.env` 并填写所需密钥（或通过环境变量配置）。
  - `db/competitor_data.db` 会在首次运行爬虫时自动创建；竞品/平台配置需通过 `input/twitter_input.json` 提供（或由每日爬虫从该文件同步到数据库）。

- **每日监控 / 日报**
  - 日期：
    - 默认：昨天（`days_ago=1`）。
    - 可选：用户指定 `--days-ago` 或 `--date`（YYYY-MM-DD）。
  - 公司范围（可选）：
    - 不指定：所有公司。
    - 指定：`["voodoo", "dream_games", ...]`。
  - 输入配置路径（可选，默认自动探测）：
    - 环境变量 `COMPETITOR_INPUT_PATH`，或
    - 相对路径 `input/twitter_input.json`。

- **时间段监控 / 周报**
  - 时间段：
    - `start_date`: 开始日期（YYYY-MM-DD）。
    - `end_date`: 结束日期（YYYY-MM-DD），必须 ≥ `start_date`。
  - 公司范围（可选）：
    - 不指定：所有公司。
    - 指定：`["voodoo", "dream_games", ...]`。
  - 平台过滤（可选）：
    - 例如：`["twitter", "tiktok", "facebook", "instagram"]`。
  - 周报保存模式（可选）：
    - `"overwrite"`：覆盖数据库中的该周期周报。
    - `"use_cached"`：如果已有该周期周报则不覆盖。

- **环境变量 / 配置（参考 `.env.example` 与 `config/config.example.yaml`）**
  - 爬虫 / API：
    - `RAPIDAPI_KEY` / `RAPIDAPI_KEY_2` / `RAPIDAPI_KEY_3`
  - AI 大模型：
    - `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`
    - 可选：`OPENROUTER_MODEL`，`OPENROUTER_MODEL_FALLBACKS`，`OPENAI_TIMEOUT`
  - 通知 & Webhook：
    - 飞书：`FEISHU_WEBHOOK_URL`，或在 `config/config.yaml` 中配置 `notification.webhooks.feishu_url`
    - 企业微信（周期周报可用）：`WEWORK_WEBHOOK_URL`（以及可选 `WEWORK_MSG_TYPE`）
  - 其它（可选）：
    - `COMPETITOR_INPUT_PATH`：输入 JSON 配置路径
    - `COMPETITOR_DB_DIR` / `OUTPUT_DIR`：历史库与输出目录
    - 代理：`PROXY_URL`，`DISABLE_PROXY`

## Step-by-Step Workflow / 步骤说明

### A. 每日爬虫（写入数据库）

1. **确认环境**
   1. 确保已激活虚拟环境，且当前工作目录为**本技能目录**。
   2. 已执行 `pip install -r requirements.txt`，可正常导入 `env_loader`、`scrapers`、`database` 等模块。
   3. 已配置 `.env`（脚本会通过 `env_loader` 自动加载）。
2. **准备配置**
   1. 确保本目录下 `input/twitter_input.json` 存在并包含 `competitors` 配置。
   2. `db/competitor_data.db` 会在首次运行时由 `database.competitor_db` 自动创建。
3. **运行每日爬虫**
   - 在本目录下从命令行调用：
     - 默认抓取今天：`python scrapers/daily_scraper.py`
     - 指定目标日期/天数：使用脚本内 `scrape_all_companies_to_database` 的参数（如 `--days-ago` 或 `--date`，根据脚本 CLI 实现）。
   - 该步骤会：
     - 从 `input/twitter_input.json` 读取配置。
     - 按公司/平台抓取 Twitter/TikTok/Instagram/Facebook 数据。
     - 调用 `scrapers/rapidapi.py` 和 Facebook 专用逻辑。
     - 将原始数据写入 `db/competitor_data.db`。

### B. 日报工作流（生成日报 + AI 分析 + 飞书推送）

1. **确认已完成步骤 A**（数据库中已有指定日期的原始数据）。
2. **根据用户需求确定参数**：
   - `--days-ago`（默认 1）或 `--date`（可选）。
   - `--companies`（可选：一组公司名）。
   - 是否跳过 AI：`--skip-ai`（默认不跳过）。
   - 是否跳过推送：`--skip-send`（默认推送）。
   - 输入 JSON 路径：`--input`（默认 `/input/twitter_input.json` 或自动探测）。
3. **调用脚本**
   - 命令行示例：
     - `python workflows/daily_workflow.py --days-ago 1`
     - `python workflows/daily_workflow.py --date 2026-02-24 --companies voodoo dream_games`
4. **内部流程（由技能遵循，不需向用户详细展开）**
   1. 读取输入配置（`load_input_json` + `parse_all_platform_accounts`）。
   2. 调用平台级爬虫（仅针对指定日期）并写入历史库 `CompetitorHistoryDB`。
   3. 使用 `analyzers/daily_ai.py` 中的 `build_competitor_prompt_for_daily` + `call_model_with_retry` 做 AI 分析。
   4. 为每个公司生成 Markdown 日报和 JSON 报告（写入 `output/` 与 `db/reports/`）。
   5. 使用 `send_company_report_to_feishu` 构建飞书卡片并调用 webhook 推送。

### C. 时间段工作流（周报 / 任意时间段复盘）

1. **确认环境与依赖**
   - 与每日工作流相同；额外依赖 `dotenv`（脚本已使用 `load_dotenv()`）。
2. **确定时间段与公司范围**
   - `--start-date` 与 `--end-date`（YYYY-MM-DD）。
   - 可选：`--companies`、`--platforms`、`--skip-send`、`--send-to-wework`、`--report-save-mode`。
3. **初次完整运行**
   - 命令行示例：
     - `python workflows/period_workflow.py --start-date 2026-01-07 --end-date 2026-01-13`
4. **如需分阶段运行（可选）**
   - 仅提取数据：
     - `python workflows/period_workflow.py --start-date ... --end-date ... --skip-analysis --skip-report`
   - 在已有提取数据基础上只做 AI 分析：
     - `python workflows/period_workflow.py --start-date ... --end-date ... --skip-extract --skip-report --extracted-data output/competitor_extracted_data_...json`
   - 在已有分析结果基础上只生成报告：
     - `python workflows/period_workflow.py --start-date ... --end-date ... --skip-extract --skip-analysis --analysis-result output/competitor_analysis_result_...json`
5. **内部流程（由技能遵循）**
   1. 使用 `reports.period_extractor.CompetitorPeriodDataExtractor` 从数据库提取给定时间段内的数据。
   2. 调用 `analyzers.period_ai.analyze_extracted_data`，按公司对整段时间的帖子做一次合并分析。
   3. 使用 `reports.period_generator.generate_period_reports` 生成周报/周期报告，保存至数据库并可选推送飞书/企业微信。

## Output Format / 输出格式

- **每日工作流输出**
  - 每个公司的 Markdown 报告文件：
    - 路径类似：`output/daily_report_{company_slug}_{YYYY-MM-DD}.md`
  - 每个公司的 JSON 报告：
    - 路径类似：`db/reports/{company_slug}_{YYYY-MM-DD}.json`
    - 结构包含：
      - `company`：公司名称
      - `date`：报告日期
      - `markdown_content`：完整 Markdown 文本
      - `ai_results`：按「公司-平台」粒度的 AI 分析结果字典
      - `platforms_data`：原始平台数据摘要
  - 飞书通知（卡片消息）：
    - 每个公司一条卡片，包含日期、来源链接、各平台摘要与行动建议。

- **时间段工作流输出**
  - 中间产物 JSON（可复用）：
    - 提取数据：`output/competitor_extracted_data_{start}_to_{end}.json`
    - AI 分析：`output/competitor_analysis_result_{start}_to_{end}.json`
  - 周报/周期报告：
    - 由 `reports/period_generator.py` 写入数据库（公司维度的 summary + 评分等）。
  - 通知：
    - 飞书卡片或企业微信 markdown 文本（取决于配置）。

## Error Handling & Stop Conditions / 错误处理

当使用本技能驱动工作流时，务必遵循以下检查和兜底逻辑：

1. **环境/依赖错误**
   - 若无法导入关键模块（如 `env_loader`、`database.competitor_db` 等）：
     - 提示用户先以**本技能目录**为当前目录，创建/激活虚拟环境并执行：
       - `pip install -r requirements.txt`
     - 停止当前运行，不要继续调用脚本。
2. **配置/数据库缺失**
   - 若 `input/twitter_input.json` 不存在：
     - 明确提示用户需要先准备该文件（可参考现有样例），然后再重试。
   - 若 `db/competitor_data.db` 完全不存在：
     - 先运行每日爬虫脚本以初始化数据库，再进行日报/时间段分析。
3. **环境变量或密钥缺失**
   - 若缺少 `OPENROUTER_API_KEY`/`OPENAI_API_KEY`：
     - 允许继续跑「纯数据抓取 + 报告生成」，但**跳过 AI 分析**（传 `--skip-ai` 或在逻辑上识别空结果），并在日志中提示「AI 分析被跳过」。
   - 若缺少 `FEISHU_WEBHOOK_URL` 且 `config/config.yaml` 中也没有 `notification.webhooks.feishu_url`：
     - 允许生成本地报告文件，但**跳过推送步骤**，并在输出中说明原因。
4. **外部 API 失败（RAPIDAPI / OpenAI / OpenRouter 等）**
   - 在脚本内部已有重试逻辑（如 `call_model_with_retry`），本技能无需重复实现重试。
   - 若某个平台数据抓取失败：
     - 记录错误，但继续处理其它平台与公司。
5. **停止条件**
   - 若连续出现严重配置错误（如缺少关键文件/数据库，或日期非法）：
     - 立即停止本轮工作流，并向用户返回清晰的错误信息与下一步修复建议。

## Notes / 额外说明

- 本技能目录为**独立可运行项目**，脚本均位于本目录内；Agent 调用时请以本目录为工作目录执行上述命令。
- 如需扩展平台或报告格式，可直接修改本目录下的 `scrapers/`、`analyzers/`、`reports/`、`workflows/` 代码，并视需要更新本 `SKILL.md`。

