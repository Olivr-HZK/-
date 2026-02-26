"""
单公司 Twitter 爬取测试（获取前一天的帖子）

用于排查某家公司 Twitter 误爬到 Starlink 等问题。
请直接修改下方硬编码的 USERNAME / USER_ID / COMPANY_NAME / DAYS_AGO 后运行：

  python tests/test_twitter_single_company.py

可选：只测 user_id、只测 username、或测 author 过滤
  python tests/test_twitter_single_company.py --by id
  python tests/test_twitter_single_company.py --by username
  python tests/test_twitter_single_company.py --no-filter   # 不传 expected_username，看原始 timeline
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 确保项目根在 path 中
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import env_loader  # noqa: F401
except ImportError:
    pass

from scrapers.rapidapi import (
    get_posts_from_twitter,
    get_twitter_user_id_from_username,
)


# ============== 硬编码配置（请按需修改） ==============
COMPANY_NAME = "King"
USERNAME = "King_Games"
USER_ID = "30028228"
DAYS_AGO = 1  # 获取多少天前的帖子，1=前一天（与每日爬虫一致）
# 可选：用于对比的“错误账号”信息（例如 Starlink），便于确认是否混用
STARLINK_USERNAME = "Starlink"
STARLINK_USER_ID = ""  # 若已知可填，用于对比
# =====================================================


def _print_posts(posts: list, label: str, check_starlink: bool = True) -> None:
    print(f"\n--- {label} (共 {len(posts)} 条) ---")
    for i, p in enumerate(posts[:15], 1):
        text = (p.get("text") or "")[:200]
        if len((p.get("text") or "")) > 200:
            text += "..."
        print(f"  {i}. {text}")
        if check_starlink and ("starlink" in text.lower() or "spacex" in text.lower() or "卫星" in text):
            print("      ⚠️ 疑似 Starlink/卫星 相关内容，请检查账号是否错误")
    if len(posts) > 15:
        print(f"  ... 还有 {len(posts) - 15} 条未显示")


def run_by_username(expected_username: str | None) -> list:
    """用 username 拉取前一天的帖子，并传 expected_username 做作者过滤"""
    print(f"\n[1] 使用 username 拉取（前 {DAYS_AGO} 天）: {USERNAME}")
    print(f"    expected_username = {expected_username!r}")
    posts = get_posts_from_twitter(
        USERNAME,
        days_ago=DAYS_AGO,
        count=50,
        expected_username=expected_username,
    )
    return posts


def run_by_user_id(expected_username: str | None) -> list:
    """用 user_id 拉取前一天的帖子，并传 expected_username 做作者过滤"""
    print(f"\n[2] 使用 user_id 拉取（前 {DAYS_AGO} 天）: {USER_ID}")
    print(f"    expected_username = {expected_username!r}")
    posts = get_posts_from_twitter(
        USER_ID,
        days_ago=DAYS_AGO,
        count=50,
        expected_username=expected_username,
    )
    return posts


def run_no_filter() -> list:
    """用 user_id 拉取前一天的帖子，不传 expected_username（看原始 timeline 是否混入他人）"""
    print(f"\n[3] 使用 user_id 拉取（前 {DAYS_AGO} 天）且 不传 expected_username: {USER_ID}")
    posts = get_posts_from_twitter(
        USER_ID,
        days_ago=DAYS_AGO,
        count=50,
        expected_username=None,
    )
    return posts


def main():
    parser = argparse.ArgumentParser(description="单公司 Twitter 爬取测试（硬编码账号）")
    parser.add_argument(
        "--by",
        choices=["username", "id", "both"],
        default="both",
        help="用 username 还是 user_id 请求（both=都测）",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="额外跑一次：不传 expected_username，看原始 timeline 是否混入 Starlink 等",
    )
    parser.add_argument(
        "--resolve-id",
        action="store_true",
        help="先调用 API 根据 USERNAME 解析 user_id，打印结果（用于核对 USER_ID 是否正确）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="将拉取结果写入该 JSON 文件（不指定则不写）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("单公司 Twitter 测试（前一天的帖子）")
    print("=" * 60)
    print(f"  公司: {COMPANY_NAME}")
    print(f"  USERNAME (硬编码): {USERNAME}")
    print(f"  USER_ID (硬编码):  {USER_ID}")
    print(f"  DAYS_AGO: {DAYS_AGO}（1=前一天）")
    print("  修改脚本顶部常量可更换测试账号")

    expected_username = USERNAME.strip().lstrip("@") or None

    if args.resolve_id:
        print("\n[0] 解析 user_id (由 USERNAME 查询)...")
        resolved = get_twitter_user_id_from_username(USERNAME, debug=True)
        print(f"    解析结果: {resolved!r}")
        if resolved and resolved != USER_ID:
            print(f"    ⚠️ 与当前硬编码 USER_ID={USER_ID!r} 不一致，请核对")

    all_posts = []

    if args.by in ("username", "both"):
        posts = run_by_username(expected_username)
        _print_posts(posts, f"按 username 拉取 + expected_username={expected_username}")
        if args.by == "username":
            all_posts = posts

    if args.by in ("id", "both"):
        posts = run_by_user_id(expected_username)
        _print_posts(posts, f"按 user_id 拉取 + expected_username={expected_username}")
        all_posts = posts if args.by == "id" else (all_posts or posts)

    if args.no_filter:
        posts_raw = run_no_filter()
        _print_posts(posts_raw, "按 user_id 拉取且 不传 expected_username（原始 timeline）")
        if not all_posts:
            all_posts = posts_raw

    if args.out and all_posts:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"\n结果已写入: {args.out}")

    print("\n" + "=" * 60)
    print("测试结束。若出现 Starlink 内容，请检查 USER_ID 是否对应 Starlink，或依赖 expected_username 过滤。")
    print("=" * 60)


if __name__ == "__main__":
    main()
