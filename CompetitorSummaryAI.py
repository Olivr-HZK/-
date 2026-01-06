import json
import os
import time
from typing import Any, Dict, List

from openai import OpenAI

import env_loader  # noqa: F401  # 确保 .env 中的 OPENROUTER_API_KEY / OPENAI_API_KEY 被加载


# === OpenRouter / OpenAI 客户端配置 ===

API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not API_KEY:
    # 保持与原项目一致的回退逻辑
    API_KEY = os.getenv("OPENAI_API_KEY", "")

DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


def load_raw_social(path: str = "/app/output/competitor_social_raw.json") -> List[Dict[str, Any]]:
    """
    读取第 1 步爬虫的结果：competitor_social_raw.json
    """
    if not os.path.exists(path):
        # 兼容本地运行
        alt = os.path.join(os.path.dirname(__file__), "output", "competitor_social_raw.json")
        if os.path.exists(alt):
            path = alt
        else:
            print(f"❌ 未找到社媒原始数据文件: {path}")
            return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析社媒原始数据失败: {exc}")
        return []

    items = data.get("items") or []
    norm_items: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        # 支持新格式：company, game, platform_type
        company = (it.get("company") or "").strip()
        game = it.get("game")  # 可能为 None
        platform_type = (it.get("platform_type") or it.get("platform") or "unknown").strip()
        url = (it.get("url") or "").strip()
        html_snippet = (it.get("html_snippet") or "").strip()
        priority = (it.get("priority") or "medium").strip()
        
        # 兼容旧格式：name, platform
        if not company:
            company = (it.get("name") or "").strip()
        if not company or not url or not html_snippet:
            continue
        
        norm_items.append(
            {
                "company": company,
                "game": game,
                "platform_type": platform_type,
                "url": url,
                "html_snippet": html_snippet,
                "priority": priority,
            }
        )
    return norm_items


def build_competitor_prompt(item: Dict[str, Any]) -> str:
    """
    针对单个竞品社媒账号构建提示词：
    - 让模型从 HTML 片段中还原最近的发言、宣传点
    - 帮忙识别"新广告创意"和"新玩法/机制"
    - 用中文输出，方便直接给投放和产品同学看
    """
    company = item["company"]
    game = item.get("game")
    platform_type = item["platform_type"]
    url = item["url"]
    snippet = item["html_snippet"]
    priority = item.get("priority", "medium")
    
    # 构建显示标题
    if game:
        title = f"{company} - {game} - {platform_type}"
        context_desc = f"【竞品公司】{company}\n【游戏名称】{game}\n【平台】{platform_type}"
    else:
        title = f"{company} - {platform_type}"
        context_desc = f"【竞品公司】{company}\n【平台】{platform_type}"
    
    # 处理 game 字段的 JSON 格式
    game_json = "null" if game is None else f'"{game}"'

    return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品社媒监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在社交媒体上的页面 HTML 片段（可能有噪音，不要求完全还原前端结构）：

---
{context_desc}
【链接】{url}
【优先级】{priority}
【HTML 片段】（可能包含最近多条发帖、评论、活动文案等）
{snippet}
---

请你从中尽量还原他们最近在社交媒体上做了哪些动作，并从「广告创意」和「玩法/机制」两个角度给出专业观察。

输出要求：
- 使用简体中文，面向懂投放和产品的同事。
- 不要夸大其词，如果信息不够清晰，要明确说明「信息不足」。
- 尽量给出可以落地的 UA 素材 / 活动玩法建议。
- 如果这是某个具体游戏的账号，请重点关注该游戏的玩法、活动、素材方向。

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "{platform_type}",
  "url": "{url}",
  "priority": "{priority}",
  "usability_score": 0-10 的数字评分（越高代表越值得跟进作为广告创意/玩法参考）,
  "analysis": {{
    "summary": "用 3-6 句话总结这个竞品在最近社媒上的主要动作（发布了什么内容、在强调什么卖点/活动）",
    "ad_creative_insights": "他们在文案、素材形式、节奏上有哪些值得参考的广告创意？用条列式中文总结。",
    "gameplay_or_mechanic_insights": "有没有显露出新的玩法、数值/活动机制、互动方式？如果有，简要概括，并说明为什么对我们有启发；如果看不出来，请写明。",
    "trend_and_positioning": "他们在形象/品牌/用户心智上试图占据什么位置？例如：硬核、休闲、搞笑、故事感、情绪价值等。",
    "risk_or_warning": "如果我们照抄这些创意/玩法，在哪些方面可能有风险（合规、品牌形象、舆论等）？如信息不足请注明。",
    "direct_action_suggestions": "给我们内部团队的可执行建议：可以尝试哪些具体素材方向、活动机制？请用中文列表列出 3-6 条。"
  }}
}}"""


def call_model_with_retry(prompt: str) -> Dict[str, Any]:
    """
    调用大模型并做简单重试，返回解析后的 JSON。
    """
    if not API_KEY:
        print("⚠️ 未配置 OPENROUTER_API_KEY / OPENAI_API_KEY，大模型分析将被跳过。")
        return {}

    timeout = float(os.environ.get("OPENAI_TIMEOUT", DEFAULT_TIMEOUT))
    last_error: Exception | None = None
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
                print(f"[WARN] 调用模型失败，重试 {attempt+1}/3，等待 {wait}s，错误：{exc}")
                time.sleep(wait)
    print(f"❌ 多次调用模型失败: {last_error}")
    return {}


def analyze_competitors() -> None:
    """
    工作流第 2 步：对爬取到的竞品社媒内容做 AI 总结与创意洞察。
    输出为 /app/output/competitor_ai_result.json
    """
    items = load_raw_social()
    if not items:
        return

    results: Dict[str, Any] = {}
    for it in items:
        company = it["company"]
        game = it.get("game")
        platform_type = it["platform_type"]
        
        # 构建显示标题
        if game:
            title = f"{company} - {game} - {platform_type}"
        else:
            title = f"{company} - {platform_type}"
        
        print(f"[*] 正在分析：{title}")
        prompt = build_competitor_prompt(it)
        data = call_model_with_retry(prompt)
        if not data:
            print(f"⚠️ 分析失败，跳过：{title}")
            continue

        # 兼容 sender 现有的结构习惯：顶层是一个映射 title -> payload
        key = data.get("title") or title
        try:
            score = float(data.get("usability_score", 0))
        except Exception:
            score = 0.0
        
        payload = {
            "company": data.get("company") or company,
            "game": data.get("game") or game,
            "platform": data.get("platform") or platform_type,
            "url": data.get("url") or it["url"],
            "priority": data.get("priority") or it.get("priority", "medium"),
            "usability_score": score,
            "analysis": data.get("analysis") or {},
        }
        results[key] = payload

    if not results:
        print("⚠️ 未生成任何有效的竞品 AI 分析结果。")
        return

    output_dir = "/app/output"
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)

    out_path = os.path.join(output_dir, "competitor_ai_result.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ 竞品社媒 AI 分析结果已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存 AI 结果失败: {exc}")


if __name__ == "__main__":
    analyze_competitors()

