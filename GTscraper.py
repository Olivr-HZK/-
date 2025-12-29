import pandas as pd
from playwright.sync_api import sync_playwright
import time


def scrape_with_sidebar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,args=[
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage', # 核心：解决 Docker 环境内存超时问题
                ]
        )
        context = browser.new_context(
            proxy={"server": "http://host.docker.internal:7890"}, #后续修改
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        target_url = "https://trends.google.com/trending?geo=US&hours=168&status=active&sort=search-volume"
        print(f"[*] 开始执行自动化侦察: {target_url}")
        
        page.goto(target_url, timeout=60000, wait_until="load") 


        # 1. 定位所有趋势行
        try:
            page.wait_for_selector('tr[data-row-id]', timeout=15000)
            rows = page.query_selector_all('tr[data-row-id]')
            print(f"[*] 发现 {len(rows)} 条趋势，开始逐一穿透侧边栏...")
        except:
            print("[-] 未能加载列表，请检查网络。")
            return

        all_data = []

        # 2. 遍历每一行并触发点击
        for i in range(len(rows)):
            try:
                # 重新获取行引用（防止 DOM 刷新导致元素失效）
                current_row = page.query_selector_all('tr[data-row-id]')[i]
                
                # 提取基本信息
                cells = current_row.query_selector_all('td')
                keyword = cells[1].inner_text().split('\n')[0]
                print(f"[>] 正在处理关键词: {keyword}")

                # 执行点击动作触发侧边栏
                current_row.click()
                
                # 等待侧边栏容器 (EMz5P) 出现并确保内容非空
                # 注意：Google 渲染侧边栏有动画延迟
                page.wait_for_selector('div.EMz5P', timeout=10000)
                time.sleep(1) # 给数据加载留一点缓冲

                # 3. 抓取侧边栏内的文章链接
                # 根据你的截图，文章在 div.EMz5P 内部的 a 标签中
                sidebar = page.query_selector('div.EMz5P')
                links = sidebar.query_selector_all('a[href^="http"]') # 只要 http 开头的链接
                
                article_links = []
                for link in links:
                    url = link.get_attribute('href')
                    # 过滤掉 Google 内部跳转链接，只保留新闻原文链接（可选）
                    if "google.com" not in url or "url?sa=t" in url:
                        article_links.append(url)
                
                # 去重后的链接列表
                unique_links = list(set(article_links))
                
                all_data.append({
                    "Rank": i + 1,
                    "Keyword": keyword,
                    "Search Volume": cells[2].inner_text().strip(),
                    "Article Links": "\n".join(unique_links) # 放入 CSV 时用换行符分隔
                })
                
                print(f"   - 抓取到 {len(unique_links)} 条关联新闻")

            except Exception as e:
                print(f"   [-] 处理第 {i+1} 行时出错: {e}")
                continue

        # 4. 保存结果
        df = pd.DataFrame(all_data)
        df.to_csv("/app/output/google_trends_raw.csv", index=False)
        print("\n[*] 任务完成！数据已保存至 google_trends_full_data.csv")

        browser.close()

if __name__ == "__main__":
    scrape_with_sidebar()