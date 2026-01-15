"""
竞品社媒AI分析模块 (第二部分)
对提取的数据进行AI分析，重点关注玩法更新和线下活动
"""
import json
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from openai import OpenAI

import env_loader  # noqa: F401

from CompetitorDailyAnalysisAI import call_model_with_retry


API_KEY = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "40"))
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY, timeout=DEFAULT_TIMEOUT)


def build_period_analysis_prompt(
    company: str,
    platform_type: str,
    game: Optional[str],
    url: str,
    posts_data: List[Dict[str, Any]],
    period_days: int
) -> str:
    """
    构建时间段分析提示词
    重点关注玩法更新和线下活动，日常维护内容不重要
    """
    if game:
        title = f"{company} - {game} - {platform_type}"
        context_desc = f"【竞品公司】{company}\n【游戏名称】{game}\n【平台】{platform_type}"
    else:
        title = f"{company} - {platform_type}"
        context_desc = f"【竞品公司】{company}\n【平台】{platform_type}"
    
    game_json = "null" if game is None else f'"{game}"'
    
    # 构建时间段内的所有帖子数据
    total_posts = sum(len(platform_posts) for platform_posts in posts_data if isinstance(platform_posts, list))
    
    if total_posts == 0:
        return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品社媒监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在社交媒体上过去 {period_days} 天的监控结果：

---
{context_desc}
【链接】{url}
【时间段】过去 {period_days} 天
【状态】该账号在过去 {period_days} 天内无社媒更新
---

请简要说明：
1. 该账号在过去 {period_days} 天内没有发布新内容
2. 建议手动查看该账号链接，了解可能的原因

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "{platform_type}",
  "url": "{url}",
  "usability_score": 0,
  "analysis": {{
    "summary": "该账号在过去 {period_days} 天内无社媒更新，建议手动查看链接了解情况。",
    "key_updates": "无新内容可分析。",
    "gameplay_changes": "无新内容可分析。",
    "offline_events": "无新内容可分析。",
    "ad_creative_insights": "无新内容可分析。",
    "platform_summary": "无更新内容。",
    "risk_or_warning": "",
    "direct_action_suggestions": "建议手动查看 {url} 了解账号状态和可能的原因。"
  }}
}}"""
    
    # 整理所有帖子（按时间排序，最新的在前）
    all_posts = []
    for platform_posts in posts_data:
        if isinstance(platform_posts, list):
            all_posts.extend(platform_posts)
    
    # 按发布时间排序（假设有 published_at 字段）
    try:
        all_posts.sort(
            key=lambda p: p.get("published_at", "") or "",
            reverse=True
        )
    except Exception:
        pass
    
    # 构建帖子摘要（最多展示30条）
    posts_summary = []
    for i, post in enumerate(all_posts[:30], 1):
        post_info = f"帖子 {i}:\n"
        
        # 标题/文本内容
        text = post.get("text") or post.get("title") or ""
        if text:
            post_info += f"- 内容: {text[:300]}\n"
        
        # 发布时间
        if post.get("published_at") or post.get("published_at_display"):
            post_info += f"- 发布时间: {post.get('published_at_display') or post.get('published_at', '')}\n"
        
        # 互动数据
        engagement = post.get("engagement", {})
        if engagement:
            eng_items = []
            if engagement.get("like"):
                eng_items.append(f"点赞: {engagement['like']}")
            if engagement.get("comment"):
                eng_items.append(f"评论: {engagement['comment']}")
            if engagement.get("share"):
                eng_items.append(f"分享: {engagement['share']}")
            if engagement.get("retweet"):
                eng_items.append(f"转发: {engagement['retweet']}")
            if engagement.get("view"):
                eng_items.append(f"观看: {engagement['view']}")
            if eng_items:
                post_info += f"- 互动数据: {', '.join(eng_items)}\n"
        
        # 帖子链接
        post_url = post.get("post_url") or post.get("link", "")
        if post_url:
            post_info += f"- 链接: {post_url}\n"
        
        # 媒体链接
        media_urls = post.get("media_urls", [])
        if media_urls:
            post_info += f"- 媒体: {len(media_urls)} 个图片/视频\n"
        
        posts_summary.append(post_info)
    
    data_content = f"""【时间段内帖子数据】（共 {total_posts} 条，展示前 {min(len(all_posts), 30)} 条）

{chr(10).join(posts_summary)}

---
注意：这些是过去 {period_days} 天内该平台的所有更新内容。请重点关注：
1. **玩法更新**：有没有新功能、新机制、新活动、新玩法相关的更新？
2. **线下活动**：有没有线下活动、展会、发布会、合作活动等？
3. **日常维护**：日常的运营维护内容（如普通宣传、节日问候等）可以简要概括，不必过于关注
4. 评分高的帖子优先展示和分析
"""

    return f"""你是一个资深的游戏发行与投放总监，专门帮团队做「竞品社媒监控 & UA 创意洞察」。

现在给你的是某个竞品公司（或其旗下游戏）在社交媒体上过去 {period_days} 天内的所有更新内容：

---
{context_desc}
【链接】{url}
【时间段】过去 {period_days} 天
{data_content}
---

请你分析他们在这段时间内在社交媒体上的动态，**重点关注玩法更新和线下活动**。

分析重点（按优先级排序）：
1. **玩法更新**：有没有新功能、新机制、新活动、新玩法相关的更新？如果有，请详细说明这些更新的内容和特点。
2. **线下活动**：有没有线下活动、展会、发布会、合作活动等？如果有，请说明活动的时间、地点、内容。
3. **广告创意**：从标题/文案风格、内容形式、发布节奏等方面，有哪些值得参考的广告创意启发？
4. **日常维护**：如果只是日常的运营维护内容（如普通宣传、节日问候等），可以简要概括，不必过于关注。
5. **平台概况**：简要概括这个平台在这段时间内的整体更新情况和特点。

特别说明：
- **评分标准**：玩法更新和线下活动评分要高（8-10分），日常维护内容评分要低（1-3分）
- **优先展示**：评分高的内容要优先展示和分析
- 使用简体中文，面向懂投放和产品的同事
- 不要夸大其词，基于实际数据进行分析
- 尽量给出可以落地的 UA 素材 / 活动玩法建议

请严格按以下 JSON 结构输出（不要出现多余字段或自然语言）：

{{
  "title": "{title}",
  "company": "{company}",
  "game": {game_json},
  "platform": "{platform_type}",
  "url": "{url}",
  "usability_score": 0-10 的数字评分（玩法更新和线下活动8-10分，日常维护1-3分）,
  "analysis": {{
    "summary": "用 3-6 句话总结这个竞品在这段时间内在该平台上的主要动作。",
    "key_updates": "**重点内容**：如果有玩法更新或线下活动，请详细说明；如果是日常维护，简要概括即可。",
    "gameplay_changes": "**玩法变化**：详细分析是否有新的玩法、机制、功能更新。如果没有，请写明。",
    "offline_events": "**线下活动**：详细说明是否有线下活动、展会、发布会等。如果没有，请写明。",
    "ad_creative_insights": "从文案、内容形式、发布节奏等方面，总结值得参考的广告创意启发。",
    "platform_summary": "简要概括这个平台在这段时间内的整体更新情况和特点（发布频率、主要内容类型等）。",
    "risk_or_warning": "如果我们照抄这些创意/玩法，在哪些方面可能有风险？",
    "direct_action_suggestions": "给我们内部团队的可执行建议：可以尝试哪些具体素材方向、活动机制？请用中文列表列出 3-6 条。"
  }}
}}"""


def analyze_platform_period_data(
    company: str,
    platform_type: str,
    game: Optional[str],
    url: str,
    platforms_data: List[Dict[str, Any]],
    period_days: int
) -> Optional[Dict[str, Any]]:
    """
    分析单个平台在一段时间内的数据
    
    Args:
        company: 公司名称
        platform_type: 平台类型
        game: 游戏名称（可选）
        url: 平台URL
        platforms_data: 该平台在时间段内的所有数据（可能来自不同日期）
        period_days: 时间段天数
    
    Returns:
        AI分析结果，如果失败则返回None
    """
    # 收集所有帖子
    all_posts = []
    for platform_data in platforms_data:
        posts = platform_data.get("posts", [])
        if posts:
            all_posts.append(posts)
    
    # 构建提示词
    prompt = build_period_analysis_prompt(
        company=company,
        platform_type=platform_type,
        game=game,
        url=url,
        posts_data=all_posts,
        period_days=period_days
    )
    
    # 调用AI分析
    data = call_model_with_retry(prompt)
    
    if not data:
        return None
    
    # 构建结果
    try:
        score = float(data.get("usability_score", 0))
    except Exception:
        score = 0.0
    
    # 计算总帖子数
    total_posts = sum(
        platform_data.get("posts_count", 0)
        for platform_data in platforms_data
    )
    
    # 构建title
    if game:
        title = f"{company} - {game} - {platform_type}"
    else:
        title = f"{company} - {platform_type}"
    
    payload = {
        "title": data.get("title") or title,
        "company": data.get("company") or company,
        "game": data.get("game") or game,
        "platform": data.get("platform") or platform_type,
        "url": data.get("url") or url,
        "usability_score": score,
        "posts_count": total_posts,
        "period_days": period_days,
        "analysis": data.get("analysis") or {},
    }
    
    return payload


def analyze_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析提取的数据
    
    Args:
        extracted_data: 从CompetitorPeriodDataExtractor提取的数据
    
    Returns:
        分析结果，格式：
        {
            "period": {...},
            "companies": {
                "company_name": {
                    "company": "company_name",
                    "platforms_analysis": {
                        "platform_key": {
                            "title": "...",
                            "company": "...",
                            "platform": "...",
                            "usability_score": 8,
                            "posts_count": 10,
                            "analysis": {...}
                        },
                        ...
                    }
                }
            },
            "analyzed_at": "..."
        }
    """
    period = extracted_data.get("period", {})
    companies_data = extracted_data.get("companies", {})
    period_days = period.get("days", 7)
    
    print(f"🤖 开始AI分析，时间段: {period.get('start_date')} 至 {period.get('end_date')} ({period_days} 天)")
    
    result = {
        "period": period,
        "companies": {},
        "analyzed_at": datetime.utcnow().isoformat() + "Z"
    }
    
    for company, company_data in companies_data.items():
        print(f"\n  分析公司: {company}")
        platforms_data_list = company_data.get("platforms_data", [])
        
        if not platforms_data_list:
            print(f"    ⚠️ {company} 无数据，跳过")
            continue
        
        # 按平台分组
        platforms_grouped: Dict[str, List[Dict[str, Any]]] = {}
        
        for platform_data in platforms_data_list:
            platform_type = platform_data.get("platform_type", "")
            game = platform_data.get("game")
            url = platform_data.get("url", "")
            
            # 构建平台唯一键
            key = f"{platform_type}_{game or 'company'}"
            if key not in platforms_grouped:
                platforms_grouped[key] = []
            
            platforms_grouped[key].append(platform_data)
        
        # 分析每个平台
        company_result = {
            "company": company,
            "platforms_analysis": {}
        }
        
        for key, platform_datas in platforms_grouped.items():
            # 获取平台信息（从第一条数据）
            first_data = platform_datas[0]
            platform_type = first_data.get("platform_type", "")
            game = first_data.get("game")
            url = first_data.get("url", "")
            
            print(f"    分析平台: {platform_type}" + (f" - {game}" if game else ""))
            
            # 分析
            analysis_result = analyze_platform_period_data(
                company=company,
                platform_type=platform_type,
                game=game,
                url=url,
                platforms_data=platform_datas,
                period_days=period_days
            )
            
            if analysis_result:
                title = analysis_result.get("title") or f"{company} - {game or ''} - {platform_type}".strip()
                company_result["platforms_analysis"][title] = analysis_result
                
                score = analysis_result.get("usability_score", 0)
                posts_count = analysis_result.get("posts_count", 0)
                print(f"      ✓ 分析完成，评分: {score}, 帖子数: {posts_count}")
            else:
                print(f"      ⚠️ 分析失败，跳过")
        
        result["companies"][company] = company_result
    
    print(f"\n✓ AI分析完成")
    return result


def save_analysis_result(analysis_result: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    保存分析结果到JSON文件
    
    Args:
        analysis_result: 分析结果
        output_path: 输出文件路径，如果为None则自动生成
    
    Returns:
        保存的文件路径
    """
    if output_path is None:
        period = analysis_result.get("period", {})
        start_date = period.get("start_date", "")
        end_date = period.get("end_date", "")
        output_dir = os.environ.get("OUTPUT_DIR")
        if not output_dir or not os.path.exists(output_dir):
            output_dir = os.path.join(os.path.dirname(__file__), "output")
            os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(
            output_dir,
            f"competitor_analysis_result_{start_date}_to_{end_date}.json"
        )
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"💾 分析结果已保存: {output_path}")
        return output_path
    except Exception as exc:
        print(f"❌ 保存分析结果失败: {exc}")
        raise


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="对提取的数据进行AI分析")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="输入的提取数据JSON文件路径（从CompetitorPeriodDataExtractor生成）"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，不指定则自动生成）"
    )
    
    args = parser.parse_args()
    
    # 读取提取的数据
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        return 1
    
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取输入文件失败: {e}")
        return 1
    
    # 分析数据
    analysis_result = analyze_extracted_data(extracted_data)
    
    # 保存结果
    output_path = save_analysis_result(analysis_result, args.output)
    
    print(f"\n✅ AI分析完成: {output_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
