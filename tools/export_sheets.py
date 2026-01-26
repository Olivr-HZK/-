"""
将数据库中的社交媒体更新（帖子/视频数据）导出到 Google Sheets
需要配置 Google Service Account 凭证
"""
import os
import sys
import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import env_loader  # noqa: F401

from database.competitor_db import CompetitorDatabaseDB

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ 缺少必要的库，请安装：")
    print("   pip install gspread google-auth")
    sys.exit(1)


def get_google_sheets_client(credentials_path: str = None) -> Optional[gspread.Client]:
    """
    获取 Google Sheets 客户端
    
    Args:
        credentials_path: Google Service Account JSON 凭证文件路径
                         如果为 None，则从环境变量 GOOGLE_CREDENTIALS_PATH 读取
    
    Returns:
        gspread.Client 实例，如果失败则返回 None
    """
    if credentials_path is None:
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    if not credentials_path:
        print("❌ 未指定 Google 凭证文件路径")
        print("   请设置环境变量 GOOGLE_CREDENTIALS_PATH 或使用 --credentials 参数")
        return None
    
    if not os.path.exists(credentials_path):
        print(f"❌ Google 凭证文件不存在: {credentials_path}")
        return None
    
    try:
        # 设置权限范围
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 加载凭证
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(creds)
        
        print(f"✅ Google Sheets 客户端初始化成功")
        return client
    
    except Exception as exc:
        print(f"❌ 初始化 Google Sheets 客户端失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return None


def get_all_posts_from_db(
    db: CompetitorDatabaseDB,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    companies: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    从数据库获取所有公司的社交媒体帖子/视频数据
    
    Args:
        db: 数据库实例
        start_date: 开始日期（可选，默认获取所有日期）
        end_date: 结束日期（可选，默认获取所有日期）
        companies: 指定公司列表（可选，默认获取所有公司）
    
    Returns:
        帖子数据列表，每条帖子一行
    """
    conn = db._get_connection()
    try:
        # 获取所有公司表
        cursor = conn.execute("""
            SELECT company_name, table_name 
            FROM company_tables_index
        """)
        company_tables = {row["company_name"]: row["table_name"] for row in cursor.fetchall()}
        
        if not company_tables:
            return []
        
        # 如果指定了公司列表，只处理这些公司
        if companies:
            company_tables = {k: v for k, v in company_tables.items() if k in companies}
        
        all_posts = []
        
        # 遍历每个公司表
        for company_name, table_name in company_tables.items():
            # 构建查询条件
            where_conditions = []
            params = []
            
            if start_date:
                where_conditions.append("fetch_date >= ?")
                params.append(start_date.strftime("%Y-%m-%d"))
            
            if end_date:
                where_conditions.append("fetch_date <= ?")
                params.append(end_date.strftime("%Y-%m-%d"))
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 查询该公司的所有帖子数据
            query = f"""
                SELECT 
                    fetch_date,
                    platform_type,
                    game,
                    url,
                    username,
                    page_id,
                    channel_id,
                    handle,
                    posts_count,
                    posts_json,
                    fetched_at
                FROM {table_name}
                WHERE {where_clause}
                ORDER BY fetch_date DESC, platform_type, game
            """
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # 解析每条记录中的帖子
            for row in rows:
                posts_json_str = row["posts_json"]
                if not posts_json_str:
                    continue
                
                try:
                    posts = json.loads(posts_json_str)
                    if not isinstance(posts, list):
                        continue
                    
                    # 为每条帖子创建一行数据
                    for post in posts:
                        # 提取帖子信息（不同平台字段可能不同）
                        post_text = (
                            post.get("text") or 
                            post.get("message") or 
                            post.get("description") or 
                            post.get("title") or 
                            ""
                        )
                        
                        post_url = (
                            post.get("post_url") or 
                            post.get("url") or 
                            post.get("link") or 
                            ""
                        )
                        
                        # 发布时间
                        published_at = (
                            post.get("published_at") or 
                            post.get("published_at_display") or 
                            post.get("time") or 
                            post.get("created_at") or 
                            ""
                        )
                        
                        # 互动数据
                        engagement = post.get("engagement", {})
                        if isinstance(engagement, dict):
                            likes = engagement.get("like", engagement.get("likes", 0))
                            comments = engagement.get("comment", engagement.get("comments", 0))
                            shares = engagement.get("share", engagement.get("shares", 0))
                            views = engagement.get("view", engagement.get("views", 0))
                        else:
                            likes = comments = shares = views = 0
                        
                        # 媒体信息
                        media_urls = post.get("media_urls", [])
                        if isinstance(media_urls, list):
                            media_count = len(media_urls)
                            media_type = "视频" if any("video" in str(url).lower() for url in media_urls) else "图片"
                        else:
                            media_count = 0
                            media_type = ""
                        
                        all_posts.append({
                            "company_name": company_name,
                            "fetch_date": row["fetch_date"],
                            "platform_type": row["platform_type"],
                            "game": row["game"] or "",
                            "url": row["url"],
                            "username": row["username"] or "",
                            "post_text": post_text[:500] if post_text else "",  # 限制长度
                            "post_url": post_url,
                            "published_at": published_at,
                            "likes": likes,
                            "comments": comments,
                            "shares": shares,
                            "views": views,
                            "media_count": media_count,
                            "media_type": media_type,
                            "fetched_at": row["fetched_at"],
                        })
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"  ⚠️ 解析帖子数据失败 ({company_name}, {row['fetch_date']}): {e}")
                    continue
        
        return all_posts
    
    finally:
        conn.close()


def export_to_google_sheets(
    db_path: Optional[str] = None,
    spreadsheet_id: str = None,
    worksheet_name: str = "社媒更新",
    credentials_path: str = None,
    create_new: bool = False,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    companies: Optional[List[str]] = None
) -> bool:
    """
    将数据库中的社交媒体更新（帖子/视频数据）导出到 Google Sheets
    
    Args:
        db_path: 数据库文件路径
        spreadsheet_id: Google Sheets 表格 ID（如果 create_new=False，优先从环境变量读取）
        worksheet_name: 工作表名称
        credentials_path: Google Service Account 凭证文件路径（优先从环境变量读取）
        create_new: 是否创建新的表格（如果为 True，会创建新表格并返回 ID）
        start_date: 开始日期（可选，格式：YYYY-MM-DD）
        end_date: 结束日期（可选，格式：YYYY-MM-DD）
        companies: 指定公司列表（可选，默认获取所有公司）
    
    Returns:
        是否导出成功
    """
    print("=" * 60)
    print("📊 导出社交媒体更新到 Google Sheets")
    print("=" * 60)
    
    # 优先从环境变量读取配置
    if not spreadsheet_id:
        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        if spreadsheet_id:
            print(f"ℹ️ 从环境变量读取表格 ID: {spreadsheet_id[:20]}...")
    
    if not credentials_path:
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if credentials_path:
            print(f"ℹ️ 从环境变量读取凭证路径: {credentials_path}")
    
    # 1. 初始化数据库
    print("\n💾 步骤 1: 连接数据库...")
    db = CompetitorDatabaseDB(db_path)
    print("✅ 数据库连接成功")
    
    # 2. 获取所有帖子数据
    print("\n📖 步骤 2: 从数据库读取帖子/视频数据...")
    if start_date:
        print(f"   开始日期: {start_date}")
    if end_date:
        print(f"   结束日期: {end_date}")
    if companies:
        print(f"   指定公司: {', '.join(companies)}")
    
    posts = get_all_posts_from_db(db, start_date=start_date, end_date=end_date, companies=companies)
    
    if not posts:
        print("⚠️ 数据库中未找到任何帖子/视频数据")
        return False
    
    print(f"✅ 找到 {len(posts)} 条帖子/视频记录")
    
    # 3. 初始化 Google Sheets 客户端
    print("\n🔐 步骤 3: 初始化 Google Sheets 客户端...")
    client = get_google_sheets_client(credentials_path)
    if not client:
        return False
    
    # 4. 打开或创建表格
    print("\n📄 步骤 4: 打开或创建 Google Sheets 表格...")
    try:
        if create_new:
            try:
                # 创建新表格
                spreadsheet = client.create(worksheet_name)
                spreadsheet.share('', perm_type='anyone', role='reader')  # 可选：设置为公开只读
                print(f"✅ 已创建新表格: {spreadsheet.title}")
                print(f"   表格 ID: {spreadsheet.id}")
                print(f"   表格 URL: {spreadsheet.url}")
            except Exception as create_exc:
                if "quota" in str(create_exc).lower() or "storage" in str(create_exc).lower():
                    print(f"❌ 无法创建新表格：Google Drive 存储配额已满")
                    print(f"\n💡 解决方案：")
                    print(f"   1. 清理 Google Drive 空间（删除不需要的文件）")
                    print(f"   2. 使用现有表格：")
                    print(f"      - 先手动创建一个 Google Sheets 表格")
                    print(f"      - 获取表格 ID（从 URL 中提取）")
                    print(f"      - 将表格共享给服务账号邮箱")
                    print(f"      - 使用 --spreadsheet-id 参数运行脚本")
                    print(f"   3. 升级 Google Drive 存储计划")
                    return False
                else:
                    raise
        else:
            if not spreadsheet_id:
                print("❌ 未指定表格 ID")
                print(f"\n💡 请使用以下方式之一：")
                print(f"   1. 在 .env 文件中设置 GOOGLE_SPREADSHEET_ID 环境变量（推荐）")
                print(f"   2. 使用 --spreadsheet-id 参数指定表格 ID")
                print(f"   3. 或使用 --create-new 创建新表格（如果存储空间充足）")
                return False
            
            spreadsheet = client.open_by_key(spreadsheet_id)
            print(f"✅ 已打开表格: {spreadsheet.title}")
            print(f"   表格 ID: {spreadsheet_id}")
        
        # 5. 获取或创建工作表
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"✅ 已打开工作表: {worksheet_name}")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
            print(f"✅ 已创建新工作表: {worksheet_name}")
    
    except Exception as exc:
        print(f"❌ 打开/创建表格失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False
    
    # 6. 准备数据
    print("\n📝 步骤 5: 准备数据...")
    
    # 表头
    headers = [
        "公司名称",
        "抓取日期",
        "平台类型",
        "游戏名称",
        "账号URL",
        "用户名",
        "帖子内容",
        "帖子链接",
        "发布时间",
        "点赞数",
        "评论数",
        "分享数",
        "观看数",
        "媒体数量",
        "媒体类型",
        "抓取时间"
    ]
    
    # 数据行
    rows = [headers]
    for post in posts:
        rows.append([
            post["company_name"],
            post["fetch_date"],
            post["platform_type"],
            post["game"],
            post["url"],
            post["username"],
            post["post_text"],
            post["post_url"],
            post["published_at"],
            post["likes"],
            post["comments"],
            post["shares"],
            post["views"],
            post["media_count"],
            post["media_type"],
            post["fetched_at"],
        ])
    
    print(f"✅ 已准备 {len(rows) - 1} 行数据（不含表头）")
    
    # 7. 写入数据
    print("\n💾 步骤 6: 写入数据到 Google Sheets...")
    try:
        # 清空现有数据
        worksheet.clear()
        
        # 写入新数据
        worksheet.update('A1', rows, value_input_option='USER_ENTERED')
        
        # 格式化表头（加粗）
        worksheet.format('A1:P1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # 自动调整列宽（可选）
        try:
            worksheet.columns_auto_resize(0, len(headers) - 1)
        except Exception:
            pass  # 如果 API 不支持自动调整列宽，忽略错误
        
        print(f"✅ 数据已成功写入 Google Sheets")
        print(f"   工作表: {worksheet_name}")
        print(f"   数据行数: {len(rows) - 1}")
        print(f"   表格 URL: {spreadsheet.url}")
        
        return True
    
    except Exception as exc:
        print(f"❌ 写入数据失败: {exc}")
        import traceback
        print(f"[调试] 错误详情: {traceback.format_exc()}")
        return False


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="将数据库中的公司社媒信息导出到 Google Sheets"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="数据库文件路径（可选，默认为 db/competitor_data.db）"
    )
    parser.add_argument(
        "--spreadsheet-id",
        type=str,
        help="Google Sheets 表格 ID（如果使用现有表格，默认从环境变量 GOOGLE_SPREADSHEET_ID 读取）"
    )
    parser.add_argument(
        "--worksheet-name",
        type=str,
        default="公司社媒信息",
        help="工作表名称（默认: 公司社媒信息）"
    )
    parser.add_argument(
        "--credentials",
        type=str,
        help="Google Service Account JSON 凭证文件路径（或设置 GOOGLE_CREDENTIALS_PATH 环境变量）"
    )
    parser.add_argument(
        "--create-new",
        action="store_true",
        help="创建新的 Google Sheets 表格（而不是使用现有表格）"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="开始日期（格式：YYYY-MM-DD，可选）"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期（格式：YYYY-MM-DD，可选）"
    )
    parser.add_argument(
        "--companies",
        type=str,
        nargs="+",
        help="指定要导出的公司列表（可选，默认导出所有公司）"
    )
    
    args = parser.parse_args()
    
    # 解析日期
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = date.fromisoformat(args.start_date)
        except ValueError:
            print(f"❌ 无效的开始日期格式: {args.start_date}，请使用 YYYY-MM-DD")
            return 1
    if args.end_date:
        try:
            end_date = date.fromisoformat(args.end_date)
        except ValueError:
            print(f"❌ 无效的结束日期格式: {args.end_date}，请使用 YYYY-MM-DD")
            return 1
    
    success = export_to_google_sheets(
        db_path=args.db_path,
        spreadsheet_id=args.spreadsheet_id,
        worksheet_name=args.worksheet_name,
        credentials_path=args.credentials,
        create_new=args.create_new,
        start_date=start_date,
        end_date=end_date,
        companies=args.companies
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
