# coding=utf-8
"""
轻量级 Sender：读取 AI 结果，格式化飞书文本并推送
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

import requests
import yaml


DEFAULT_INPUT_PATH = "/app/output/ai_result.json"
DEFAULT_MAX_BYTES = 29000


def load_ai_results(file_path: str) -> Dict:
    if not os.path.exists(file_path):
        print(f"❌ 未找到 AI 结果文件: {file_path}")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析 AI 结果失败: {exc}")
        return {}


def extract_trends(ai_data: Dict) -> List[Tuple[str, Dict]]:
    """从 AI 结果中提取趋势项"""
    if not isinstance(ai_data, dict):
        return []

    # 数据格式可能以 google_trend_ai 包裹
    if "google_trend_ai" in ai_data and isinstance(ai_data["google_trend_ai"], dict):
        ai_data = ai_data["google_trend_ai"]

    trends: List[Tuple[str, Dict]] = []
    for title, payload in ai_data.items():
        if isinstance(payload, dict):
            trends.append((title, payload))

    return trends


def format_rank(ranks) -> str:
    if isinstance(ranks, list) and ranks:
        return str(ranks[0])
    if isinstance(ranks, (int, float)):
        return str(ranks)
    return ""


def split_text_by_bytes(text: str, max_bytes: int) -> List[str]:
    """按字节数切分文本，尽量保持行完整"""
    if not text:
        return []

    batches: List[str] = []
    current = ""

    for line in text.splitlines(keepends=True):
        candidate = current + line
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
            continue

        if current:
            batches.append(current)
            current = ""

        # 单行超限时按字节截断
        encoded = line.encode("utf-8")
        while len(encoded) > max_bytes:
            chunk = encoded[:max_bytes]
            # 尝试安全解码
            for cut in range(0, 4):
                try:
                    decoded = chunk[: len(chunk) - cut].decode("utf-8")
                    batches.append(decoded)
                    encoded = encoded[len(decoded.encode("utf-8")) :]
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # 极端情况直接跳过
                encoded = b""

        if encoded:
            current = encoded.decode("utf-8")

    if current:
        batches.append(current)

    return batches


def format_score(score) -> str:
    """根据分数返回带颜色提示的显示（使用彩色圆点以兼容文本消息）"""
    try:
        val = float(score)
    except Exception:
        return ""

    if val > 9.0:
        icon = "🟡"  # golden
    elif val > 8:
        icon = "🟣"  # purple
    elif val > 6.5:
        icon = "⚫"   # black
    else:
        icon = "⚪"   # gray

    return f"{icon} {val:.2f}"


def build_feishu_text(trends: List[Tuple[str, Dict]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "📈 **Google Trends AI 精选**",
        f"<font color='grey'>更新时间：{now}</font>",
        "",
    ]

    if not trends:
        lines.append("📭 未找到可推送的趋势数据")
        return "\n".join(lines)

    # 按评分排序（降序），无评分排后
    def score_key(item):
        _, payload = item
        try:
            return float(payload.get("usability_score", -1))
        except Exception:
            return -1

    sorted_trends = sorted(trends, key=score_key, reverse=True)

    lines.append(f"共 {len(sorted_trends)} 条趋势：")

    for idx, (title, payload) in enumerate(sorted_trends, 1):
        url = (
            payload.get("mobileUrl")
            or payload.get("mobile_url")
            or payload.get("url")
            or ""
        )
        rank_text = format_rank(payload.get("ranks"))
        analysis = payload.get("analysis", {}) if isinstance(payload, dict) else {}
        score_val = payload.get("usability_score")
        score_text = format_score(score_val)
        high_score_tag = ""
        try:
            if float(score_val) > 9.0:
                high_score_tag = "❗"
            else:
                high_score_tag = "🏷️"
        except Exception:
            pass

        # 核心信息（去除缩进，适配手机矩形块显示）
        lines.append(f"{idx}. {high_score_tag} **{title.strip()}**{high_score_tag}")
        if score_text:
            lines.append(f"⭐ **启发性评分**: {score_text}")
        if rank_text:
            lines.append(f"🔥 热度排名: {rank_text}")

        summary = analysis.get("summary") or ""
        nature = analysis.get("nature") or ""
        ua_inspiration = analysis.get("ua_inspiration") or ""
        suitability = analysis.get("ai_suitability_check") or ""

        if summary:
            lines.append(f"📝 **摘要**:\n**{summary}**\n")
        if nature:
            lines.append(f"🎭 性质:\n{nature}")
        if ua_inspiration:
            lines.append(f"🎯 **UA灵感**:\n{ua_inspiration}")
        if suitability:
            lines.append(f"🤖 **生成适配**:\n{suitability}")

        if url:
            lines.append(f"🔗 链接:\n[查看链接]({url})")

        lines.append("━━━")

    return "\n".join(lines)


def get_feishu_webhook() -> str:
    for env_key in ("FEISHU_WEBHOOK_URL", "FEISHU_URL", "FEISHU_WEBHOOK"):
        if os.environ.get(env_key):
            return os.environ[env_key]

    config_path = os.environ.get("CONFIG_PATH", "/app/config/config.yaml")
    if os.path.exists(config_path):
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


def send_feishu_text(webhook: str, text: str, max_bytes: int) -> bool:
    chunks = split_text_by_bytes(text, max_bytes)
    if not chunks:
        print("⚠️ 推送内容为空，已跳过")
        return False

    success = True
    for idx, chunk in enumerate(chunks, 1):
        payload = {"msg_type": "text", "content": {"text": chunk}}
        try:
            resp = requests.post(webhook, json=payload, timeout=15)
            resp_data = {}
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = {}

            code = resp_data.get("StatusCode", resp_data.get("code", 0))
            if resp.status_code != 200 or code not in (0,):
                success = False
                print(f"❌ 第 {idx} 批推送失败: {resp.text}")
            else:
                print(f"✅ 第 {idx} 批推送成功")
        except Exception as exc:
            success = False
            print(f"❌ 第 {idx} 批推送异常: {exc}")
    return success


def main() -> int:
    input_path = os.environ.get("SENDER_INPUT_PATH", DEFAULT_INPUT_PATH)
    max_bytes = int(os.environ.get("SENDER_MAX_BYTES", DEFAULT_MAX_BYTES))

    webhook = get_feishu_webhook()
    if not webhook:
        print("❌ 未找到飞书 webhook，请设置 FEISHU_WEBHOOK_URL 或配置 config.yaml")
        return 1

    ai_data = load_ai_results(input_path)
    trends = extract_trends(ai_data)

    if not trends:
        print("⚠️ AI 结果为空或格式不符，未发送推送")
        return 1

    text = build_feishu_text(trends)
    ok = send_feishu_text(webhook, text, max_bytes)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
