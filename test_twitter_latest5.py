"""
Twitter 抓取测试脚本

目标：
- 抓取指定账号最新 5 条推文
- 校验关键字段是否存在（内容、点赞、转发、查看）
- 将结果写入 output/twitter_latest5_test.json

使用：
1) 单账号：
   python test_twitter_latest5.py --username voodooplatform

2) 从 input/twitter_input.json 读取所有 twitter 账号并逐个测试：
   python test_twitter_latest5.py --input input/twitter_input.json
"""

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List

import env_loader  # noqa: F401

from CompetitorScraperRapidAPI import get_rapidapi_key, get_posts_from_twitter


def _safe_int(val: Any) -> int:
    if val is None:
        return 0
    # twitter241 views.count often is string
    if isinstance(val, str):
        try:
            return int(val)
        except Exception:
            # remove commas if any
            try:
                return int(val.replace(",", ""))
            except Exception:
                return 0
    try:
        return int(val)
    except Exception:
        return 0


def _extract_usernames_from_input(input_path: str) -> List[str]:
    if not os.path.exists(input_path):
        return []
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    usernames: List[str] = []
    for comp in data.get("competitors", []) or []:
        if not isinstance(comp, dict):
            continue
        for plat in (comp.get("platforms") or []):
            if not isinstance(plat, dict):
                continue
            if (plat.get("type") or "").strip().lower() != "twitter":
                continue
            u = (plat.get("username") or "").strip().lstrip("@")
            if u:
                usernames.append(u)
        for game in (comp.get("games") or []):
            if not isinstance(game, dict):
                continue
            for plat in (game.get("platforms") or []):
                if not isinstance(plat, dict):
                    continue
                if (plat.get("type") or "").strip().lower() != "twitter":
                    continue
                u = (plat.get("username") or "").strip().lstrip("@")
                if u:
                    usernames.append(u)

    # 去重但保持顺序
    seen = set()
    out: List[str] = []
    for u in usernames:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def fetch_latest5(username: str) -> Dict[str, Any]:
    username = username.strip().lstrip("@")
    posts = get_posts_from_twitter(username, days_ago=None, count=20)
    latest5 = posts[:5]

    normalized: List[Dict[str, Any]] = []
    for p in latest5:
        eng = p.get("engagement") or {}
        normalized.append(
            {
                "text": (p.get("text") or "").strip(),
                "post_url": p.get("post_url") or "",
                "published_at": p.get("published_at") or "",
                "published_at_display": p.get("published_at_display") or "",
                "like": _safe_int(eng.get("like")),
                "retweet": _safe_int(eng.get("retweet")),
                "view": _safe_int(eng.get("view")),
                "raw_engagement": eng,
            }
        )

    # 简单校验：至少有 text 或 url；互动字段存在（允许为 0）
    for i, t in enumerate(normalized, 1):
        if not t["text"] and not t["post_url"]:
            raise ValueError(f"tweet {i} missing both text and post_url")

    return {
        "username": username,
        "tweets_count": len(normalized),
        "tweets": normalized,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Twitter latest 5 tweets via RapidAPI")
    parser.add_argument("--username", "-u", help="Twitter username (without @)", default="")
    parser.add_argument("--input", "-i", help="Input json path (twitter_input.json)", default="")
    parser.add_argument(
        "--output",
        "-o",
        help="Output json path",
        default=os.path.join("output", "twitter_latest5_test.json"),
    )

    args = parser.parse_args()

    api_key = get_rapidapi_key()
    if not api_key:
        print("❌ 未配置 RAPIDAPI_KEY，请在 .env 设置 RAPIDAPI_KEY=...")
        return 2

    usernames: List[str] = []
    if args.username:
        usernames = [args.username.strip().lstrip("@")]
    elif args.input:
        usernames = _extract_usernames_from_input(args.input)
    else:
        print("❌ 请提供 --username 或 --input")
        return 2

    if not usernames:
        print("❌ 未找到任何 username")
        return 2

    results: Dict[str, Any] = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "source": "twitter241.p.rapidapi.com",
        "items": [],
    }

    for u in usernames:
        print(f"[*] 测试抓取 @{u} 最新 5 条推文...")
        item = fetch_latest5(u)
        results["items"].append(item)
        print(f"    ✓ 获取到 {item['tweets_count']} 条")

    out_dir = os.path.dirname(args.output) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 测试结果已写入: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

