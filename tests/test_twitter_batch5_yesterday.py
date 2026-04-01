"""
批量测试：抓取多个账号昨天的所有推文（RapidAPI - twitter241）

特性：
- 从内置 ACCOUNTS 里取前 5 个（可改）
- 小并发（默认 3 线程）降低 429 风险
- 输出到 output/twitter_batch5_yesterday.json

运行：
    python -m tests.test_twitter_batch5_yesterday
    python tests/test_twitter_batch5_yesterday.py
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import env_loader  # noqa: F401
except ModuleNotFoundError:
    # 兜底：从项目根读取 .env
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from scrapers.rapidapi import get_rapidapi_key, get_posts_from_twitter


ACCOUNTS: List[Tuple[str, str]] = [
    ("OpenAI", "OpenAI"),
    ("Google DeepMind", "GoogleDeepMind"),
    ("NVIDIA", "nvidia"),
    ("NVIDIA AI", "NVIDIAAI"),
    ("Anthropic", "AnthropicAI"),
    ("Meta AI", "MetaAI"),
    ("DeepSeek", "deepseek_ai"),
    ("Alibaba Qwen", "Alibaba_Qwen"),
    ("Midjourney", "midjourney"),
    ("Kimi Moonshot", "Kimi_Moonshot"),
    ("MiniMax", "MiniMax_AI"),
    ("ByteDance", "BytedanceTalk"),
    ("DeepMind Research", "DeepMind"),
    ("Google AI", "GoogleAI"),
    ("Groq", "GroqInc"),
    ("Hailuo AI", "Hailuo_AI"),
    ("MIT CSAIL", "MIT_CSAIL"),
    ("IBM Data", "IBMData"),
    ("Elon Musk", "elonmusk"),
    ("Sam Altman", "sama"),
    ("Mark Zuckerberg", "zuck"),
    ("Demis Hassabis", "demishassabis"),
    ("Dario Amodei", "DarioAmodei"),
]


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


def fetch_one_yesterday(display_name: str, username: str) -> Dict[str, Any]:
    posts = get_posts_from_twitter(username, days_ago=1, count=100, expected_username=username)
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
            }
        )
    return {
        "display_name": display_name,
        "username": username,
        "tweets_count": len(normalized),
        "tweets": normalized,
    }


def main() -> int:
    api_key = get_rapidapi_key()
    if not api_key:
        print("❌ 未配置 RAPIDAPI_KEY，请在 .env 设置 RAPIDAPI_KEY=...")
        return 2

    # 取前 5 个账号
    targets = ACCOUNTS[:5]
    print(f"[*] 本次测试 {len(targets)} 个账号（昨天的推文，按 UTC 日历日）")
    for name, user in targets:
        print(f"    - {name} @{user}")

    results: Dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "twitter241.p.rapidapi.com",
        "description": "Batch 5 accounts - yesterday tweets",
        "items": [],
    }

    # 小并发：3 线程，兼顾速度与 429 风险
    max_workers = int(os.getenv("TWITTER_BATCH_WORKERS", "3"))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_one_yesterday, name, user): (name, user)
            for name, user in targets
        }
        for fut in as_completed(futures):
            name, user = futures[fut]
            try:
                item = fut.result()
                print(f"    ✓ {name} @{user}: {item['tweets_count']} 条")
                results["items"].append(item)
            except Exception as exc:
                print(f"    ✗ {name} @{user} 抓取失败: {exc}")

    os.makedirs("output", exist_ok=True)
    out_path = os.path.join("output", "twitter_batch5_yesterday.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已写入: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

