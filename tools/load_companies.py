"""
从 JSON 文件加载所有公司及平台配置到数据库
读取 input/twitter_input.json，将所有公司的社媒配置保存到数据库
"""
import os
import sys
import json
from typing import Dict, List, Any, Optional

import env_loader  # noqa: F401

from database.competitor_db import CompetitorDatabaseDB


def load_companies_from_json_to_database(
    json_path: str = "input/twitter_input.json",
    db_path: Optional[str] = None
) -> bool:
    """
    从 JSON 文件加载所有公司配置并保存到数据库
    
    Args:
        json_path: JSON 文件路径
        db_path: 数据库文件路径（可选，默认为 db/competitor_data.db）
    
    Returns:
        是否加载成功
    """
    print("=" * 60)
    print("📖 从 JSON 加载公司及平台配置到数据库")
    print("=" * 60)
    
    # 检查 JSON 文件是否存在
    if not os.path.exists(json_path):
        print(f"❌ JSON 配置文件不存在: {json_path}")
        return False
    
    # 读取 JSON 文件
    print(f"\n📄 读取 JSON 文件: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"❌ 读取 JSON 文件失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False
    
    competitors = data.get("competitors", [])
    if not competitors:
        print("⚠️ JSON 文件中未找到任何公司配置")
        return False
    
    print(f"✅ 成功读取 JSON 文件")
    print(f"📋 找到 {len(competitors)} 个公司配置")
    
    # 初始化数据库
    print(f"\n💾 初始化数据库连接...")
    db = CompetitorDatabaseDB(db_path)
    print(f"✅ 数据库连接已建立")
    
    # 统计信息
    success_count = 0
    fail_count = 0
    total_company_platforms = 0
    total_game_platforms = 0
    
    # 更新每个公司的配置
    print(f"\n📝 开始更新公司配置到数据库...")
    print("=" * 60)
    
    for idx, competitor in enumerate(competitors, 1):
        company_name = competitor.get("name", "").strip()
        if not company_name:
            print(f"\n  [{idx}/{len(competitors)}] ⚠️ 跳过：公司名称为空")
            continue
        
        priority = competitor.get("priority", "high")
        platforms = competitor.get("platforms", [])
        games = competitor.get("games", [])
        
        # 统计平台数量
        company_platforms_count = len(platforms)
        game_platforms_count = sum(len(g.get("platforms", [])) for g in games)
        
        print(f"\n  [{idx}/{len(competitors)}] 📝 更新公司: {company_name}")
        print(f"      优先级: {priority}")
        print(f"      公司级平台: {company_platforms_count} 个")
        print(f"      游戏数: {len(games)} 个")
        print(f"      游戏级平台: {game_platforms_count} 个")
        
        # 构建社媒配置结构
        social_media_config = {
            "platforms": platforms,
            "games": games
        }
        
        try:
            success = db.save_company_social_media_config(
                company=company_name,
                priority=priority,
                social_media_config=social_media_config
            )
            
            if success:
                success_count += 1
                total_company_platforms += company_platforms_count
                total_game_platforms += game_platforms_count
                print(f"      ✅ {company_name} 配置已保存")
            else:
                fail_count += 1
                print(f"      ❌ {company_name} 配置保存失败")
        
        except Exception as exc:
            fail_count += 1
            print(f"      ❌ {company_name} 配置保存时出错: {exc}")
            import traceback
            print(f"      [调试] 错误详情: {traceback.format_exc()}")
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 加载总结")
    print("=" * 60)
    print(f"  总公司数: {len(competitors)}")
    print(f"  成功: {success_count} 个公司")
    if fail_count > 0:
        print(f"  失败: {fail_count} 个公司")
    print(f"  公司级平台总数: {total_company_platforms} 个")
    print(f"  游戏级平台总数: {total_game_platforms} 个")
    print(f"  总平台数: {total_company_platforms + total_game_platforms} 个")
    print("=" * 60)
    
    if success_count > 0:
        print("\n✅ 配置已成功加载到数据库")
        return True
    else:
        print("\n❌ 没有成功加载任何配置")
        return False


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="从 JSON 文件加载所有公司及平台配置到数据库"
    )
    parser.add_argument(
        "--json-path",
        type=str,
        default="input/twitter_input.json",
        help="JSON 配置文件路径（默认: input/twitter_input.json）"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    
    args = parser.parse_args()
    
    success = load_companies_from_json_to_database(
        json_path=args.json_path,
        db_path=args.db_path
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

