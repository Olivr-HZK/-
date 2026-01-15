"""
竞品社媒日报生成模块 (第三部分)
按公司生成飞书日报，包含AI分析结果、监控时间段和平台信息
"""
import json
import os
import time
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime, date

import requests

import env_loader  # noqa: F401

from CompetitorDatabaseDB import CompetitorDatabaseDB


def _get_company_color(company: str) -> str:
    """为不同公司分配不同颜色的边框"""
    colors = [
        "blue", "wathet", "turquoise", "green", "yellow", "orange",
        "red", "carmine", "violet", "purple", "indigo", "grey",
    ]
    hash_value = hash(company.lower()) % len(colors)
    return colors[hash_value]


def _platform_icon(platform: str) -> str:
    """根据平台类型返回图标"""
    p = (platform or "").lower()
    if "twitter" in p or "x.com" in p or p == "x":
        return "🐦"
    if "instagram" in p or "ig" == p:
        return "📸"
    if "tiktok" in p:
        return "🎵"
    if "youtube" in p:
        return "▶️"
    if "facebook" in p or "fb" == p:
        return "📘"
    return "🌐"


def get_feishu_webhook() -> str:
    """获取飞书webhook地址"""
    for env_key in ("FEISHU_WEBHOOK_URL", "FEISHU_URL", "FEISHU_WEBHOOK"):
        if os.environ.get(env_key):
            return os.environ[env_key]
    
    config_path = os.environ.get("CONFIG_PATH", "/app/config/config.yaml")
    if not os.path.exists(config_path):
        alt = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        if os.path.exists(alt):
            config_path = alt
        else:
            return ""
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return (
            cfg.get("notification", {})
            .get("webhooks", {})
            .get("feishu_url", "")
        )
    except Exception:
        return ""


def get_company_platforms_from_db(
    db: CompetitorDatabaseDB,
    company: str
) -> List[Dict[str, Any]]:
    """
    从数据库获取公司监控的所有平台信息
    
    Args:
        db: 数据库实例
        company: 公司名称
    
    Returns:
        平台列表，格式：
        [
            {
                "type": "twitter",
                "game": "game_name" or None,
                "url": "...",
                "username": "...",
                "enabled": True
            },
            ...
        ]
    """
    platforms = db.get_company_platforms(company, enabled_only=False)
    
    result = []
    for platform in platforms:
        result.append({
            "type": platform.get("type", ""),
            "game": platform.get("game"),
            "url": platform.get("url", ""),
            "username": platform.get("username"),
            "page_id": platform.get("page_id"),
            "channel_id": platform.get("channel_id"),
            "handle": platform.get("handle"),
            "enabled": platform.get("enabled", True)
        })
    
    return result


def build_company_period_feishu_card(
    company: str,
    period: Dict[str, Any],
    platforms_analysis: Dict[str, Any],
    monitored_platforms: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    构建公司时间段日报的飞书卡片
    
    Args:
        company: 公司名称
        period: 时间段信息 {"start_date": "...", "end_date": "...", "days": 7}
        platforms_analysis: AI分析结果 {title: payload, ...}
        monitored_platforms: 监控的平台列表（从数据库获取）
    
    Returns:
        飞书卡片字典
    """
    company_color = _get_company_color(company)
    start_date = period.get("start_date", "")
    end_date = period.get("end_date", "")
    days = period.get("days", 7)
    
    elements: List[Dict[str, Any]] = []
    
    # 添加时间段和来源信息
    header_info = [
        f"📅 **监控时间段**: {start_date} 至 {end_date} (共 {days} 天)"
    ]
    
    # 显示所有监控的平台
    sources = []
    if monitored_platforms:
        platform_icons = {
            "twitter": "🐦", "tiktok": "🎵", "youtube": "▶️",
            "facebook": "📘", "instagram": "📷",
        }
        
        # 按平台类型分组
        platform_groups: Dict[str, List[Dict[str, Any]]] = {}
        for platform in monitored_platforms:
            platform_type = platform.get("type", "").lower()
            if platform_type not in platform_groups:
                platform_groups[platform_type] = []
            platform_groups[platform_type].append(platform)
        
        for platform_type, platforms_list in sorted(platform_groups.items()):
            icon = platform_icons.get(platform_type, "🌐")
            for platform in platforms_list:
                game = platform.get("game")
                url = platform.get("url", "")
                
                if not url:
                    # 尝试根据平台类型和用户名生成URL
                    username = platform.get("username")
                    if platform_type == "twitter" and username:
                        url = f"https://x.com/{username}"
                    elif platform_type == "tiktok" and username:
                        url = f"https://www.tiktok.com/@{username}"
                    elif platform_type == "instagram" and username:
                        url = f"https://www.instagram.com/{username}/"
                    elif platform_type == "facebook":
                        page_id = platform.get("page_id", "")
                        if page_id:
                            url = f"https://www.facebook.com/{page_id}"
                    elif platform_type == "youtube":
                        handle = platform.get("handle")
                        channel_id = platform.get("channel_id")
                        if handle:
                            url = f"https://www.youtube.com/@{handle}"
                        elif channel_id:
                            url = f"https://www.youtube.com/channel/{channel_id}"
                
                if url:
                    label = f"{icon} {platform_type.upper()}"
                    if game:
                        label += f" - {game}"
                    enabled_status = "✅" if platform.get("enabled", True) else "⏸️"
                    sources.append(f"{label} {enabled_status}: [{url}]({url})")
    
    if sources:
        header_info.append(f"📎 **监控平台** ({len(sources)} 个):\n" + "\n".join([f"   • {s}" for s in sources]))
    else:
        header_info.append("📎 **监控平台**: 未配置")
    
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(header_info)
        }
    })
    elements.append({"tag": "hr"})
    
    # 按评分排序AI结果
    sorted_results = sorted(
        platforms_analysis.items(),
        key=lambda x: float(x[1].get("usability_score", 0)),
        reverse=True
    )
    
    if not sorted_results:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "📝 **说明**: 该时间段内所有平台均无社媒更新。"
            }
        })
    else:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "📊 **平台更新分析** (按评分排序，高评分优先)"
            }
        })
        elements.append({"tag": "hr"})
        
        # 为每个平台添加详细信息
        for idx, (title, payload) in enumerate(sorted_results, 1):
            game = payload.get("game")
            platform = payload.get("platform") or ""
            url = payload.get("url") or ""
            score = payload.get("usability_score", "")
            posts_count = payload.get("posts_count", 0)
            period_days = payload.get("period_days", 7)
            analysis = payload.get("analysis") or {}
            
            platform_icon = _platform_icon(platform)
            
            # 构建平台标题
            platform_title_parts = [f"{platform_icon}"]
            if game:
                platform_title_parts.append(f"**{game}**")
            else:
                platform_title_parts.append(f"**{company} 官方账号**")
            if platform:
                platform_title_parts.append(f"({platform})")
            
            platform_title = " ".join(platform_title_parts)
            
            # 创建字段
            fields: List[Dict[str, Any]] = []
            
            # 平台信息和链接
            platform_info = f"**{idx}. {platform_title}**"
            if url:
                platform_info += f"\n🔗 [{url}]({url})"
            
            fields.append({
                "is_short": False,
                "text": {
                    "tag": "lark_md",
                    "content": platform_info
                }
            })
            
            # 评分和帖子数
            score_info = []
            if score != "":
                try:
                    score_val = float(score)
                    score_stars = "⭐" * min(int(score_val / 2), 5) if score_val > 0 else ""
                    score_info.append(f"📊 **可用性评分**: {score} {score_stars}")
                except Exception:
                    score_info.append(f"📊 **可用性评分**: {score}")
            
            if posts_count:
                score_info.append(f"📝 **更新帖子数**: {posts_count} 条 (过去 {period_days} 天)")
            
            if score_info:
                fields.append({
                    "is_short": False,
                    "text": {
                        "tag": "lark_md",
                        "content": "\n".join(score_info)
                    }
                })
            
            if fields:
                elements.append({"tag": "div", "fields": fields})
            
            # 分析内容
            content_lines = []
            summary = analysis.get("summary") or ""
            key_updates = analysis.get("key_updates") or ""
            gameplay_changes = analysis.get("gameplay_changes") or ""
            offline_events = analysis.get("offline_events") or ""
            ad_insight = analysis.get("ad_creative_insights") or ""
            platform_summary = analysis.get("platform_summary") or ""
            actions_raw = analysis.get("direct_action_suggestions") or ""
            
            if summary:
                content_lines.append(f"📝 **摘要**: {summary}")
            
            if key_updates:
                content_lines.append(f"🔑 **重点内容**: {key_updates}")
            
            if gameplay_changes:
                content_lines.append(f"🎮 **玩法变化**: {gameplay_changes}")
            
            if offline_events:
                content_lines.append(f"🎪 **线下活动**: {offline_events}")
            
            if ad_insight:
                content_lines.append(f"🎯 **广告创意观察**: {ad_insight}")
            
            if platform_summary:
                content_lines.append(f"📊 **平台概况**: {platform_summary}")
            
            if actions_raw:
                if isinstance(actions_raw, list):
                    actions = "\n".join([f"  - {item}" for item in actions_raw if item])
                else:
                    actions = str(actions_raw)
                if actions:
                    content_lines.append(f"✅ **建议动作**:\n{actions}")
            
            if content_lines:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "\n\n".join(content_lines)
                    }
                })
            
            # 如果不是最后一个，添加分隔线
            if idx < len(sorted_results):
                elements.append({"tag": "hr"})
    
    # 构建卡片
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": company_color,
            "title": {
                "tag": "plain_text",
                "content": f"🏁 竞品监控 · {company} (时间段报告)"
            }
        },
        "elements": elements
    }
    
    return card


def send_company_period_report_to_feishu(
    company: str,
    card: Dict[str, Any]
) -> bool:
    """
    发送公司时间段报告到飞书
    
    Args:
        company: 公司名称
        card: 飞书卡片
    
    Returns:
        是否发送成功
    """
    webhook = get_feishu_webhook()
    
    if not webhook:
        print(f"  ⚠️ 未找到飞书webhook，跳过推送")
        return False
    
    payload = {"msg_type": "interactive", "card": card}
    
    sent = False
    for attempt in range(3):
        try:
            resp = requests.post(webhook, json=payload, timeout=20)
            resp_data = {}
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = {}
            
            code = resp_data.get("StatusCode", resp_data.get("code", 0))
            if resp.status_code == 200 and code in (0,):
                print(f"  ✓ {company} 时间段报告已推送到飞书")
                return True
            else:
                print(f"  ❌ 飞书推送失败 (尝试 {attempt + 1}/3): {resp.text[:200]}")
        except Exception as exc:
            print(f"  ❌ 飞书推送异常 (尝试 {attempt + 1}/3): {exc}")
        
        if attempt < 2:
            time.sleep(2)
    
    return False


def generate_period_reports(
    analysis_result: Dict[str, Any],
    db_path: Optional[str] = None,
    skip_send: bool = False
) -> Dict[str, Any]:
    """
    生成时间段报告并发送到飞书
    
    Args:
        analysis_result: AI分析结果（从CompetitorPeriodAnalysisAI生成）
        db_path: 数据库路径（用于获取监控平台信息）
        skip_send: 是否跳过发送到飞书
    
    Returns:
        报告生成结果
    """
    period = analysis_result.get("period", {})
    companies_analysis = analysis_result.get("companies", {})
    
    print(f"📄 开始生成时间段报告")
    print(f"   时间段: {period.get('start_date')} 至 {period.get('end_date')}")
    print(f"   公司数: {len(companies_analysis)}")
    
    # 初始化数据库（用于获取监控平台信息）
    db = CompetitorDatabaseDB(db_path) if db_path else CompetitorDatabaseDB()
    
    reports = {}
    
    for company, company_data in companies_analysis.items():
        print(f"\n  📄 生成报告: {company}")
        
        platforms_analysis = company_data.get("platforms_analysis", {})
        
        # 从数据库获取监控的平台信息
        monitored_platforms = get_company_platforms_from_db(db, company)
        print(f"   监控平台数: {len(monitored_platforms)}")
        
        # 构建飞书卡片
        card = build_company_period_feishu_card(
            company=company,
            period=period,
            platforms_analysis=platforms_analysis,
            monitored_platforms=monitored_platforms
        )
        
        reports[company] = {
            "card": card,
            "platforms_count": len(platforms_analysis),
            "monitored_platforms_count": len(monitored_platforms)
        }
        
        # 发送到飞书
        if not skip_send:
            send_company_period_report_to_feishu(company, card)
    
    # 保存报告到文件
    output_dir = os.environ.get("OUTPUT_DIR")
    if not output_dir or not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
    
    start_date = period.get("start_date", "")
    end_date = period.get("end_date", "")
    report_file = os.path.join(
        output_dir,
        f"competitor_period_reports_{start_date}_to_{end_date}.json"
    )
    
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        print(f"\n💾 报告已保存: {report_file}")
    except Exception as exc:
        print(f"⚠️ 保存报告失败: {exc}")
    
    print(f"\n✓ 报告生成完成，共 {len(reports)} 个公司")
    return reports


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生成时间段报告并发送到飞书")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="输入的AI分析结果JSON文件路径（从CompetitorPeriodAnalysisAI生成）"
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="跳过发送到飞书，只生成报告文件"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    
    args = parser.parse_args()
    
    # 读取AI分析结果
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        return 1
    
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            analysis_result = json.load(f)
    except Exception as e:
        print(f"❌ 读取输入文件失败: {e}")
        return 1
    
    # 生成报告
    reports = generate_period_reports(
        analysis_result=analysis_result,
        db_path=args.db_path,
        skip_send=args.skip_send
    )
    
    print(f"\n✅ 报告生成完成，共 {len(reports)} 个公司")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
