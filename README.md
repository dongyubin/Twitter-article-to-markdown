# Twitter Article To Markdown

一个用于 Codex 的 X/Twitter 长文抓取 Skill：在 Windows 环境中配合 `gallery-dl`、Chrome Cookie 和内置转换脚本，把 X Article / 推特长文保存为 Markdown，并整理本地图片 assets。

## 内容

- `twitter-article-to-markdown-skill/SKILL.md`：Codex 使用说明。
- `twitter-article-to-markdown-skill/scripts/twitter_article_to_md.py`：将本地 HTML 转成 Markdown。
- `twitter-article-to-markdown-skill/scripts/twitter_article_graphql_to_md.py`：当 `gallery-dl` 只下载图片时，用 GraphQL 回退抓取正文和互动数据。
- `twitter-article-to-markdown-skill/examples/prompt.md`：示例提示词。

## 安全

不要提交真实 Cookie、账号 token、抓取出的 JSON、下载图片或生成的 Markdown。仓库已通过 `.gitignore` 默认排除这些本地数据。
