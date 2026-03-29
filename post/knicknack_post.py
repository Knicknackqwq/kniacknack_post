import os
import json
import logging
import resend
from datetime import datetime
from dotenv import load_dotenv

from rss_bilibili_news import BilibiliHotSearchParser
from rss_bilibili_dynamic import BilibiliDynamicParser
from rss_batch import RSSBatchParser 
from rss_tldr import TldrParser,TldrLlm
from rss_ruanyifeng import RSSRuanyifengParser
from rss_changelog import ChangelogNightlyParser,ChangelogNightLlm
from rss_infzm import InfzmParser
from email_typography import EmailTypography

# # 配置日志
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KnicknackPost:
    def __init__(self):
        load_dotenv()
        self.log_file = "log.json"
        self.data_dir = "data"
        self.last_time = self._load_last_time()
        self.now_date=datetime.now()
        
        # 初始化目录
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        else:
            # 清理旧的中间文件
            for f in os.listdir(self.data_dir):
                if f.endswith((".json", ".txt", ".html")):
                    os.remove(os.path.join(self.data_dir, f))

    def _load_last_time(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_last_time(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.last_time, f, indent=4)

    def _write_data(self, filename, content):
        path = os.path.join(self.data_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            if filename.endswith(".json"):
                json.dump(content, f, ensure_ascii=False, indent=4)
            else:
                f.write(str(content))

    def run(self):
        # logging.info("🚀 启动每日情报获取任务...")

        # 1. BILIBILI 热搜 (无 last_date)
        # logging.info("获取 Bilibili 热搜...")
        hot_list = BilibiliHotSearchParser().fetch()
        self._write_data("bilibili_hot.json", hot_list)

        # 2. BILIBILI 动态
        # 假设 .env 中配置了 RSS_BILIBILI_DYN_URL
        # logging.info("获取 Bilibili 动态...")
        
        url = os.getenv("RSS_BILIBILI_DYNAMIC")
        UIDS=os.getenv("BILIBILI_USER_ID").split()
        dyn_items = []
        for uid in UIDS:
            url_uid = f"{url}{uid}"+"/hideGoods=1"
            last_date = self.last_time.get(uid, "2026-01-01T00:00:00Z")
            dyn_item, new_date = BilibiliDynamicParser().parse(last_date, url_uid)
            dyn_items.append(dyn_item)
            self.last_time[uid] = new_date
        self._write_data("bilibili_dynamic.json", dyn_items)
        

        # 3. The Batch 周报
        # logging.info("获取 The Batch 周报...")
        last_date = self.last_time.get("batch_week", "2026-01-01T00:00:00Z")
        week_items, new_date = RSSBatchParser().parse("RSS_BATCH_WEEKLY",last_date)
        self._write_data("batch_week.json", week_items)
        self.last_time["batch_week"] = new_date

        # 4. The Batch Letter
        # logging.info("获取 The Batch Letter...")
        last_date = self.last_time.get("batch_letter", "2026-01-01T00:00:00Z")
        letter_items, new_date = RSSBatchParser().parse("RSS_BATCH_LETTER", last_date)
        self._write_data("batch_letter.json", letter_items)
        self.last_time["batch_letter"] = new_date

        # 5. TLDR 每日简报 (含 LLM 处理)
        # logging.info("获取并处理 TLDR 简报...")
        last_date = self.last_time.get("tldr", "2026-01-01T00:00:00Z")
        # 假设 tldr 解析器返回的是一段大文本供 LLM 总结
        raw_tldr_text, new_date = TldrParser().parse(last_date)
        if raw_tldr_text:
            tldr_json = TldrLlm().get_structured_summary(raw_tldr_text)
            self._write_data("tldr_list.json", tldr_json)
        self.last_time["tldr"] = new_date

        # 6. 阮一峰周刊
        last_date = self.last_time.get("ruanyifeng", "2026-01-01T00:00:00Z")
        ruanyi_items, new_date = RSSRuanyifengParser.parse(last_date)
        self._write_data("ruanyifeng.json", ruanyi_items)
        self.last_time["ruanyifeng"] = new_date

        # 7. Changelog Nightly (含 LLM 处理)
        # logging.info("获取并处理 Changelog GitHub 趋势...")
        last_date = self.last_time.get("changelog", "2026-01-01T00:00:00Z")
        # 返回 (list_of_repos, raw_text_for_summary, new_date)
        repo_list, new_date = ChangelogNightlyParser().parse(last_date)
        self._write_data("changelog_night_list.json", repo_list)
        digest = ChangelogNightLlm().get_narrative_digest(repo_list)
        self._write_data("changelog_digest.txt", digest)
        self.last_time["changelog"] = new_date

        # 8. 南方周末
        # logging.info("获取南方周末动态...")
        infzm_items = InfzmParser().fetch() # 假设南周总是拿最新的10条
        self._write_data("infzm.json", infzm_items)

        # === 核心：渲染与发送 ===
        # logging.info("🎨 开始渲染邮件排版...")
        html_content = EmailTypography().render_daily_email()
        
        # 保存一份备份到 data 目录供检查
        self._write_data("daily_report_final.html", html_content)

        # logging.info("📧 正在通过 Resend 发送邮件...")
        self.send_mail(html_content)

        # 任务成功，持久化状态
        self._save_last_time()
        # logging.info("✅ 所有任务已完成！")

    def send_mail(self, html_body):
        resend.api_key = os.getenv("RESEND_API_KEY")
        if not resend.api_key:
            # logging.error("未配置 RESEND_API_KEY，发送取消")
            return

        params = {
            "from": os.getenv("EMAIL_FROM", "Bot <onboarding@resend.dev>"),
            "to": [os.getenv("EMAIL_TO")],
            "subject": f"Knicknack POST - {self.now_date.strftime('%m月%d日')}",
            "html": html_body,
        }
        try:
            resend.Emails.send(params)
            # logging.info("邮件发送成功")
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")


if __name__ == "__main__":
    app = KnicknackPost()
    app.run()