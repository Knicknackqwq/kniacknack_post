import os
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import timezone
from dotenv import load_dotenv

class RSSRuanyifengParser:
    """
    解析 阮一峰的网络日志 RSS
    """
    def __init__(self):
        load_dotenv()
        self.new_items = []
        self.feed = feedparser.parse(os.getenv("RSS_RUANYIFENG"))

    def _unify_date(self, date_str):
        """
        将输入的日期字符串统一转换为 ISO 8601 格式的 UTC 时间字符串
        """
        if not date_str:
            return "1970-01-01T00:00:00Z"
        dt = parser.parse(date_str)
        utc_dt = dt.astimezone(timezone.utc).replace(microsecond=0)
        return utc_dt.isoformat().replace("+00:00", "Z")

    def _extract_data(self, entry):
        """
        内部方法：提取字段并清洗 description（取前15个字）
        """
        raw_html = entry.get("summary", "")
        soup = BeautifulSoup(raw_html, 'html.parser')
        clean_text = soup.get_text().strip().replace('\n', ' ')
        
        if clean_text:
            description_val = clean_text[:30] + "......"
        else:
            description_val = None

        return {
            "title": entry.get("title", ""),
            "author": "ruanyifeng", 
            "pubDate": entry.get("published", ""),
            "description": description_val,
            "link": entry.get("link", "")
        }

    def parse(self, last_date_str: str):
        """
        解析 RSS 并在 last_date 之后更新的内容
        :param last_date_str: 上次记录的日期
        :param rss_url: 主模块从 .env 传入的 RSS_RUANYIFENG 路径
        """
        

        last_date_unified = self._unify_date(last_date_str)
        
        
        self.new_items = []
        current_latest_str = last_date_unified

        for entry in self.feed.entries:
            entry_pub_date = entry.get("published", "")
            entry_date_unified = self._unify_date(entry_pub_date)
            
            if entry_date_unified > last_date_unified:
                item_data = self._extract_data(entry)
                self.new_items.append(item_data)
                
                if entry_date_unified > current_latest_str:
                    current_latest_str = entry_date_unified
            else:
                break

        return self.new_items, current_latest_str

# --- 测试代码 ---
if __name__ == "__main__":
    # 模拟主模块逻辑
    parser_instance = RSSRuanyifengParser()
    
   
    # 模拟历史日期
    test_last_date = "Fri, 20 Mar 2026 07:59:16 +0800"
    
    items, next_date = parser_instance.parse(test_last_date)
    
    print(f"抓取到新日志数量: {len(items)}")
    print(f"下次运行使用的日期: {next_date}")
    
    if items:
        import json
        with open("data/ruanyifeng.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        for item in items:
            print(json.dumps(item, indent=4, ensure_ascii=False))
       