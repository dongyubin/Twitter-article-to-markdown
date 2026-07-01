# Twitter Article To Markdown

一个用于 Codex 的 X/Twitter 长文抓取 Skill：在 Windows 环境中配合 `gallery-dl`、Chrome Cookie 和内置转换脚本，把 X Article / 推特长文保存为 Markdown，并整理本地图片 assets。

适合这类需求：

- 把 `x.com/<user>/status/<id>` 长文保存成 Markdown。
- 自动保留标题、作者、原帖链接、点赞、转发、回复、引用、浏览和收藏数。
- 下载文章图片，并放到同名 `.assets` 目录，方便离线阅读。
- 在 Codex / AI 编程助手里作为一个可复用 Skill 使用。

## 内容

- `twitter-article-to-markdown-skill/SKILL.md`：Codex 使用说明。
- `twitter-article-to-markdown-skill/scripts/twitter_article_to_md.py`：将本地 HTML 转成 Markdown。
- `twitter-article-to-markdown-skill/scripts/twitter_article_graphql_to_md.py`：当 `gallery-dl` 只下载图片时，用 GraphQL 回退抓取正文和互动数据。
- `twitter-article-to-markdown-skill/examples/prompt.md`：示例提示词。

## 让 AI 帮你安装

如果你正在使用 Codex、Claude Code 或其他能操作本机终端和文件的 AI 助手，可以直接把下面这段话复制给它：

```text
请帮我在 Windows 上安装这个 Codex Skill：
https://github.com/dongyubin/Twitter-article-to-markdown

要求：
1. 检查我是否安装了 Git、Python 和 pip。
2. 克隆仓库到一个合适的本地目录。
3. 把仓库里的 twitter-article-to-markdown-skill 文件夹复制到 %USERPROFILE%\.codex\skills\twitter-article-to-markdown。
4. 安装依赖：gallery-dl、beautifulsoup4、markdownify、requests。
5. 创建工作目录：%USERPROFILE%\Desktop\twitter-cli，并在里面创建 cookies、downloads、markdown 三个目录。
6. 不要读取、打印、提交或上传我的 Cookie、token、抓取 JSON、下载图片和生成的 Markdown。
7. 安装完成后，用一个 x.com/status 链接测试命令是否能正常启动，但不要擅自发布任何内容。
```

安装完成后，新开一个 Codex 会话，对它说：

```text
使用 twitter-article-to-markdown skill，帮我抓取这个 X/Twitter 长文并保存为 Markdown：
https://x.com/用户名/status/推文ID
```

## 手动安装

### 1. 克隆仓库

```powershell
cd "$env:USERPROFILE\Desktop"
git clone https://github.com/dongyubin/Twitter-article-to-markdown.git
cd .\Twitter-article-to-markdown
```

### 2. 安装为 Codex Skill

```powershell
$skillRoot = Join-Path $env:USERPROFILE ".codex\skills\twitter-article-to-markdown"
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
Copy-Item -Recurse -Force ".\twitter-article-to-markdown-skill\*" $skillRoot
```

目录最终应该类似这样：

```text
C:\Users\你的用户名\.codex\skills\twitter-article-to-markdown\
  SKILL.md
  README.md
  examples\
  scripts\
```

### 3. 安装 Python 依赖

```powershell
python -m pip install --upgrade pip
python -m pip install --upgrade gallery-dl beautifulsoup4 markdownify requests
python -m gallery_dl --version
```

如果 `python` 不可用，先安装 Python for Windows，并勾选 `Add python.exe to PATH`。

### 4. 创建工作目录

```powershell
$root = Join-Path $env:USERPROFILE "Desktop\twitter-cli"
New-Item -ItemType Directory -Force -Path $root | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "cookies") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "downloads") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "markdown") | Out-Null
```

默认输出位置：

```text
C:\Users\你的用户名\Desktop\twitter-cli\markdown
```

## Cookie 准备

有些 X/Twitter 内容需要登录态才能访问。推荐方式：

1. 用 Chrome 打开 `https://x.com` 并确认已登录。
2. 安装 Chrome 插件 `Get cookies.txt LOCALLY` [Chrome插件地址](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)、[Github源码地址](https://github.com/kairi003/Get-cookies.txt-LOCALLY)。
3. 在 `x.com` 页面导出 Cookie。
4. 保存为：

```text
C:\Users\你的用户名\Desktop\twitter-cli\cookies\twitter_cookies.txt
```

Cookie 是登录凭证，只能保存在本机。不要发给别人，不要提交到 GitHub，不要让 AI 在回复里打印 Cookie 内容。

## 使用方法

### 方法一：在 Codex 里使用 Skill

安装后，直接给 Codex 这类提示：

```text
使用 twitter-article-to-markdown skill，帮我抓取这个 X/Twitter 长文并保存为 Markdown：
https://x.com/用户名/status/推文ID
```

如果你希望保存互动数据，也可以明确说：

```text
抓取正文、图片、点赞、转发、回复、引用、浏览和收藏数，并保存到 Markdown 开头。
```

### 方法二：手动运行脚本

先用 `gallery-dl` 下载媒体和元数据：

```powershell
$url = "https://x.com/用户名/status/推文ID"
$root = Join-Path $env:USERPROFILE "Desktop\twitter-cli"
python -m gallery_dl --cookies "$root\cookies\twitter_cookies.txt" --directory "$root\downloads" $url
python -m gallery_dl -j $url | Set-Content -LiteralPath "$root\downloads\推文ID_gallery.json" -Encoding UTF8
```

如果 `gallery-dl` 下载到了 `.htm` / `.html`，运行 HTML 转 Markdown：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_to_md.py" --root "$env:USERPROFILE\Desktop\twitter-cli" --source-url $url --latest-only
```

如果 `gallery-dl` 只下载到图片、没有 HTML，运行 GraphQL 回退脚本：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_graphql_to_md.py" $url --root "$env:USERPROFILE\Desktop\twitter-cli" --save-json
```

生成结果通常在：

```text
C:\Users\你的用户名\Desktop\twitter-cli\markdown\文章标题-推文ID.md
C:\Users\你的用户名\Desktop\twitter-cli\markdown\文章标题-推文ID.assets\
```

## 常见问题

### Codex 没有识别到 Skill

确认 `SKILL.md` 在这个目录下：

```text
C:\Users\你的用户名\.codex\skills\twitter-article-to-markdown\SKILL.md
```

然后重启 Codex 或开启新会话。

### `python` 命令不可用

安装 Python for Windows，并勾选 `Add python.exe to PATH`。也可以尝试：

```powershell
py --version
```

### `gallery-dl` 返回 401 或 403

通常是 Cookie 失效、导出错域名，或者账号没有权限访问该内容。重新登录 `x.com`，再导出 `x.com` Cookie 覆盖：

```text
Desktop\twitter-cli\cookies\twitter_cookies.txt
```

### 只下载图片，没有正文

这属于常见情况。使用 GraphQL 回退脚本：

```powershell
python ".\twitter-article-to-markdown-skill\scripts\twitter_article_graphql_to_md.py" "https://x.com/用户名/status/推文ID" --root "$env:USERPROFILE\Desktop\twitter-cli" --save-json
```

### 不想导出 Cookie

可以先尝试不用 Cookie 的 GraphQL 回退脚本。公开内容有时可以抓取，但受 X 页面结构和访问限制影响，不保证稳定。

## 安全

不要提交真实 Cookie、账号 token、抓取出的 JSON、下载图片或生成的 Markdown。仓库已通过 `.gitignore` 默认排除这些本地数据。

本仓库只应包含 Skill 源码和使用说明，不应包含个人登录态或抓取结果。
