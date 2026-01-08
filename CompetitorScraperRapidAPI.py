"""
使用 RapidAPI 抓取竞品社媒账号的帖子数据
支持 Instagram, TikTok, YouTube, Twitter/X 四个平台
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

import requests
import yaml

import env_loader  # noqa: F401  # 确保 .env 中的 RAPIDAPI_KEY 被加载


# RapidAPI 配置
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOSTS = {
    "instagram": "instagram120.p.rapidapi.com",
    "tiktok": "tiktok-api23.p.rapidapi.com",
    "youtube": "youtube138.p.rapidapi.com",
    "twitter": "twitter241.p.rapidapi.com",
}


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = os.environ.get("CONFIG_PATH", "/app/config/config.yaml")
    if not os.path.exists(config_path):
        alt_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        if os.path.exists(alt_path):
            config_path = alt_path
        else:
            print(f"⚠️ 未找到配置文件: {config_path}")
            return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        print(f"⚠️ 读取配置失败: {exc}")
        return {}


def get_competitor_accounts(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从配置文件读取竞品账号信息"""
    competitors = cfg.get("competitor_monitor", {}).get("competitors") or cfg.get("competitors") or []
    
    if not competitors:
        section = cfg.get("competitor_monitor") or {}
        if not section.get("enable", True):
            return []
        accounts = section.get("social_accounts") or []
        norm_accounts = []
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            name = (acc.get("name") or "").strip()
            url = (acc.get("url") or "").strip()
            if not name or not url:
                continue
            platform = (acc.get("platform") or "unknown").strip()
            norm_accounts.append({
                "company": name,
                "game": None,
                "platform_type": platform,
                "url": url,
                "priority": "medium"
            })
        return norm_accounts
    
    norm_accounts = []
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
            url = (platform.get("url") or "").strip()
            if not url:
                continue
            platform_type = (platform.get("type") or "unknown").strip()
            norm_accounts.append({
                "company": company_name,
                "game": None,
                "platform_type": platform_type,
                "url": url,
                "priority": company_priority
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
                url = (platform.get("url") or "").strip()
                if not url:
                    continue
                platform_type = (platform.get("type") or "unknown").strip()
                norm_accounts.append({
                    "company": company_name,
                    "game": game_name,
                    "platform_type": platform_type,
                    "url": url,
                    "priority": game_priority
                })
    
    return norm_accounts


def extract_username_from_url(url: str, platform: str) -> Optional[str]:
    """从URL中提取用户名/ID"""
    platform_lower = platform.lower()
    
    if "instagram" in platform_lower:
        # https://www.instagram.com/username/ or https://instagram.com/username/
        match = re.search(r'instagram\.com/([^/?]+)', url)
        return match.group(1) if match else None
    
    elif "tiktok" in platform_lower:
        # https://www.tiktok.com/@username
        match = re.search(r'tiktok\.com/@([^/?]+)', url)
        return match.group(1) if match else None
    
    elif "youtube" in platform_lower:
        # https://www.youtube.com/@username or https://www.youtube.com/c/channel or https://www.youtube.com/channel/UCxxxxx
        match = re.search(r'youtube\.com/(?:@|channel/|c/)([^/?]+)', url)
        return match.group(1) if match else None
    
    elif "twitter" in platform_lower or "x.com" in url.lower():
        # https://x.com/username or https://twitter.com/username
        match = re.search(r'(?:twitter\.com|x\.com)/([^/?]+)', url)
        return match.group(1) if match else None
    
    return None


def get_posts_from_instagram(username: str, days_ago: int = 1) -> List[Dict[str, Any]]:
    """使用 RapidAPI 获取 Instagram 帖子"""
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return []
    
    host = RAPIDAPI_HOSTS["instagram"]
    url = f"https://{host}/api/instagram/posts"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host,
        'Content-Type': 'application/json'
    }
    
    payload = {"username": username, "maxId": ""}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        posts = []
        result = data.get("result", {})
        edges = result.get("edges", [])
        
        # 计算昨天的时间戳范围
        yesterday = datetime.now() - timedelta(days=days_ago)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0).timestamp()
        yesterday_end = yesterday.replace(hour=23, minute=59, second=59).timestamp()
        
        for edge in edges:
            node = edge.get("node", {})
            taken_at = node.get("taken_at_timestamp", 0)
            
            # 只取昨天的帖子
            if yesterday_start <= taken_at <= yesterday_end:
                caption_node = node.get("caption", {})
                caption_text = caption_node.get("text", "") if caption_node else ""
                
                # 提取图片URL
                media_urls = []
                image_versions = node.get("image_versions2", {})
                candidates = image_versions.get("candidates", [])
                if candidates:
                    media_urls.append(candidates[0].get("url", ""))
                
                # 提取视频URL
                video_versions = node.get("video_versions", [])
                if video_versions:
                    media_urls.append(video_versions[0].get("url", ""))
                
                # 互动数据
                engagement = {
                    "like": node.get("like_count", 0),
                    "comment": node.get("comment_count", 0),
                }
                
                post = {
                    "text": caption_text,
                    "published_at": datetime.fromtimestamp(taken_at).isoformat(),
                    "published_at_display": datetime.fromtimestamp(taken_at).strftime("%Y-%m-%d %H:%M:%S"),
                    "post_url": f"https://www.instagram.com/p/{node.get('code', '')}/",
                    "media_urls": media_urls,
                    "engagement": engagement,
                }
                posts.append(post)
        
        return posts
    
    except Exception as exc:
        print(f"  ❌ Instagram API 调用失败: {exc}")
        return []


def get_tiktok_secuid_from_username(username: str) -> Optional[str]:
    """
    从 username (uniqueId) 获取 TikTok secUid
    使用 RapidAPI: /api/user/info?uniqueId=xxx
    """
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return None
    
    host = RAPIDAPI_HOSTS["tiktok"]
    url = f"https://{host}/api/user/info"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    params = {"uniqueId": username}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 从响应中提取 secUid
        # 响应结构: userInfo.user.secUid
        user_info = data.get("userInfo", {})
        user = user_info.get("user", {})
        sec_uid = user.get("secUid")
        
        if sec_uid:
            print(f"  ✓ 获取到 secUid: {sec_uid[:30]}... (username: {username})")
            return sec_uid
        else:
            print(f"  ⚠️ 响应中未找到 secUid，响应结构: {list(data.keys())}")
            if "userInfo" in data:
                print(f"  [调试] userInfo keys: {list(data['userInfo'].keys())}")
                if "user" in data["userInfo"]:
                    print(f"  [调试] user keys: {list(data['userInfo']['user'].keys())}")
    except requests.exceptions.HTTPError as e:
        print(f"  ❌ HTTP 错误: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"  [调试] 错误响应: {error_data}")
            except:
                print(f"  [调试] 错误响应文本: {e.response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 获取 secUid 失败: {e}")
    
    return None


def get_posts_from_tiktok(username_or_secuid: str, days_ago: int = 1, original_username: str = None) -> List[Dict[str, Any]]:
    """
    使用 RapidAPI 获取 TikTok 视频
    
    Args:
        username_or_secuid: username 或 secUid
        days_ago: 日期过滤（None 表示不过滤）
        original_username: 原始 username（用于生成 post_url），如果为 None 则从 API 响应中提取
    """
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return []
    
    host = RAPIDAPI_HOSTS["tiktok"]
    url = f"https://{host}/api/user/posts"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    # 判断传入的是 secUid（长字符串，通常以 MS4w 开头）还是 username
    # secUid 通常很长（50+ 字符），username 通常较短
    if len(username_or_secuid) > 30 and username_or_secuid.startswith("MS4w"):
        # 看起来是 secUid，直接使用
        sec_uid = username_or_secuid
        username_for_url = original_username or username_or_secuid  # 如果没有提供原始 username，使用传入值
        print(f"  [调试] 检测到 secUid，直接使用: {sec_uid[:30]}...")
    else:
        # 是 username，需要获取 secUid
        username_for_url = username_or_secuid
        print(f"  [调试] 检测到 username，正在获取 secUid: {username_or_secuid}")
        sec_uid = get_tiktok_secuid_from_username(username_or_secuid)
        if not sec_uid:
            print(f"  ⚠️ 无法获取 secUid，跳过")
            return []
    
    params = {
        "secUid": sec_uid,  # 使用 secUid 参数
        "count": 35,
        "cursor": 0
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 调试：打印 API 响应结构
        print(f"  [调试] TikTok API 响应状态码: {response.status_code}")
        print(f"  [调试] 响应 keys: {list(data.keys())}")
        if "data" in data:
            data_obj = data.get("data", {})
            print(f"  [调试] data keys: {list(data_obj.keys())}")
            item_list = data_obj.get("itemList", [])
            print(f"  [调试] itemList 长度: {len(item_list)}")
        else:
            print(f"  [调试] 响应数据（前500字符）: {str(data)[:500]}")
            item_list = []
        
        posts = []
        
        # 日期过滤（可选）：如果 days_ago 为 None，则不做日期过滤
        day_start_ts = None
        day_end_ts = None
        if days_ago is not None:
            # 计算指定天数前的时间戳范围（TikTok使用秒级时间戳）
            target_day = datetime.now() - timedelta(days=int(days_ago))
            day_start_ts = target_day.replace(hour=0, minute=0, second=0).timestamp()
            day_end_ts = target_day.replace(hour=23, minute=59, second=59).timestamp()
        
        for item in item_list:
            create_time = item.get("createTime", 0)
            
            # 日期过滤（如果启用）
            if day_start_ts is not None and day_end_ts is not None:
                if not (day_start_ts <= create_time <= day_end_ts):
                    continue
            
            # 提取内容（无论是否启用日期过滤都要提取）
            contents = item.get("contents", [])
            desc = contents[0].get("desc", "") if contents else item.get("desc", "")
            
            # 提取视频URL
            media_urls = []
            video_info = item.get("video", {})
            if video_info:
                play_addr = video_info.get("bitrateInfo", [{}])[0].get("PlayAddr", {})
                url_list = play_addr.get("UrlList", [])
                if url_list:
                    media_urls.append(url_list[0])
            
            # 互动数据
            stats = item.get("stats", {})
            engagement = {
                "like": stats.get("diggCount", 0),
                "comment": stats.get("commentCount", 0),
                "share": stats.get("shareCount", 0),
                "view": stats.get("playCount", 0),
            }
            
            post = {
                "text": desc,
                "published_at": datetime.fromtimestamp(create_time).isoformat(),
                "published_at_display": datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S"),
                "post_url": f"https://www.tiktok.com/@{username_for_url}/video/{item.get('id', '')}",
                "media_urls": media_urls,
                "engagement": engagement,
            }
            posts.append(post)
        
        return posts
    
    except Exception as exc:
        print(f"  ❌ TikTok API 调用失败: {exc}")
        return []


def get_youtube_channel_id_from_handle(handle: str, debug: bool = False) -> Optional[str]:
    """通过 handle/@username 获取 YouTube channel ID"""
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return None
    
    host = RAPIDAPI_HOSTS["youtube"]
    
    # 去掉 @ 符号
    handle_clean = handle.lstrip("@")
    
    # 尝试使用 channel/details 或其他可能的端点
    # 注意：这取决于 RapidAPI YouTube API 是否支持从 handle 获取 channel ID
    # 如果 API 不支持，可能需要先获取频道详情
    
    # 方法1：直接尝试用 handle 调用，看 API 是否支持
    url = f"https://{host}/channel/details/"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    params = {"handle": handle_clean}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if debug:
                print(f"  [调试] channel/details 响应: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            # 尝试从响应中提取 channel ID
            # 这里需要根据实际 API 响应格式调整
            channel_id = data.get("channelId") or data.get("id") or data.get("channel", {}).get("id")
            if channel_id:
                print(f"  ✓ 获取到 channel ID: {channel_id} (handle: {handle_clean})")
                return channel_id
    except Exception as e:
        if debug:
            print(f"  [调试] channel/details 调用失败: {e}")
    
    # 方法2：如果上面失败，尝试直接用 handle 作为 id（某些 API 可能支持）
    # 如果 API 不支持 handle，返回 None，让调用者直接使用 handle 试试
    print(f"  ⚠️ 无法通过 API 获取 channel ID，将尝试直接使用 handle: {handle_clean}")
    return None


def get_posts_from_youtube(channel_id_or_handle: str, days_ago: int = 1) -> List[Dict[str, Any]]:
    """使用 RapidAPI 获取 YouTube 视频"""
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return []
    
    host = RAPIDAPI_HOSTS["youtube"]
    url = f"https://{host}/channel/videos/"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    # 判断是 channel ID (UC开头，通常是24个字符) 还是 handle
    channel_id = channel_id_or_handle.lstrip("@")
    
    # Channel ID 通常是 UC 开头，24个字符
    is_channel_id = channel_id.startswith("UC") and len(channel_id) == 24
    
    if not is_channel_id:
        # 如果不是 channel ID，尝试获取
        print(f"  [YouTube] 检测到 handle/custom URL: {channel_id}")
        print(f"  [YouTube] 尝试获取对应的 channel ID...")
        resolved_id = get_youtube_channel_id_from_handle(channel_id)
        if resolved_id:
            channel_id = resolved_id
        else:
            print(f"  [YouTube] 无法获取 channel ID，直接使用 handle 尝试...")
            # 继续使用 handle，某些 API 可能支持
    
    params = {
        "id": channel_id,
        "filter": "videos_latest",
        "hl": "en",
        "gl": "US"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        posts = []
        contents = data.get("contents", [])
        
        # 计算昨天
        yesterday = datetime.now() - timedelta(days=days_ago)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0)
        yesterday_end = yesterday.replace(hour=23, minute=59, second=59)
        
        for content in contents:
            published_time_text = content.get("publishedTimeText", "")
            
            # 解析时间文本（如 "13 minutes ago", "3 hours ago"）
            # 简化处理：如果包含 "hour" 或 "minute" 且数字<=24，认为是昨天
            is_yesterday = False
            if "hour" in published_time_text.lower():
                hours_match = re.search(r'(\d+)\s*hour', published_time_text)
                if hours_match:
                    hours = int(hours_match.group(1))
                    if hours <= 24:
                        is_yesterday = True
            elif "minute" in published_time_text.lower():
                is_yesterday = True  # 几分钟前肯定是最近的
            
            # 更精确：尝试从 publishedTimeText 解析完整时间
            # 这里简化处理，实际应该解析完整时间
            
            if is_yesterday or True:  # 暂时都包含，实际应该精确判断
                title = content.get("title", "")
                video_id = content.get("videoId", "")
                
                # 提取缩略图
                media_urls = []
                thumbnails = content.get("thumbnails", [])
                if thumbnails:
                    media_urls.append(thumbnails[-1].get("url", ""))
                
                # 互动数据
                stats = content.get("stats", {})
                engagement = {
                    "view": stats.get("views", 0),
                }
                
                post = {
                    "text": title,
                    "published_at_display": published_time_text,
                    "post_url": f"https://www.youtube.com/watch?v={video_id}",
                    "media_urls": media_urls,
                    "engagement": engagement,
                }
                posts.append(post)
        
        return posts
    
    except Exception as exc:
        print(f"  ❌ YouTube API 调用失败: {exc}")
        return []


def get_twitter_user_id_from_username(username: str, debug: bool = False) -> Optional[str]:
    """通过 username 获取 Twitter user ID"""
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return None
    
    host = RAPIDAPI_HOSTS["twitter"]
    url = f"https://{host}/user"
    
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    params = {"username": username}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 调试：打印响应
        if debug:
            print(f"\n  [调试] API 响应状态码: {response.status_code}")
            print(f"  [调试] 响应数据: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
        
        # 从响应中提取 rest_id
        # API 响应结构: result.data.user.result.rest_id
        user_result = data.get("result", {}).get("data", {}).get("user", {}).get("result", {})
        user_id = user_result.get("rest_id", "")
        
        if user_id:
            print(f"  ✓ 获取到 user ID: {user_id} (username: {username})")
            return user_id
        else:
            print(f"  ⚠️ 未能从响应中提取 user ID")
            if debug:
                print(f"  [调试] user_result keys: {list(user_result.keys())}")
            return None
    
    except requests.exceptions.HTTPError as exc:
        print(f"  ❌ HTTP 错误: {exc}")
        if debug and hasattr(exc, 'response') and exc.response is not None:
            print(f"  [调试] 错误响应: {exc.response.text[:500]}")
        return None
    except Exception as exc:
        print(f"  ❌ 获取 Twitter user ID 失败: {exc}")
        return None


def _parse_twitter_created_at(created_at_str: str) -> Optional[datetime]:
    """
    解析 Twitter created_at 格式：\"Tue Jun 06 19:31:02 +0000 2023\"
    返回带时区的 datetime（通常是 UTC）。
    """
    if not created_at_str:
        return None
    try:
        return datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return None


def _unwrap_tweet_result(tweet_result: Any) -> Optional[Dict[str, Any]]:
    """
    twitter241 的 tweet_results.result 有时是 Tweet，也可能是 TweetWithVisibilityResults 等包装类型。
    返回最终的 Tweet dict（__typename == 'Tweet'），否则返回 None。
    """
    if not isinstance(tweet_result, dict):
        return None
    cur = tweet_result
    # 最多解包 3 层，避免死循环
    for _ in range(3):
        t = cur.get("__typename")
        if t == "Tweet":
            return cur
        if t == "TweetWithVisibilityResults":
            # 常见结构：{"tweet": {"result": {...}}}
            cur = (cur.get("tweet") or {}).get("result") or {}
            continue
        # 其他类型暂不支持
        return None
    return None


def _tweet_author_screen_name(tweet: Dict[str, Any]) -> str:
    """
    从 tweet.core.user_results.result.legacy.screen_name 提取作者 handle
    """
    try:
        return (
            tweet.get("core", {})
            .get("user_results", {})
            .get("result", {})
            .get("legacy", {})
            .get("screen_name", "")
        ) or ""
    except Exception:
        return ""


def _iter_tweet_results(obj: Any) -> List[Dict[str, Any]]:
    """
    递归遍历 dict/list，收集所有 tweet_results.result（原始、未解包）。
    用于兼容 TimelineTimelineItem / TimelineTimelineModule 等多种结构。
    """
    out: List[Dict[str, Any]] = []
    if isinstance(obj, dict):
        if "tweet_results" in obj and isinstance(obj["tweet_results"], dict):
            res = obj["tweet_results"].get("result")
            if isinstance(res, dict):
                out.append(res)
        for v in obj.values():
            out.extend(_iter_tweet_results(v))
    elif isinstance(obj, list):
        for it in obj:
            out.extend(_iter_tweet_results(it))
    return out


def _find_bottom_cursor(obj: Any) -> Optional[str]:
    """
    在 instruction/entry 结构中查找下一页的 bottom cursor（cursorType == 'Bottom'）。
    """
    if isinstance(obj, dict):
        # 形式一：{"cursorType": "Bottom", "value": "...."}
        if (obj.get("cursorType") == "Bottom") and isinstance(obj.get("value"), str):
            return obj["value"]
        # 形式二：{"content":{"operation":{"cursor":{"cursorType":"Bottom","value":"..."}}}}
        cur = obj.get("cursor")
        if isinstance(cur, dict) and cur.get("cursorType") == "Bottom" and isinstance(cur.get("value"), str):
            return cur["value"]
        for v in obj.values():
            found = _find_bottom_cursor(v)
            if found:
                return found
    elif isinstance(obj, list):
        for it in obj:
            found = _find_bottom_cursor(it)
            if found:
                return found
    return None


def get_posts_from_twitter(
    username_or_id: str,
    days_ago: int | None = None,
    count: int = 20,
) -> List[Dict[str, Any]]:
    """
    使用 RapidAPI 获取 Twitter/X 推文
    - days_ago=None: 不做日期过滤，返回最新 count 条（解析到多少返回多少）
    - days_ago=int: 仅返回该天(相对今天)的推文（按 UTC 日历日）
    """
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return []
    
    host = RAPIDAPI_HOSTS["twitter"]
    
    # 判断传入的是 user ID 还是 username
    user_id = username_or_id
    username_for_url: str | None = None
    if not user_id.isdigit():
        username_for_url = username_or_id.strip().lstrip("@")
        # 如果是 username，先获取 user ID
        print(f"  [Twitter] 检测到 username，正在获取 user ID...")
        user_id = get_twitter_user_id_from_username(username_for_url)
        if not user_id:
            print("  ❌ 无法获取 user ID，跳过")
            return []
    
    url = f"https://{host}/user-tweets"
    headers = {
        'x-rapidapi-key': RAPIDAPI_KEY,
        'x-rapidapi-host': host
    }
    
    params = {
        "user": user_id,
        "count": int(count),
    }
    
    try:
        posts: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        target_author = (username_for_url or "").strip().lstrip("@").lower() if username_for_url else None

        # 如果需要日期过滤：按 UTC 的日历日过滤
        day_start_utc: datetime | None = None
        day_end_utc: datetime | None = None
        if days_ago is not None:
            target_day = datetime.now(timezone.utc) - timedelta(days=int(days_ago))
            day_start_utc = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end_utc = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)

        next_cursor: Optional[str] = None
        page = 0

        while True:
            page += 1
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", {})
            timeline = result.get("timeline", {})
            instructions = timeline.get("instructions", [])

            for instruction in instructions:
                # 收集推文
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        tweet_results_raw = _iter_tweet_results(entry)
                        for raw in tweet_results_raw:
                            tweet = _unwrap_tweet_result(raw)
                            if not tweet:
                                continue
                            tweet_id = tweet.get("rest_id", "")
                            if not tweet_id or tweet_id in seen_ids:
                                continue

                            author = _tweet_author_screen_name(tweet).lower()
                            if target_author and author and author != target_author:
                                continue

                            legacy = tweet.get("legacy", {}) or {}
                            created_at = _parse_twitter_created_at(legacy.get("created_at", ""))
                            if created_at is None:
                                continue
                            created_at_utc = created_at.astimezone(timezone.utc)

                            if day_start_utc and day_end_utc:
                                if not (day_start_utc <= created_at_utc <= day_end_utc):
                                    continue

                            full_text = (legacy.get("full_text") or "").strip()
                            engagement = {
                                "like": legacy.get("favorite_count", 0),
                                "retweet": legacy.get("retweet_count", 0),
                                "reply": legacy.get("reply_count", 0),
                                "quote": legacy.get("quote_count", 0),
                                "bookmark": legacy.get("bookmark_count", 0),
                            }
                            views = (tweet.get("views") or {}).get("count")
                            if views is not None:
                                engagement["view"] = views

                            handle = username_for_url or (author or username_or_id)
                            post_url = f"https://x.com/{handle}/status/{tweet_id}"

                            posts.append(
                                {
                                    "text": full_text,
                                    "published_at": created_at_utc.isoformat(),
                                    "published_at_display": created_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                    "post_url": post_url,
                                    "engagement": engagement,
                                }
                            )
                            seen_ids.add(tweet_id)

                # 查找下一页游标
                if next_cursor is None:
                    cur = _find_bottom_cursor(instruction)
                    if cur:
                        next_cursor = cur

            # 是否满足数量
            if len(posts) >= int(count):
                break
            # 没有游标或翻页上限，退出
            if not next_cursor or page >= 3:
                break
            # 准备下一页
            params = dict(params)
            params["cursor"] = next_cursor
            next_cursor = None

        posts.sort(key=lambda p: p.get("published_at", ""), reverse=True)
        return posts[: int(count)]
    
    except Exception as exc:
        print(f"  ❌ Twitter API 调用失败: {exc}")
        return []


def scrape_posts_with_rapidapi(account: Dict[str, Any], days_ago: int = 1) -> List[Dict[str, Any]]:
    """根据平台类型调用对应的 API"""
    platform_type = account.get("platform_type", "").lower()
    url = account.get("url", "")
    
    identifier = extract_username_from_url(url, platform_type)
    if not identifier:
        print(f"  ⚠️ 无法从 URL 提取标识符: {url}")
        return []
    
    print(f"  [RapidAPI] 平台: {platform_type}, 标识符: {identifier}")
    
    if "instagram" in platform_type:
        return get_posts_from_instagram(identifier, days_ago)
    elif "tiktok" in platform_type:
        return get_posts_from_tiktok(identifier, days_ago)
    elif "youtube" in platform_type:
        return get_posts_from_youtube(identifier, days_ago)
    elif "twitter" in platform_type or "x.com" in url.lower():
        return get_posts_from_twitter(identifier, days_ago)
    else:
        print(f"  ⚠️ 不支持的平台类型: {platform_type}")
        return []


def scrape_competitor_social_with_rapidapi() -> None:
    """主函数：使用 RapidAPI 抓取竞品社媒帖子"""
    if not RAPIDAPI_KEY:
        print("❌ 未配置 RAPIDAPI_KEY，请在 .env 文件中设置")
        return
    
    cfg = load_config()
    accounts = get_competitor_accounts(cfg)
    if not accounts:
        print("⚠️ 未找到竞品账号配置")
        return
    
    print(f"[*] 发现 {len(accounts)} 个竞品平台需要抓取")
    
    items = []
    for acc in accounts:
        company = acc["company"]
        game = acc.get("game")
        platform_type = acc["platform_type"]
        url = acc["url"]
        priority = acc.get("priority", "medium")
        
        display_name = f"{company} - {game}" if game else company
        print(f"\n[*] 正在抓取：{display_name} - {platform_type} ({url}) [优先级: {priority}]")
        
        # 获取昨天的帖子（days_ago=1 表示昨天）
        posts = scrape_posts_with_rapidapi(acc, days_ago=1)
        print(f"  ✓ 解析到 {len(posts)} 条昨天的帖子")
        
        item = {
            "company": company,
            "game": game,
            "platform_type": platform_type,
            "url": url,
            "priority": priority,
            "posts": posts,
            "posts_count": len(posts),
        }
        items.append(item)
    
    if not items:
        print("⚠️ 未成功抓取到任何竞品社媒内容。")
        return
    
    # 保存结果
    output_dir = "/app/output"
    if not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
    
    out_path = os.path.join(output_dir, "competitor_social_raw.json")
    payload = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "items": items,
    }
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 竞品社媒原始数据已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存结果失败: {exc}")


if __name__ == "__main__":
    scrape_competitor_social_with_rapidapi()
