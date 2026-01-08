"""
Twitter 监控完整工作流
1. 爬取 Twitter 推文
2. AI 分析
3. 推送到飞书
"""
import os
import sys

from TwitterScraper import scrape_twitter_workflow
from TwitterAnalysisAI import analyze_twitter_tweets
from TwitterFeishuSender import main as send_to_feishu


def run_twitter_workflow(input_path: str = None, max_tweets: int = 5, skip_send: bool = False):
    """运行完整的 Twitter 监控工作流"""
    print("\n" + "=" * 60)
    print("Twitter 监控完整工作流")
    print("=" * 60)
    print()
    
    # 步骤 1: 爬取推文
    print("【步骤 1/3】爬取 Twitter 推文")
    print("-" * 60)
    output_path = scrape_twitter_workflow(input_path=input_path, max_tweets=max_tweets)
    
    if not output_path:
        print("\n❌ 爬取推文失败，工作流终止")
        return 1
    
    # 步骤 2: AI 分析
    print("\n" + "=" * 60)
    print("【步骤 2/3】AI 分析推文")
    print("-" * 60)
    try:
        analyze_twitter_tweets()
    except Exception as exc:
        print(f"\n❌ AI 分析失败: {exc}")
        return 1
    
    # 步骤 3: 推送到飞书
    if not skip_send:
        print("\n" + "=" * 60)
        print("【步骤 3/3】推送到飞书")
        print("-" * 60)
        exit_code = send_to_feishu()
        if exit_code != 0:
            print("\n⚠️ 飞书推送失败，但数据已保存")
    else:
        print("\n⚠️ 跳过飞书推送（skip_send=True）")
    
    print("\n" + "=" * 60)
    print("✅ 工作流完成")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Twitter 监控工作流")
    parser.add_argument("--input", "-i", help="输入 JSON 文件路径", default=None)
    parser.add_argument("--max-tweets", "-n", type=int, help="每个账号最多抓取的推文数", default=5)
    parser.add_argument("--skip-send", action="store_true", help="跳过飞书推送")
    
    args = parser.parse_args()
    
    exit_code = run_twitter_workflow(
        input_path=args.input,
        max_tweets=args.max_tweets,
        skip_send=args.skip_send
    )
    
    sys.exit(exit_code)
