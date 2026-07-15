---
name: twitter-article-to-markdown
description: 在 Windows/Codex 环境中抓取 X/Twitter 长文并保存为 Markdown。用于用户给出 x.com/twitter.com 推文链接、X Article 链接，或提出“抓取推特长文”“保存 X 长文为 md”“Twitter-cli 抓文章”“用 Cookie 抓取推特文章”等需求时；默认使用 Chrome 导出的 cookies.txt、gallery-dl 和本 skill 内置转换脚本完成抓取、转换、整理。
---

# Twitter Article To Markdown

## 目标

把 X/Twitter 长文保存为本地 Markdown 文件。默认流程：

1. 检查 Windows 上的 Python。
2. 检查或安装 `gallery-dl`、`beautifulsoup4`、`markdownify`。
3. 检查 Chrome 插件导出的 Cookie 文件。
4. 使用 Cookie 抓取 X/Twitter 链接。
5. 将下载到的 HTML 转换成 Markdown。
6. 将文章图片复制到同名 `.assets` 目录，尽量保持 Markdown 可离线阅读。

## 何时使用

当用户出现以下意图时启用：

- “抓取这个 X 长文”
- “把这篇推特长文保存成 Markdown”
- “用 Twitter-cli 保存推文文章”
- “用 Chrome Cookie 抓 X Article”
- “帮我把 x.com/.../status/... 转成 md”
- “把 x.com/i/article/... 下载下来”

如果用户只是问概念、教程或排错，不要直接抓取，先解释或检查。

## 默认目录

在 Windows 上优先使用：

```text
%USERPROFILE%\Desktop\twitter-cli
```

目录结构：

```text
twitter-cli/
  cookies/
    twitter_cookies.txt
  downloads/
  markdown/
  scripts/
```

如果当前 workspace 已经有用户指定目录，优先使用用户指定目录。

## 输入

至少需要一个 X/Twitter 链接：

```text
https://x.com/<username>/status/<tweet_id>
https://twitter.com/<username>/status/<tweet_id>
https://x.com/i/article/<article_id>
```

可选输入：

- Cookie 文件路径
- 输出目录
- 是否只转换最新下载的 HTML
- 是否清洗已有 HTML，不重新抓取

## 安全规则

Cookie 是登录凭证，必须当作敏感文件处理：

- 不要在最终回复中展示 Cookie 内容。
- 不要把 Cookie 复制到 Markdown 正文、日志、README 或公开文件里。
- 不要提交 Cookie 文件。
- 如果 Cookie 缺失或过期，引导用户用 Chrome 插件 `Get cookies.txt LOCALLY` 重新导出。

## 工作流

### 1. 建立工作目录

在 PowerShell 中执行：

```powershell
$root = Join-Path $env:USERPROFILE "Desktop\twitter-cli"
New-Item -ItemType Directory -Force -Path $root | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "cookies") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "downloads") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "markdown") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "scripts") | Out-Null
```

### 2. 检查 Python

优先执行：

```powershell
python --version
```

如果失败，尝试：

```powershell
py --version
```

后续命令根据可用情况使用 `python` 或 `py`。如果两者都不可用，告诉用户安装 Python，并勾选 `Add python.exe to PATH`。

### 3. 安装依赖

使用模块方式安装，避免 Windows PATH 问题：

```powershell
python -m pip install --upgrade pip
python -m pip install --upgrade gallery-dl beautifulsoup4 markdownify requests
```

验证：

```powershell
python -m gallery_dl --version
```

不要依赖裸命令 `gallery-dl`，Windows 上它经常不在 PATH 中。

### 4. 检查 Cookie

默认 Cookie 路径：

```text
%USERPROFILE%\Desktop\twitter-cli\cookies\twitter_cookies.txt
```

检查：

```powershell
Get-ChildItem "$env:USERPROFILE\Desktop\twitter-cli\cookies\twitter_cookies.txt"
```

如果不存在，提示用户：

1. Chrome 打开 `https://x.com` 并确认已登录。
2. 安装或打开 `Get cookies.txt LOCALLY`。
3. 导出 x.com Cookie。
4. 保存为 `twitter_cookies.txt`。
5. 放到 `Desktop\twitter-cli\cookies\`。

### 5. 抓取链接

将用户给出的 URL 放入命令：

```powershell
python -m gallery_dl --cookies "$env:USERPROFILE\Desktop\twitter-cli\cookies\twitter_cookies.txt" --directory "$env:USERPROFILE\Desktop\twitter-cli\downloads" "<X_OR_TWITTER_URL>"
```

如果用户给的是多个链接，逐个执行。不要并发抓取 X/Twitter，避免触发限制。

### 6. 转换 Markdown

使用本 skill 的脚本：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_to_md.py" --root "$env:USERPROFILE\Desktop\twitter-cli" --source-url "<X_OR_TWITTER_URL>"
```

如果在 skill 目录外调用，使用脚本的绝对路径。

如果 `gallery-dl` 只下载了图片，没有下载 `.htm` / `.html`，说明这类 X Article 正文没有走 HTML 下载。改用 GraphQL 回退脚本：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_graphql_to_md.py" "<X_OR_TWITTER_URL>" --root "$env:USERPROFILE\Desktop\twitter-cli" --save-json
```

GraphQL 回退脚本不会在仓库里保存固定 token。它会优先读取本机环境变量 `X_GUEST_BEARER_TOKEN`，没有设置时再尝试从 X 前端脚本动态发现 guest bearer token。

GraphQL 回退脚本必须保留 X Article 内嵌的 `MARKDOWN` 实体。这类实体通常承载表格和 fenced code block，例如 `bash`、`json`、`tsx`、`text` 代码块。转换完成后，应校验 Markdown 中是否存在原文表格和代码围栏，不要只检查正文段落和图片。

如果已经用 `gallery-dl` 下载过图片，先保存一份媒体元数据，GraphQL 脚本会优先把图片映射成本地 assets 文件：

```powershell
python -m gallery_dl -j "<X_OR_TWITTER_URL>" > "$env:USERPROFILE\Desktop\twitter-cli\downloads\<TWEET_ID>_gallery.json"
```

脚本默认：

- 从 `downloads` 查找 `.htm` / `.html`。
- 输出到 `markdown`。
- 为每篇文章创建同名 `.assets` 目录。
- 复制同目录下与文章 ID 相关的图片。
- 生成带 front matter 的 Markdown。
- 保留 X Article 中的表格、代码块等内嵌 Markdown 内容。

### 7. 交付结果

最终回复中说明：

- Markdown 文件路径
- 图片目录路径
- 是否成功抓取
- 如果失败，失败原因和下一步

不要长篇复述教程。

## 常见故障处理

### 找不到 Python

让用户安装 Python for Windows，并勾选 `Add python.exe to PATH`。也可以尝试 `py`。

### 找不到 gallery-dl

使用：

```powershell
python -m gallery_dl
```

不要要求用户必须配置 PATH。

### 401、403、需要登录

通常是 Cookie 失效或导出错域名。让用户重新在 Chrome 登录 `x.com`，导出 `x.com` Cookie，覆盖 `twitter_cookies.txt`。

### 没有 HTML 文件

可能原因：

- 链接不是长文 Article。
- 该内容需要更高权限。
- Cookie 失效。
- X/Twitter 页面结构变化。

建议先用浏览器确认文章能正常打开，再重新导出 Cookie。如果 `gallery-dl --list-keywords` 能看到 `article['id']`、`article['title']`，但下载目录里只有图片，使用 `twitter_article_graphql_to_md.py` 回退脚本抓取正文。

### Markdown 很乱

继续清洗 Markdown：删除按钮文字、导航残留、重复链接和空行，保留标题、作者、正文和图片。必要时根据具体 HTML 结构修改脚本。

### 表格或代码块丢失

X Article 的表格和代码块常被放在 `content_state.entityMap` 的 `MARKDOWN` 实体里，而不是普通段落 block。处理 GraphQL JSON 时必须读取 atomic block 的 entity，并把 `entity["data"]["markdown"]` 原样写入 Markdown。若转换后缺少表格或代码块，检查：

```powershell
Select-String "$env:USERPROFILE\Desktop\twitter-cli\downloads\<TWEET_ID>_tweetresult.json" -Pattern '"type": "MARKDOWN"'
```

如果 JSON 中存在 `MARKDOWN` 实体但输出文件没有表格或代码围栏，说明转换脚本存在回归，需要修复 `twitter_article_graphql_to_md.py` 的 atomic entity 处理逻辑。

## 输出口径

成功时简短汇报：

```text
已抓取并转换完成：
Markdown: <path>
Assets: <path>
```

失败时直接给可执行修复：

```text
这次卡在 Cookie 登录状态：gallery-dl 返回 403。请重新用 Chrome 插件导出 x.com Cookie，覆盖 cookies\twitter_cookies.txt，然后我继续跑同一条命令。
```
