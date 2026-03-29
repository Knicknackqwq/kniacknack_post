import os
import re
import json
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import timezone
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

class TldrParser:
    """
    解析 TLDR Newsletter (Kill-the-newsletter 格式)
    """
    def __init__(self):
        load_dotenv()
        self.new_items_text = ""

    def _unify_date(self, date_str):
        """统一日期格式为 ISO 8601 UTC"""
        if not date_str:
            return "1970-01-01T00:00:00Z"
        dt = parser.parse(date_str)
        utc_dt = dt.astimezone(timezone.utc).replace(microsecond=0)
        return utc_dt.isoformat().replace("+00:00", "Z")

    def _is_valid_article(self, title_text):
        """
        判断是否为有效的新闻条目（含阅读时间、Repo或Launch等标识）
        同时剔除广告和赞助内容
        """
        # 排除关键词
        exclude_keywords = ["Sponsor", "Advertise", "Sign Up", "Unsubscribe", "Together With"]
        if any(key.lower() in title_text.lower() for key in exclude_keywords):
            return False
        
        # 包含标识符则视为有效内容
        valid_patterns = [
            r"minute read", 
            r"GitHub Repo", 
            r"Product Launch", 
            r"Tool",
            r"\(.*\)" # 通常包含在括号内的标识
        ]
        return any(re.search(pattern, title_text, re.IGNORECASE) for pattern in valid_patterns)

    def _extract_clean_text(self, html_content):
        """
        从复杂的 HTML 中提取新闻摘要，每条摘要占一行
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        summaries = []

        # TLDR 的结构通常是 <a><strong>Title (x minute read)</strong></a>
        # 后面紧跟着包含摘要的 <span> 或文本
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text().strip()
            
            # 1. 验证标题是否符合新闻条目特征
            if self._is_valid_article(title):
                # 2. 寻找摘要：通常在 link 的父级容器或后续兄弟节点中
                # 逻辑：寻找当前 <a> 标签之后最接近的 text 块
                parent_div = link.find_parent('div', class_='text-block')
                if parent_div:
                    # 获取该 div 内除了标题以外的文字
                    full_text = parent_div.get_text(separator=" ", strip=True)
                    # 去掉标题部分，剩下的就是摘要
                    summary = full_text.replace(title, "").strip()
                    if summary:
                        # 清理多余空格和换行
                        summary = re.sub(r'\s+', ' ', summary)
                        summaries.append(summary)
        
        return "\n".join(summaries)

    def parse(self, last_date_str: str):
        """
        执行解析逻辑
        :return: (cleaned_text, updated_last_date)
        """
        rss_url= os.getenv("RSS_TLDR")
        if not rss_url:
            print("Error: RSS_TLDR URL not provided.")
            return "", last_date_str

        last_date_unified = self._unify_date(last_date_str)
        feed = feedparser.parse(rss_url)
        
        all_new_text = []
        current_latest_str = last_date_unified
        num=0
        # Atom feed 的 entries 通常按时间从新到旧
        for entry in feed.entries:
            # 获取发布时间 (Atom 常用 published)
            entry_pub_date = entry.get("published") or entry.get("updated")
            entry_date_unified = self._unify_date(entry_pub_date)

            if entry_date_unified > last_date_unified:
                # 提取 HTML 内容内容
                html_content = entry.get("content", [{}])[0].get("value", "")
                if not html_content:
                    html_content = entry.get("summary", "")
                
                # 清洗并整理文本
                cleaned_text = self._extract_clean_text(html_content)
                if cleaned_text:
                    all_new_text.append(cleaned_text)
                    num+=1

                if entry_date_unified > current_latest_str:
                    current_latest_str = entry_date_unified
            else:
                break

        # 将多个 entry 的内容合并，并确保每个摘要占一行
        final_text = "\n".join(all_new_text)
        return final_text, current_latest_str




class TldrLlm:
    """
    Tldr_llm 类：负责调用 DeepSeek API 对简报内容进行结构化总结
    """
    def __init__(self, prompt_file=r"tldr_prompt.json"):
        # 1. 加载环境变量
        load_dotenv()
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_URL") 
        
        # 2. 初始化 OpenAI 客户端 (DeepSeek 兼容 OpenAI 格式)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # 3. 读取外部 Prompt 文件
        self.system_prompt = self._load_prompt(prompt_file)

    def _load_prompt(self, file_path):
        """内部方法：从 json 文件读取 Prompt 配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"核心错误：无法读取 Prompt 文件 {file_path}。错误详情: {e}")
            return None

    def get_structured_summary(self, raw_tldr_text):
        """
        核心方法：发送文本至大模型并获取 JSON 输出
        :param raw_tldr_text: 整理好的原始文本字符串
        :return: tldr_text (list of dicts) 或空列表
        """
        if not raw_tldr_text or not raw_tldr_text.strip():
            return []
        if not self.system_prompt:
            return []
        try:
            # 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model="deepseek-chat",  
                messages=[
                    self.system_prompt,
                    {"role": "user", "content": raw_tldr_text}
                ],
                # 开启 JSON Mode (DeepSeek 支持此参数，确保返回的是合法 JSON)
                response_format={'type': 'json_object'},
                temperature=0.3, # 降低随机性
                stream=False
            )

            # 获取返回内容
            content = response.choices[0].message.content
            
            # 解析字符串为 JSON 对象
            tldr_json = json.loads(content)
            
            # 如果返回的是 {"news": [...]} 结构，自动提取列表部分
            if isinstance(tldr_json, dict) and len(tldr_json) == 1:
                key = list(tldr_json.keys())[0]
                if isinstance(tldr_json[key], list):
                    return tldr_json[key]
            
            return tldr_json

        except Exception as e:
            # 捕获所有错误（API 超时、错误码、解析失败等）
            print(f"--- LLM 调用出错 ---")
            if hasattr(e, 'status_code'):
                print(f"错误码: {e.status_code}")
            print(f"错误信息: {str(e)}")
            print(f"-------------------")
            return []

# --- 测试代码 ---
if __name__ == "__main__":
    # 模拟主程序调用
    parser_instance = TldrParser()
    llm=TldrLlm()
    # 模拟历史日期
    test_last_date = "2026-03-24T13:23:35.565Z"
    # 从环境变量读取 URL
    
    result_text, next_date = parser_instance.parse(test_last_date, test_url)
    
    print(f"--- Updated Date: {next_date} ---")
    print("--- Extracted Summaries ---")
    print(result_text)
    result = llm.get_structured_summary(result_text)
    print("LLM 结构化输出:")    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    with open("data/tldr_list.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

