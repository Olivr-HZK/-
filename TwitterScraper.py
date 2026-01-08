"""
Twitter 推文爬虫
从 JSON 输入读取配置，抓取指定 Twitter 账号的前5条推文
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

import env_loader  # noqa: F401
from CompetitorScraperRapidAPI import (
    RAPIDAPI_KEY,
    extract_username_from_url,
    get_twitter_user_id_from_username,
    get_posts_from_twitter,
)


def load_input_json(input_path: str = "/app/input/twitter_input.json") -> Dict[str, Any]:
    """从 JSON 文件读取输入配置"""
    if not os.path.exists(input_path):
        # 兼容本地运行
        alt = os.path.join(os.path.dirname(__file__), "input", "twitter_input.json")
        if os.path.exists(alt):
            input_path = alt
        else:
            print(f"❌ 未找到输入文件: {input_path}")
            print(f"   请创建输入文件，格式参考: {os.path.dirname(__file__)}/input/twitter_input.json.example")
            return {}
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析输入文件失败: {exc}")
        return {}


def parse_competitors_from_json(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 JSON 数据中解析竞品账号列表"""
    competitors = data.get("competitors", [])
    
    accounts = []
    for competitor in competitors:
        if not isinstance(competitor, dict):
            continue
        
        company_name = (competitor.get("name") or "").strip()
        if not company_name:
            continue
        
        company_priority = (competitor.get("priority") or "medium").strip().lower()
        
        # 处理公司级别的平台
        for platform in (competitor.get("platforms") or []):
            if not isinstance(platform, dict) or not platform.get("enabled", True):
                continue
            
            platform_type = (platform.get("type") or "").strip().lower()
            if platform_type != "twitter":
                continue  # 只处理 Twitter 平台
            
            # 新策略：优先使用 username；url 仅作为可选展示入口
            username = (platform.get("username") or "").strip().lstrip("@")
            url = (platform.get("url") or "").strip()
            user_id = (platform.get("user_id") or "").strip()  # 新增：读取保存的 user_id
            if not username:
                # 兼容：如果未提供 username，则尝试从 url 提取
                if url:
                    username = extract_username_from_url(url, "twitter") or ""
                    username = username.strip().lstrip("@")
            if not username:
                print(f"⚠️ 跳过：未提供 twitter username，且无法从 url 提取。company={company_name}, url={url}")
                continue
            if not url:
                url = f"https://x.com/{username}"
            
            accounts.append({
                "company": company_name,
                "game": None,
                "platform_type": "twitter",
                "url": url,
                "username": username,
                "user_id": user_id,  # 新增：保存 user_id
                "priority": company_priority,
                "platform_config": platform,  # 保存原始配置，用于更新
            })
        
        # 处理游戏级别的平台
        for game in (competitor.get("games") or []):
            if not isinstance(game, dict):
                continue
            
            game_name = (game.get("name") or "").strip()
            if not game_name:
                continue
            
            game_priority = (game.get("priority") or company_priority).strip().lower()
            
            for platform in (game.get("platforms") or []):
                if not isinstance(platform, dict) or not platform.get("enabled", True):
                    continue
                
                platform_type = (platform.get("type") or "").strip().lower()
                if platform_type != "twitter":
                    continue
                
                username = (platform.get("username") or "").strip().lstrip("@")
                url = (platform.get("url") or "").strip()
                if not username:
                    if url:
                        username = extract_username_from_url(url, "twitter") or ""
                        username = username.strip().lstrip("@")
                if not username:
                    print(
                        f"⚠️ 跳过：未提供 twitter username，且无法从 url 提取。company={company_name}, game={game_name}, url={url}"
                    )
                    continue
                if not url:
                    url = f"https://x.com/{username}"
                
                accounts.append({
                    "company": company_name,
                    "game": game_name,
                    "platform_type": "twitter",
                    "url": url,
                    "username": username,
                    "priority": game_priority,
                })
    
    return accounts


def scrape_twitter_tweets(accounts: List[Dict[str, Any]], max_tweets: int = 5) -> List[Dict[str, Any]]:
    """抓取 Twitter 推文（限制最多 max_tweets 条）"""
    if not RAPIDAPI_KEY:
        print("❌ 未配置 RAPIDAPI_KEY，请在 .env 文件中设置")
        return []
    
    items = []
    for acc in accounts:
        company = acc["company"]
        game = acc.get("game")
        url = acc["url"]
        priority = acc.get("priority", "medium")
        
        display_name = f"{company} - {game}" if game else company
        print(f"\n[*] 正在抓取：{display_name} ({url}) [优先级: {priority}]")
        
        # 新策略：优先使用输入中的 username
        username = (acc.get("username") or "").strip().lstrip("@")
        if not username:
            # 兼容：如果没传 username 再从 url 提取
            username = extract_username_from_url(url, "twitter") or ""
            username = username.strip().lstrip("@")
        if not username:
            print(f"  ❌ 未提供 username，且无法从 url 提取: {url}")
            continue
        
        # 获取推文（直接拿最新推文，不按日期过滤）
        print(f"  [Twitter] 账号: {username}")
        all_posts = get_posts_from_twitter(username, days_ago=None, count=max(20, max_tweets))
        
        # 只取前 max_tweets 条（最新的）
        posts = all_posts[:max_tweets]
        print(f"  ✓ 获取到 {len(posts)} 条推文（从 {len(all_posts)} 条中选取最新 {max_tweets} 条）")
        
        item = {
            "company": company,
            "game": game,
            "platform_type": "twitter",
            "url": url,
            "username": username,
            "priority": priority,
            "posts": posts,
            "posts_count": len(posts),
        }
        items.append(item)
    
    return items


def save_twitter_data(items: List[Dict[str, Any]], output_path: str = "/app/output/twitter_raw.json") -> None:
    """保存抓取的 Twitter 数据"""
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        # 兼容本地运行
        alt_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(alt_dir, exist_ok=True)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    
    payload = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "items": items,
    }
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Twitter 数据已保存至: {output_path}")
    except Exception as exc:
        print(f"❌ 保存数据失败: {exc}")


def scrape_twitter_workflow(input_path: str = None, max_tweets: int = 5) -> str:
    """
    主工作流：抓取 Twitter 推文
    返回输出文件路径
    """
    if input_path is None:
        input_path = os.environ.get("TWITTER_INPUT_PATH", "/app/input/twitter_input.json")
    
    print("=" * 60)
    print("Twitter 推文爬虫工作流")
    print("=" * 60)
    print()
    
    # 1. 读取输入配置
    print("[步骤 1] 读取输入配置...")
    data = load_input_json(input_path)
    if not data:
        return ""
    
    # 2. 解析竞品账号
    print("[步骤 2] 解析竞品账号...")
    accounts = parse_competitors_from_json(data)
    if not accounts:
        print("⚠️ 未找到任何 Twitter 账号配置")
        return ""
    
    print(f"✓ 找到 {len(accounts)} 个 Twitter 账号")
    
    # 3. 抓取推文
    print("\n[步骤 3] 抓取 Twitter 推文...")
    items = scrape_twitter_tweets(accounts, max_tweets=max_tweets, input_path=input_path)
    
    if not items:
        print("⚠️ 未成功抓取到任何推文")
        return ""
    
    # 4. 保存数据
    print("\n[步骤 4] 保存数据...")
    output_path = os.environ.get("TWITTER_OUTPUT_PATH", "/app/output/twitter_raw.json")
    save_twitter_data(items, output_path)
    
    return output_path


if __name__ == "__main__":
    scrape_twitter_workflow()
