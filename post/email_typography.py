import os
import json
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import logging

class EmailTypography:
    def __init__(self, data_dir="data", template_dir="templates", template_file="email_template.html"):
        self.data_dir = data_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template_file = template_file
        self.logger = logging.getLogger(__name__)

    def _safe_load_json_list(self, filename):
        """
        统一读取逻辑：返回一个列表。
        如果文件不存在、为空或不是列表，则返回空列表 []。
        """
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.exception(f"读取 {filename} 失败")
            return []

    def _safe_load_txt(self, filename):
        """读取 LLM 生成的纯文本摘要"""
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return ""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def _normalize_item(self, item, source_type):
        """
        统一字段映射。
        增加严格截断逻辑，防止邮件源码过大被 Gmail 截断。
        """
        # 提取简介并强制截断（500字符）
        desc = item.get("description") or item.get("summary") or item.get("Desc") or ""
        clean_summary = desc[:500] + "..." if len(desc) > 500 else desc

        # Changelog 源字段映射稍微不同
        if source_type == "changelog":
            return {
                "title": item.get("Repo"),
                "author": item.get("Stats"),
                "time": "Trending",
                "summary": clean_summary,
                "image_url": None,
                "url": item.get("Link")
            }
        
        # 其他源标准映射
        return {
            "title": item.get("title"),
            "author": item.get("author", ""),
            "time": item.get("pubDate", ""),
            "summary": clean_summary,
            "image_url": item.get("image_url"), # 即使为 None，MJML 模板中已做 if 判断
            "url": item.get("link")
        }

    def render_daily_email(self):
        """
        流水线渲染逻辑
        """
        # 1. 加载热搜和 AI 摘要
        bilibili_hot = self._safe_load_json_list("bilibili_hot.json")
        changelog_digest = self._safe_load_txt("changelog_digest.txt")
        
        # 2. 待处理源配置（严格按你要求的顺序）
        source_configs = [
            ("Bilibili 动态", "bilibili_dynamic.json", "dyn"),
            ("The Batch 周报", "batch_week.json", "week"),
            ("The Batch Letter", "batch_letter.json", "letter"),
            ("TLDR 每日简报", "tldr_list.json", "tldr"),
            ("科技爱好者周刊", "ruanyifeng.json", "ruanyi"),
            ("GitHub 每日趋势", "changelog_night_list.json", "changelog"),
            ("南方周末", "infzm.json", "infzm")
        ]

        final_sources = []
        total_article_count = 0

        # 3. 逐个文件处理，转换格式
        for display_name, filename, s_type in source_configs:
            raw_list = self._safe_load_json_list(filename)
            
            if not raw_list:
                continue # 如果该列表为空，跳过该章节

            # 执行归一化
            articles = [self._normalize_item(i, s_type) for i in raw_list]

            # 针对 GitHub 趋势，如果有 AI 总结，将其作为列表第一项插入
            if s_type == "changelog" and changelog_digest:
                articles.insert(0, {
                    "title": "今日 GitHub 综述 (AI 生成)",
                    "author": "DeepSeek Assistant",
                    "time": "Summary",
                    "summary": changelog_digest,
                    "image_url": None,
                    "url": "#"
                })

            final_sources.append({
                "name": display_name,
                "articles": articles
            })
            total_article_count += len(articles)

        # 4. 组装数据并交给 Jinja2 渲染
        render_context = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_count": total_article_count,
            "bilibili_hot_search": bilibili_hot,
            "news_sources": final_sources
        }

        template = self.env.get_template(self.template_file)
        return template.render(render_context)

# if __name__ == "__main__":
#     # 本地预览测试
#     typo = EmailTypography()
#     final_html = typo.render_daily_email()
    
#     output_path = os.path.join("data", "daily_report_final.html")
#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(final_html)
#     print(f"渲染成功，预览文件已生成至: {output_path}")
    