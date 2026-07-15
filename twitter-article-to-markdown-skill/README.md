# Twitter Article To Markdown Skill

这个目录是从 `Windows-Codex-Chrome插件-Twitter-cli抓取推特长文保姆级教程.md` 整理出来的 Codex Skill。

它的用途是：以后你给 Codex 一个 X/Twitter 长文链接，Codex 可以按 `SKILL.md` 的流程检查环境、使用 Cookie 抓取文章，并把 HTML 转成 Markdown。

## 文件说明

```text
twitter-article-to-markdown-skill/
  SKILL.md
  scripts/
    twitter_article_to_md.py
    twitter_article_graphql_to_md.py
  README.md
  examples/
    prompt.md
```

## 默认工作目录

```text
C:\Users\你的用户名\Desktop\twitter-cli
```

默认结构：

```text
twitter-cli/
  cookies/
    twitter_cookies.txt
  downloads/
  markdown/
  scripts/
```

## 手动运行转换脚本

如果已经用 `gallery-dl` 抓取过文章，可以直接运行：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_to_md.py" --root "$env:USERPROFILE\Desktop\twitter-cli" --latest-only
```

如果要写入原文链接：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_to_md.py" --root "$env:USERPROFILE\Desktop\twitter-cli" --source-url "https://x.com/用户名/status/推文ID" --latest-only
```

如果 `gallery-dl` 只下载到图片、没有下载 `.htm` / `.html`，可以使用 GraphQL 回退脚本：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_graphql_to_md.py" "https://x.com/用户名/status/推文ID" --root "$env:USERPROFILE\Desktop\twitter-cli" --save-json
```

GraphQL 回退脚本会处理 X Article 里的内嵌 Markdown 实体，包括：

- Markdown 表格
- fenced code block，例如 bash、json、tsx 代码块
- X Article 正文图片
- 原帖互动数据

如果转换后缺少表格或代码块，优先检查 `downloads\<TWEET_ID>_tweetresult.json` 里的 `content_state.entityMap` 是否存在 `type: "MARKDOWN"`。

## 依赖

```powershell
python -m pip install --upgrade gallery-dl beautifulsoup4 markdownify requests
```

## Cookie

Cookie 文件默认放在：

```text
C:\Users\你的用户名\Desktop\twitter-cli\cookies\twitter_cookies.txt
```

Cookie 是敏感登录凭证，不要公开、不要提交到 GitHub。

## 敏感信息

仓库不应包含真实 Cookie、账号令牌、抓取出的私有 JSON 或个人下载结果。

GraphQL 回退脚本默认会尝试从 X 前端脚本动态发现 guest bearer token；如果 X 页面结构变化，也可以临时在本机设置环境变量：

```powershell
$env:X_GUEST_BEARER_TOKEN = "你的临时 bearer token"
```
