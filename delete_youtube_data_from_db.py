"""
删除数据库中所有 YouTube 平台的数据
包括：
1. company_platforms 表中的 YouTube 平台配置
2. 各公司表中的 YouTube 帖子数据
"""
import os
import sqlite3
from typing import List

from CompetitorDatabaseDB import CompetitorDatabaseDB


def delete_all_youtube_data(db_path: str = None) -> None:
    """
    删除数据库中所有 YouTube 数据
    
    Args:
        db_path: 数据库文件路径，如果为None则使用默认路径
    """
    print("=" * 60)
    print("🗑️  删除数据库中所有 YouTube 数据")
    print("=" * 60)
    print()
    
    db = CompetitorDatabaseDB(db_path)
    conn = db._get_connection()
    
    try:
        # 1. 删除 company_platforms 表中的 YouTube 配置
        print("📋 步骤 1/2: 删除 company_platforms 表中的 YouTube 配置...")
        cursor = conn.execute("""
            SELECT COUNT(*) as count 
            FROM company_platforms 
            WHERE platform_type = 'youtube'
        """)
        config_count = cursor.fetchone()["count"]
        
        if config_count > 0:
            conn.execute("""
                DELETE FROM company_platforms 
                WHERE platform_type = 'youtube'
            """)
            print(f"  ✓ 已删除 {config_count} 条 YouTube 平台配置")
        else:
            print(f"  ℹ️  未找到 YouTube 平台配置")
        
        # 2. 删除各公司表中的 YouTube 帖子数据
        print()
        print("📋 步骤 2/2: 删除各公司表中的 YouTube 帖子数据...")
        
        # 获取所有公司表名
        cursor = conn.execute("""
            SELECT table_name 
            FROM company_tables_index
        """)
        company_tables = [row["table_name"] for row in cursor.fetchall()]
        
        total_deleted = 0
        companies_with_data = []
        
        for table_name in company_tables:
            # 检查表是否存在
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if not cursor.fetchone():
                continue
            
            # 查询该表中 YouTube 数据的数量
            try:
                cursor = conn.execute(f"""
                    SELECT COUNT(*) as count 
                    FROM {table_name} 
                    WHERE platform_type = 'youtube'
                """)
                youtube_count = cursor.fetchone()["count"]
                
                if youtube_count > 0:
                    # 删除 YouTube 数据
                    conn.execute(f"""
                        DELETE FROM {table_name} 
                        WHERE platform_type = 'youtube'
                    """)
                    total_deleted += youtube_count
                    companies_with_data.append((table_name, youtube_count))
                    print(f"  ✓ {table_name}: 删除了 {youtube_count} 条 YouTube 数据")
            except Exception as e:
                print(f"  ⚠️  处理表 {table_name} 时出错: {e}")
        
        # 提交所有更改
        conn.commit()
        
        print()
        print("=" * 60)
        print("📊 删除总结")
        print("=" * 60)
        print(f"  平台配置删除: {config_count} 条")
        print(f"  帖子数据删除: {total_deleted} 条")
        print(f"  涉及公司表数: {len(companies_with_data)} 个")
        
        if companies_with_data:
            print()
            print("  详细列表:")
            for table_name, count in companies_with_data:
                print(f"    • {table_name}: {count} 条")
        
        print()
        print("✅ 所有 YouTube 数据已删除")
        print("=" * 60)
        
    except Exception as exc:
        conn.rollback()
        print(f"❌ 删除失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        raise
    
    finally:
        conn.close()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="删除数据库中所有 YouTube 数据")
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认删除（防止误操作）"
    )
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("⚠️  警告：此操作将永久删除数据库中所有 YouTube 数据！")
        print("⚠️  请使用 --confirm 参数确认删除操作")
        print()
        response = input("是否继续？(输入 'yes' 确认): ")
        if response.lower() != 'yes':
            print("❌ 操作已取消")
            return 1
    
    try:
        delete_all_youtube_data(args.db_path)
        return 0
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
