"""
从数据库读取竞品公司YouTube配置，爬取最新的5个Shorts并保存到数据库
支持数据库去重
"""
import json
import os
import re
import sys
from datetime import date, datetime, timezone

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import env_loader  # noqa: F401  # 确保 .env 被加载

from database.competitor_db import CompetitorDatabaseDB
from scrapers.rapidapi import (
    get_youtube_shorts_from_channel,
    get_youtube_channel_id_from_handle_for_shorts,
)


def scrape_youtube_shorts_to_database():
    """从数据库读取配置，爬取YouTube Shorts并保存到数据库"""
    print("=" * 60)
    print("📹 YouTube Shorts 爬取并保存到数据库")
    print("=" * 60)
    print()
    
    # 初始化数据库
    db = CompetitorDatabaseDB()
    
    # 获取所有公司
    companies = db.get_all_companies()
    if not companies:
        print("❌ 数据库中未找到任何公司")
        return 1
    
    print(f"📋 找到 {len(companies)} 个公司")
    print()
    
    total_platforms = 0
    total_new_shorts = 0
    success_count = 0
    fail_count = 0
    
    # 遍历每个公司
    for company in companies:
        print(f"{'=' * 60}")
        print(f"🏢 处理公司: {company}")
        print(f"{'=' * 60}")
        
        # 获取该公司的所有YouTube平台（包括公司级和游戏级）
        # 先获取公司级平台
        company_platforms = db.get_company_platforms(
            company=company,
            platform_type="youtube",
            enabled_only=True
        )
        
        # 获取所有游戏级平台（需要直接查询数据库）
        conn = db._get_connection()
        game_platforms = []
        try:
            cursor = conn.execute("""
                SELECT game_name, platform_type, username, url, user_id, page_id,
                       channel_id, handle, sec_uid, enabled, priority
                FROM company_platforms
                WHERE company_name = ? 
                  AND platform_type = 'youtube'
                  AND game_name IS NOT NULL
                  AND enabled = 1
                ORDER BY game_name, platform_type
            """, (company,))
            
            rows = cursor.fetchall()
            for row in rows:
                platform = {
                    "type": row["platform_type"],
                    "enabled": bool(row["enabled"]),
                    "game": row["game_name"]
                }
                if row["url"]:
                    platform["url"] = row["url"]
                if row["channel_id"]:
                    platform["channel_id"] = row["channel_id"]
                if row["handle"]:
                    platform["handle"] = row["handle"]
                if row["priority"]:
                    platform["priority"] = row["priority"]
                game_platforms.append(platform)
        finally:
            conn.close()
        
        all_platforms = company_platforms + game_platforms
        
        if not all_platforms:
            print(f"  ⚠️ {company} 没有启用的YouTube平台，跳过")
            print()
            continue
        
        print(f"  📋 找到 {len(all_platforms)} 个YouTube平台")
        print()
        
        # 处理每个YouTube平台
        platforms_data = []
        
        for platform in all_platforms:
            platform_type = platform.get("type", "youtube")
            game = platform.get("game")
            url = platform.get("url", "")
            channel_id = platform.get("channel_id", "")
            handle = platform.get("handle", "")
            
            # 构建显示名称
            if game:
                display_name = f"{company} - {game}"
            else:
                display_name = f"{company} 官方账号"
            
            print(f"  📺 处理平台: {display_name}")
            print(f"     URL: {url}")
            print(f"     Channel ID: {channel_id or '未配置'}")
            print(f"     Handle: {handle or '未配置'}")
            
            # 确定标识符（优先使用channel_id）
            identifier = channel_id if channel_id else (handle.lstrip("@") if handle else "")
            
            if not identifier:
                print(f"     ⚠️ 未找到channel_id或handle，跳过")
                fail_count += 1
                continue
            
            # 如果没有channel_id，尝试从handle获取
            if not channel_id and handle:
                print(f"     [调试] 未找到channel_id，尝试从handle获取...")
                resolved_channel_id = get_youtube_channel_id_from_handle_for_shorts(handle.lstrip("@"))
                if resolved_channel_id:
                    channel_id = resolved_channel_id
                    identifier = channel_id
                    print(f"     ✓ 获取到channel_id: {channel_id}")
            
            # 获取历史video_ids用于去重（查询所有历史数据）
            print(f"     🔍 查询历史数据用于去重...")
            historical_video_ids = set()
            
            # 查询该平台的所有历史数据（不限制日期）
            table_name = db._get_table_name(company)
            conn = db._get_connection()
            try:
                # 检查表是否存在
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                
                if cursor.fetchone():
                    # 查询所有历史数据
                    query = f"""
                        SELECT posts_json FROM {table_name}
                        WHERE platform_type = ? AND url = ?
                    """
                    params = [platform_type, url]
                    
                    if game:
                        query += " AND game = ?"
                        params.append(game)
                    else:
                        query += " AND game IS NULL"
                    
                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # 从所有历史posts中提取video_id
                    for row in rows:
                        try:
                            posts = json.loads(row["posts_json"])
                            for post in posts:
                                # 尝试多种可能的字段名
                                video_id = (
                                    post.get("video_id") or 
                                    post.get("videoId") or 
                                    post.get("id") or
                                    ""
                                )
                                if video_id:
                                    historical_video_ids.add(video_id)
                                
                                # 从post_url中提取（用于YouTube Shorts）
                                post_url = post.get("post_url", "")
                                if "/shorts/" in post_url:
                                    match = re.search(r'/shorts/([A-Za-z0-9_-]+)', post_url)
                                    if match:
                                        historical_video_ids.add(match.group(1))
                                elif "/watch?v=" in post_url:
                                    match = re.search(r'/watch\?v=([A-Za-z0-9_-]+)', post_url)
                                    if match:
                                        historical_video_ids.add(match.group(1))
                        except Exception:
                            continue
            finally:
                conn.close()
            
            print(f"     📊 历史数据中有 {len(historical_video_ids)} 个video_id")
            
            # 爬取最新的5个Shorts
            print(f"     🕷️ 爬取最新的5个Shorts...")
            try:
                posts = get_youtube_shorts_from_channel(
                    identifier,
                    count=5,
                    historical_video_ids=historical_video_ids
                )
                
                if posts:
                    print(f"     ✓ 成功获取 {len(posts)} 条新Shorts")
                    total_new_shorts += len(posts)
                    
                    # 准备保存到数据库的数据
                    platform_data = {
                        "platform_type": platform_type,
                        "game": game,
                        "url": url,
                        "channel_id": channel_id,
                        "handle": handle,
                        "posts": posts,
                        "posts_count": len(posts),
                        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    }
                    platforms_data.append(platform_data)
                    success_count += 1
                else:
                    print(f"     ⚠️ 未获取到新Shorts（可能都是历史数据）")
                    # 即使没有新数据，也保存空数据（用于记录查询时间）
                    platform_data = {
                        "platform_type": platform_type,
                        "game": game,
                        "url": url,
                        "channel_id": channel_id,
                        "handle": handle,
                        "posts": [],
                        "posts_count": 0,
                        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    }
                    platforms_data.append(platform_data)
                
            except Exception as exc:
                print(f"     ❌ 爬取失败: {exc}")
                import traceback
                print(f"     [调试] 错误详情:")
                print(traceback.format_exc())
                fail_count += 1
                continue
            
            print()
        
        # 保存到数据库
        if platforms_data:
            print(f"  💾 保存数据到数据库...")
            save_success = db.save_raw_data(
                company=company,
                platforms_data=platforms_data,
                fetch_date=date.today()
            )
            
            if save_success:
                print(f"  ✓ {company} 数据保存成功")
                total_platforms += len(platforms_data)
            else:
                print(f"  ❌ {company} 数据保存失败")
                fail_count += 1
        else:
            print(f"  ⚠️ {company} 没有可保存的数据")
            fail_count += 1
        
        print()
    
    # 总结
    print("=" * 60)
    print("📊 爬取总结")
    print("=" * 60)
    print(f"  处理公司数: {len(companies)}")
    print(f"  处理平台数: {total_platforms}")
    print(f"  新Shorts数: {total_new_shorts}")
    print(f"  成功: {success_count} 个平台")
    if fail_count > 0:
        print(f"  失败: {fail_count} 个平台")
    print("=" * 60)
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    exit_code = scrape_youtube_shorts_to_database()
    sys.exit(exit_code)
