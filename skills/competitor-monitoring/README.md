# 竞品社媒监控 Skill（独立项目）

本目录为**独立可运行项目**，包含每日爬虫、日报工作流与周期（周报）工作流所需全部脚本，可直接打包交付或交给 OpenClaw 使用。

## 目录结构

```
competitor-monitoring/
├── SKILL.md              # OpenClaw 技能说明（触发条件、步骤、输出格式）
├── README.md             # 本说明
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例（复制为 .env 后填写）
├── env_loader.py         # 环境变量加载
├── config/
│   └── config.example.yaml  # 可选配置文件示例
├── input/                # 竞品配置（需自备 twitter_input.json）
├── database/             # 数据库访问层
├── scrapers/             # 社媒爬虫（Twitter/TikTok/Instagram/Facebook）
├── analyzers/            # AI 分析
├── reports/              # 周期报告提取与生成
└── workflows/            # 入口脚本
```

## 快速开始

1. **安装依赖**（建议使用虚拟环境）  
   ```bash
   cd /path/to/competitor-monitoring
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **配置环境**  
   - 复制 `.env.example` 为 `.env`，填写 `RAPIDAPI_KEY`、`OPENROUTER_API_KEY`、`FEISHU_WEBHOOK_URL` 等。  
   - 将竞品配置 JSON 放入 `input/twitter_input.json`（格式见主项目或 `.env.example` 说明）。

3. **运行**  
   - 每日爬虫（抓取并写入数据库）：  
     `python scrapers/daily_scraper.py [--days-ago 0] [--json-path input/twitter_input.json]`  
   - 日报工作流（爬取 + AI 分析 + 日报 + 飞书推送）：  
     `python workflows/daily_workflow.py [--days-ago 1] [--input input/twitter_input.json]`  
   - 周期/周报工作流：  
     `python workflows/period_workflow.py --start-date 2026-01-07 --end-date 2026-01-13`

所有命令均需在**本目录**下执行，以便正确解析 `database`、`scrapers` 等模块。

## 输出与配置

- 数据库与输出目录默认落在本目录下的 `db/`、`workflows/output/` 等（可通过环境变量 `COMPETITOR_DB_DIR`、`OUTPUT_DIR` 覆盖）。  
- 详细步骤、必需输入、输出格式与错误处理见 **SKILL.md**。
