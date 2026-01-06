import asyncio
import csv
import json
import os
import re
from html import unescape
from typing import Dict, List, Tuple

import requests
from openai import OpenAI

import env_loader  # noqa: F401  # 确保 .env 环境变量被加载

# 优先使用环境变量提供的 API Key；如未设置则回退到原硬编码值
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not API_KEY:
    API_KEY = "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"

# MODIFIED: allow timeout override and proxy via env
DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


# === 内容抓取与清洗 ===

def clean_html(text: str) -> str:
    """移除脚本/样式及 HTML 标签，保留可读正文片段"""
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_article_content(url: str, timeout: int = 10, max_chars: int = 1200) -> str:
    """抓取文章正文片段，失败则返回空字符串"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return ""
        cleaned = clean_html(resp.text)
        return cleaned[:max_chars]
    except Exception:
        return ""


async def fetch_articles_for_keyword(
    keyword: str, links: List[str], max_links: int = 2, semaphore: asyncio.Semaphore = None
) -> List[Dict[str, str]]:
    """并发抓取关键词关联的文章"""
    tasks = []
    results: List[Dict[str, str]] = []

    for link in links[:max_links]:
        async def _fetch(link=link):
            if semaphore:
                async with semaphore:
                    content = await asyncio.to_thread(fetch_article_content, link)
            else:
                content = await asyncio.to_thread(fetch_article_content, link)
            if content:
                results.append({"url": link, "excerpt": content})

        tasks.append(asyncio.create_task(_fetch()))

    if tasks:
        await asyncio.gather(*tasks)

    return results


# === 数据准备 ===

def read_trends_from_csv(
    csv_path: str = "/app/output/google_trends_raw.csv",
    max_items: int = 30,
    max_links_per_trend: int = 3,
) -> List[Dict]:
    trends: List[Dict] = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_items:
                    break
                keyword = (row.get("Keyword") or "").strip()
                if not keyword:
                    continue
                raw_links = (row.get("Article Links") or "").splitlines()
                links = [ln.strip() for ln in raw_links if ln.strip()]
                trends.append(
                    {
                        "keyword": keyword,
                        "rank": row.get("Rank") or "",
                        "search_volume": row.get("Search Volume") or "",
                        "links": links[:max_links_per_trend],
                    }
                )
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return trends


# === AI 阶段一：关键词筛选 ===

def select_keywords_with_ai(trends: List[Dict], pick: int = 5) -> List[str]:
    if not trends:
        return []

    candidates = [
        {
            "keyword": t["keyword"],
            "rank": t["rank"],
            "search_volume": t["search_volume"],
            "urls": t.get("links", [])[:2],
        }
        for t in trends
    ]
    prompt = f"""You are selecting Google Trends suitable for casual game ads.

Input candidates (JSON list with keyword, rank, volume, URLs):
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Our firm:We're a dynamic firm creating & marketing casual games globally. We focus on AI - powered content. Our growth loop involves user acquisition, product development, and monetization. We seek creative assets with engaging visuals, clear value, cultural relevance, optimization potential, and a data - driven approach. We use innovative AI for content creation.

Interests: Funny events, entertainment, scandals, pop culture, light-hearted viral news and anythings that our company may interested.
UNINTERESTED: Serious politics(strictly forbiden), diplomacy, war, deaths/obituaries, routine sports scores.

# Hints:
If you find some topics are actually refering to a same event, you should try to avoid duplicated reporting. For example, if multiple keywords are refering to one movie or event, you just need to keep the one with highest volumn.

despite the uninterested events, you should try to give more potential events (don't be too strict on "Interestes" events)

Task:
- Use both keyword and URL clues to judge cultural/creative potential.
- Choose up to {pick} keywords with highest UA/ads potential; drop low-signal or uninterested topics.



Output strictly as JSON: {{"selected_keywords": ["kw1","kw2",...]}}
Do not add extra fields."""
    response = None
    # MODIFIED: add simple retry with backoff and allow per-call timeout override
    timeout = float(os.environ.get("OPENAI_TIMEOUT", DEFAULT_TIMEOUT))
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="google/gemini-3-flash-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=timeout,
            )
            break
        except Exception as exc:
            if attempt == 2:
                raise
            wait = 2 * (attempt + 1)
            print(f"[WARN] select_keywords retry {attempt+1}/3 after error: {exc}, waiting {wait}s")
            time.sleep(wait)

    ai_content = response.choices[0].message.content

    try:
        data = json.loads(ai_content)
        selected = data.get("selected_keywords") or []
        return [kw for kw in selected if isinstance(kw, str) and kw.strip()]
    except Exception as e:
        print(f"Failed to parse selection JSON: {e}\nRaw: {ai_content}")
        return []


# === AI 阶段二：深度分析 ===

def build_final_prompt_for_topic(topic_payload: Dict) -> str:
    """为单个主题生成深度分析提示"""
    trends_json = json.dumps([topic_payload], ensure_ascii=False, indent=2)
    return f"""# Role
You are a Senior UA (User Acquisition) Specialist and Creative Director for a leading AI-driven casual gaming company. Your expertise lies in distilling viral trends into actionable ad creative concepts and product optimization ideas.

# Input Data
JSON Content of Today's Google Trends:
---
{trends_json}
---

# Core Business Context (Target)
- Company Focus: Casual Games & Audio Social Products.
- Key Tech: AI-driven dynamic content, Stylized Models (adapting to different markets), Multi-agent systems.
- Goal: Create high-conversion ad creatives and optimize user interaction based on cultural zeitgeist.

# Task Instructions

1. **Deep Content Analysis**: 
- For this trends, read through the whole events providing the URLs to extract the core emotional hook and visual potential.
- You are required give a precise summary on the event. You should'not bragging the event, state what it is. Remeber to add description about the event because people may not familiar with it (unless it's common knowledge)

3. **Scoring Logic (Usability Score: 0-10)**:
Calculate the score using this weighted formula:
- **Trend Power (30%)**: Based on Rank and Search Volume.
- **Cultural Resonance (20%)**: Does it touch a "nerve" in US culture? (Nostalgia, Controversy, Joy).
- **Reference Value (50%)**: How easily can this be turned into a CASUAL GAME AD? (e.g., Can it become a intriging mini game ad? A stylized visual skin? A viral audio hook?)

# Output Requirements (JSON Template)
You **MUST** return a single JSON object. The "Trend Title" should be the original keyword.
The "AI_Insight" must be in Chinese, structured as: [Event Summary] + [Ad/UA Inspiration] + [Nature of Event].



```json
{{
"google_trend_ai": {{
        "Keyword_Title": {{
        "url": "primary_link",
        "ranks": rank_number,
        "usability_score": float,
            "analysis": {{
                "summary": "用一段文字来精确概括事件，其中必须包含事件的介绍(如这这个电影的基本介绍)以及具体为什么这个时候有热度",
                "ua_inspiration": "针对休闲游戏广告投放、素材创意（视频与图片的生成创意）的具体启发。严禁：对玩法和游戏产品本身的建议；用晦涩难懂的总结形容特点。必须：做到UA focus。将具体热点和UA结合。例如：有一温馨的歌火（名字叫xxx）了，正确输出例如：用xxx做bgm（记得考虑版权问题）；错误输出：用温馨的歌作bgm。你的职责：为每一个UA灵感生成一小段可以用于图片或视频（具体看你的灵感说的是什么）生成的提示词",
                "nature": "事件性质分类（如：影视，丑闻，游戏，节日，气候，大事件，等等）",
                "ai_suitability_check": "说明该趋势是否适合AI模型生成素材，若不适合请直言 (should fitting your reference value)"
            }},
        "mobileUrl": ""
        }}
    }}
}}
```"""


def generate_topic_report(topic_payload: Dict) -> Dict:
    """对单个主题调用模型生成报告"""
    prompt = build_final_prompt_for_topic(topic_payload)
    response = None
    timeout = float(os.environ.get("OPENAI_TIMEOUT", DEFAULT_TIMEOUT))
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="google/gemini-3-flash-preview",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=timeout,
            )
            break
        except Exception as exc:
            if attempt == 2:
                raise
            wait = 2 * (attempt + 1)
            print(f"[WARN] final_report retry {attempt+1}/3 after error: {exc}, waiting {wait}s")
            time.sleep(wait)

    ai_content = response.choices[0].message.content
    try:
        return json.loads(ai_content)
    except Exception as e:
        print(f"Failed to parse final JSON: {e}\nRaw: {ai_content}")
        return {}


# === 主流程 ===

async def process():
    # 第一步：读取 CSV，最多 30 条，初筛关键词
    trends = read_trends_from_csv(max_items=30, max_links_per_trend=3)
    if not trends:
        print("⚠️ 未从 CSV 读取到有效趋势数据")
        return

    selected_keywords = select_keywords_with_ai(trends, pick=5)
    if not selected_keywords:
        print("⚠️ AI 未返回可用的关键词，流程结束")
        return

    # 第二步：仅对入选关键词抓取正文
    semaphore = asyncio.Semaphore(5)
    keyword_to_links = {t["keyword"]: t["links"] for t in trends}
    fetch_tasks = []
    for kw in selected_keywords:
        links = keyword_to_links.get(kw, [])
        fetch_tasks.append(
            fetch_articles_for_keyword(kw, links, max_links=2, semaphore=semaphore)
        )

    fetched_articles = await asyncio.gather(*fetch_tasks)

    # 组装供二次 AI 使用的 payload
    selected_payload: List[Dict] = []
    for kw, articles in zip(selected_keywords, fetched_articles):
        rank = next((t["rank"] for t in trends if t["keyword"] == kw), "")
        search_volume = next((t["search_volume"] for t in trends if t["keyword"] == kw), "")
        selected_payload.append(
            {
                "keyword": kw,
                "rank": rank,
                "search_volume": search_volume,
                "articles": articles,
                "links": keyword_to_links.get(kw, []),
            }
        )

    # 可选：保存中间数据便于排查
    try:
        with open("/app/output/trends_selected.json", "w", encoding="utf-8") as f:
            json.dump(
                {"selected_keywords": selected_keywords, "trends": selected_payload},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print(f"写入中间文件失败: {e}")

    # 第三步：逐主题生成最终 JSON 报告并汇总
    merged = {"google_trend_ai": {}}
    for topic in selected_payload:
        topic_report = generate_topic_report(topic)
        if not topic_report or "google_trend_ai" not in topic_report:
            print(f"[WARN] 单主题生成失败，跳过: {topic.get('keyword')}")
            continue
        # 合并单主题结果
        merged["google_trend_ai"].update(topic_report["google_trend_ai"])

    if not merged["google_trend_ai"]:
        print("⚠️ 最终报告生成失败")
        return

    output_path = "/app/output/ai_result.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"✅ AI Analysis saved to {output_path}")
    except Exception as e:
        print(f"❌ Failed to save AI JSON: {e}")


def process_ai_response():
    asyncio.run(process())


if __name__ == "__main__":
    process_ai_response()
