import json
import os
from typing import Any, Dict, List, Tuple

import requests
import yaml

import env_loader  # noqa: F401


DEFAULT_INPUT_PATH = "/app/output/tiktok_ai_result.json"


def load_ai_results(file_path: str) -> Dict[str, Any]:
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
        return cfg.get("notification", {}).get("webhooks", {}).get("feishu_url", "")
    except Exception as exc:
        print(f"⚠️ 读取配置失败，跳过 config.yaml: {exc}")
        return ""


def _format_report_date(ai_data: Dict[str, Any]) -> str:
    from datetime import datetime
    for payload in ai_data.values():
        if isinstance(payload, dict):
            fetched_at = payload.get("fetched_at")
            if fetched_at:
                try:
                    dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                    return dt.strftime("%Y-%m-%d")
                except:
                    pass
    return datetime.now().strftime("%Y-%m-%d")


def build_tiktok_markdown(ai_data: Dict[str, Any]) -> str:
    if not isinstance(ai_data, dict):
        return ""
    lines: List[str] = []
    lines.append("🏁【竞品 TikTok 监控 · 自动播报】")
    report_date = _format_report_date(ai_data)
    lines.append(f"📅 日期: {report_date}")
    lines.append("📎 来源: TikTok")
    lines.append("")

    # 按公司分组
    companies: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for title, payload in ai_data.items():
        if not isinstance(payload, dict):
            continue
        company = payload.get("company") or "未知公司"
        companies.setdefault(company, []).append((title, payload))

    for idx, company in enumerate(sorted(companies.keys()), 1):
        items = companies[company]
        # 排序：评分高的在前
        def score_of(p: Dict[str, Any]) -> float:
            try:
                return float(p.get("usability_score", -1))
            except:
                return -1.0
        items.sort(key=lambda kv: score_of(kv[1]), reverse=True)
        lines.append(f"{idx}. 🏢 {company}")
        lines.append("")
        for sub_idx, (title, payload) in enumerate(items, 1):
            game = payload.get("game")
            username = payload.get("username") or ""
            url = payload.get("url") or ""
            priority = payload.get("priority", "medium")
            score = payload.get("usability_score", "")
            videos_count = payload.get("videos_count", 0)
            analysis = payload.get("analysis") or {}

            subtitle = f"   {sub_idx}) 🎵 "
            if game:
                subtitle += f"{game} "
            subtitle += f"(@{username})"
            if priority and priority != "medium":
                subtitle += " " + ("🔴" if priority == "high" else "🟡")
            lines.append(subtitle)

            if url:
                lines.append(f"      🔗 链接: {url}")
            if score != "":
                try:
                    score_val = float(score)
                    icon = "⭐" * min(int(score_val / 2), 5) if score_val > 0 else ""
                    lines.append(f"      📊 可用性评分: {score} {icon}")
                except:
                    lines.append(f"      📊 可用性评分: {score}")
            if videos_count:
                lines.append(f"      🎬 分析视频数: {videos_count} 条")

            summary = analysis.get("summary") or ""
            key_videos = analysis.get("key_videos_analysis") or ""
            ad_insight = analysis.get("ad_creative_insights") or ""
            gameplay = analysis.get("gameplay_or_mechanic_insights") or ""
            actions = analysis.get("direct_action_suggestions") or ""

            if summary:
                lines.append(f"      📝 摘要: {summary}")
            if key_videos:
                lines.append(f"      🔍 关键视频分析: {key_videos}")
            if ad_insight:
                lines.append(f"      🎯 广告创意观察: {ad_insight}")
            if gameplay:
                lines.append(f"      🎮 玩法/机制观察: {gameplay}")
            if actions:
                lines.append(f"      ✅ 建议动作: {actions}")
            lines.append("")
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("")
    return "\n".join(lines)


def send_to_feishu(webhook: str, text: str) -> bool:
    if not webhook:
        print("❌ 未找到飞书 webhook，请设置 FEISHU_WEBHOOK_URL 或配置 config.yaml")
        return False
    if not text.strip():
        print("⚠️ 文本内容为空，取消发送。")
        return False
    payload = {"msg_type": "text", "content": {"text": text}}
    try:
        resp = requests.post(webhook, json=payload, timeout=20)
        if resp.status_code == 200:
            print("✅ TikTok 监控分析已推送至飞书群。")
            return True
        print(f"❌ 飞书推送失败: {resp.status_code} {resp.text}")
        return False
    except Exception as exc:
        print(f"❌ 飞书推送异常: {exc}")
        return False


def main() -> int:
    input_path = os.environ.get("TIKTOK_AI_INPUT_PATH", DEFAULT_INPUT_PATH)
    webhook = get_feishu_webhook()
    ai_data = load_ai_results(input_path)
    if not ai_data:
        print("⚠️ AI 结果为空或格式不符，未发送推送")
        return 1
    text = build_tiktok_markdown(ai_data)
    ok = send_to_feishu(webhook, text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

