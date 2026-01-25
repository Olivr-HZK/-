"""
删除数据库中 King 公司的所有 YouTube 平台数据
包括：
- company_platforms 表中的 King 相关 YouTube 平台配置
- 各公司表中的 King YouTube 帖子数据（如果有对应的表）
"""
import os
import sys
import sqlite3
from typing import Optional

import env_loader  # noqa: F401

from CompetitorDatabaseDB import CompetitorDatabaseDB


def delete_king_youtube_from_database(db_path: Optional[str] = None, confirm: bool = False) -> bool:
    """
    删除数据库中 King 公司的所有 YouTube 数据
    
    Args:
        db_path: 数据库文件路径（可选，默认为 db/competitor_data.db）
        confirm: 是否已确认删除（如果为 False，会要求用户输入确认）
    
    Returns:
        是否删除成功
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "db", "competitor_data.db")
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    # 确认删除
    if not confirm:
        print("=" * 60)
        print("⚠️  警告：此操作将删除数据库中 King 公司的所有 YouTube 数据")
        print("=" * 60)
        print("\n将删除以下数据：")
        print("  1. company_platforms 表中的 King 相关 YouTube 平台配置")
        print("  2. 各公司表中的 King YouTube 帖子数据（如果有）")
        print("\n此操作不可逆！")
        
        user_input = input("\n请输入 'yes' 确认删除，或按 Enter 取消: ").strip().lower()
        if user_input != "yes":
            print("❌ 操作已取消")
            return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        deleted_counts = {
            "company_platforms": 0,
            "company_tables": 0
        }
        
        # 1. 删除 company_platforms 表中的 King YouTube 记录
        print("\n📝 步骤 1: 删除 company_platforms 表中的 King YouTube 平台配置...")
        cursor = conn.execute("""
            SELECT COUNT(*) as count FROM company_platforms
            WHERE company_name = 'King' AND platform_type = 'youtube'
        """)
        count_before = cursor.fetchone()["count"]
        
        conn.execute("""
            DELETE FROM company_platforms
            WHERE company_name = 'King' AND platform_type = 'youtube'
        """)
        deleted_counts["company_platforms"] = count_before
        print(f"  ✓ 删除了 {count_before} 条 YouTube 平台配置记录")
        
        # 2. 查找并删除各公司表中的 King YouTube 数据
        print("\n📝 步骤 2: 查找并删除各公司表中的 King YouTube 数据...")
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE 'company_%'
        """)
        company_tables = [row["name"] for row in cursor.fetchall()]
        
        for table_name in company_tables:
            # 检查表结构，看是否有 company 或 company_name 字段和 platform_type 字段
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row["name"] for row in cursor.fetchall()]
            
            has_company_col = "company" in columns or "company_name" in columns
            has_platform_col = "platform_type" in columns
            
            if has_company_col and has_platform_col:
                company_col = "company" if "company" in columns else "company_name"
                
                cursor = conn.execute(f"""
                    SELECT COUNT(*) as count FROM {table_name}
                    WHERE {company_col} = 'King' AND platform_type = 'youtube'
                """)
                count_before = cursor.fetchone()["count"]
                if count_before > 0:
                    conn.execute(f"""
                        DELETE FROM {table_name}
                        WHERE {company_col} = 'King' AND platform_type = 'youtube'
                    """)
                    deleted_counts["company_tables"] += count_before
                    print(f"  ✓ 从 {table_name} 表中删除了 {count_before} 条 YouTube 记录")
        
        # 提交事务
        conn.commit()
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("✅ 删除完成")
        print("=" * 60)
        print(f"删除统计：")
        print(f"  - company_platforms 表: {deleted_counts['company_platforms']} 条")
        print(f"  - 各公司表: {deleted_counts['company_tables']} 条")
        print(f"  - 总计: {sum(deleted_counts.values())} 条记录")
        print("=" * 60)
        
        return True
    
    except Exception as exc:
        conn.rollback()
        print(f"\n❌ 删除过程中发生错误: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False
    
    finally:
        conn.close()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="删除数据库中 King 公司的所有 YouTube 数据"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="直接确认删除，不要求用户输入"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🗑️  King 公司 YouTube 数据删除工具")
    print("=" * 60)
    
    success = delete_king_youtube_from_database(
        db_path=args.db_path,
        confirm=args.confirm
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

