import json
import os
import time
from typing import Any, Dict, List, Tuple

from openai import OpenAI

import env_loader  # noqa: F401


API_KEY = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


def load_facebook_data(path: str = "/app/output/facebook_raw.json") -> Tuple[List[Dict[str, Any]], str | None]:
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(__file__), "output", "facebook_raw.json")
        if os.path.exists(alt):
            path = alt
        else:
            print(f"❌ 未找到 Facebook 数据文件: {path}")
            return [], None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析 Facebook 数据失败: {exc}")
        return [], None
    items = data.get("items") or []
    fetched_at = data.get("fetched_at")
    return items, fetched_at


def build_facebook_prompt(item: Dict[str, Any]) -> str:
    company = item["company"]
    game = item.get("game")
    url = item.get("url", "")
    page_id = item.get("page_id", "")
    priority = item.get("priority", "medium")
    posts = item.get("posts", [])

    if game:
        title = f"{company} - {game} - Facebook"
        context_desc = f"【竞品公司】{company}\n【游戏名称】{game}\n【Facebook 页面】{url or page_id}"
    else:
        title = f"{company} - Facebook"
        context_desc = f"【竞品公司】{company}\n【Facebook 页面】{url or page_id}"

    game_json = "null" if game is None else f'"{game}"'

    if posts:
        lines = []
        for i, p in enumerate(posts, 1):
            seg = f"帖子 {i}:\n"
            if p.get("time"):
                seg += f"- 时间: {p['time']}\n"
            if p.get("title"):
                seg += f"- 标题: {p['title']}\n"
            if p.get("text"):
                seg += f"- 文本: {p['text']}\n"
            if p.get("link"):
                seg += f"- 链接: {p['link']}\n"
            lines.append(seg)
        posts_content = f"【最新 Facebook 帖子】（共 {len(posts)} 条）\n\n" + "\n".join(lines)
    else:
        posts_content = "【帖子数据】\n未获取到 Facebook 帖子。"

    return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品 Facebook 监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在 Facebook 页面上的最新帖子：

---
{context_desc}
【优先级】{priority}
{posts_content}
---

请你深入分析这些帖子，并从「广告创意」和「玩法/机制」两个角度给出专业观察。

分析重点：
1. 他们在 Facebook 上主要发布哪些类型的内容（活动、公告、软文、社区互动等）？
2. 文案风格、图片/视频使用、排版有什么特点？
3. 有无值得借鉴的用户互动设计（评论引导、投票、活动参与方式等）？
4. 对我们在 Facebook 或其他社媒上的投放与品牌运营有什么启发？

输出要求：
- 使用简体中文，面向懂投放和产品的同事
- 不要夸大其词，基于实际帖子内容进行分析
- 尽量给出可以落地的 UA 素材/活动玩法建议

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "facebook",
  "url": "{url}",
  "page_id": "{page_id}",
  "priority": "{priority}",
  "usability_score": 0-10 的数字评分（越高代表越值得跟进作为广告创意/玩法参考）, 
  "analysis": {{
    "summary": "用 3-6 句话总结这个竞品在 Facebook 上的最新动态和主要内容风格。",
    "content_strategy": "概括他们在 Facebook 上的内容策略（如频率、主题、内容形式），以及与用户沟通的方式。",
    "ad_creative_insights": "从图片/视频、标题、文案、行动号召等角度，总结值得参考的广告创意启发。用条列式中文总结。",
    "community_and_engagement": "他们如何运营社区与用户互动？有哪些评论互动、问答、活动机制值得学习？",
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


def analyze_facebook_posts() -> None:
    print("=" * 60)
    print("Facebook 帖子 AI 分析")
    print("=" * 60)
    print()
    items, fetched_at = load_facebook_data()
    if not items:
        print("⚠️ 未找到 Facebook 数据")
        return
    print(f"✓ 读取到 {len(items)} 个账号的数据\n")

    results: Dict[str, Any] = {}
    for item in items:
        company = item["company"]
        game = item.get("game")
        url = item.get("url", "")
        display = f"{company} - {game}" if game else company
        print(f"[*] 正在分析：{display} (Facebook)")
        prompt = build_facebook_prompt(item)
        data = call_ai_with_retry(prompt)
        if not data:
            print("  ⚠️ 分析失败，跳过")
            continue
        key = data.get("title") or f"{display} - Facebook"
        payload = {
            "company": data.get("company") or company,
            "game": data.get("game") or game,
            "platform": "facebook",
            "url": data.get("url") or url,
            "page_id": data.get("page_id") or item.get("page_id", ""),
            "priority": data.get("priority") or item.get("priority", "medium"),
            "usability_score": float(data.get("usability_score", 0)),
            "posts_count": item.get("posts_count", 0),
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
    out_path = os.path.join(output_dir, "facebook_ai_result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Facebook AI 分析结果已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存分析结果失败: {exc}")


if __name__ == "__main__":
    analyze_facebook_posts()

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}