import os
import json
import logging
import smtplib
from datetime import datetime
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.header import Header
from logging.handlers import RotatingFileHandler
from rss_bilibili_news import BilibiliHotSearchParser
from rss_bilibili_dynamic import BilibiliDynamicParser
from rss_batch import RSSBatchParser 
from rss_tldr import TldrParser,TldrLlm
from rss_ruanyifeng import RSSRuanyifengParser
from rss_changelog import ChangelogNightlyParser,ChangelogNightLlm
from rss_infzm import InfzmParser
from email_typography import EmailTypography


class KnicknackPost:
    def __init__(self):
        load_dotenv()
        self.logger=self._setup_logger()
        self.data_dir = "data"
        self.last_time_file = "last_date.json"
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
        if os.path.exists(self.last_time_file):
            with open(self.last_time_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_last_time(self):
        with open(self.last_time_file, 'w') as f:
            json.dump(self.last_time, f, indent=4)

    def _write_data(self, filename, content):
        path = os.path.join(self.data_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            if filename.endswith(".json"):
                json.dump(content, f, ensure_ascii=False, indent=4)
            else:
                f.write(str(content))

    def _setup_logger(self):
        logger = logging.getLogger()   # root logger
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)

        file_handler = RotatingFileHandler(
            "logs/post.log",
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger.addHandler(console)
        logger.addHandler(file_handler)

        return logger

    def run(self):
        self.logger.info("knicknack_post start")

        # 1. BILIBILI 热搜 (无 last_date)
        self.logger.info("获取 Bilibili 热搜...")
        bilibili_news=BilibiliHotSearchParser()
        hot_list = bilibili_news.fetch()
        self._write_data("bilibili_hot.json", hot_list)

        # 2. BILIBILI 动态
        # 假设 .env 中配置了 RSS_BILIBILI_DYN_URL
        self.logger.info("获取 Bilibili 动态...")
        url = os.getenv("RSS_BILIBILI_DYNAMIC")
        UIDS=os.getenv("BILIBILI_USER_ID").split()
        bilibili_dynamic=BilibiliDynamicParser()
        dyn_items = []
        for uid in UIDS:
            url_uid = f"{url}{uid}"+"/hideGoods=1"
            last_date = self.last_time.get(uid, "2026-01-01T00:00:00Z")
            dyn_item, new_date = bilibili_dynamic.parse(last_date, url_uid)
            dyn_items += dyn_item
            self.last_time[uid] = new_date
            self.logger.info(f"{url_uid} - {new_date}")
        self._write_data("bilibili_dynamic.json", dyn_items)
        

        # 3. The Batch 周报
        self.logger.info("获取 The Batch 周报...")
        last_date = self.last_time.get("batch_week", "2026-01-01T00:00:00Z")
        batch_parser = RSSBatchParser()
        week_items, new_date = batch_parser.parse("RSS_BATCH_WEEKLY", last_date)
        self._write_data("batch_week.json", week_items)
        self.last_time["batch_week"] = new_date

        # 4. The Batch Letter
        self.logger.info("获取 The Batch Letter...")
        last_date = self.last_time.get("batch_letter", "2026-01-01T00:00:00Z")
        letter_items, new_date = batch_parser.parse("RSS_BATCH_LETTER", last_date)
        self._write_data("batch_letter.json", letter_items)
        self.last_time["batch_letter"] = new_date

        # 5. TLDR 每日简报 (含 LLM 处理)
        self.logger.info("获取并处理 TLDR 简报...")
        last_date = self.last_time.get("tldr", "2026-01-01T00:00:00Z")
        # 假设 tldr 解析器返回的是一段大文本供 LLM 总结
        tldr_parser = TldrParser()
        raw_tldr_text, new_date = tldr_parser.parse(last_date)
        tlde_llm_summary = TldrLlm()
        if raw_tldr_text:
            tldr_json = tlde_llm_summary.get_structured_summary(raw_tldr_text)
            self._write_data("tldr_list.json", tldr_json)
        self.last_time["tldr"] = new_date

        # 6. 阮一峰周刊
        self.logger.info("获取阮一峰周刊...")
        last_date = self.last_time.get("ruanyifeng", "2026-01-01T00:00:00Z")
        ruanyifeng_parser = RSSRuanyifengParser()
        ruanyi_items, new_date = ruanyifeng_parser.parse(last_date)
        self._write_data("ruanyifeng.json", ruanyi_items)
        self.last_time["ruanyifeng"] = new_date

        # 7. Changelog Nightly (含 LLM 处理)
        self.logger.info("获取并处理 Changelog GitHub 趋势...")
        last_date = self.last_time.get("changelog", "2026-01-01T00:00:00Z")
        # 返回 (list_of_repos, raw_text_for_summary, new_date)
        changelog_parser = ChangelogNightlyParser()
        repo_list, new_date = changelog_parser.parse(last_date)
        self._write_data("changelog_night_list.json", repo_list)
        changelog_llm = ChangelogNightLlm()
        digest = changelog_llm.get_narrative_digest(repo_list)
        self._write_data("changelog_digest.txt", digest)
        self.last_time["changelog"] = new_date

        # 8. 南方周末
        self.logger.info("获取南方周末动态...")
        infzm_parser = InfzmParser()
        infzm_items = infzm_parser.fetch() 
        self._write_data("infzm.json", infzm_items)

        # === 核心：渲染与发送 ===
        self.logger.info("开始渲染邮件排版...")
        email_type=EmailTypography()
        html_content = email_type.render_daily_email()
        
        # 保存一份备份到 data 目录供检查
        self._write_data("daily_report_final.html", html_content)

        self.logger.info("正在发送邮件...")
        self.send_mail(html_content)

        # 任务成功，持久化状态
        self._save_last_time()
        self.logger.info("knicknack_post completed")

    def send_mail(self, html_body):
         # 1. 从环境变量获取配置
        smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        sender = os.getenv("EMAIL_FROM")
        password = os.getenv("SMTP_KEY")
        receiver = os.getenv("EMAIL_TO")

        if not all([sender, password, receiver]):
            logging.error("SMTP 配置不完整，发送取消")
            return

        # 2. 构建邮件对象
        # 注意类型必须是 "html"，编码必须是 "utf-8"
        msg = MIMEText(html_body, "html", "utf-8")
        
        # 设置邮件头
        subject = f"Knicknack POST - {datetime.now().strftime('%m月%d日')}"
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = f"Knicknack POST Agent <{sender}>" # 也可以自定义显示名称
        msg["To"] = receiver

        try:
            # 3. 通过 SSL 连接发送
            # QQ 邮箱 465 端口强制使用 SMTP_SSL
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender, password)
                server.sendmail(sender, [receiver], msg.as_string())
            logging.info("邮件发送成功")
        except Exception as e:
            logging.exception(f"邮件发送失败")


if __name__ == "__main__":
    app = KnicknackPost()
    try:
        app.run()
    except Exception as e:
        app.logger.exception("knicknack_post 异常")