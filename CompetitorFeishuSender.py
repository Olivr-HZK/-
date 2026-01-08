import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests
import yaml

import env_loader  # noqa: F401  # 确保 .env 中的 FEISHU_WEBHOOK_URL 被加载


DEFAULT_INPUT_PATH = "/app/output/competitor_ai_result.json"


def load_ai_results(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        # 兼容本地运行
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
    """
    与原 sender 中保持一致的 webhook 获取逻辑：
    - 优先读取环境变量 FEISHU_WEBHOOK_URL / FEISHU_URL / FEISHU_WEBHOOK
    - 否则回落到 config/config.yaml 的 notification.webhooks.feishu_url
    """
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


def _platform_icon(platform: str) -> str:
    """
    根据平台类型返回一个简单的 icon，提升可读性。
    """
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


def _format_report_date(ai_data: Dict[str, Any]) -> str:
    """
    从结果中推断抓取日期（fetched_at），用于日报头部展示。
    """
    if not isinstance(ai_data, dict):
        return ""

    fetched_at: str | None = None
    for payload in ai_data.values():
        if not isinstance(payload, dict):
            continue
        fetched_at = payload.get("fetched_at")
        if fetched_at:
            break

    if not fetched_at:
        return ""

    try:
        # 兼容 ISO8601 带 Z 的格式
        if fetched_at.endswith("Z"):
            dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(fetched_at)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return fetched_at


def build_markdown_text(ai_data: Dict[str, Any]) -> str:
    """
    将竞品 AI 分析结果转成一段 Markdown 文本，通过飞书机器人推送。
    - 按公司品牌分组展示
    - 在日报头部展示抓取日期和来源说明
    - 每条信息增加平台 icon、优先级 icon、互动情况等，提升可读性
    """
    if not isinstance(ai_data, dict):
        return ""

    report_date = _format_report_date(ai_data)
    header_line = "🏁【竞品社媒监控 · 自动播报】"
    if report_date:
        header_line += f"\n📅 日期: {report_date}（抓取时间）"
    header_line += "\n📎 来源: 各竞品官方社媒页面（X / Instagram / TikTok 等）"

    lines: List[str] = [header_line]

    # 先按公司进行分组
    company_groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for title, payload in ai_data.items():
        if not isinstance(payload, dict):
            continue
        company = payload.get("company") or title
        company_groups.setdefault(company, []).append((title, payload))

    def score_of(payload: Dict[str, Any]) -> float:
        try:
            return float(payload.get("usability_score", -1))
        except Exception:
            return -1.0

    # 按公司名称排序，组内再按评分从高到低排序
    for company_idx, (company, items) in enumerate(sorted(company_groups.items(), key=lambda kv: kv[0].lower()), 1):
        lines.append("")
        lines.append(f"{company_idx}. 🏢 {company}")

        # 组内排序
        items_sorted = sorted(items, key=lambda kv: score_of(kv[1]), reverse=True)
        for idx, (title, payload) in enumerate(items_sorted, 1):
            game = payload.get("game")
            platform = payload.get("platform") or ""
            url = payload.get("url") or ""
            priority = payload.get("priority", "medium")
            score = payload.get("usability_score", "")
            analysis = payload.get("analysis") or {}

            summary = analysis.get("summary") or ""
            ad_insight = analysis.get("ad_creative_insights") or ""
            gameplay_insight = analysis.get("gameplay_or_mechanic_insights") or ""
            action_suggestions = analysis.get("direct_action_suggestions") or ""
            engagement = analysis.get("engagement") or ""

            platform_icon = _platform_icon(platform)

            # 每条子项标题：平台 + 游戏
            sub_title = f"   {idx}) {platform_icon}"
            if game:
                sub_title += f" {game}"
            else:
                sub_title += f" {company} 官方账号"
            if platform:
                sub_title += f"（{platform}）"
            if priority and priority != "medium":
                priority_icon = "🔴" if priority == "high" else "🟡"
                sub_title += f" {priority_icon}"

            lines.append(sub_title)

            # 链接与评分
            if url:
                lines.append(f"      - 🔗 链接: {url}")
            if score != "":
                try:
                    score_val = float(score)
                    score_icon = "⭐" * min(int(score_val / 2), 5) if score_val > 0 else ""
                    lines.append(f"      - 📊 可用性评分: {score} {score_icon}")
                except Exception:
                    lines.append(f"      - 📊 可用性评分: {score}")

            # 互动情况（尽量对应原帖点赞/评论等）
            if engagement:
                lines.append(f"      - 👍 互动概览: {engagement}")

            if summary:
                lines.append(f"      - 📝 摘要: {summary}")
            if ad_insight:
                lines.append(f"      - 🎯 广告创意观察: {ad_insight}")
            if gameplay_insight:
                lines.append(f"      - 🎮 玩法/机制观察: {gameplay_insight}")
            if action_suggestions:
                lines.append(f"      - ✅ 建议动作: {action_suggestions}")

        lines.append("━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def send_to_feishu(webhook: str, text: str) -> bool:
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
            print("✅ 竞品社媒监控已推送至飞书群。")
            return True
        print(f"❌ 飞书推送失败: {resp.status_code} {resp.text}")
        return False
    except Exception as exc:
        print(f"❌ 飞书推送异常: {exc}")
        return False


def main() -> int:
    input_path = os.environ.get("COMPETITOR_AI_INPUT_PATH", DEFAULT_INPUT_PATH)
    webhook = get_feishu_webhook()

    ai_data = load_ai_results(input_path)
    if not ai_data:
        print("⚠️ AI 结果为空或格式不符，未发送推送")
        return 1

    text = build_markdown_text(ai_data)
    ok = send_to_feishu(webhook, text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

