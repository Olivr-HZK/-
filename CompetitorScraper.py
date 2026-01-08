import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import env_loader  # noqa: F401  # 支持从 .env 读取代理等配置


def load_config() -> Dict[str, Any]:
    """
    加载配置文件，默认路径与原项目保持一致：/app/config/config.yaml
    也支持通过 CONFIG_PATH 环境变量覆盖。
    """
    config_path = os.environ.get("CONFIG_PATH", "/app/config/config.yaml")
    if not os.path.exists(config_path):
        # 兼容本地直接运行仓库根目录的情况
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
    """
    从 config.yaml 中读取竞品社媒账号配置，支持新的层级结构：
    
    competitors:
      - name: voodoo
        priority: high
        platforms:
          - url: https://x.com/voodooplatform
            enabled: true
            type: twitter
        games:
          - name: papers.io
            platforms:
              - url: https://www.instagram.com/paper.io2game/
                enabled: true
                type: instagram
    """
    # 优先使用新的 competitors 格式
    competitors = cfg.get("competitor_monitor", {}).get("competitors") or cfg.get("competitors") or []
    
    # 如果没有新格式，回退到旧的 social_accounts 格式
    if not competitors:
        section = cfg.get("competitor_monitor") or {}
        if not section.get("enable", True):
            print("⚠️ competitor_monitor.enable = false，跳过爬取。")
            return []
        accounts = section.get("social_accounts") or []
        norm_accounts: List[Dict[str, Any]] = []
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            name = (acc.get("name") or "").strip()
            url = (acc.get("url") or "").strip()
            if not name or not url:
                continue
            platform = (acc.get("platform") or "").strip() or "unknown"
            norm_accounts.append({
                "company": name,
                "game": None,
                "platform_type": platform,
                "url": url,
                "priority": "medium"
            })
        if not norm_accounts:
            print("⚠️ 未在 config.yaml 中配置竞品信息，跳过爬取。")
        return norm_accounts
    
    # 处理新的 competitors 格式
    norm_accounts: List[Dict[str, Any]] = []
    
    for competitor in competitors:
        if not isinstance(competitor, dict):
            continue
        
        company_name = (competitor.get("name") or "").strip()
        if not company_name:
            continue
        
        company_priority = (competitor.get("priority") or "medium").strip().lower()
        
        # 处理公司级别的平台
        company_platforms = competitor.get("platforms") or []
        for platform in company_platforms:
            if not isinstance(platform, dict):
                continue
            if not platform.get("enabled", True):
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
        games = competitor.get("games") or []
        for game in games:
            if not isinstance(game, dict):
                continue
            game_name = (game.get("name") or "").strip()
            if not game_name:
                continue
            game_priority = (game.get("priority") or company_priority).strip().lower()
            
            game_platforms = game.get("platforms") or []
            for platform in game_platforms:
                if not isinstance(platform, dict):
                    continue
                if not platform.get("enabled", True):
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
    
    if not norm_accounts:
        print("⚠️ 未找到任何启用的竞品平台，跳过爬取。")
    else:
        print(f"[*] 发现 {len(norm_accounts)} 个竞品平台需要爬取")
    
    return norm_accounts


def build_proxies(cfg: Dict[str, Any]) -> Dict[str, str]:
    section = cfg.get("competitor_monitor") or {}
    use_proxy = bool(section.get("use_proxy", False))
    proxy_url = section.get("proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not use_proxy or not proxy_url:
        return {}
    return {"http": proxy_url, "https": proxy_url}


def fetch_page_with_playwright(url: str, platform_type: str, proxies: Dict[str, str]) -> str:
    """
    使用Playwright模拟浏览器抓取页面，等待JavaScript渲染完成。
    这对于Twitter、Instagram、TikTok等动态加载的平台特别重要。
    """
    use_playwright = os.environ.get("USE_PLAYWRIGHT", "true").lower() == "true"
    if not use_playwright:
        return ""
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            
            # 配置代理
            context_options = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080},
                "ignore_https_errors": True,
            }
            
            if proxies and proxies.get("http"):
                proxy_url = proxies["http"].replace("http://", "").replace("https://", "")
                context_options["proxy"] = {"server": f"http://{proxy_url}"}
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            page.set_default_navigation_timeout(60000)
            
            # 屏蔽部分资源以加快加载
            def route_handler(route):
                url = route.request.url
                if any(domain in url for domain in ["fonts.googleapis.com", "fonts.gstatic.com", "googletagmanager.com", "analytics"]):
                    route.abort()
                else:
                    route.continue_()
            page.route("**/*", route_handler)
            
            print(f"  [Playwright] 正在加载页面: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 根据不同平台等待不同的内容加载
            platform_lower = platform_type.lower()
            wait_time = 3  # 默认等待时间
            
            if "twitter" in platform_lower or "x.com" in url.lower():
                # 等待推文加载
                try:
                    page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                except PlaywrightTimeout:
                    # 如果没找到推文，至少等待页面稳定
                    time.sleep(3)
                wait_time = 5
            elif "instagram" in platform_lower:
                # Instagram需要滚动触发加载
                try:
                    page.wait_for_selector('article', timeout=10000)
                    # 滚动页面以触发懒加载
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                except PlaywrightTimeout:
                    time.sleep(3)
                wait_time = 5
            elif "tiktok" in platform_lower:
                # TikTok需要等待视频卡片
                try:
                    page.wait_for_selector('[data-e2e="user-post-item"]', timeout=10000)
                except PlaywrightTimeout:
                    time.sleep(3)
                wait_time = 5
            elif "youtube" in platform_lower:
                # YouTube等待视频列表
                try:
                    page.wait_for_selector('#dismissible, ytd-video-renderer', timeout=10000)
                except PlaywrightTimeout:
                    time.sleep(3)
                wait_time = 4
            else:
                # 其他平台通用等待
                time.sleep(wait_time)
            
            # 等待页面稳定
            time.sleep(wait_time)
            
            # 获取渲染后的HTML
            html = page.content()
            
            browser.close()
            print(f"  [Playwright] 页面加载完成，HTML长度: {len(html)}")
            return html
            
    except Exception as exc:
        print(f"  [Playwright] 抓取失败: {exc}")
        return ""


def fetch_page(url: str, proxies: Dict[str, str], platform_type: str = "unknown") -> str:
    """
    抓取页面 HTML，优先使用Playwright，失败则回退到requests。
    """
    # 对于需要JavaScript的平台，优先使用Playwright
    platform_lower = platform_type.lower()
    needs_js = any(p in platform_lower for p in ["twitter", "instagram", "tiktok", "youtube", "x.com"])
    
    if needs_js:
        html = fetch_page_with_playwright(url, platform_type, proxies)
        if html:
            return html
        print(f"  [回退] Playwright失败，尝试使用requests...")
    
    # 回退到requests（对于LinkedIn等可能不需要JS的平台）
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20, proxies=proxies or None)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        print(f"  [requests] 抓取失败: {exc}")
        return ""


def extract_json_from_script(html: str) -> List[Dict[str, Any]]:
    """
    从HTML的script标签中提取JSON数据（很多社交媒体平台会在这里嵌入数据）。
    """
    results = []
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script', type='application/json')
    scripts.extend(soup.find_all('script', type='application/ld+json'))
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) or isinstance(data, list):
                results.append(data)
        except (json.JSONDecodeError, AttributeError):
            continue
    
    # 也尝试查找包含window.__INITIAL_STATE__或类似结构的script
    for script in soup.find_all('script'):
        if not script.string:
            continue
        # 查找常见的嵌入式JSON模式
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
            r'"__d"\s*:\s*({.+?})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, script.string, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) or isinstance(data, list):
                        results.append(data)
                except json.JSONDecodeError:
                    continue
    
    return results


def parse_twitter_posts(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    解析Twitter/X的帖子信息。
    """
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # 尝试从JSON-LD提取
    json_data_list = extract_json_from_script(html)
    for data in json_data_list:
        if isinstance(data, dict) and data.get('@type') == 'Person':
            # 可能包含作者信息
            pass
    
    # 查找推文容器（Twitter的常见结构）
    # Twitter使用article标签包含推文
    articles = soup.find_all('article', {'data-testid': 'tweet'})
    if not articles:
        # 尝试其他可能的容器
        articles = soup.find_all('div', class_=re.compile(r'tweet|status', re.I))
    
    for article in articles[:10]:  # 最多提取10条
        post = {}
        
        # 提取文本内容
        text_elem = article.find('div', {'data-testid': 'tweetText'})
        if not text_elem:
            text_elem = article.find('div', class_=re.compile(r'text|content', re.I))
        if text_elem:
            post['text'] = text_elem.get_text(strip=True)
        
        # 提取时间
        time_elem = article.find('time')
        if time_elem:
            post['published_at'] = time_elem.get('datetime', '')
            post['published_at_display'] = time_elem.get_text(strip=True)
        
        # 提取互动数据
        # Twitter的互动按钮通常有特定的data-testid
        interactions = {}
        for interaction_type in ['like', 'reply', 'retweet', 'view']:
            elem = article.find('button', {'data-testid': f'{interaction_type}Button'})
            if not elem:
                elem = article.find('div', string=re.compile(r'\d+', re.I))
            if elem:
                text = elem.get_text(strip=True)
                # 提取数字（处理K, M等单位）
                num_match = re.search(r'([\d.]+)([KMB]?)', text.replace(',', ''))
                if num_match:
                    num = float(num_match.group(1))
                    unit = num_match.group(2)
                    if unit == 'K':
                        num *= 1000
                    elif unit == 'M':
                        num *= 1000000
                    interactions[interaction_type] = int(num)
        
        if interactions:
            post['engagement'] = interactions
        
        # 提取帖子链接
        link_elem = article.find('a', href=re.compile(r'/status/'))
        if link_elem:
            href = link_elem.get('href', '')
            post['post_url'] = urljoin(base_url, href)
        
        # 提取媒体链接
        media_links = []
        for img in article.find_all('img', src=re.compile(r'pbs\.twimg\.com|media')):
            src = img.get('src', '')
            if src and src not in media_links:
                media_links.append(src)
        if media_links:
            post['media_urls'] = media_links
        
        if post.get('text') or post.get('media_urls'):
            posts.append(post)
    
    return posts


def parse_instagram_posts(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    解析Instagram的帖子信息。
    """
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Instagram通常在script标签中嵌入JSON数据
    # 查找包含window._sharedData或类似结构的script
    for script in soup.find_all('script'):
        if not script.string:
            continue
        script_text = script.string
        
        # 尝试提取window._sharedData
        if 'window._sharedData' in script_text or '__additionalDataLoaded' in script_text:
            # 查找JSON对象
            json_match = re.search(r'window\._sharedData\s*=\s*({.+?});', script_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'({"config".+?});', script_text, re.DOTALL)
            
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    if 'entry_data' in data:
                        entry_data = data['entry_data']
                        if 'ProfilePage' in entry_data:
                            user_data = entry_data['ProfilePage'][0].get('graphql', {}).get('user', {})
                            timeline = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                            for edge in timeline[:12]:  # 最多12条
                                node = edge.get('node', {})
                                post = {
                                    'text': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                                    'published_at': node.get('taken_at_timestamp', ''),
                                    'post_url': f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                                    'media_urls': [node.get('display_url', '')] if node.get('display_url') else [],
                                    'engagement': {
                                        'like': node.get('edge_liked_by', {}).get('count', 0),
                                        'comment': node.get('edge_media_to_comment', {}).get('count', 0),
                                    }
                                }
                                if post['text'] or post['media_urls']:
                                    posts.append(post)
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"  [Instagram] JSON解析失败: {e}")
                    continue
    
    # 也尝试从其他JSON数据中提取
    json_data_list = extract_json_from_script(html)
    for data in json_data_list:
        if isinstance(data, dict):
            # 查找包含帖子数据的结构
            if 'entry_data' in data:
                entry_data = data['entry_data']
                if 'ProfilePage' in entry_data:
                    user_data = entry_data['ProfilePage'][0].get('graphql', {}).get('user', {})
                    timeline = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                    for edge in timeline[:12]:  # 最多12条
                        node = edge.get('node', {})
                        post = {
                            'text': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                            'published_at': node.get('taken_at_timestamp', ''),
                            'post_url': f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                            'media_urls': [node.get('display_url', '')] if node.get('display_url') else [],
                            'engagement': {
                                'like': node.get('edge_liked_by', {}).get('count', 0),
                                'comment': node.get('edge_media_to_comment', {}).get('count', 0),
                            }
                        }
                        if post['text'] or post['media_urls']:
                            posts.append(post)
    
    # 如果JSON解析失败，尝试HTML解析
    if not posts:
        articles = soup.find_all('article')
        for article in articles[:12]:
            post = {}
            
            # 提取文本 - Instagram的文本可能在多个位置
            text_elem = article.find('span', class_=re.compile(r'text|caption', re.I))
            if not text_elem:
                text_elem = article.find('div', string=re.compile(r'.{10,}', re.DOTALL))
            if text_elem:
                post['text'] = text_elem.get_text(strip=True)
            
            # 提取时间
            time_elem = article.find('time')
            if time_elem:
                post['published_at'] = time_elem.get('datetime', '')
            
            # 提取互动数据 - 改进匹配逻辑
            interactions = {}
            for elem in article.find_all(['span', 'a', 'button']):
                text = elem.get_text(strip=True)
                # 匹配数字格式（如 "1,234 likes" 或 "1.2K"）
                num_match = re.search(r'([\d,\.]+)\s*(K|M)?', text)
                if num_match:
                    num_str = num_match.group(1).replace(',', '')
                    unit = num_match.group(2)
                    try:
                        num = float(num_str)
                        if unit == 'K':
                            num *= 1000
                        elif unit == 'M':
                            num *= 1000000
                        if 'like' in text.lower() or 'likes' in text.lower():
                            interactions['like'] = int(num)
                        elif 'comment' in text.lower() or 'comments' in text.lower():
                            interactions['comment'] = int(num)
                    except ValueError:
                        pass
            
            if interactions:
                post['engagement'] = interactions
            
            # 提取图片和视频
            media_urls = []
            for img in article.find_all('img'):
                src = img.get('src', '') or img.get('data-src', '')
                if src and ('instagram' in src or 'cdn' in src) and src not in media_urls:
                    media_urls.append(src)
            if media_urls:
                post['media_urls'] = media_urls
            
            # 提取帖子链接
            link_elem = article.find('a', href=re.compile(r'/p/'))
            if link_elem:
                href = link_elem.get('href', '')
                post['post_url'] = urljoin(base_url, href)
            
            if post.get('text') or post.get('media_urls'):
                posts.append(post)
    
    return posts


def parse_tiktok_posts(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    解析TikTok的视频信息。
    """
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # TikTok在script标签中嵌入数据，通常包含__UNIVERSAL_DATA_FOR_REHYDRATION__
    for script in soup.find_all('script'):
        if not script.string:
            continue
        script_text = script.string
        
        # 查找包含视频数据的JSON
        if '__UNIVERSAL_DATA_FOR_REHYDRATION__' in script_text or 'ItemModule' in script_text:
            # 尝试提取JSON对象
            json_match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*({.+?});', script_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'({"ItemModule".+?});', script_text, re.DOTALL)
            
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    # 查找视频数据
                    if 'ItemModule' in data:
                        items = data['ItemModule']
                        for item_id, item in list(items.items())[:12]:  # 最多12条
                            post = {
                                'text': item.get('desc', ''),
                                'published_at': item.get('createTime', ''),
                                'post_url': f"https://www.tiktok.com/@{item.get('author', '')}/video/{item_id}",
                                'media_urls': [item.get('video', {}).get('downloadAddr', '')] if item.get('video') else [],
                                'engagement': {
                                    'like': item.get('stats', {}).get('diggCount', 0),
                                    'comment': item.get('stats', {}).get('commentCount', 0),
                                    'share': item.get('stats', {}).get('shareCount', 0),
                                    'view': item.get('stats', {}).get('playCount', 0),
                                }
                            }
                            if post['text'] or post['media_urls']:
                                posts.append(post)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"  [TikTok] JSON解析失败: {e}")
                    continue
    
    # 也尝试从其他JSON数据中提取
    json_data_list = extract_json_from_script(html)
    for data in json_data_list:
        if isinstance(data, dict):
            # 查找视频数据
            if 'ItemModule' in data:
                items = data['ItemModule']
                for item_id, item in list(items.items())[:12]:  # 最多12条
                    post = {
                        'text': item.get('desc', ''),
                        'published_at': item.get('createTime', ''),
                        'post_url': f"https://www.tiktok.com/@{item.get('author', '')}/video/{item_id}",
                        'media_urls': [item.get('video', {}).get('downloadAddr', '')] if item.get('video') else [],
                        'engagement': {
                            'like': item.get('stats', {}).get('diggCount', 0),
                            'comment': item.get('stats', {}).get('commentCount', 0),
                            'share': item.get('stats', {}).get('shareCount', 0),
                            'view': item.get('stats', {}).get('playCount', 0),
                        }
                    }
                    if post['text'] or post['media_urls']:
                        posts.append(post)
    
    # HTML解析作为备选
    if not posts:
        videos = soup.find_all('div', class_=re.compile(r'video|item', re.I))
        for video in videos[:12]:
            post = {}
            
            # 提取描述
            desc_elem = video.find('div', class_=re.compile(r'desc|title', re.I))
            if desc_elem:
                post['text'] = desc_elem.get_text(strip=True)
            
            # 提取互动数据
            interactions = {}
            for span in video.find_all('span', class_=re.compile(r'count|number', re.I)):
                text = span.get_text(strip=True)
                num_match = re.search(r'([\d.]+)([KMB]?)', text.replace(',', ''))
                if num_match:
                    num = float(num_match.group(1))
                    unit = num_match.group(2)
                    if unit == 'K':
                        num *= 1000
                    elif unit == 'M':
                        num *= 1000000
                    interactions['view'] = int(num)
            
            if interactions:
                post['engagement'] = interactions
            
            if post.get('text'):
                posts.append(post)
    
    return posts


def parse_youtube_posts(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    解析YouTube的视频信息。
    """
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # YouTube在script标签中嵌入JSON-LD
    json_data_list = extract_json_from_script(html)
    for data in json_data_list:
        if isinstance(data, dict) and data.get('@type') == 'VideoObject':
            post = {
                'text': data.get('name', ''),
                'published_at': data.get('uploadDate', ''),
                'post_url': data.get('url', ''),
                'media_urls': [data.get('thumbnailUrl', '')] if data.get('thumbnailUrl') else [],
                'engagement': {
                    'view': data.get('interactionCount', 0),
                }
            }
            if post['text']:
                posts.append(post)
    
    # HTML解析
    if not posts:
        videos = soup.find_all('div', {'id': 'dismissible'})
        for video in videos[:12]:
            post = {}
            
            # 提取标题
            title_elem = video.find('a', {'id': 'video-title'})
            if title_elem:
                post['text'] = title_elem.get_text(strip=True)
                post['post_url'] = urljoin(base_url, title_elem.get('href', ''))
            
            # 提取时间
            time_elem = video.find('span', class_=re.compile(r'published|time', re.I))
            if time_elem:
                post['published_at_display'] = time_elem.get_text(strip=True)
            
            # 提取观看数
            view_elem = video.find('span', string=re.compile(r'views', re.I))
            if view_elem:
                text = view_elem.get_text(strip=True)
                num_match = re.search(r'([\d.]+)([KMB]?)', text.replace(',', ''))
                if num_match:
                    num = float(num_match.group(1))
                    unit = num_match.group(2)
                    if unit == 'K':
                        num *= 1000
                    elif unit == 'M':
                        num *= 1000000
                    post['engagement'] = {'view': int(num)}
            
            if post.get('text'):
                posts.append(post)
    
    return posts


def parse_posts_from_html(html: str, platform_type: str, url: str) -> List[Dict[str, Any]]:
    """
    根据平台类型解析帖子信息。
    """
    platform_type_lower = platform_type.lower()
    
    if 'twitter' in platform_type_lower or 'x.com' in url.lower():
        return parse_twitter_posts(html, url)
    elif 'instagram' in platform_type_lower:
        return parse_instagram_posts(html, url)
    elif 'tiktok' in platform_type_lower:
        return parse_tiktok_posts(html, url)
    elif 'youtube' in platform_type_lower:
        return parse_youtube_posts(html, url)
    else:
        # 对于其他平台，尝试通用解析
        posts = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试提取JSON-LD数据
        json_data_list = extract_json_from_script(html)
        for data in json_data_list:
            if isinstance(data, dict):
                if data.get('@type') in ['Article', 'BlogPosting', 'NewsArticle']:
                    post = {
                        'text': data.get('headline', '') or data.get('name', ''),
                        'published_at': data.get('datePublished', ''),
                        'post_url': data.get('url', ''),
                    }
                    if post['text']:
                        posts.append(post)
        
        # 如果JSON解析失败，尝试HTML通用解析
        if not posts:
            articles = soup.find_all(['article', 'div'], class_=re.compile(r'post|item|card', re.I))
            for article in articles[:10]:
                post = {}
                text_elem = article.find(['h1', 'h2', 'h3', 'p', 'span'], class_=re.compile(r'title|text|content', re.I))
                if text_elem:
                    post['text'] = text_elem.get_text(strip=True)
                if post.get('text'):
                    posts.append(post)
        
        return posts


def scrape_competitor_social() -> None:
    """
    工作流第 1 步：抓取竞品公司在社交媒体上的最新动态（HTML 片段）。
    结果保存在 /app/output/competitor_social_raw.json
    """
    cfg = load_config()
    accounts = get_competitor_accounts(cfg)
    if not accounts:
        return

    proxies = build_proxies(cfg)
    items: List[Dict[str, Any]] = []
    for acc in accounts:
        company = acc["company"]
        game = acc.get("game")
        platform_type = acc["platform_type"]
        url = acc["url"]
        priority = acc.get("priority", "medium")
        
        # 构建显示名称
        if game:
            display_name = f"{company} - {game}"
        else:
            display_name = company
        
        print(f"[*] 正在抓取：{display_name} - {platform_type} ({url}) [优先级: {priority}]")
        html = fetch_page(url, proxies, platform_type)
        if not html:
            print(f"  ⚠️ 未能获取页面内容，跳过")
            continue
        
        # 解析帖子信息
        posts = parse_posts_from_html(html, platform_type, url)
        print(f"  ✓ 解析到 {len(posts)} 条帖子/视频")
        
        # 保留HTML片段作为备选（用于AI分析），但主要使用解析出的帖子数据
        item = {
            "company": company,
            "game": game,
            "platform_type": platform_type,
            "url": url,
            "priority": priority,
            "posts": posts,  # 新增：解析出的帖子列表
            "posts_count": len(posts),  # 新增：帖子数量
            "html_snippet": html[:5000] if len(html) > 5000 else html,  # 保留部分HTML作为备选
        }
        
        items.append(item)

    if not items:
        print("⚠️ 未成功抓取到任何竞品社媒内容。")
        return

    output_dir = "/app/output"
    # 兼容本地直接运行（仓库根目录）
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
        print(f"✅ 竞品社媒原始数据已保存至: {out_path}")
    except Exception as exc:
        print(f"❌ 保存结果失败: {exc}")


if __name__ == "__main__":
    scrape_competitor_social()

