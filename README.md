# Knicknack POST

这是 `post/` 目录下的一个 RSS 聚合、邮件排版与发送项目。它从多源 RSS 读取内容，处理并生成一封 HTML 格式的每日技术简报邮件。
相关技术方案见个人Blog[Knicknack_post分类](https://knicknackqwq.github.io/categories/Knicknack-POST/分类)

## 主要功能

- 采集 Bilibili 实时热搜
- 采集多个 Bilibili 用户动态
- 采集 DeepLearning.AI The Batch 周报与 Letter
- 采集 TLDR 每日简报并通过 LLM 生成结构化总结
- 采集 阮一峰/南方周末 RSS 内容
- 采集 Changelog Nightly GitHub 热门仓库并生成 AI 综述
- 使用 Jinja2 模板渲染 HTML 邮件
- 通过 SMTP 发送邮件

## 项目结构

- `knicknack_post.py` - 主程序入口，负责全流程调度：抓取、数据写入、邮件渲染、发送、状态持久化
- `email_typography.py` - 负责从 `data/` 读取数据并渲染 `templates/email_template.html`
- `rss_bilibili_news.py` - 解析 Bilibili 热搜 RSS
- `rss_bilibili_dynamic.py` - 解析 Bilibili 动态 RSS
- `rss_batch.py` - 解析 The Batch 周报与 Letter RSS
- `rss_tldr.py` - 解析 TLDR RSS，并调用 LLM 生成结构化摘要
- `rss_ruanyifeng.py` - 解析 阮一峰 RSS
- `rss_changelog.py` - 解析 Changelog Nightly 内容并使用 LLM 生成简报
- `rss_infzm.py` - 解析 南方周末 RSS
- `templates/email_template.html` - Jinja2 邮件模板
- `data/` - 中间数据、最终 HTML 与状态文件
- `logs/` - 运行日志文件

## 依赖

建议使用 Python 3.10+。主要依赖如下：

- `feedparser`
- `beautifulsoup4`
- `python-dotenv`
- `python-dateutil`
- `jinja2`
- `openai`

依赖可以通过 `pip install feedparser beautifulsoup4 python-dotenv python-dateutil jinja2 openai` 安装。

## 配置

项目通过 `.env` 文件加载配置。所有配置项包括：

```env
RSS_BILIBILI_DYNAMIC=
BILIBILI_USER_ID=
RSS_BILIBILI_NEWS=
RSS_INFZM=
RSS_BATCH_WEEKLY=
RSS_BATCH_LETTER=
RSS_RUANYIFENG=
RSS_TLDR=
RSS_CHANGELOG_NIGHT=

LLM_URL=
LLM_API_KEY=

SMTP_SERVER=
SMTP_PORT=
EMAIL_FROM=
SMTP_KEY=
EMAIL_TO=
```

### `.env` 示例说明

- `RSS_BILIBILI_DYNAMIC`：Bilibili 动态 RSS 源地址前缀
- `BILIBILI_USER_ID`：需要抓取动态的 Bilibili 用户 ID 列表，空格分隔
- `RSS_BILIBILI_NEWS`：Bilibili 热搜 RSS 地址
- `RSS_INFZM`：南方周末 RSS
- `RSS_BATCH_WEEKLY` / `RSS_BATCH_LETTER`：The Batch RSS 地址
- `RSS_RUANYIFENG`：阮一峰 RSS 地址
- `RSS_TLDR`：TLDR 简报 RSS 地址
- `RSS_CHANGELOG_NIGHT`：Changelog Nightly RSS 地址
- `LLM_URL` / `LLM_API_KEY`：LLM 服务地址与 API 密钥
- `SMTP_SERVER` / `SMTP_PORT`：邮件 SMTP 服务器与端口
- `EMAIL_FROM` / `SMTP_KEY` / `EMAIL_TO`：邮件发送账户、授权码与接收地址

## 运行方式



拉取该项目后，在post/目录下.env文件中填入上述配置
在 `post/` 目录下运行：

```bash
pip install -r requirements.txt
python knicknack_post.py
```

该命令会执行：

1. 获取各源 RSS 数据
2. 写入 `data/` 下的 JSON / TXT 文件
3. 渲染最终 HTML 并写入 `data/daily_report_final.html`
4. 发送邮件
5. 更新 `last_date.json` 记录抓取时间

## 关键流程

1. `knicknack_post.py` 启动并加载 `.env`
2. 每个 RSS 模块按最新更新时间抓取新条目
3. 抓取结果写入 `data/` 目录
4. `EmailTypography.render_daily_email()` 读取数据并渲染邮件模板
5. `knicknack_post.py.send_mail()` 通过 SMTP 发送最终 HTML

## 输出文件说明

- `data/bilibili_hot.json`：Bilibili 热搜列表
- `data/bilibili_dynamic.json`：Bilibili 动态列表
- `data/batch_week.json` / `data/batch_letter.json`：The Batch 内容
- `data/tldr_list.json`：TLDR 结构化摘要
- `data/ruanyifeng.json`：阮一峰文章列表
- `data/changelog_night_list.json`：Changelog Nightly 仓库列表
- `data/changelog_digest.txt`：LLM 生成的 GitHub 趋势简报
- `data/infzm.json`：南方周末内容
- `data/daily_report_final.html`：最终渲染的邮件 HTML
- `last_date.json`：各 RSS 数据源上次抓取时间

## 注意事项

- 当前项目默认使用 `.env` 中的 RSS 地址，部分地址为本地 RSSHub 代理示例
- `openai` 模块用于 DeepSeek API 兼容调用
- `email_template.html` 采用 Jinja2 模板语法，模板控件会渲染 `render_daily_email()` 传入的数据

## 常见调试

- 若邮件未发送，请检查 SMTP 配置是否正确
- 若某 RSS 未返回内容，可在 `data/` 中查看中间文件是否已生成
- 若 LLM 生成失败，可查看 `logs/post.log` 中的异常信息
