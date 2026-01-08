import json
import os
import time
from typing import Any, Dict, List, Tuple

from openai import OpenAI

import env_loader  # noqa: F401


API_KEY = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


def load_tiktok_data(path: str = "/app/output/tiktok_raw.json") -> Tuple[List[Dict[str, Any]], str | None]:
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(__file__), "output", "tiktok_raw.json")
        if os.path.exists(alt):
            path = alt
        else:
            print(f"❌ 未找到 TikTok 数据文件: {path}")
            return [], None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析 TikTok 数据失败: {exc}")
        return [], None
    items = data.get("items") or []
    fetched_at = data.get("fetched_at")
    return items, fetched_at


def build_tiktok_prompt(item: Dict[str, Any]) -> str:
    company = item["company"]
    game = item.get("game")
    username = item.get("username", "")
    url = item["url"]
    priority = item.get("priority", "medium")
    videos = item.get("videos", [])

    if game:
        title = f"{company} - {game} - TikTok"
        context_desc = f"【竞品公司】{company}\n【游戏名称】{game}\n【TikTok账号】@{username}"
    else:
        title = f"{company} - TikTok"
        context_desc = f"【竞品公司】{company}\n【TikTok账号】@{username}"

    game_json = "null" if game is None else f'"{game}"'

    if videos:
        lines = []
        for i, v in enumerate(videos, 1):
            seg = f"视频 {i}:\n"
            if v.get("title"):
                seg += f"- 标题: {v['title']}\n"
            if v.get("text"):
                seg += f"- 文本: {v['text']}\n"
            if v.get("time"):
                seg += f"- 时间: {v['time']}\n"
            if v.get("link"):
                seg += f"- 链接: {v['link']}\n"
            lines.append(seg)
        videos_content = f"【最新短视频】（共 {len(videos)} 条）\n\n" + "\n".join(lines)
    else:
        videos_content = "【短视频数据】\n未获取到短视频数据。"

    return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品 TikTok 监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在 TikTok 上的最新短视频：

---
{context_desc}
【链接】{url}
【优先级】{priority}
{videos_content}
---

请你深入分析这些短视频，并从「广告创意」和「玩法/机制」两个角度给出专业观察。

分析重点：
1. 最近视频关注的主题与风格是什么？是否有活动、更新、联动？
2. 内容结构（前 3 秒抓点、转场、字幕、BGM、UGC/演员/实录等）有什么可借鉴之处？
3. 文案与视觉的配合方式是否有效？对我们有什么启发？
4. 可转化为 UA 素材/活动玩法的点有哪些？

输出要求：
- 使用简体中文，面向懂投放和产品的同事
- 不要夸大其词，基于实际视频内容进行分析
- 给出可以落地的 UA 素材/活动玩法建议

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "tiktok",
  "username": "{username}",
  "url": "{url}",
  "priority": "{priority}",
  "usability_score": 0-10 的数字评分（越高代表越值得跟进作为广告创意/玩法参考）,
  "analysis": {{
    "summary": "用 3-6 句话总结这个竞品在 TikTok 上的最新动态和主要内容风格。",
    "key_videos_analysis": "分析最重要或最受欢迎的几条短视频，说明它们传达了什么信息，为什么值得关注。",
    "ad_creative_insights": "从短视频的镜头、节奏、字幕、BGM、梗/互动等角度，总结值得参考的广告创意启发。用条列式中文总结。",
    "gameplay_or_mechanic_insights": "有没有透露新的玩法、机制、活动、更新？如果有，简要概括，并说明为什么对我们有启发。",
    "direct_action_suggestions": "给我们内部团队的可执行建议：可以尝试哪些具体素材方向、活动机制、文案风格？请用中文列表列出 3-6 条。"
  }}
}}"""


def call_ai_with_retry(prompt: str) -> Dict[str, Any]:
    if not API_KEY:
        print("⚠️ 未配置 OPENROUTER_API_KEY / OPENAI_API_KEY，AI 分析将被跳过。")
        return {}
    timeout = float(os.environ.get("OPENAI_TIMEOUT", DEFAULT_TIMEOUT))
    last_error = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="google/gemini-3-flash-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=timeout,
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                wait = 2 * (attempt + 1)
                print(f"  [WARN] AI 调用失败，重试 {attempt+1}/3，等待 {wait}s，错误：{exc}")
                time.sleep(wait)
    print(f"  ❌ 多次调用 AI 失败: {last_error}")
    return {}


def analyze_tiktok_videos() -> None:
    print("=" * 60)
    print("TikTok 短视频 AI 分析")
    print("=" * 60)
    print()
    items, fetched_at = load_tiktok_data()
    if not items:
        print("⚠️ 未找到 TikTok 数据")
        return
    print(f"✓ 读取到 {len(items)} 个账号的数据\n")
    results = {}
    for item in items:
        company = item["company"]
        game = item.get("game")
        username = item.get("username", "")
        display = f"{company} - {game}" if game else company
        print(f"[*] 正在分析：{display} (@{username})")
        prompt = build_tiktok_prompt(item)
        data = call_ai_with_retry(prompt)
        if not data:
            print("  ⚠️ 分析失败，跳过")
            continue
        key = data.get("title") or f"{display} - TikTok"
        payload = {
            "company": data.get("company") or company,
            "game": data.get("game") or game,
            "platform": "tiktok",
            "username": data.get("username") or username,
            "url": data.get("url") or item["url"],
            "priority": data.get("priority") or item.get("priority", "medium"),
            "usability_score": float(data.get("usability_score", 0)),
            "videos_count": item.get("videos_count", 0),
            "fetched_at": fetched_at,
            "analysis": data.get("analysis") or {},
        }
        results[key] = payload
    if not results:
        print("⚠️ 未生成任何有效的分析结果")
        return
    output_dir = "/app/output"
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "tiktok_ai_result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ TikTok AI 分析结果已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存分析结果失败: {exc}")


if __name__ == "__main__":
    analyze_tiktok_videos()

