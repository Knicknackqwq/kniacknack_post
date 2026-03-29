import os
import json
import feedparser
from dateutil import parser
from datetime import timezone
from dotenv import load_dotenv

class RSSBatchParser:
    """
    解析 DeepLearning.AI 'The Batch' 系列 RSS
    """
    def __init__(self):
        self.new_items = []
        self.rss_url = None 

    def _unify_date(self, date_str):
        """
        将输入的日期字符串统一转换为 ISO 8601 格式的 UTC 时间字符串 (结尾带 Z)
        """
        if not date_str:
            return "1970-01-01T00:00:00Z"
        dt = parser.parse(date_str)
        # 强制转为 UTC 时区并抹除微秒
        utc_dt = dt.astimezone(timezone.utc).replace(microsecond=0)
        return utc_dt.isoformat().replace("+00:00", "Z")

    def _extract_data(self, entry):
        """
        内部方法：从 RSS entry 中提取字段，并将 category 合并为 description
        """
        # 提取 category：feedparser 将 <category> 存储在 tags 列表中
        tags = entry.get("tags", [])
        categories = [tag.get("term") for tag in tags if tag.get("term")]
        
        # 将所有 category 用空格连接，如果没有则为 None
        description_val = " ".join(categories) if categories else None

        return {
            "title": entry.get("title", ""),
            "author": entry.get("author", "Not known"),
            "pubDate": entry.get("published", ""),
            "description": description_val,
            "link": entry.get("link", "")
        }

    def parse(self,rss_url: str,last_date_str: str):
        """
        解析指定 RSS URL 并在 last_date 之后更新的内容
        """
        load_dotenv()
        self.rss_url = os.getenv(rss_url)
       

        last_date_unified = self._unify_date(last_date_str)
        feed = feedparser.parse(self.rss_url)
        
        self.new_items = []
        current_latest_str = last_date_unified

        # feed.entries 通常按时间从新到旧排序
        for entry in feed.entries:
            entry_pub_date = entry.get("published", "")
            entry_date_unified = self._unify_date(entry_pub_date)
            
            if entry_date_unified > last_date_unified:
                item_data = self._extract_data(entry)
                self.new_items.append(item_data)
                
                # 记录本次抓取到的最新日期
                if entry_date_unified > current_latest_str:
                    current_latest_str = entry_date_unified
            else:
                # 遇到旧内容，停止遍历
                break

        return self.new_items, current_latest_str

# # --- 测试代码 ---
# if __name__ == "__main__":
#     # 模拟主模块 knicknack_post.py 的调用逻辑
    
#     # 1. 初始化解析器
#     parser_instance = RSSBatchParser()
    
#     # 2. 从 .env 获取不同的 URL

    
#     # 3. 模拟历史日期
#     test_last_date = "19 Mar 2026 15:05:45 GMT"
    
#     # 测试解析 Weekly
#     print("--- Testing Weekly ---")
#     items_w, next_date_w = parser_instance.parse("RSS_BATCH_WEEKLY", test_last_date)
#     print(f"Weekly 新条目: {len(items_w)}, 下次日期: {next_date_w}")
#     with open("data/batch_week.json", "w", encoding="utf-8") as f:
#         json.dump(items_w, f, ensure_ascii=False, indent=2)
    
#     # 测试解析 Letter
#     print("\n--- Testing Letter ---")
#     items_l, next_date_l = parser_instance.parse("RSS_BATCH_LETTER", test_last_date)
#     print(f"Letter 新条目: {len(items_l)}, 下次日期: {next_date_l}")
#     with open("data/batch_letter.json", "w", encoding="utf-8") as f:
#         json.dump(items_l, f, ensure_ascii=False, indent=2)