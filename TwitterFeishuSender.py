"""
Twitter 分析结果飞书推送
将 Twitter AI 分析结果推送到飞书群
"""
import json
import os
from typing import Any, Dict

import requests
import yaml

import env_loader  # noqa: F401


DEFAULT_INPUT_PATH = "/app/output/twitter_ai_result.json"


def load_ai_results(file_path: str) -> Dict[str, Any]:
    """读取 Twitter AI 分析结果"""
    if not os.path.exists(file_path):
        alt = os.path.join(os.path.dirname(__file__), "output", os.path.basename(file_path))
        if os.path.exists(alt):
            file_path = alt
        else:
            print(f"❌ 未找到 AI 结果文件: {file_path}")
            return {}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析 AI 结果失败: {exc}")
        return {}


def get_feishu_webhook() -> str:
    """获取飞书 webhook URL"""
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
    except Exception as exc:
        print(f"⚠️ 读取配置失败，跳过 config.yaml: {exc}")
        return ""


def _format_report_date(ai_data: Dict[str, Any]) -> str:
    """从数据中提取日期"""
    for payload in ai_data.values():
        if isinstance(payload, dict):
            fetched_at = payload.get("fetched_at")
            if fetched_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                    return dt.strftime("%Y-%m-%d")
                except:
                    pass
    return datetime.now().strftime("%Y-%m-%d")


def build_twitter_markdown(ai_data: Dict[str, Any]) -> str:
    """将 Twitter AI 分析结果转换为飞书 Markdown 格式"""
    if not isinstance(ai_data, dict):
        return ""
    
    lines = ["🏁【竞品 Twitter 监控 · 自动播报】"]
    
    # 添加日期和来源
    report_date = _format_report_date(ai_data)
    lines.append(f"📅 日期: {report_date}")
    lines.append(f"📎 来源: Twitter (X)")
    lines.append("")
    
    # 按公司分组
    companies = {}
    for title, payload in ai_data.items():
        if not isinstance(payload, dict):
            continue
        
        company = payload.get("company") or "未知公司"
        if company not in companies:
            companies[company] = []
        companies[company].append((title, payload))
    
    # 按公司排序
    company_names = sorted(companies.keys())
    
    for idx, company in enumerate(company_names, 1):
        company_items = companies[company]
        
        # 按评分排序
        def score_of(item):
            try:
                return float(item[1].get("usability_score", -1))
            except:
                return -1.0
        
        company_items.sort(key=score_of, reverse=True)
        
        lines.append(f"{idx}. 🏢 {company}")
        lines.append("")
        
        for sub_idx, (title, payload) in enumerate(company_items, 1):
            game = payload.get("game")
            username = payload.get("username", "")
            url = payload.get("url", "")
            priority = payload.get("priority", "medium")
            score = payload.get("usability_score", "")
            tweets_count = payload.get("tweets_count", 0)
            analysis = payload.get("analysis") or {}
            
            # 子标题
            sub_title = f"   {sub_idx}) 🐦 "
            if game:
                sub_title += f"{game} "
            sub_title += f"(@{username})"
            
            if priority and priority != "medium":
                priority_icon = "🔴" if priority == "high" else "🟡"
                sub_title += f" {priority_icon}"
            
            lines.append(sub_title)
            
            if url:
                lines.append(f"      🔗 链接: {url}")
            if score != "":
                try:
                    score_val = float(score)
                    score_icon = "⭐" * min(int(score_val / 2), 5) if score_val > 0 else ""
                    lines.append(f"      📊 可用性评分: {score} {score_icon}")
                except:
                    lines.append(f"      📊 可用性评分: {score}")
            if tweets_count > 0:
                lines.append(f"      📝 分析推文数: {tweets_count} 条")
            
            # 分析内容
            summary = analysis.get("summary") or ""
            key_tweets = analysis.get("key_tweets_analysis") or ""
            ad_insight = analysis.get("ad_creative_insights") or ""
            gameplay_insight = analysis.get("gameplay_or_mechanic_insights") or ""
            engagement_analysis = analysis.get("engagement_analysis") or ""
            action_suggestions = analysis.get("direct_action_suggestions") or ""
            
            if summary:
                lines.append(f"      📝 摘要: {summary}")
            if key_tweets:
                lines.append(f"      🔍 关键推文分析: {key_tweets}")
            if ad_insight:
                lines.append(f"      🎯 广告创意观察: {ad_insight}")
            if gameplay_insight:
                lines.append(f"      🎮 玩法/机制观察: {gameplay_insight}")
            if engagement_analysis:
                lines.append(f"      📈 互动分析: {engagement_analysis}")
            if action_suggestions:
                lines.append(f"      ✅ 建议动作: {action_suggestions}")
            
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("")
    
    return "\n".join(lines)


def send_to_feishu(webhook: str, text: str) -> bool:
    """发送消息到飞书"""
    if not webhook:
        print("❌ 未找到飞书 webhook，请设置 FEISHU_WEBHOOK_URL 或配置 config.yaml")
        return False
    
    if not text.strip():
        print("⚠️ 文本内容为空，取消发送。")
        return False
    
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    
    try:
        resp = requests.post(webhook, json=payload, timeout=20)
        if resp.status_code == 200:
            print("✅ Twitter 监控分析已推送至飞书群。")
            return True
        print(f"❌ 飞书推送失败: {resp.status_code} {resp.text}")
        return False
    except Exception as exc:
        print(f"❌ 飞书推送异常: {exc}")
        return False


def main() -> int:
    """主函数"""
    input_path = os.environ.get("TWITTER_AI_INPUT_PATH", DEFAULT_INPUT_PATH)
    webhook = get_feishu_webhook()
    
    ai_data = load_ai_results(input_path)
    if not ai_data:
        print("⚠️ AI 结果为空或格式不符，未发送推送")
        return 1
    
    text = build_twitter_markdown(ai_data)
    ok = send_to_feishu(webhook, text)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
