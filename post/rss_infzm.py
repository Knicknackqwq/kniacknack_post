import os
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

class InfzmParser:
    """
    解析 南方周末 RSS 的解析器类
    """
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        self.rss_url = os.getenv("RSS_INFZM")

    def _extract_description(self, html_content):
        """
        内部方法：从 HTML 中提取 <blockquote class="nfzm-bq"> 的内容
        """
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        # 寻找特定类名的 blockquote
        bq_tag = soup.find('blockquote', class_='nfzm-bq')
        
        if bq_tag:
            # 提取纯文本并去除两端空格
            return bq_tag.get_text(strip=True)
        return None

    def fetch(self):
        """
        核心方法：获取南方周末最新的 5 条内容
        :return: list (包含解析后字典的列表)
        """
        # 解析 RSS 源
        feed = feedparser.parse(self.rss_url)
        
        results = []
        
        # 仅处理前 10 条数据
        for entry in feed.entries[:5]:
            # 处理描述字段，仅保留 blockquote 里的文字
            clean_desc = self._extract_description(entry.summary)
            
            item_data = {
                "title": entry.title,
                "author": entry.get('author', "infzm"),
                "pubDate": entry.get('published', "None time"),
                "description": clean_desc,
                "link": entry.link
            }
            results.append(item_data)

        return results

# # --- 测试代码 ---
# if __name__ == "__main__":
#     # 模拟环境：如果你本地测试没有 .env，可以临时取消下面一行的注释
#     # os.environ["RSS_INFZM"] = "http://127.0.0.1:1200/infzm/1"
    
#     parser_instance = InfzmParser()
#     news_list = parser_instance.fetch()
    
#     print(f"--- 南方周末-推荐 (共获取 {len(news_list)} 条) ---")
    
#     if news_list:
#         import json
#         with open("data/infzm.json", "w", encoding="utf-8") as f:
#             json.dump(news_list, f, ensure_ascii=False, indent=2)
#         for item in news_list:
#             print(json.dumps(item, indent=4, ensure_ascii=False))
        