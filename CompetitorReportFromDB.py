"""
从历史数据库读取AI分析结果，生成日报并发送到飞书
这是一个独立的工作流，不需要重新爬取或分析数据
"""
import os
import json
import argparse
import requests
import yaml
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from CompetitorHistoryDB import CompetitorHistoryDB
from CompetitorDailyWorkflow import build_company_daily_report, send_company_report_to_feishu

def load_ai_analysis_from_db(db: CompetitorHistoryDB, company: str, target_date: date) -> Optional[Dict[str, Any]]:
    """从数据库加载AI分析结果"""
    ai_data = db.load_ai_analysis(company, target_date)
    if not ai_data:
        return None
    
    # 返回 results 字段（格式为 {title: payload}）
    return ai_data.get("results", {})


def load_raw_data_from_db(db: CompetitorHistoryDB, company: str, target_date: date) -> Optional[List[Dict[str, Any]]]:
    """从数据库加载原始数据，转换为 platforms_data 格式"""
    raw_data = db.load_raw_data(company, target_date)
    if not raw_data:
        return None
    
    platforms_dict = raw_data.get("platforms", {})
    
    # 转换为列表格式
    platforms_data = []
    for key, platform_info in platforms_dict.items():
        platforms_data.append({
            "platform_type": platform_info.get("platform_type", ""),
            "game": platform_info.get("game"),
            "url": platform_info.get("url", ""),
            "username": platform_info.get("username"),
            "page_id": platform_info.get("page_id"),
            "channel_id": platform_info.get("channel_id"),
            "posts": platform_info.get("posts", []),
            "posts_count": platform_info.get("posts_count", 0),
            "fetched_at": platform_info.get("fetched_at"),
        })
    
    return platforms_data


def convert_ai_results_to_workflow_format(ai_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    将数据库中的AI分析结果转换为工作流需要的格式
    
    数据库格式: {title: payload}
    工作流格式: {title: payload} (相同，但确保格式一致)
    """
    return ai_results


def generate_report_from_db(
    company: str,
    target_date: date,
    db: CompetitorHistoryDB,
    days_ago: int = 1
) -> Optional[str]:
    """
    从数据库生成公司日报
    
    Args:
        company: 公司名称
        target_date: 目标日期
        db: 数据库实例
        days_ago: 相对今天的天数（用于报告标题）
    
    Returns:
        生成的Markdown报告文本，如果失败则返回None
    """
    print(f"\n  📖 读取 {company} 的数据...")
    
    # 1. 加载AI分析结果
    ai_results = load_ai_analysis_from_db(db, company, target_date)
    if not ai_results:
        print(f"    ⚠️ 未找到 {company} 在 {target_date} 的AI分析结果")
        return None
    
    print(f"    ✓ 找到 {len(ai_results)} 个平台的AI分析结果")
    
    # 2. 加载原始数据（用于获取帖子URL等信息）
    platforms_data = load_raw_data_from_db(db, company, target_date)
    if not platforms_data:
        print(f"    ⚠️ 未找到 {company} 在 {target_date} 的原始数据")
        # 即使没有原始数据，也可以生成报告（只是没有原帖链接）
        platforms_data = []
    
    print(f"    ✓ 找到 {len(platforms_data)} 个平台的原始数据")
    
    # 3. 转换AI结果格式
    ai_results_formatted = convert_ai_results_to_workflow_format(ai_results)
    
    # 4. 生成日报
    print(f"    📝 生成日报...")
    report_text = build_company_daily_report(
        company=company,
        ai_results=ai_results_formatted,
        platforms_data=platforms_data,
        days_ago=days_ago
    )
    
    print(f"    ✓ 日报生成完成，长度: {len(report_text)} 字符")
    return report_text


def send_report_to_feishu(company: str, report_text: str) -> bool:
    """发送报告到飞书"""
    print(f"\n  📤 发送 {company} 的日报到飞书...")
    success = send_company_report_to_feishu(company, report_text)
    if success:
        print(f"    ✓ {company} 日报已发送到飞书")
    else:
        print(f"    ❌ {company} 日报发送失败")
    return success


def run_report_from_db_workflow(
    target_date: Optional[date] = None,
    target_companies: Optional[List[str]] = None,
    skip_send: bool = False,
    days_ago: int = 1
):
    """
    从数据库读取AI分析结果，生成日报并发送到飞书
    
    Args:
        target_date: 目标日期，如果为None则使用 days_ago 计算
        target_companies: 目标公司列表，如果为None则处理所有有数据的公司
        skip_send: 是否跳过发送到飞书
        days_ago: 相对今天的天数（如果 target_date 为 None）
    """
    print("=" * 60)
    print("📊 从数据库生成日报工作流")
    print("=" * 60)
    print()
    
    # 确定目标日期
    if target_date is None:
        target_date = date.today() - timedelta(days=days_ago)
    
    print(f"📅 目标日期: {target_date}")
    print()
    
    # 初始化数据库
    db = CompetitorHistoryDB()
    
    # 确定要处理的公司列表
    if target_companies:
        companies = target_companies
        print(f"📋 指定公司: {', '.join(companies)}")
    else:
        companies = db.get_companies_for_date(target_date, is_ai=True)
        print(f"📋 找到 {len(companies)} 个公司有AI分析数据: {', '.join(companies)}")
    
    if not companies:
        print("⚠️ 未找到任何公司的数据，退出")
        return
    
    print()
    
    # 计算 days_ago（用于报告标题）
    days_ago_calc = (date.today() - target_date).days
    
    # 处理每个公司
    success_count = 0
    fail_count = 0
    
    for company in companies:
        print(f"\n{'=' * 60}")
        print(f"🏢 处理公司: {company}")
        print(f"{'=' * 60}")
        
        try:
            # 生成日报
            report_text = generate_report_from_db(
                company=company,
                target_date=target_date,
                db=db,
                days_ago=days_ago_calc
            )
            
            if not report_text:
                print(f"  ❌ {company} 日报生成失败")
                fail_count += 1
                continue
            
            # 保存日报到文件
            output_dir = os.environ.get("OUTPUT_DIR")
            if not output_dir or not os.path.exists(output_dir):
                alt_dir = os.path.join(os.path.dirname(__file__), "output")
                if not os.path.exists(alt_dir):
                    os.makedirs(alt_dir, exist_ok=True)
                output_dir = alt_dir
            
            date_str = target_date.strftime("%Y-%m-%d")
            safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_company = safe_company.replace(' ', '_').lower()
            report_file = os.path.join(output_dir, f"daily_report_{safe_company}_{date_str}_from_db.md")
            
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                print(f"  💾 日报已保存: {report_file}")
            except Exception as exc:
                print(f"  ⚠️ 保存日报失败: {exc}")
            
            # 发送到飞书
            if not skip_send:
                if send_report_to_feishu(company, report_text):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print(f"  ⏭️ 跳过发送到飞书")
                success_count += 1
                
        except Exception as exc:
            print(f"  ❌ 处理 {company} 时出错: {exc}")
            import traceback
            print(f"  [调试] 错误详情: {traceback.format_exc()}")
            fail_count += 1
    
    # 总结
    print()
    print("=" * 60)
    print("📊 工作流完成")
    print("=" * 60)
    print(f"✓ 成功: {success_count} 个公司")
    if fail_count > 0:
        print(f"❌ 失败: {fail_count} 个公司")
    print()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="从数据库读取AI分析结果，生成日报并发送到飞书")
    parser.add_argument(
        "--date",
        type=str,
        help="目标日期 (YYYY-MM-DD)，如果不指定则使用 --days-ago",
    )
    parser.add_argument(
        "--days-ago",
        type=int,
        default=1,
        help="相对今天的天数（默认: 1，即昨天）",
    )
    parser.add_argument(
        "--companies",
        type=str,
        nargs="+",
        help="指定要处理的公司列表（空格分隔）",
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="跳过发送到飞书，只生成报告文件",
    )
    
    args = parser.parse_args()
    
    # 解析日期
    target_date = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ 无效的日期格式: {args.date}，请使用 YYYY-MM-DD")
            return 1
    
    # 运行工作流
    run_report_from_db_workflow(
        target_date=target_date,
        target_companies=args.companies,
        skip_send=args.skip_send,
        days_ago=args.days_ago
    )
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
