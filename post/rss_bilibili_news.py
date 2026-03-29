import os
import feedparser
from dotenv import load_dotenv

class BilibiliHotSearchParser:
    """
    解析 Bilibili 热搜 RSS 的解析器类
    """
    def __init__(self):
        # 加载环境变量
        load_dotenv(dotenv_path=".env")
        self.rss_url = os.getenv("RSS_BILIBILI_NEWS")

    def fetch(self):
        """
        核心方法：获取热搜数据
        """
        if not self.rss_url:
            print("错误：未在 .env 中找到 RSS_BILIBILI_NEWS 配置")
            return []

        # 解析 RSS
        feed = feedparser.parse(self.rss_url)
        
        hot_items = []
        
        # 提取前 10 条热搜 (B站热搜通常固定返回 10 条)
        for entry in feed.entries[:10]:
            item_data = {
                "title": entry.title,
                "link": entry.link
            }
            hot_items.append(item_data)

        return hot_items

# --- 测试代码 ---
if __name__ == "__main__":
    # 请确保你的 .env 文件中有 RSS_BILIBILI_NEW=http://...
    
    parser_instance = BilibiliHotSearchParser()
    hot_results = parser_instance.fetch()
    
    print(f"--- Bilibili 热搜 (共 {len(hot_results)} 条) ---")
    if hot_results:
        import json
        print(json.dumps(hot_results, indent=4, ensure_ascii=False))
        with open("data/bilibili_hot.json", "w", encoding="utf-8") as f:
            json.dump(hot_results, f, ensure_ascii=False, indent=2)