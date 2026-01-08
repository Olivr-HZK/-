"""
测试 RapidAPI 爬虫功能
运行此文件来验证各个平台的 API 调用是否正常
"""
import os
import json
from datetime import datetime, timedelta

import env_loader  # noqa: F401
from CompetitorScraperRapidAPI import (
    RAPIDAPI_KEY,
    extract_username_from_url,
    get_posts_from_instagram,
    get_posts_from_tiktok,
    get_posts_from_youtube,
    get_posts_from_twitter,
    get_twitter_user_id_from_username,
    get_youtube_channel_id_from_handle,
)


def test_username_extraction():
    """测试从 URL 提取用户名"""
    print("=" * 60)
    print("测试 1: URL 用户名提取")
    print("=" * 60)
    
    test_cases = [
        ("https://www.instagram.com/voodoo.io/", "instagram"),
        ("https://www.tiktok.com/@gamemobcontrol", "tiktok"),
        ("https://www.youtube.com/@Paper.io2", "youtube"),
        ("https://x.com/voodooplatform", "twitter"),
        ("https://twitter.com/dreamgames", "twitter"),
    ]
    
    for url, platform in test_cases:
        username = extract_username_from_url(url, platform)
        print(f"  {platform:12} | {url}")
        print(f"  {'':12} | -> {username}")
        print()
    
    print()


def test_instagram_api():
    """测试 Instagram API"""
    print("=" * 60)
    print("测试 2: Instagram API")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    # 测试账号（可以替换为实际要测试的账号）
    test_username = "voodoo.io"  # 替换为你想测试的 Instagram 用户名
    
    print(f"  正在测试账号: {test_username}")
    posts = get_posts_from_instagram(test_username, days_ago=1)
    
    print(f"  ✓ 获取到 {len(posts)} 条昨天的帖子")
    if posts:
        print("\n  示例帖子:")
        for i, post in enumerate(posts[:3], 1):  # 只显示前3条
            print(f"\n  帖子 {i}:")
            print(f"    文本: {post.get('text', '')[:100]}...")
            print(f"    发布时间: {post.get('published_at_display', '')}")
            print(f"    链接: {post.get('post_url', '')}")
            print(f"    互动: {post.get('engagement', {})}")
    print()


def test_tiktok_api():
    """测试 TikTok API"""
    print("=" * 60)
    print("测试 3: TikTok API")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    # 测试账号
    test_username = "gamemobcontrol"  # 替换为你想测试的 TikTok 用户名
    
    print(f"  正在测试账号: {test_username}")
    posts = get_posts_from_tiktok(test_username, days_ago=1)
    
    print(f"  ✓ 获取到 {len(posts)} 条昨天的帖子")
    if posts:
        print("\n  示例帖子:")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n  帖子 {i}:")
            print(f"    文本: {post.get('text', '')[:100]}...")
            print(f"    发布时间: {post.get('published_at_display', '')}")
            print(f"    链接: {post.get('post_url', '')}")
            print(f"    互动: {post.get('engagement', {})}")
    print()


def test_youtube_channel_id_conversion():
    """测试 YouTube handle 转 channel ID"""
    print("=" * 60)
    print("测试 4a: YouTube Handle -> Channel ID 转换")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    test_handles = ["@Paper.io2", "Paper.io2", "UCJ5v_MCY6GNUBTO8-D3XoAg"]  # 最后一个已经是 channel ID
    
    for handle in test_handles:
        print(f"\n  测试 handle: {handle}")
        if handle.startswith("UC") and len(handle) == 24:
            print(f"  ✓ 这已经是 channel ID，无需转换")
        else:
            channel_id = get_youtube_channel_id_from_handle(handle, debug=(handle == test_handles[0]))
            if channel_id:
                print(f"  ✓ Channel ID: {channel_id}")
            else:
                print(f"  ⚠️ 无法获取 channel ID，API 可能需要直接使用 handle")
    
    print()


def test_youtube_api():
    """测试 YouTube API"""
    print("=" * 60)
    print("测试 4b: YouTube API (获取视频)")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    # 测试 channel ID 或 handle
    # 方式1: 使用 handle
    test_channel = "@Paper.io2"  # 替换为你想测试的 YouTube handle
    # 方式2: 直接使用 channel ID
    # test_channel = "UCJ5v_MCY6GNUBTO8-D3XoAg"  # 替换为你想测试的 channel ID
    
    print(f"  正在测试频道: {test_channel}")
    print("  ✓ 支持使用 handle (@username) 或 channel ID (UC开头)")
    posts = get_posts_from_youtube(test_channel, days_ago=1)
    
    print(f"  ✓ 获取到 {len(posts)} 条最近的视频")
    if posts:
        print("\n  示例视频:")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n  视频 {i}:")
            print(f"    标题: {post.get('text', '')[:100]}...")
            print(f"    发布时间: {post.get('published_at_display', '')}")
            print(f"    链接: {post.get('post_url', '')}")
            print(f"    观看数: {post.get('engagement', {}).get('view', 0)}")
    print()


def test_twitter_user_id_conversion():
    """测试 Twitter username 转 user ID"""
    print("=" * 60)
    print("测试 5a: Twitter Username -> User ID 转换")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    # 注意：Twitter username 是大小写不敏感的，但要去掉 @ 符号
    test_usernames = ['MrBeast', 'voodooplatform', 'dreamgames']
    
    for i, username in enumerate(test_usernames):
        print(f"\n  测试 username: {username}")
        # 第一个测试启用调试模式
        debug = (i == 0)
        user_id = get_twitter_user_id_from_username(username, debug=debug)
        if user_id:
            print(f"  ✓ User ID: {user_id}")
        else:
            print(f"  ✗ 获取失败")
    
    print()


def test_twitter_api():
    """测试 Twitter API"""
    print("=" * 60)
    print("测试 5b: Twitter API (获取推文)")
    print("=" * 60)
    
    if not RAPIDAPI_KEY:
        print("  ❌ 未配置 RAPIDAPI_KEY")
        return
    
    # 现在可以直接使用 username，会自动转换为 user ID
    test_username = "VoodooPlatform"  # 可以直接使用 username
    
    print(f"  正在测试账号: {test_username}")
    print("  ✓ 现在支持直接使用 username，会自动转换为 user ID")
    
    posts = get_posts_from_twitter(test_username, days_ago=1)
    
    print(f"  ✓ 获取到 {len(posts)} 条昨天的推文")
    if posts:
        print("\n  示例推文:")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n  推文 {i}:")
            print(f"    文本: {post.get('text', '')[:100]}...")
            print(f"    发布时间: {post.get('published_at_display', '')}")
            print(f"    链接: {post.get('post_url', '')}")
            print(f"    互动: {post.get('engagement', {})}")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("RapidAPI 爬虫功能测试")
    print("=" * 60)
    print()
    
    if not RAPIDAPI_KEY:
        print("❌ 错误：未配置 RAPIDAPI_KEY")
        print("\n请在 .env 文件中添加:")
        print("  RAPIDAPI_KEY=your_rapidapi_key_here")
        print("\n或者设置环境变量:")
        print("  export RAPIDAPI_KEY=your_rapidapi_key_here")
        return
    
    print(f"✓ RapidAPI Key 已配置（前10个字符: {RAPIDAPI_KEY[:10]}...）")
    print()
    
    # 运行测试
    test_username_extraction()
    
    # 取消注释下面的行来测试各个平台
    #test_instagram_api()
    #test_tiktok_api()
    test_youtube_channel_id_conversion()
    test_youtube_api()
    #test_twitter_user_id_conversion()
    #test_twitter_api()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n提示：")
    print("1. 如果某个平台测试失败，检查 RAPIDAPI_KEY 是否正确")
    print("2. 确保 RapidAPI 订阅了对应的 API 服务")
    print("3. 检查账号标识符是否正确（Instagram username, TikTok username, YouTube channel ID, Twitter username）")
    print("4. Twitter 现在支持直接使用 username，会自动转换为 user ID")


if __name__ == "__main__":
    main()
