import os
import json
from openai import OpenAI
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from dateutil import parser
from datetime import timezone
from email.utils import parsedate_to_datetime

class ChangelogNightlyParser:
    def __init__(self):
        load_dotenv()
        self.rss_url = os.getenv("RSS_CHANGELOG_NIGHT")

    def _unify_date(self, date_str):
        if not date_str: return "1970-01-01T00:00:00Z"
        try:
            dt = parser.parse(date_str)
        except:
            dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _clean_content(self, html_content):
        """
        修复版脱水逻辑：
        不再依赖链接包含 "github.com"，而是通过 CSS Class 定位数据块
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        repo_blocks = []

        # 1. 核心特征：Changelog 每个项目都在 class="repository" 的 div 里
        repo_divs = soup.find_all('div', class_='repository')

        for repo in repo_divs:
            # --- 提取标题和链接 ---
            # 标题在 <h3> 标签内
            h3_tag = repo.find('h3')
            if not h3_tag:
                continue
            
            a_tag = h3_tag.find('a')
            repo_name = a_tag.get_text(strip=True) if a_tag else h3_tag.get_text(strip=True)
            repo_url = a_tag['href'] if a_tag else ""

            # --- 提取统计信息 (Stars & Language) ---
            # 在 <tr class="stats"> 的 <p> 标签里
            stats_text = ""
            stats_tr = repo.find('tr', class_='stats')
            if stats_tr:
                stats_p = stats_tr.find('p')
                if stats_p:
                    # 总星数、今日增长星数、语言
                    stats_text = " ".join(stats_p.get_text().split())

            # --- 提取简介 ---
            # 在 <tr class="about"> 的 <p> 标签里
            description = ""
            about_tr = repo.find('tr', class_='about')
            if about_tr:
                desc_p = about_tr.find('p')
                if desc_p:
                    description = desc_p.get_text(strip=True)

            # --- 组合成 JSON 格式 ---
            block = {
                "Repo": repo_name,
                "Stats": stats_text,
                "Desc": description,
                "Link": repo_url,
            }
            repo_blocks.append(block)

        return repo_blocks

    def parse(self, last_date_str: str):
        if not self.rss_url:
            print("错误：未在 .env 中找到 RSS_CHANGELOG_NIGHT 配置")
            return "", last_date_str

        last_date_unified = self._unify_date(last_date_str)
        feed = feedparser.parse(self.rss_url)
        
        all_output_data = []
        current_latest_str = last_date_unified

        for entry in feed.entries:
            entry_date_unified = self._unify_date(entry.published)
            
            if entry_date_unified > last_date_unified:
                # 获取 HTML 源码，Atom 格式通常在 content[0].value
                raw_html = entry.content[0].value
                extracted_blocks = self._clean_content(raw_html)
                
                if extracted_blocks:
                    all_output_data.extend(extracted_blocks)
                
                if entry_date_unified > current_latest_str:
                    current_latest_str = entry_date_unified
            else:
                break 

        return all_output_data, current_latest_str
    
class ChangelogNightLlm:
    """
    ChangelogNightLlm 类：负责将 GitHub 热门项目列表转化为一段严谨、学术风格的自然文本简报
    """
    def __init__(self, prompt_file="changelog_night_prompt.json"):
        # 1. 加载配置
        load_dotenv()
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_URL")
        
        # 2. 初始化 DeepSeek 客户端
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # 3. 加载系统 Prompt
        self.system_prompt = self._load_prompt(prompt_file)

    def _load_prompt(self, file_path):
        """内部方法：从 json 读取 prompt"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：无法读取 {file_path}，将使用默认配置。错误: {e}")
            return {"role": "system", "content": "You are a professional technical editor."}

    def _prepare_minimal_text(self, json_data):
        """
        内部方法：从原始 JSON 中仅提取 Repo 和 Desc
        """
        if not json_data or not isinstance(json_data, list):
            return ""
        
        lines = []
        for item in json_data:
            repo = item.get("Repo", "Unknown Repo")
            desc = item.get("Desc", "No description provided.")
            lines.append(f"Repo: {repo} | Desc: {desc}")
        
        return "\n".join(lines)

    def get_narrative_digest(self, changelog_night_text):
        """
        核心方法：发送提取后的文本，返回自然语言简报
        :param changelog_night_text: 解析好的 JSON 列表数据
        :return: changelog_digest (string)
        """
        # 1. 数据脱水与校验
        input_text = self._prepare_minimal_text(changelog_night_text)
        if not input_text:
            return ""

        try:
            # 2. 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    self.system_prompt,
                    {"role": "user", "content": f"请基于以下仓库列表生成简报：\n{input_text}"}
                ],
                # 针对自然文本生成的参数优化
                temperature=0.4, 
                max_tokens=600,
                stream=False
            )

            # 3. 提取结果
            changelog_digest = response.choices[0].message.content
            return changelog_digest.strip()

        except Exception as e:
            # 4. 错误处理与打印
            print(f"--- DeepSeek API 调用异常 ---")
            if hasattr(e, 'status_code'):
                print(f"错误码: {e.status_code}") 
            print(f"错误详情: {str(e)}")
            print(f"---------------------------")
            return "" 



# # --- 测试代码 ---
# if __name__ == "__main__":
#     # 设一个较旧的时间点以确保能抓到数据
#     test_date = "2026-03-25T01:59:38.106Z"
#     parser_instance = ChangelogNightlyParser()
    
#     # 也可以手动测试你复制的那段 HTML 字符串
#     # test_html = """ ... """
#     # print(parser_instance._clean_content(test_html))

#     text_out, next_date = parser_instance.parse(test_date)
#     print(f"--- 状态: 提取完成 ---")
#     print(f"--- 更新时间: {next_date} ---")
#     print(f"--- 项目组数: {len(text_out)} ---")
#     print(f"--- 类型: {type(text_out)} ---")
#     with open("data/changelog_night_list.json", "w", encoding="utf-8") as f:
#         f.write(json.dumps(text_out, ensure_ascii=False, indent=2))



# --- 测试代码 ---
if __name__ == "__main__":
    # 模拟输入数据
    test_json = []
    with open("data/changelog_night_list.json", "r", encoding="utf-8") as f:
        test_json = json.load(f)
    
    llm_handler = ChangelogNightLlm()
    digest = llm_handler.get_narrative_digest(test_json)
    
    if digest:
        print("生成的简报内容：")
        print(digest)
        with open("data/changelog_digest.txt", "w", encoding="utf-8") as f:
            f.write(digest)
    else:
        print("简报生成失败。")