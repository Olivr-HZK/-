"""
竞品监控历史数据库
按日期和公司存储爬取数据和AI分析结果
"""
import json
import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pathlib import Path


class CompetitorHistoryDB:
    """竞品历史数据库，使用JSON文件存储"""
    
    def __init__(self, db_dir: str = None):
        """
        初始化数据库
        
        Args:
            db_dir: 数据库目录路径，默认为 /app/db 或项目根目录下的 db
        """
        if db_dir is None:
            db_dir = os.environ.get("COMPETITOR_DB_DIR", "/app/db")
            if not os.path.exists(db_dir):
                alt_dir = os.path.join(os.path.dirname(__file__), "db")
                if os.path.exists(alt_dir):
                    db_dir = alt_dir
                else:
                    # 创建默认目录
                    db_dir = alt_dir
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)
        
        # 数据目录结构
        self.raw_data_dir = os.path.join(self.db_dir, "raw_data")  # 原始爬取数据
        self.ai_analysis_dir = os.path.join(self.db_dir, "ai_analysis")  # AI分析结果
        self.daily_report_dir = os.path.join(self.db_dir, "daily_report")  # 日报JSON
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.ai_analysis_dir, exist_ok=True)
        os.makedirs(self.daily_report_dir, exist_ok=True)
    
    def _get_date_str(self, dt: Optional[date] = None) -> str:
        """获取日期字符串 YYYY-MM-DD"""
        if dt is None:
            dt = date.today()
        return dt.strftime("%Y-%m-%d")
    
    def _get_file_path(self, company: str, date_str: str, is_ai: bool = False) -> str:
        """
        获取存储文件路径
        
        Args:
            company: 公司名称
            date_str: 日期字符串 YYYY-MM-DD
            is_ai: 是否为AI分析数据
        
        Returns:
            文件路径
        """
        # 清理公司名称，用于文件名（移除特殊字符）
        safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company = safe_company.replace(' ', '_').lower()
        
        base_dir = self.ai_analysis_dir if is_ai else self.raw_data_dir
        filename = f"{safe_company}_{date_str}.json"
        return os.path.join(base_dir, filename)
    
    def save_raw_data(
        self, 
        company: str, 
        platforms_data: List[Dict[str, Any]], 
        fetch_date: Optional[date] = None
    ) -> str:
        """
        保存原始爬取数据
        
        Args:
            company: 公司名称
            platforms_data: 各平台的数据列表，每个元素包含：
                - platform_type: 平台类型（twitter, tiktok, youtube, facebook等）
                - game: 游戏名称（可选）
                - url: 账号URL
                - posts: 帖子列表
                - posts_count: 帖子数量
                - fetched_at: 抓取时间
            fetch_date: 抓取日期，默认为今天
        
        Returns:
            保存的文件路径
        """
        date_str = self._get_date_str(fetch_date)
        file_path = self._get_file_path(company, date_str, is_ai=False)
        
        # 加载已有数据（如果存在）
        existing_data = self.load_raw_data(company, fetch_date) or {}
        
        # 合并数据（按平台组织）
        platforms_dict = existing_data.get("platforms", {})
        
        for platform_data in platforms_data:
            platform_type = platform_data.get("platform_type", "unknown")
            game = platform_data.get("game")
            
            # 平台+游戏的组合键
            key = f"{platform_type}"
            if game:
                key = f"{platform_type}_{game}"
            
            platforms_dict[key] = {
                "platform_type": platform_type,
                "game": game,
                "url": platform_data.get("url", ""),
                "username": platform_data.get("username"),
                "page_id": platform_data.get("page_id"),
                "channel_id": platform_data.get("channel_id"),
                "posts": platform_data.get("posts", []),
                "posts_count": platform_data.get("posts_count", 0),
                "fetched_at": platform_data.get("fetched_at") or datetime.utcnow().isoformat() + "Z",
            }
        
        # 构建完整数据结构
        data = {
            "company": company,
            "date": date_str,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "platforms": platforms_dict,
        }
        
        # 保存到文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已保存原始数据: {file_path}")
            return file_path
        except Exception as exc:
            print(f"  ❌ 保存原始数据失败: {exc}")
            return ""
    
    def load_raw_data(self, company: str, fetch_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        加载原始爬取数据
        
        Args:
            company: 公司名称
            fetch_date: 日期，默认为今天
        
        Returns:
            数据字典，如果不存在则返回None
        """
        date_str = self._get_date_str(fetch_date)
        file_path = self._get_file_path(company, date_str, is_ai=False)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"  ⚠️ 加载原始数据失败: {exc}")
            return None
    
    def save_ai_analysis(
        self,
        company: str,
        ai_results: Dict[str, Any],
        analysis_date: Optional[date] = None
    ) -> str:
        """
        保存AI分析结果
        
        Args:
            company: 公司名称
            ai_results: AI分析结果字典，格式为 {title: payload, ...}
            analysis_date: 分析日期，默认为今天
        
        Returns:
            保存的文件路径
        """
        date_str = self._get_date_str(analysis_date)
        file_path = self._get_file_path(company, date_str, is_ai=True)
        
        # 构建数据结构
        data = {
            "company": company,
            "date": date_str,
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "results": ai_results,  # 保持原有的 {title: payload} 结构
        }
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已保存AI分析结果: {file_path}")
            return file_path
        except Exception as exc:
            print(f"  ❌ 保存AI分析结果失败: {exc}")
            return ""
    
    def load_ai_analysis(self, company: str, analysis_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        加载AI分析结果
        
        Args:
            company: 公司名称
            analysis_date: 日期，默认为今天
        
        Returns:
            数据字典，如果不存在则返回None
        """
        date_str = self._get_date_str(analysis_date)
        file_path = self._get_file_path(company, date_str, is_ai=True)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"  ⚠️ 加载AI分析结果失败: {exc}")
            return None
    
    def get_companies_for_date(self, target_date: Optional[date] = None, is_ai: bool = False) -> List[str]:
        """
        获取指定日期有数据的公司列表
        
        Args:
            target_date: 日期，默认为今天
            is_ai: 是否查询AI分析数据
        
        Returns:
            公司名称列表
        """
        date_str = self._get_date_str(target_date)
        base_dir = self.ai_analysis_dir if is_ai else self.raw_data_dir
        
        companies = set()
        if os.path.exists(base_dir):
            for filename in os.listdir(base_dir):
                if filename.endswith(f"_{date_str}.json"):
                    # 提取公司名称：{company}_{date}.json
                    company_part = filename.rsplit(f"_{date_str}.json", 1)[0]
                    companies.add(company_part.replace("_", " ").title())
        
        return sorted(list(companies))
    
    def get_all_dates_for_company(self, company: str, is_ai: bool = False) -> List[str]:
        """
        获取指定公司有数据的日期列表
        
        Args:
            company: 公司名称
            is_ai: 是否查询AI分析数据
        
        Returns:
            日期字符串列表（YYYY-MM-DD）
        """
        base_dir = self.ai_analysis_dir if is_ai else self.raw_data_dir
        
        # 清理公司名称
        safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_company = safe_company.replace(' ', '_').lower()
        
        dates = []
        if os.path.exists(base_dir):
            prefix = f"{safe_company}_"
            for filename in os.listdir(base_dir):
                if filename.startswith(prefix) and filename.endswith(".json"):
                    # 提取日期：{company}_YYYY-MM-DD.json
                    date_part = filename[len(prefix):-5]  # 移除前缀和.json
                    if len(date_part) == 10 and date_part.count("-") == 2:
                        dates.append(date_part)
        
        return sorted(dates, reverse=True)  # 最新日期在前


if __name__ == "__main__":
    # 简单测试
    db = CompetitorHistoryDB()
    
    # 测试保存原始数据
    test_data = [
        {
            "platform_type": "twitter",
            "game": None,
            "url": "https://x.com/test",
            "posts": [{"text": "test", "post_url": "https://x.com/test/1"}],
            "posts_count": 1,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    ]
    db.save_raw_data("Test Company", test_data)
    
    # 测试加载
    loaded = db.load_raw_data("Test Company")
    print(f"加载结果: {loaded is not None}")
