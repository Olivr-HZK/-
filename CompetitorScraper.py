import json
import os
from datetime import datetime
from typing import Dict, List, Any

import requests
import yaml

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


def fetch_page(url: str, proxies: Dict[str, str]) -> str:
    """
    简单抓取页面 HTML，并做一定长度截断。
    复杂平台（如 X/TikTok）的结构交给后续 AI 自行“读页面片段”做推理。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, proxies=proxies or None)
        resp.raise_for_status()
        text = resp.text
        # 为了控制 token，做一个简单截断；后续 AI 会基于片段做分析
        max_len = int(os.environ.get("COMPETITOR_HTML_MAX_CHARS", "12000"))
        return text[:max_len]
    except Exception as exc:
        print(f"❌ 抓取 {url} 失败: {exc}")
        return ""


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
        html = fetch_page(url, proxies)
        if not html:
            continue
        
        items.append(
            {
                "company": company,
                "game": game,
                "platform_type": platform_type,
                "url": url,
                "priority": priority,
                "html_snippet": html,
            }
        )

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

