"""
清空数据库并重新加载 JSON 配置
用于清理重复配置和重新初始化数据库
"""
import os
import sys
import json
import argparse
from typing import Optional

import env_loader  # noqa: F401

from CompetitorDatabaseDB import CompetitorDatabaseDB


def clear_company_platforms(db: CompetitorDatabaseDB) -> bool:
    """
    清空 company_platforms 表的内容（仅删除平台配置，保留其他数据）
    
    Args:
        db: 数据库实例
    
    Returns:
        是否清空成功
    """
    conn = db._get_connection()
    try:
        print("\n" + "=" * 60)
        print("🗑️  清空 company_platforms 表")
        print("=" * 60)
        
        # 删除所有公司平台配置
        cursor = conn.execute("SELECT COUNT(*) as count FROM company_platforms")
        platform_count = cursor.fetchone()["count"]
        conn.execute("DELETE FROM company_platforms")
        print(f"  ✓ 已删除 {platform_count} 条平台配置记录")
        
        # 注意：保留以下数据
        # - companies 表（公司基本信息）
        # - {company}_raw_data 表（原始爬取数据）
        # - weekly_reports 表（周报数据）
        # - company_tables_index 表（公司表索引）
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ company_platforms 表清空完成")
        print("=" * 60)
        print("ℹ️  已保留：")
        print("   - companies 表（公司基本信息）")
        print("   - 原始爬取数据表（{company}_raw_data）")
        print("   - weekly_reports 表（周报数据）")
        print("=" * 60)
        return True
        
    except Exception as exc:
        conn.rollback()
        print(f"❌ 清空 company_platforms 表失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False
    finally:
        conn.close()


def load_companies_from_json(
    json_path: str = "input/twitter_input.json",
    db: Optional[CompetitorDatabaseDB] = None,
    db_path: Optional[str] = None
) -> bool:
    """
    从 JSON 文件加载所有公司配置并写入数据库
    
    Args:
        json_path: JSON 文件路径
        db: 数据库实例（如果提供，使用该实例；否则创建新实例）
        db_path: 数据库路径（仅在 db 为 None 时使用）
    
    Returns:
        是否加载成功
    """
    try:
        if not os.path.exists(json_path):
            print(f"❌ JSON 配置文件不存在: {json_path}")
            return False
        
        print("\n" + "=" * 60)
        print("📖 从 JSON 加载公司配置到数据库")
        print("=" * 60)
        
        # 读取 JSON 文件
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        competitors = data.get("competitors", [])
        if not competitors:
            print("⚠️ JSON 文件中未找到任何公司配置")
            return False
        
        # 创建或使用数据库实例
        if db is None:
            db = CompetitorDatabaseDB(db_path)
        
        print(f"📋 找到 {len(competitors)} 个公司配置")
        
        success_count = 0
        fail_count = 0
        
        # 更新每个公司的配置
        for competitor in competitors:
            company_name = competitor.get("name", "").strip()
            if not company_name:
                continue
            
            priority = competitor.get("priority", "high")
            
            # 构建社媒配置结构
            social_media_config = {
                "platforms": competitor.get("platforms", []),
                "games": competitor.get("games", [])
            }
            
            print(f"\n  📝 加载公司配置: {company_name}")
            success = db.save_company_social_media_config(
                company=company_name,
                priority=priority,
                social_media_config=social_media_config
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                print(f"    ❌ {company_name} 配置加载失败")
        
        print("\n" + "=" * 60)
        print("✅ 配置加载完成")
        print("=" * 60)
        print(f"  成功: {success_count} 个公司")
        if fail_count > 0:
            print(f"  失败: {fail_count} 个公司")
        print("=" * 60)
        
        return success_count > 0
    
    except Exception as exc:
        print(f"❌ 从 JSON 加载配置失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="清空 company_platforms 表并重新加载 JSON 配置"
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
    parser.add_argument(
        "--skip-clear",
        action="store_true",
        help="跳过清空数据库步骤（仅加载配置）"
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="跳过加载配置步骤（仅清空数据库）"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认执行（避免误操作）"
    )
    
    args = parser.parse_args()
    
    # 安全检查：如果没有 --confirm，需要用户确认
    if not args.confirm:
        print("⚠️  警告：此操作将清空 company_platforms 表（平台配置）！")
        print("   将保留：companies 表、原始爬取数据、周报数据")
        print("   如果只想清空配置但保留原始数据，请使用 --skip-load 参数")
        print()
        response = input("确认继续？(yes/no): ").strip().lower()
        if response != "yes":
            print("❌ 操作已取消")
            return 1
    
    # 初始化数据库
    db = CompetitorDatabaseDB(args.db_path)
    
    # 步骤 1: 清空 company_platforms 表（如果未跳过）
    if not args.skip_clear:
        success = clear_company_platforms(db)
        if not success:
            print("❌ 清空 company_platforms 表失败，终止操作")
            return 1
    else:
        print("ℹ️  跳过清空 company_platforms 表步骤")
    
    # 步骤 2: 加载配置（如果未跳过）
    if not args.skip_load:
        success = load_companies_from_json(
            json_path=args.json_path,
            db=db,
            db_path=args.db_path
        )
        if not success:
            print("❌ 加载配置失败")
            return 1
    else:
        print("ℹ️  跳过加载配置步骤")
    
    print("\n" + "=" * 60)
    print("✅ 操作完成")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

