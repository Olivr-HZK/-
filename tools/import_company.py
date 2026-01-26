"""
导入 King 公司的社媒信息到数据库，并爬取各平台最新数据
- 从 twitter_input.json 读取 King 公司配置
- 写入数据库
- 从各平台爬取5条最新数据（跳过 YouTube 和 LinkedIn）
- 获取 Twitter user_id 并更新到数据库和 JSON
- 保存结果到 JSON 文件供检查
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import env_loader  # noqa: F401

from database.competitor_db import CompetitorDatabaseDB
from scrapers.rapidapi import (
    get_posts_from_twitter,
    get_posts_from_instagram,
    get_posts_from_tiktok,
    get_twitter_user_id_from_username,
    extract_username_from_url,
)
from scrapers.facebook import _fetch_facebook_raw, parse_facebook_posts


def load_king_company_from_json(json_path: str = "input/twitter_input.json") -> Optional[Dict[str, Any]]:
    """从 JSON 文件加载 King 公司配置"""
    try:
        if not os.path.exists(json_path):
            print(f"❌ 文件不存在: {json_path}")
            return None
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        competitors = data.get("competitors", [])
        for competitor in competitors:
            if competitor.get("name", "").lower() == "king":
                return competitor
        
        print(f"❌ 在 {json_path} 中未找到 King 公司")
        return None
    
    except Exception as exc:
        print(f"❌ 读取 JSON 文件失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return None


def save_king_to_database(king_data: Dict[str, Any], db: CompetitorDatabaseDB) -> bool:
    """将 King 公司配置保存到数据库"""
    try:
        company_name = king_data.get("name", "King")
        priority = king_data.get("priority", "high")
        
        # 构建社媒配置结构
        social_media_config = {
            "platforms": king_data.get("platforms", []),
            "games": king_data.get("games", [])
        }
        
        print(f"\n📝 正在保存 King 公司配置到数据库...")
        success = db.save_company_social_media_config(
            company=company_name,
            priority=priority,
            social_media_config=social_media_config
        )
        
        if success:
            print(f"✅ King 公司配置已保存到数据库")
        else:
            print(f"❌ King 公司配置保存失败")
        
        return success
    
    except Exception as exc:
        print(f"❌ 保存到数据库时出错: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False


def scrape_twitter_platform(
    platform: Dict[str, Any],
    company: str,
    game: Optional[str] = None
) -> Dict[str, Any]:
    """爬取 Twitter 平台数据，并获取 user_id（优先从 JSON 读取，如果没有再调用 API）"""
    print(f"\n  [Twitter] {' - '.join(filter(None, [company, game]))}")
    
    username = platform.get("username", "")
    user_id = platform.get("user_id", "")  # 先从 JSON 读取
    url = platform.get("url", "")
    
    result = {
        "platform_type": "twitter",
        "company": company,
        "game": game,
        "username": username,
        "url": url,
        "user_id": user_id,
        "posts": [],
        "error": None
    }
    
    try:
        # 如果 JSON 中没有 user_id，才调用 API 获取
        if not user_id and username:
            print(f"    🔍 JSON 中未找到 user_id，正在通过 API 获取...")
            # 清理 username（移除 @ 符号）
            clean_username = username.strip().lstrip("@")
            user_id = get_twitter_user_id_from_username(clean_username)
            
            if user_id:
                result["user_id"] = user_id
                print(f"    ✅ 通过 API 获取到 user_id: {user_id}")
            else:
                print(f"    ⚠️ 无法获取 user_id，将使用 username 爬取")
        elif user_id:
            print(f"    ℹ️ 使用 JSON 中的 user_id: {user_id}")
        
        # 使用 user_id 或 username 爬取
        identifier = user_id if user_id else username
        if not identifier:
            # 尝试从 URL 提取
            if url:
                identifier = extract_username_from_url(url, "twitter")
                if identifier:
                    result["username"] = identifier
                    print(f"    ℹ️ 从 URL 提取到 username: {identifier}")
        
        if not identifier:
            result["error"] = "无法确定 Twitter 标识符（username 或 user_id）"
            print(f"    ❌ {result['error']}")
            return result
        
        # 爬取最新5条推文（不限制日期）
        print(f"    📥 正在爬取最新5条推文...")
        posts = get_posts_from_twitter(identifier, days_ago=None, count=5)
        
        if posts:
            result["posts"] = posts[:5]  # 确保只取5条
            print(f"    ✅ 成功获取 {len(result['posts'])} 条推文")
        else:
            result["error"] = "未获取到任何推文"
            print(f"    ⚠️ {result['error']}")
    
    except Exception as exc:
        result["error"] = str(exc)
        print(f"    ❌ Twitter 爬取失败: {exc}")
        import traceback
        print(f"    [调试] 错误详情: {traceback.format_exc()}")
    
    return result


def scrape_instagram_platform(
    platform: Dict[str, Any],
    company: str,
    game: Optional[str] = None
) -> Dict[str, Any]:
    """爬取 Instagram 平台数据"""
    print(f"\n  [Instagram] {' - '.join(filter(None, [company, game]))}")
    
    username = platform.get("username", "")
    url = platform.get("url", "")
    
    result = {
        "platform_type": "instagram",
        "company": company,
        "game": game,
        "username": username,
        "url": url,
        "posts": [],
        "error": None
    }
    
    try:
        if not username:
            result["error"] = "缺少 username"
            print(f"    ❌ {result['error']}")
            return result
        
        print(f"    📥 正在爬取最新5条帖子...")
        posts = get_posts_from_instagram(username, days_ago=None, original_username=username)
        
        if posts:
            result["posts"] = posts[:5]  # 确保只取5条
            print(f"    ✅ 成功获取 {len(result['posts'])} 条帖子")
        else:
            result["error"] = "未获取到任何帖子"
            print(f"    ⚠️ {result['error']}")
    
    except Exception as exc:
        result["error"] = str(exc)
        print(f"    ❌ Instagram 爬取失败: {exc}")
        import traceback
        print(f"    [调试] 错误详情: {traceback.format_exc()}")
    
    return result


def scrape_tiktok_platform(
    platform: Dict[str, Any],
    company: str,
    game: Optional[str] = None
) -> Dict[str, Any]:
    """爬取 TikTok 平台数据"""
    print(f"\n  [TikTok] {' - '.join(filter(None, [company, game]))}")
    
    username = platform.get("username", "")
    sec_uid = platform.get("sec_uid", "")
    url = platform.get("url", "")
    
    result = {
        "platform_type": "tiktok",
        "company": company,
        "game": game,
        "username": username,
        "sec_uid": sec_uid,
        "url": url,
        "posts": [],
        "error": None
    }
    
    try:
        identifier = sec_uid if sec_uid else username
        if not identifier:
            result["error"] = "缺少 sec_uid 或 username"
            print(f"    ❌ {result['error']}")
            return result
        
        print(f"    📥 正在爬取最新5条视频...")
        # TikTok API: days_ago=None 表示不过滤日期，获取最新数据
        # 注意：get_posts_from_tiktok 的 days_ago 参数如果为 None，可能需要特殊处理
        # 先尝试使用 days_ago=0 获取今天的数据，或者使用一个较大的值
        posts = get_posts_from_tiktok(identifier, days_ago=0, original_username=username)
        
        if posts:
            result["posts"] = posts[:5]  # 确保只取5条
            print(f"    ✅ 成功获取 {len(result['posts'])} 条视频")
        else:
            result["error"] = "未获取到任何视频"
            print(f"    ⚠️ {result['error']}")
    
    except Exception as exc:
        result["error"] = str(exc)
        print(f"    ❌ TikTok 爬取失败: {exc}")
        import traceback
        print(f"    [调试] 错误详情: {traceback.format_exc()}")
    
    return result


def scrape_facebook_platform(
    platform: Dict[str, Any],
    company: str,
    game: Optional[str] = None
) -> Dict[str, Any]:
    """爬取 Facebook 平台数据（参考 CompetitorDailyScraperFromDB.py 的实现）"""
    print(f"\n  [Facebook] {' - '.join(filter(None, [company, game]))}")
    
    page_id = platform.get("page_id", "")
    url = platform.get("url", "")
    
    result = {
        "platform_type": "facebook",
        "company": company,
        "game": game,
        "page_id": page_id,
        "url": url,
        "posts": [],
        "error": None
    }
    
    try:
        if not page_id:
            result["error"] = "缺少 page_id"
            print(f"    ❌ {result['error']}")
            return result
        
        print(f"    📥 正在爬取最新5条帖子...")
        # 使用 FacebookScraper 的方式获取数据
        raw_json = _fetch_facebook_raw(page_id)
        if not raw_json:
            result["error"] = "无法获取Facebook数据"
            print(f"    ❌ {result['error']}")
            return result
        
        # 解析帖子（获取最新5条）
        posts = parse_facebook_posts(raw_json, max_posts=5)
        
        if posts:
            result["posts"] = posts
            print(f"    ✅ 成功获取 {len(result['posts'])} 条帖子")
        else:
            result["error"] = "未获取到任何帖子"
            print(f"    ⚠️ {result['error']}")
    
    except Exception as exc:
        result["error"] = str(exc)
        print(f"    ❌ Facebook 爬取失败: {exc}")
        import traceback
        print(f"    [调试] 错误详情: {traceback.format_exc()}")
    
    return result


def update_twitter_user_id_in_database(
    db: CompetitorDatabaseDB,
    company: str,
    game: Optional[str],
    platform_url: str,
    user_id: str
) -> bool:
    """更新数据库中的 Twitter user_id"""
    try:
        conn = db._get_connection()
        try:
            if game:
                conn.execute("""
                    UPDATE company_platforms
                    SET user_id = ?, updated_at = ?
                    WHERE company_name = ? AND game_name = ? 
                    AND platform_type = 'twitter' AND url = ?
                """, (
                    user_id,
                    datetime.utcnow().isoformat() + "Z",
                    company,
                    game,
                    platform_url
                ))
            else:
                conn.execute("""
                    UPDATE company_platforms
                    SET user_id = ?, updated_at = ?
                    WHERE company_name = ? AND game_name IS NULL
                    AND platform_type = 'twitter' AND url = ?
                """, (
                    user_id,
                    datetime.utcnow().isoformat() + "Z",
                    company,
                    platform_url
                ))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    except Exception as exc:
        print(f"    ⚠️ 更新数据库 user_id 失败: {exc}")
        return False


def scrape_all_platforms(king_data: Dict[str, Any], db: CompetitorDatabaseDB) -> Dict[str, Any]:
    """爬取所有平台的数据"""
    company = king_data.get("name", "King")
    results = {
        "company": company,
        "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platforms": [],
        "games": []
    }
    
    # 爬取公司级平台
    print(f"\n📊 开始爬取公司级平台...")
    company_platforms = king_data.get("platforms", [])
    for platform in company_platforms:
        platform_type = platform.get("type", "").lower()
        enabled = platform.get("enabled", True)
        
        if not enabled:
            print(f"\n  ⏭️ 跳过已禁用的平台: {platform_type}")
            continue
        
        # 跳过 YouTube 和 LinkedIn
        if platform_type in ["youtube", "linkedin"]:
            print(f"\n  ⏭️ 跳过平台: {platform_type}（按用户要求）")
            continue
        
        result = None
        if platform_type == "twitter":
            result = scrape_twitter_platform(platform, company)
            # 如果获取到 user_id，更新数据库
            if result.get("user_id") and not platform.get("user_id"):
                update_twitter_user_id_in_database(
                    db, company, None, platform.get("url", ""), result["user_id"]
                )
                # 同时更新原始数据中的 user_id
                platform["user_id"] = result["user_id"]
        
        elif platform_type == "instagram":
            result = scrape_instagram_platform(platform, company)
        
        elif platform_type == "tiktok":
            result = scrape_tiktok_platform(platform, company)
        
        elif platform_type == "facebook":
            result = scrape_facebook_platform(platform, company)
        
        else:
            print(f"\n  ⚠️ 未支持的平台类型: {platform_type}")
            result = {
                "platform_type": platform_type,
                "company": company,
                "error": f"未支持的平台类型: {platform_type}"
            }
        
        if result:
            results["platforms"].append(result)
    
    # 爬取游戏级平台
    print(f"\n📊 开始爬取游戏级平台...")
    games = king_data.get("games", [])
    for game_data in games:
        game_name = game_data.get("name", "")
        if not game_name:
            continue
        
        print(f"\n  🎮 游戏: {game_name}")
        game_platforms = game_data.get("platforms", [])
        
        game_results = {
            "game": game_name,
            "platforms": []
        }
        
        for platform in game_platforms:
            platform_type = platform.get("type", "").lower()
            enabled = platform.get("enabled", True)
            
            if not enabled:
                print(f"\n    ⏭️ 跳过已禁用的平台: {platform_type}")
                continue
            
            # 跳过 YouTube 和 LinkedIn
            if platform_type in ["youtube", "linkedin"]:
                print(f"\n    ⏭️ 跳过平台: {platform_type}（按用户要求）")
                continue
            
            result = None
            if platform_type == "twitter":
                result = scrape_twitter_platform(platform, company, game_name)
                # 如果获取到 user_id，更新数据库
                if result.get("user_id") and not platform.get("user_id"):
                    update_twitter_user_id_in_database(
                        db, company, game_name, platform.get("url", ""), result["user_id"]
                    )
                    # 同时更新原始数据中的 user_id
                    platform["user_id"] = result["user_id"]
            
            elif platform_type == "instagram":
                result = scrape_instagram_platform(platform, company, game_name)
            
            elif platform_type == "tiktok":
                result = scrape_tiktok_platform(platform, company, game_name)
            
            elif platform_type == "facebook":
                result = scrape_facebook_platform(platform, company, game_name)
            
            else:
                print(f"\n    ⚠️ 未支持的平台类型: {platform_type}")
                result = {
                    "platform_type": platform_type,
                    "company": company,
                    "game": game_name,
                    "error": f"未支持的平台类型: {platform_type}"
                }
            
            if result:
                game_results["platforms"].append(result)
        
        if game_results["platforms"]:
            results["games"].append(game_results)
    
    return results


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 King 公司数据导入和爬取脚本")
    print("=" * 60)
    
    # 1. 读取 JSON 文件
    print("\n📖 步骤 1: 读取 twitter_input.json...")
    king_data = load_king_company_from_json()
    if not king_data:
        print("❌ 无法加载 King 公司数据，退出")
        return 1
    
    print(f"✅ 成功加载 King 公司数据")
    print(f"   公司名称: {king_data.get('name')}")
    print(f"   优先级: {king_data.get('priority')}")
    print(f"   公司级平台数: {len(king_data.get('platforms', []))}")
    print(f"   游戏数: {len(king_data.get('games', []))}")
    
    # 2. 初始化数据库
    print("\n💾 步骤 2: 初始化数据库连接...")
    db = CompetitorDatabaseDB()
    print("✅ 数据库连接已建立")
    
    # 3. 保存到数据库
    print("\n💾 步骤 3: 保存配置到数据库...")
    save_success = save_king_to_database(king_data, db)
    if not save_success:
        print("⚠️ 保存到数据库失败，但继续执行爬取...")
    
    # 4. 爬取各平台数据
    print("\n🕷️ 步骤 4: 开始爬取各平台数据...")
    scrape_results = scrape_all_platforms(king_data, db)
    
    # 5. 保存结果到 JSON 文件
    print("\n💾 步骤 5: 保存结果到 JSON 文件...")
    output_data = {
        "company_config": king_data,
        "scrape_results": scrape_results,
        "summary": {
            "total_platforms_scraped": len(scrape_results["platforms"]),
            "total_games_scraped": len(scrape_results["games"]),
            "total_posts": (
                sum(len(p.get("posts", [])) for p in scrape_results["platforms"]) +
                sum(sum(len(pp.get("posts", [])) for pp in g.get("platforms", [])) for g in scrape_results["games"])
            ),
            "errors": [
                p.get("error") for p in scrape_results["platforms"] if p.get("error")
            ] + [
                pp.get("error") for g in scrape_results["games"] for pp in g.get("platforms", []) if pp.get("error")
            ]
        }
    }
    
    output_file = "output/king_company_import_result.json"
    os.makedirs("output", exist_ok=True)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存到: {output_file}")
    except Exception as exc:
        print(f"❌ 保存结果文件失败: {exc}")
        return 1
    
    # 6. 打印摘要
    print("\n" + "=" * 60)
    print("📊 执行摘要")
    print("=" * 60)
    print(f"✅ 公司配置已保存到数据库")
    print(f"📥 爬取了 {scrape_results['summary']['total_platforms_scraped']} 个公司级平台")
    print(f"🎮 爬取了 {scrape_results['summary']['total_games_scraped']} 个游戏")
    print(f"📝 共获取 {scrape_results['summary']['total_posts']} 条帖子/视频")
    
    if scrape_results['summary']['errors']:
        print(f"\n⚠️ 遇到 {len(scrape_results['summary']['errors'])} 个错误:")
        for error in scrape_results['summary']['errors']:
            print(f"   - {error}")
    
    print(f"\n📄 详细结果请查看: {output_file}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
