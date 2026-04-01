"""
Elon Musk 昨日推文抓取测试脚本

功能：
- 使用 RapidAPI（twitter241.p.rapidapi.com）抓取 Elon Musk 昨天的所有推文
- 简单校验字段
- 将结果写入 output/twitter_elon_yesterday.json 方便查看

用法：
    python -m tests.test_twitter_elon_yesterday
    python tests/test_twitter_elon_yesterday.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import env_loader  # noqa: F401
except ModuleNotFoundError:
    # 兜底：简单从项目根目录读取 .env（如果存在）
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from scrapers.rapidapi import get_rapidapi_key, get_posts_from_twitter


def _safe_int(val: Any) -> int:
    if val is None:
        return 0
    if isinstance(val, str):
        try:
            return int(val.replace(",", ""))
        except Exception:
            return 0
    try:
        return int(val)
    except Exception:
        return 0


def fetch_elon_yesterday() -> Dict[str, Any]:
    """
    抓取 Elon Musk 昨天的所有推文（按 UTC 日历日）
    Twitter Username: elonmusk
    """
    username = "elonmusk"
    # days_ago=1 -> 昨天的推文，内部按 UTC 0-24 点过滤
    posts: List[Dict[str, Any]] = get_posts_from_twitter(username, days_ago=1, count=100, expected_username=username)

    normalized: List[Dict[str, Any]] = []
    for p in posts:
        eng = p.get("engagement") or {}
        normalized.append(
            {
                "text": (p.get("text") or "").strip(),
                "post_url": p.get("post_url") or "",
                "published_at": p.get("published_at") or "",
                "published_at_display": p.get("published_at_display") or "",
                "like": _safe_int(eng.get("like")),
                "retweet": _safe_int(eng.get("retweet")),
                "reply": _safe_int(eng.get("reply")),
                "quote": _safe_int(eng.get("quote")),
                "view": _safe_int(eng.get("view")),
                "raw_engagement": eng,
            }
        )

    # 简单校验：每条至少要有文本或链接
    for i, t in enumerate(normalized, 1):
        if not t["text"] and not t["post_url"]:
            raise ValueError(f"tweet {i} 缺少 text 和 post_url 字段")

    return {
        "username": username,
        "tweets_count": len(normalized),
        "tweets": normalized,
    }


def main() -> int:
    api_key = get_rapidapi_key()
    if not api_key:
        print("❌ 未配置 RAPIDAPI_KEY，请在 .env 设置 RAPIDAPI_KEY=...")
        return 2

    print("[*] 正在抓取 Elon Musk 昨天的所有推文（days_ago=1, 按 UTC 日历日）...")
    result = fetch_elon_yesterday()
    print(f"    ✓ 共获取到 {result['tweets_count']} 条推文")

    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "twitter_elon_yesterday.json")

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "twitter241.p.rapidapi.com",
        "description": "Elon Musk 昨日推文（按 UTC 日历日）",
        "item": result,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已写入: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

