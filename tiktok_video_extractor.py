#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok Video Extractor
集成 API 调用、JSON 解析、结构化输出的完整脚本
"""
import http.client
import json
import datetime
import re
import traceback
from typing import List, Dict, Optional


class TikTokExtractor:
    """TikTok 视频数据提取器"""
    
    API_HOST = "tiktok-api23.p.rapidapi.com"
    API_KEY = "8d120f3cf8msh03e3f63d9190a01p1102bejsn723218ffa275"
    REQUEST_TIMEOUT = 15
    
    def __init__(self, api_key: Optional[str] = None, api_host: Optional[str] = None):
        """初始化提取器"""
        self.api_key = api_key or self.API_KEY
        self.api_host = api_host or self.API_HOST
    
    def fetch_user_videos(self, sec_uid: str, count: int = 1, cursor: int = 0) -> Dict:
        """
        获取用户视频数据
        
        Args:
            sec_uid: TikTok 用户的 secUid
            count: 获取视频数量
            cursor: 分页游标
        
        Returns:
            API 响应（已解析为 dict）
        """
        try:
            conn = http.client.HTTPSConnection(self.api_host, timeout=self.REQUEST_TIMEOUT)
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.api_host
            }
            
            path = f"/api/user/posts?secUid={sec_uid}&count={count}&cursor={cursor}"
            conn.request("GET", path, headers=headers)
            res = conn.getresponse()
            data = res.read()
            
            # 尝试解析 JSON
            try:
                return json.loads(data.decode('utf-8', errors='replace'))
            except Exception:
                return {"raw": data.decode('utf-8', errors='replace')}
        except Exception as e:
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    def extract_videos_from_response(self, api_response: Dict) -> List[Dict]:
        """
        从 API 响应中提取视频列表
        
        Args:
            api_response: API 返回的原始 JSON
        
        Returns:
            提取的视频列表，每个视频包含 {time, title, text}
        """
        videos = []
        
        def collect_video_entries(obj):
            """递归收集视频对象"""
            if isinstance(obj, dict):
                # 判断是否为视频条目（含 createTime 和 id/videoID）
                if 'createTime' in obj and ('id' in obj or 'videoID' in obj):
                    videos.append(obj)
                for v in obj.values():
                    collect_video_entries(v)
            elif isinstance(obj, list):
                for item in obj:
                    collect_video_entries(item)
        
        collect_video_entries(api_response)
        
        # 提取关键字段
        results = []
        seen = set()
        
        for v in videos:
            # 时间戳转换
            ts = v.get('createTime')
            if isinstance(ts, (int, float)):
                try:
                    t = datetime.datetime.utcfromtimestamp(int(ts)).isoformat() + 'Z'
                except Exception:
                    t = str(ts)
            else:
                t = str(ts)
            
            # 提取文本
            text = v.get('desc') or ''
            if not text and isinstance(v.get('contents'), list) and len(v.get('contents')) > 0:
                text = v['contents'][0].get('desc', '')
            
            # 提取标题
            title = v.get('title') or (v.get('music') or {}).get('title') or (v.get('author') or {}).get('nickname') or ''
            
            # 提取链接（优先级：playAddr > downloadAddr > ''）
            link = ''
            video_info = v.get('video') or {}
            if isinstance(video_info, dict):
                # 尝试从 playAddr 或 PlayAddrStruct 中提取
                play_addr = video_info.get('playAddr')
                if isinstance(play_addr, dict):
                    link = play_addr.get('UrlList', [None])[0] or ''
                elif isinstance(play_addr, str):
                    link = play_addr
                # 备选方案：downloadAddr
                if not link:
                    download_addr = video_info.get('downloadAddr')
                    if isinstance(download_addr, str):
                        link = download_addr
            
            # 规范化空白
            text = ' '.join(text.split())
            title = ' '.join(title.split())
            
            # 去重
            key = (t, title, text, link)
            if key not in seen:
                seen.add(key)
                results.append({
                    'time': t,
                    'title': title,
                    'text': text,
                    'link': link
                })
        
        return results
    
    def extract_from_tiktok(self, sec_uid: str, count: int = 1, cursor: int = 0, max_results: int = None) -> Dict:
        """
        完整流程：调用 API → 解析数据 → 返回结构化 JSON
        
        Args:
            sec_uid: TikTok 用户的 secUid
            count: API 查询参数（API 行为可能与数量无关）
            cursor: 分页游标
            max_results: 最多返回多少个视频（None 表示不限制）
        
        Returns:
            包含 videos 列表的字典
        """
        # 调用 API
        api_response = self.fetch_user_videos(sec_uid, count, cursor)
        
        # 检查错误
        if 'error' in api_response:
            return {
                'success': False,
                'error': api_response['error'],
                'videos': []
            }
        
        # 提取视频
        videos = self.extract_videos_from_response(api_response)
        total_parsed = len(videos)
        
        # 限制返回数量
        if max_results is not None and len(videos) > max_results:
            videos = videos[:max_results]
        
        return {
            'success': True,
            'count': len(videos),
            'total_parsed': total_parsed,
            'videos': videos,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
        }

    def extract_from_username(self, unique_id: str, max_results: int = 5) -> Dict:
        """
        使用 TikTok username (uniqueId) 获取视频的简化信息（标题、文本、时间、链接）
        依赖现有 RapidAPI 逻辑（通过另一个模块函数）而不是 secUid。
        """
        try:
            # 延迟导入，避免循环依赖
            from CompetitorScraperRapidAPI import get_posts_from_tiktok
        except Exception:
            return {
                'success': False,
                'error': 'Failed to import get_posts_from_tiktok',
                'videos': []
            }
        try:
            print(f"  [调试] 调用 get_posts_from_tiktok，username={unique_id}")
            posts = get_posts_from_tiktok(unique_id, days_ago=None)  # 最新视频，不做日期过滤
            print(f"  [调试] get_posts_from_tiktok 返回 {len(posts)} 条帖子")
        except Exception as e:
            import traceback
            print(f"  [调试] get_posts_from_tiktok 异常: {e}")
            print(f"  [调试] 异常堆栈: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'videos': []
            }
        # 规范化成标题/文本/时间/链接
        videos = []
        for p in posts[: max_results or 5]:
            # time/published_at
            t = p.get('published_at') or ''
            # text/desc
            text = (p.get('text') or '').strip()
            # 简单标题：前 40 字符或空
            title = text[:40]
            # link/post_url
            link = p.get('post_url') or ''
            videos.append({'time': t, 'title': title, 'text': text, 'link': link})
        return {
            'success': True,
            'count': len(videos),
            'videos': videos,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
        }
    
    def save_to_json(self, data: Dict, output_path: str) -> bool:
        """保存结果到 JSON 文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"ERROR: Failed to save {output_path}: {e}")
            return False


def main():
    """
    主程序示例
    
    使用方式：
    1. 导入此模块：from tiktok_video_extractor import TikTokExtractor
    2. 创建提取器实例：extractor = TikTokExtractor()
    3. 调用方法：result = extractor.extract_from_tiktok(sec_uid, count=10, max_results=10)
    4. 保存结果：extractor.save_to_json(result, 'output.json')
    
    返回字段：time, title, text, link
    """
    # 示例：使用 Paper.io 2 官方账号的 secUid
    sec_uid = "MS4wLjABAAAA97P4TH9njxqDHqdftTvymu5lJES_A9AkvN7cnelhs6D6J-6dh_GC2rlXj1OuIn6D"
    
    print("=== TikTok Video Extractor ===")
    print(f"正在提取用户视频 (secUid: {sec_uid[:30]}...)")
    
    extractor = TikTokExtractor()
    # 注意：count 参数可能不控制返回数量；使用 max_results 限制
    result = extractor.extract_from_tiktok(sec_uid, count=1, max_results=1)
    
    print(f"\n成功: {result['success']}")
    print(f"视频数: {result['count']}")
    if result.get('total_parsed'):
        print(f"API 返回总数: {result['total_parsed']}")
    
    if result['success'] and result['videos']:
        print("\n提取的视频:")
        for i, v in enumerate(result['videos'], 1):
            print(f"\n[{i}] 时间: {v['time']}")
            print(f"    标题: {v['title']}")
            print(f"    文本: {v['text'][:60]}...")
            if v['link']:
                print(f"    链接: {v['link'][:80]}...")
    
    # 保存到 JSON
    output_path = 'tiktok_videos_output.json'
    if extractor.save_to_json(result, output_path):
        print(f"\n✓ 结果已保存到: {output_path}")
    
    return result


if __name__ == '__main__':
    main()
