"""
删除数据库中各公司帖子表内所有的 YouTube 帖子
只删除帖子数据，不删除平台配置
"""
import os
import sqlite3
from typing import List

from database.competitor_db import CompetitorDatabaseDB


def delete_all_youtube_posts(db_path: str = None) -> None:
    """
    删除数据库中各公司帖子表内所有的 YouTube 帖子
    
    Args:
        db_path: 数据库文件路径，如果为None则使用默认路径
    """
    print("=" * 60)
    print("🗑️  删除数据库中各公司帖子表内所有的 YouTube 帖子")
    print("=" * 60)
    print()
    
    db = CompetitorDatabaseDB(db_path)
    conn = db._get_connection()
    
    try:
        # 获取所有公司表名
        print("📋 正在查找所有公司表...")
        cursor = conn.execute("""
            SELECT table_name 
            FROM company_tables_index
        """)
        company_tables = [row["table_name"] for row in cursor.fetchall()]
        
        if not company_tables:
            print("  ℹ️  未找到任何公司表")
            return
        
        print(f"  ✓ 找到 {len(company_tables)} 个公司表")
        print()
        
        total_deleted = 0
        companies_with_data = []
        
        # 遍历每个公司表，删除 YouTube 帖子
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
                    print(f"  ✓ {table_name}: 删除了 {youtube_count} 条 YouTube 帖子")
            except Exception as e:
                print(f"  ⚠️  处理表 {table_name} 时出错: {e}")
        
        # 提交所有更改
        conn.commit()
        
        print()
        print("=" * 60)
        print("📊 删除总结")
        print("=" * 60)
        print(f"  总删除帖子数: {total_deleted} 条")
        print(f"  涉及公司表数: {len(companies_with_data)} 个")
        
        if companies_with_data:
            print()
            print("  详细列表:")
            for table_name, count in companies_with_data:
                print(f"    • {table_name}: {count} 条")
        
        print()
        print("✅ 所有 YouTube 帖子已删除")
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
    
    parser = argparse.ArgumentParser(description="删除数据库中各公司帖子表内所有的 YouTube 帖子")
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
        print("⚠️  警告：此操作将永久删除数据库中所有 YouTube 帖子数据！")
        print("⚠️  请使用 --confirm 参数确认删除操作")
        print()
        response = input("是否继续？(输入 'yes' 确认): ")
        if response.lower() != 'yes':
            print("❌ 操作已取消")
            return 1
    
    try:
        delete_all_youtube_posts(args.db_path)
        return 0
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
