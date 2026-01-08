import json
import os
from datetime import datetime
from typing import Any, Dict, List

import env_loader  # noqa: F401
from CompetitorScraperRapidAPI import extract_username_from_url
from tiktok_video_extractor import TikTokExtractor


def load_input_json(input_path: str = "/app/input/twitter_input.json") -> Dict[str, Any]:
    if not os.path.exists(input_path):
        alt = os.path.join(os.path.dirname(__file__), "input", "twitter_input.json")
        if os.path.exists(alt):
            input_path = alt
        else:
            print(f"❌ 未找到输入文件: {input_path}")
            return {}
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"❌ 读取或解析输入失败: {exc}")
        return {}


def parse_tiktok_accounts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    competitors = data.get("competitors") or []
    accounts: List[Dict[str, Any]] = []
    for comp in competitors:
        if not isinstance(comp, dict):
            continue
        company = (comp.get("name") or "").strip()
        if not company:
            continue
        priority = (comp.get("priority") or "medium").strip().lower()
        for plat in (comp.get("platforms") or []):
            if not isinstance(plat, dict):
                continue
            if (plat.get("type") or "").strip().lower() != "tiktok":
                continue
            username = (plat.get("username") or "").strip().lstrip("@")
            url = (plat.get("url") or "").strip()
            sec_uid = (plat.get("sec_uid") or "").strip()  # 新增：读取保存的 sec_uid
            if not username and url:
                username = extract_username_from_url(url, "tiktok") or ""
                username = username.strip().lstrip("@")
            if not username:
                print(f"⚠️ 跳过：未提供 tiktok username，且无法从 url 提取。company={company}, url={url}")
                continue
            if not url:
                url = f"https://www.tiktok.com/@{username}"
            accounts.append(
                {
                    "company": company,
                    "game": None,
                    "platform_type": "tiktok",
                    "username": username,
                    "url": url,
                    "sec_uid": sec_uid,  # 新增：保存 sec_uid
                    "priority": priority,
                    "platform_config": plat,  # 保存原始配置，用于更新
                }
            )
        for game in (comp.get("games") or []):
            if not isinstance(game, dict):
                continue
            game_name = (game.get("name") or "").strip()
            game_priority = (game.get("priority") or priority).strip().lower()
            for plat in (game.get("platforms") or []):
                if not isinstance(plat, dict):
                    continue
                if (plat.get("type") or "").strip().lower() != "tiktok":
                    continue
                username = (plat.get("username") or "").strip().lstrip("@")
                url = (plat.get("url") or "").strip()
                sec_uid = (plat.get("sec_uid") or "").strip()  # 新增：读取保存的 sec_uid
                if not username and url:
                    username = extract_username_from_url(url, "tiktok") or ""
                    username = username.strip().lstrip("@")
                if not username:
                    print(
                        f"⚠️ 跳过：未提供 tiktok username，且无法从 url 提取。company={company}, game={game_name}, url={url}"
                    )
                    continue
                if not url:
                    url = f"https://www.tiktok.com/@{username}"
                accounts.append(
                    {
                        "company": company,
                        "game": game_name,
                        "platform_type": "tiktok",
                        "username": username,
                        "url": url,
                        "sec_uid": sec_uid,  # 新增：保存 sec_uid
                        "priority": game_priority,
                        "platform_config": plat,  # 保存原始配置，用于更新
                    }
                )
    return accounts


def update_secuid_in_json(input_path: str, username: str, sec_uid: str) -> None:
    """更新 JSON 文件中的 sec_uid"""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        updated = False
        for competitor in data.get("competitors", []):
            # 检查公司级别的平台
            for platform in (competitor.get("platforms") or []):
                if (platform.get("username", "").strip().lstrip("@") == username and 
                    (platform.get("type") or "").strip().lower() == "tiktok"):
                    platform["sec_uid"] = sec_uid
                    updated = True
                    break
            
            # 检查游戏级别的平台
            for game in (competitor.get("games") or []):
                for platform in (game.get("platforms") or []):
                    if (platform.get("username", "").strip().lstrip("@") == username and 
                        (platform.get("type") or "").strip().lower() == "tiktok"):
                        platform["sec_uid"] = sec_uid
                        updated = True
                        break
        
        if updated:
            with open(input_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已更新 JSON 文件中的 sec_uid")
    except Exception as exc:
        print(f"  ⚠️ 更新 JSON 文件失败: {exc}")


def scrape_tiktok_videos(accounts: List[Dict[str, Any]], max_videos: int = 5, input_path: str = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    from CompetitorScraperRapidAPI import get_tiktok_secuid_from_username
    
    for acc in accounts:
        company = acc["company"]
        game = acc.get("game")
        username = acc["username"]
        sec_uid = acc.get("sec_uid", "")  # 读取保存的 sec_uid
        url = acc["url"]
        priority = acc.get("priority", "medium")
        display_name = f"{company} - {game}" if game else company
        print(f"\n[*] 正在抓取：{display_name} (TikTok @{username}) [优先级: {priority}]")

        # 优先使用保存的 sec_uid，如果没有则获取
        if not sec_uid:
            print(f"  [TikTok] 账号: {username}，正在获取 secUid...")
            sec_uid = get_tiktok_secuid_from_username(username)
            if sec_uid and input_path:
                update_secuid_in_json(input_path, username, sec_uid)
        else:
            print(f"  [TikTok] 账号: {username}，使用已保存的 secUid: {sec_uid[:30]}...")
        
        if not sec_uid:
            print(f"  ❌ 无法获取 secUid，跳过")
            continue

        # 使用 sec_uid 获取视频
        from CompetitorScraperRapidAPI import get_posts_from_tiktok
        posts = get_posts_from_tiktok(sec_uid, days_ago=None, original_username=username)  # 传入 sec_uid 和原始 username
        
        # 转换为视频格式
        videos = []
        for p in posts[:max_videos]:
            videos.append({
                'time': p.get('published_at', ''),
                'title': (p.get('text', '') or '')[:40],
                'text': p.get('text', ''),
                'link': p.get('post_url', '')
            })
        
        print(f"  ✓ 获取到 {len(videos)} 条视频")

        items.append(
            {
                "company": company,
                "game": game,
                "platform_type": "tiktok",
                "username": username,
                "url": url,
                "priority": priority,
                "videos": videos,
                "videos_count": len(videos),
            }
        )
    return items


def save_tiktok_data(items: List[Dict[str, Any]], output_path: str = "/app/output/tiktok_raw.json") -> None:
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        alt_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(alt_dir, exist_ok=True)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    payload = {"fetched_at": datetime.utcnow().isoformat() + "Z", "items": items}
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n✅ TikTok 数据已保存至: {output_path}")
    except Exception as exc:
        print(f"❌ 保存数据失败: {exc}")


def scrape_tiktok_workflow(input_path: str = None, max_videos: int = 5) -> str:
    if input_path is None:
        input_path = os.environ.get("TIKTOK_INPUT_PATH", "/app/input/twitter_input.json")
    print("=" * 60)
    print("TikTok 视频爬虫工作流")
    print("=" * 60)
    print()

    print("[步骤 1] 读取输入配置...")
    data = load_input_json(input_path)
    if not data:
        return ""

    print("[步骤 2] 解析 TikTok 账号...")
    accounts = parse_tiktok_accounts(data)
    if not accounts:
        print("⚠️ 未找到任何 TikTok 账号配置")
        return ""
    print(f"✓ 找到 {len(accounts)} 个 TikTok 账号")

    print("\n[步骤 3] 抓取 TikTok 视频...")
    items = scrape_tiktok_videos(accounts, max_videos=max_videos, input_path=input_path)
    if not items:
        print("⚠️ 未成功抓取到任何视频")
        return ""

    print("\n[步骤 4] 保存数据...")
    output_path = os.environ.get("TIKTOK_OUTPUT_PATH", "/app/output/tiktok_raw.json")
    save_tiktok_data(items, output_path)
    return output_path


if __name__ == "__main__":
    scrape_tiktok_workflow()

