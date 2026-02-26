"""
将数据库中的周报数据导出为 CSV 文件
每个公司一个 CSV 文件，每个平台一行，所有分析字段展开
"""
import os
import sys
import csv
import json
import sqlite3
import re
from typing import Dict, Any, Optional
from pathlib import Path

import env_loader  # noqa: F401

from database.competitor_db import CompetitorDatabaseDB


def slugify(name: str) -> str:
    """把公司名转成安全的文件名"""
    if not name:
        return "unknown"
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]+", "", name)
    return name or "unknown"


def ensure_output_dir(output_dir: str) -> None:
    """确保输出目录存在"""
    os.makedirs(output_dir, exist_ok=True)


def export_weekly_reports_to_csv(
    db_path: Optional[str] = None,
    output_dir: str = "output/weekly_reports"
) -> None:
    """
    将数据库中的周报数据导出为 CSV 文件
    
    Args:
        db_path: 数据库文件路径（可选，默认为 db/competitor_data.db）
        output_dir: 输出目录（默认: output/weekly_reports）
    """
    print("=" * 60)
    print("📊 导出周报数据到 CSV")
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
    
    # 为每个公司维护一个 CSV writer
    writers: Dict[str, csv.writer] = {}
    files: Dict[str, Any] = {}
    company_stats: Dict[str, int] = {}  # 统计每个公司的平台数
    
    # 统一的列设计：一行 = 一个公司某个平台在某个周期的分析
    header = [
        "company",                    # 公司名称
        "start_date",                 # 周期开始日期
        "end_date",                   # 周期结束日期
        "period_days",                # 监控天数
        "created_at",                 # 报告创建时间
        "platform_title",             # 平台标题（如：King - Candy Crush Saga - instagram）
        "platform",                   # 平台类型（twitter / instagram / facebook / ...）
        "game",                       # 游戏名称（如果有）
        "url",                        # 平台 URL
        "usability_score",            # 可用性评分
        "weekly_score",               # 周报评分（新玩法/线下活动高分）
        "weekly_title",               # 周报简短标题
        "posts_count",                # 帖子数量
        # 分析字段全部展开
        "summary",                    # 摘要
        "key_updates",               # 重点内容
        "gameplay_changes",          # 玩法变化
        "offline_events",            # 线下活动
        "ad_creative_insights",      # 广告创意观察
        "platform_summary",          # 平台概况
        "risk_or_warning",           # 风险或警告
        "direct_action_suggestions", # 建议动作（多条用换行拼接）
    ]
    
    success_count = 0
    error_count = 0
    
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
        # 兼容新格式：按公司汇总的 company_analysis（一行代表该公司整周）
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
        
        # 为该公司准备 CSV writer（如果还没有）
        if company not in writers:
            slug = slugify(company)
            csv_path = os.path.join(output_dir, f"weekly_{slug}.csv")
            f = open(csv_path, "w", newline="", encoding="utf-8")
            writer = csv.writer(f)
            writer.writerow(header)
            writers[company] = writer
            files[company] = f
            company_stats[company] = 0
            print(f"📝 创建 CSV: {csv_path}")
        
        writer = writers[company]
        
        # 遍历该周报的所有平台分析
        for key, plat in platforms_analysis.items():
            # plat 是单个平台的整体信息
            ana = plat.get("analysis") or {}
            
            # direct_action_suggestions 是 list，转成多行文本
            suggestions = ana.get("direct_action_suggestions") or []
            if isinstance(suggestions, list):
                suggestions_text = "\n".join(suggestions)
            else:
                suggestions_text = str(suggestions) if suggestions else ""
            
            # 构建一行数据
            row_data = [
                company,
                data.get("start_date") or start_date,
                data.get("end_date") or end_date,
                period_days or "",
                created_at,
                plat.get("title") or key,
                plat.get("platform") or "",
                plat.get("game") or "",
                plat.get("url") or "",
                plat.get("usability_score", ""),
                plat.get("weekly_score", ""),
                plat.get("weekly_title", ""),
                plat.get("posts_count", ""),
                ana.get("summary", ""),
                ana.get("key_updates", ""),
                ana.get("gameplay_changes", ""),
                ana.get("offline_events", ""),
                ana.get("ad_creative_insights", ""),
                ana.get("platform_summary", ""),
                ana.get("risk_or_warning", ""),
                suggestions_text,
            ]
            
            writer.writerow(row_data)
            company_stats[company] += 1
            success_count += 1
    
    # 关闭所有文件
    for company, f in files.items():
        f.close()
        print(f"✅ {company}: {company_stats[company]} 个平台已导出")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("📊 导出总结")
    print("=" * 60)
    print(f"  成功导出: {success_count} 个平台")
    if error_count > 0:
        print(f"  失败: {error_count} 条记录")
    print(f"  生成文件数: {len(files)} 个 CSV")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="将数据库中的周报数据导出为 CSV 文件（每个公司一个 CSV）"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/weekly_reports",
        help="输出目录（默认: output/weekly_reports）"
    )
    
    args = parser.parse_args()
    
    export_weekly_reports_to_csv(
        db_path=args.db_path,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    sys.exit(main())
