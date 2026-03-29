import feedparser
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import timezone

class BilibiliDynamicParser:
    """
    解析 Bilibili 动态 RSS 
    """
    def __init__(self):
        self.new_items = []

    def _unify_date(self, date_str):
        """
        将输入的日期字符串统一转换为 ISO 8601 格式的 UTC 时间字符串
        """
        dt = parser.parse(date_str)
        # 强制转为 UTC 时区并抹除微秒
        utc_dt = dt.astimezone(timezone.utc).replace(microsecond=0)
        return utc_dt.isoformat().replace("+00:00", "Z")

    def _extract_data(self, entry):
        """
        内部方法：从 RSS entry 中提取并清洗字段
        """
        soup = BeautifulSoup(entry.summary, 'html.parser')
        
        # 1. 提取 description：entry.summary 中的全部纯文本（去掉所有 HTML 标签）
        description = soup.get_text().strip()

        # 2. 提取 image_url (选取第一个 img 标签)
        img_tag = soup.find('img')
        image_url = ""
        if img_tag and img_tag.get('src'):
            image_url = img_tag['src']
            if image_url.startswith('//'):
                image_url = "https:" + image_url
            if '.webp' in image_url:
                image_url = image_url.replace('.webp', '.jpg')

        return {
            "title": entry.title,
            "author": entry.author if 'author' in entry else "Not known",
            "pubDate": entry.published,
            "description": description,
            "image_url": image_url,
            "link": entry.link
        }

    def parse(self, last_date_str: str, rss_url: str):
        """
        解析指定 URL 并在 last_date 之后更新的内容
        """
        last_date_unified = self._unify_date(last_date_str)
        feed = feedparser.parse(rss_url)
        self.new_items = []
        current_latest_str = last_date_unified

        for entry in feed.entries:
            entry_date_unified = self._unify_date(entry.published)
            
            if entry_date_unified > last_date_unified:
                item_data = self._extract_data(entry)
                self.new_items.append(item_data)
                if entry_date_unified > current_latest_str:
                    current_latest_str = entry_date_unified
            else:
                # 遇到旧内容，跳出
                break
        return self.new_items, current_latest_str

# # --- 测试代码 ---
# if __name__ == "__main__":
#     # 模拟历史记录中的时间
#     test_last_date = "Wed, 04 Feb 2026 04:31:13 GMT" 
#     # 填入你自己的 RSSHub 地址进行测试
#     test_url = "http://127.0.0.1:1200/bilibili/user/dynamic/650533600" 
    
#     parser_instance = BilibiliDynamicParser()
#     next_date = parser_instance.parse(test_last_date, test_url)
#     print(f"下次运行使用的日期: {next_date}")
#     test_last_date = "Wed, 18 Mar 2026 5:11:38 GMT" 
#     # 填入你自己的 RSSHub 地址进行测试
#     test_url = "http://127.0.0.1:1200/bilibili/user/dynamic/25876945" 
    
#     parser_instance = BilibiliDynamicParser()
#     next_date = parser_instance.parse(test_last_date, test_url)
#     print(f"下次运行使用的日期: {next_date}")

    
    
        