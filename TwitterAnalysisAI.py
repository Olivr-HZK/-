"""
Twitter 推文 AI 分析
对抓取的 Twitter 推文进行 AI 分析
"""
import json
import os
import time
from typing import Any, Dict, List, Tuple

from openai import OpenAI

import env_loader  # noqa: F401


# OpenRouter / OpenAI 客户端配置
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not API_KEY:
    API_KEY = os.getenv("OPENAI_API_KEY", "")

DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


def load_twitter_data(path: str = "/app/output/twitter_raw.json") -> Tuple[List[Dict[str, Any]], str | None]:
    """读取 Twitter 推文数据"""
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(__file__), "output", "twitter_raw.json")
        if os.path.exists(alt):
            path = alt
        else:
            print(f"❌ 未找到 Twitter 数据文件: {path}")
            return [], None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析 Twitter 数据失败: {exc}")
        return [], None
    
    items = data.get("items") or []
    fetched_at = data.get("fetched_at")
    return items, fetched_at


def build_twitter_analysis_prompt(item: Dict[str, Any]) -> str:
    """构建 Twitter 推文分析的提示词"""
    company = item["company"]
    game = item.get("game")
    username = item.get("username", "")
    url = item["url"]
    priority = item.get("priority", "medium")
    posts = item.get("posts", [])
    
    # 构建显示标题
    if game:
        title = f"{company} - {game} - Twitter"
        context_desc = f"【竞品公司】{company}\n【游戏名称】{game}\n【Twitter账号】@{username}"
    else:
        title = f"{company} - Twitter"
        context_desc = f"【竞品公司】{company}\n【Twitter账号】@{username}"
    
    game_json = "null" if game is None else f'"{game}"'
    
    # 构建推文内容
    if posts and len(posts) > 0:
        tweets_summary = []
        for i, post in enumerate(posts, 1):
            tweet_info = f"推文 {i}:\n"
            tweet_info += f"- 内容: {post.get('text', '')}\n"
            if post.get("published_at_display"):
                tweet_info += f"- 发布时间: {post['published_at_display']}\n"
            if post.get("post_url"):
                tweet_info += f"- 链接: {post['post_url']}\n"
            if post.get("engagement"):
                eng = post["engagement"]
                eng_str = ", ".join([f"{k}: {v}" for k, v in eng.items() if v])
                if eng_str:
                    tweet_info += f"- 互动数据: {eng_str}\n"
            tweets_summary.append(tweet_info)
        
        tweets_content = f"""【最新推文】（共 {len(posts)} 条）

{chr(10).join(tweets_summary)}
"""
    else:
        tweets_content = "【推文数据】\n未获取到推文数据。"
    
    return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品 Twitter 监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在 Twitter 上的最新推文：

---
{context_desc}
【链接】{url}
【优先级】{priority}
{tweets_content}
---

请你深入分析这些推文，并从「广告创意」和「玩法/机制」两个角度给出专业观察。

分析重点：
1. 他们最近发布了什么内容？有什么新动态、活动、产品更新？
2. 推文的互动情况如何？哪些推文最受欢迎？反映了什么趋势？
3. 文案风格和创意方向有什么特点？对我们有什么启发？
4. 是否透露了新的游戏机制、活动玩法或营销策略？

输出要求：
- 使用简体中文，面向懂投放和产品的同事
- 不要夸大其词，基于实际推文内容进行分析
- 尽量给出可以落地的 UA 素材/活动玩法建议
- 如果这是某个具体游戏的账号，请重点关注该游戏的玩法、活动、素材方向

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "twitter",
  "username": "{username}",
  "url": "{url}",
  "priority": "{priority}",
  "usability_score": 0-10 的数字评分（越高代表越值得跟进作为广告创意/玩法参考）,
  "analysis": {{
    "summary": "用 3-6 句话总结这个竞品在 Twitter 上的最新动态和主要动作。",
    "key_tweets_analysis": "分析最重要或最受欢迎的几条推文，说明它们传达了什么信息，为什么值得关注。",
    "ad_creative_insights": "从推文的文案、风格、配图、互动方式等角度，总结值得参考的广告创意启发。用条列式中文总结。",
    "gameplay_or_mechanic_insights": "有没有透露新的玩法、机制、活动、更新？如果有，简要概括，并说明为什么对我们有启发。",
    "trend_and_positioning": "从推文内容看，他们在形象/品牌/用户心智上试图占据什么位置？例如：硬核、休闲、搞笑、故事感、情绪价值等。",
    "engagement_analysis": "分析推文的互动数据（点赞、转发、评论、观看），哪些类型的推文最受欢迎？有什么规律？",
    "direct_action_suggestions": "给我们内部团队的可执行建议：可以尝试哪些具体素材方向、活动机制、文案风格？请用中文列表列出 3-6 条。"
  }}
}}"""


def call_ai_with_retry(prompt: str) -> Dict[str, Any]:
    """调用 AI 模型并重试"""
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


def analyze_twitter_tweets() -> None:
    """主函数：分析 Twitter 推文"""
    print("=" * 60)
    print("Twitter 推文 AI 分析")
    print("=" * 60)
    print()
    
    # 1. 读取 Twitter 数据
    input_path = os.environ.get("TWITTER_OUTPUT_PATH", "/app/output/twitter_raw.json")
    items, fetched_at = load_twitter_data(input_path)
    
    if not items:
        print("⚠️ 未找到 Twitter 数据")
        return
    
    print(f"✓ 读取到 {len(items)} 个账号的数据\n")
    
    # 2. 对每个账号进行 AI 分析
    results = {}
    for item in items:
        company = item["company"]
        game = item.get("game")
        username = item.get("username", "")
        
        if game:
            display_name = f"{company} - {game}"
        else:
            display_name = company
        
        print(f"[*] 正在分析：{display_name} (@{username})")
        
        prompt = build_twitter_analysis_prompt(item)
        data = call_ai_with_retry(prompt)
        
        if not data:
            print(f"  ⚠️ 分析失败，跳过")
            continue
        
        # 使用 title 作为 key
        key = data.get("title") or f"{display_name} - Twitter"
        
        # 添加推文数量信息
        payload = {
            "company": data.get("company") or company,
            "game": data.get("game") or game,
            "platform": "twitter",
            "username": data.get("username") or username,
            "url": data.get("url") or item["url"],
            "priority": data.get("priority") or item.get("priority", "medium"),
            "usability_score": float(data.get("usability_score", 0)),
            "tweets_count": item.get("posts_count", 0),
            "fetched_at": fetched_at,
            "analysis": data.get("analysis") or {},
        }
        results[key] = payload
    
    if not results:
        print("⚠️ 未生成任何有效的分析结果")
        return
    
    # 3. 保存分析结果
    output_dir = "/app/output"
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
    
    out_path = os.path.join(output_dir, "twitter_ai_result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Twitter AI 分析结果已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存分析结果失败: {exc}")


if __name__ == "__main__":
    analyze_twitter_tweets()
