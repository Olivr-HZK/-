"""
将数据库中的周报数据导出为 CSV 文件（行格式）
每个公司每个平台一行，一个 CSV 包含所有公司所有平台
"""
import os
import sys
import csv
import json
import sqlite3
import re
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

# 添加项目根目录到 Python 路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import env_loader  # noqa: F401
except ImportError:
    pass  # env_loader 是可选的

from database.competitor_db import CompetitorDatabaseDB


def slugify(name: str) -> str:
    """把公司名转成安全的文件名"""
    if not name:
        return "unknown"
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]+", "", name)
    return name or "unknown"


def get_platform_column_name(company: str, platform: str, game: Optional[str] = None) -> str:
    """生成平台列名：公司_平台_游戏（如果有游戏）"""
    parts = [company]
    if game:
        parts.append(game)
    parts.append(platform)
    return "_".join(parts)


def ensure_output_dir(output_dir: str) -> None:
    """确保输出目录存在"""
    os.makedirs(output_dir, exist_ok=True)


def export_weekly_reports_to_csv_wide(
    db_path: Optional[str] = None,
    output_dir: str = "output/weekly_reports_wide"
) -> None:
    """
    将数据库中的周报数据导出为 CSV 文件（行格式）
    每个公司每个平台一行，一个 CSV 包含所有公司所有平台
    
    Args:
        db_path: 数据库文件路径（可选，默认为 db/competitor_data.db）
        output_dir: 输出目录（默认: output/weekly_reports_wide）
    """
    print("=" * 60)
    print("📊 导出周报数据到 CSV（行格式：每个公司每个平台一行）")
    print("=" * 60)
    
    # 确定数据库路径
    if db_path is None:
        project_root = Path(__file__).parent.parent
        db_path = project_root / "db" / "competitor_data.db"
        if not db_path.exists():
            # 尝试 Docker 环境路径
            docker_db_path = Path("/app/db/competitor_data.db")
            if docker_db_path.exists():
                db_path = docker_db_path
            else:
                print(f"❌ 数据库文件不存在: {db_path}")
                return
    
    db_path = str(db_path)
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"📁 数据库路径: {db_path}")
    print(f"📁 输出目录: {output_dir}")
    print()
    
    # 确保输出目录存在
    ensure_output_dir(output_dir)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 查询所有周报
    cur.execute(
        "SELECT company_name, start_date, end_date, report_content, created_at "
        "FROM weekly_reports "
        "ORDER BY company_name, start_date DESC, end_date DESC"
    )
    rows = cur.fetchall()
    
    if not rows:
        print("⚠️ 数据库中没有周报数据")
        conn.close()
        return
    
    print(f"📋 找到 {len(rows)} 条周报记录")
    print()
    
    # 行格式：一个平台一行
    # 定义列顺序
    header = [
        "company",                    # 公司名称
        "start_date",                 # 周期开始日期
        "end_date",                   # 周期结束日期
        "period_days",                # 监控天数
        "created_at",                 # 报告创建时间
        "platform_title",             # 平台标题
        "platform",                   # 平台类型
        "game",                       # 游戏名称
        "url",                        # 平台 URL
        "usability_score",            # 可用性评分
        "weekly_score",               # 周报评分（新玩法/线下活动高分）
        "weekly_title",               # 周报简短标题
        "posts_count",                # 帖子数量
        "summary",                    # 摘要
        "key_updates",                # 重点内容
        "gameplay_changes",           # 玩法变化
        "offline_events",            # 线下活动
        "ad_creative_insights",      # 广告创意观察
        "platform_summary",          # 平台概况
        "risk_or_warning",           # 风险或警告
        "direct_action_suggestions", # 建议动作
    ]
    
    success_count = 0
    error_count = 0
    
    # 处理每条周报记录，直接写入行
    all_rows: list[list[str]] = []
    for row in rows:
        company_name = row["company_name"]
        start_date = row["start_date"]
        end_date = row["end_date"]
        created_at = row["created_at"]
        content = row["report_content"]
        
        if not content:
            continue
        
        try:
            data = json.loads(content)
        except Exception as exc:
            print(f"❌ 解析 JSON 失败: company={company_name}, error={exc}")
            error_count += 1
            continue
        
        company = data.get("company") or company_name
        period_days = None
        if isinstance(data.get("period"), dict):
            period_days = data["period"].get("days")
        
        platforms_analysis: Dict[str, Any] = data.get("platforms_analysis") or {}
        if not platforms_analysis and data.get("company_analysis"):
            ca = data["company_analysis"]
            ana = {
                "summary": ca.get("summary", ""),
                "key_updates": "",
                "gameplay_changes": ca.get("new_gameplay", ""),
                "offline_events": ca.get("offline_events", ""),
                "ad_creative_insights": "",
                "platform_summary": ca.get("routine_note", ""),
                "risk_or_warning": "",
                "direct_action_suggestions": ca.get("direct_action_suggestions") or [],
            }
            plat = {
                "title": f"{company} 汇总",
                "platform": "",
                "game": "",
                "url": "",
                "usability_score": ca.get("weekly_score", ""),
                "weekly_score": ca.get("weekly_score", ""),
                "weekly_title": ca.get("weekly_title", ""),
                "posts_count": ca.get("posts_count", ""),
                "analysis": ana,
            }
            platforms_analysis = {"公司汇总": plat}
        if not platforms_analysis:
            continue
        
        # 遍历该周报的所有平台分析
        for key, plat in platforms_analysis.items():
            # plat 是单个平台的整体信息
            ana = plat.get("analysis") or {}
            
            platform = plat.get("platform") or ""
            game = plat.get("game") or ""
            
            # 处理 direct_action_suggestions（列表转文本）
            suggestions = ana.get("direct_action_suggestions") or []
            if isinstance(suggestions, list):
                suggestions_text = "\n".join(suggestions)
            else:
                suggestions_text = str(suggestions) if suggestions else ""
            
            # 构建一行数据（每个公司每个平台一行）
            row_data = [
                company,
                data.get("start_date") or start_date,
                data.get("end_date") or end_date,
                str(period_days) if period_days else "",
                created_at,
                plat.get("title") or key,
                platform,
                game,
                plat.get("url") or "",
                str(plat.get("usability_score", "")) if plat.get("usability_score") else "",
                str(plat.get("weekly_score", "")) if plat.get("weekly_score") else "",
                plat.get("weekly_title", "") or "",
                str(plat.get("posts_count", "")) if plat.get("posts_count") else "",
                ana.get("summary", ""),
                ana.get("key_updates", ""),
                ana.get("gameplay_changes", ""),
                ana.get("offline_events", ""),
                ana.get("ad_creative_insights", ""),
                ana.get("platform_summary", ""),
                ana.get("risk_or_warning", ""),
                suggestions_text,
            ]
            all_rows.append(row_data)
            success_count += 1

    if not all_rows:
        print("⚠️ 没有找到任何平台数据")
        conn.close()
        return

    # 生成 CSV 文件（行格式，一个文件包含所有公司所有平台）
    csv_path = os.path.join(output_dir, "weekly_reports_rows.csv")

    print(f"📝 生成 CSV: {csv_path}")
    print(f"   行数: {len(all_rows)}（每行一个公司一个平台）")
    print(f"   列数: {len(header)} 字段")
    print()

    # 写入 CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row_data in all_rows:
            writer.writerow(row_data)
    
    conn.close()
    
    print()
    print("=" * 60)
    print("📊 导出总结")
    print("=" * 60)
    print(f"  成功导出: {success_count} 个平台（行）")
    if error_count > 0:
        print(f"  失败: {error_count} 条记录")
    print(f"  生成文件: {csv_path}")
    print(f"  行数: {len(all_rows)}（每行一个公司一个平台）")
    print(f"  列数: {len(header)} 字段")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="将数据库中的周报数据导出为 CSV 文件（行格式：每个公司每个平台一行）"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/weekly_reports_wide",
        help="输出目录（默认: output/weekly_reports_wide）"
    )
    
    args = parser.parse_args()
    
    export_weekly_reports_to_csv_wide(
        db_path=args.db_path,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    sys.exit(main())
